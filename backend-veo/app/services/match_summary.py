"""
Match summary service.

This module implements the backend aggregation for the
`GET /matches/{match_id}/summary` endpoint.

Design goals:
- Single payload for match + participations + team metrics + player metrics (grid).
- No N+1 queries (explicit joins).
- No derived computations (raw values only).
- Frontend-friendly structure (Excel-like grid).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models import (
    Match,
    MatchPlayerParticipation,
    MetricDefinition,
    MetricScope,
    MetricSide,
    Player,
    PlayerMatchMetricValue,
    TeamMatchMetricValue,
)
from app.schemas.summary import (
    MatchSummaryMatch,
    MatchSummaryResponse,
    ParticipationWithPlayer,
    PlayerGridColumn,
    PlayerGridPlayer,
    PlayerMetricsGrid,
    TeamMetricCell,
    TeamMetricsBlock,
)


class MatchSummaryService:
    """Service responsible for building the match summary payload."""

    def __init__(self, db: Session) -> None:
        """
        Initialize the service.

        Args:
            db: SQLAlchemy session.
        """
        self.db = db

    def get_match_summary(self, match_id: int) -> MatchSummaryResponse:
        """
        Build the full match summary payload for a given match.

        This performs a small set of optimized queries (no N+1) to gather:
        - match info (including VEO metadata)
        - participations enriched with player identity
        - team metrics split by OWN / OPPONENT
        - player metrics as an Excel-like grid

        Args:
            match_id: Match identifier.

        Returns:
            A MatchSummaryResponse object.

        Raises:
            ValueError: If the match does not exist.
        """
        match = self._get_match_or_raise(match_id)
        participations = self._get_participations_with_players(match_id)
        team_metrics = self._get_team_metrics(match_id)
        player_grid = self._get_player_metrics_grid(match_id)

        return MatchSummaryResponse(
            match=self._map_match(match),
            participations=participations,
            team_metrics=team_metrics,
            player_metrics=player_grid,
        )

    # ---------------------------------------------------------------------
    # Queries
    # ---------------------------------------------------------------------

    def _get_match_or_raise(self, match_id: int) -> Match:
        """Fetch a match by ID or raise.

        Args:
            match_id: Match identifier.

        Returns:
            Match ORM object.

        Raises:
            ValueError: If match does not exist.
        """
        match = self.db.query(Match).get(match_id)
        if not match:
            raise ValueError("Match not found")
        return match

    def _get_participations_with_players(
        self, match_id: int
    ) -> List[ParticipationWithPlayer]:
        """
        Fetch participations for a match enriched with player identity.

        This uses a join between match_player_participations and players.

        Args:
            match_id: Match identifier.

        Returns:
            List of ParticipationWithPlayer objects.
        """
        rows: List[Tuple[MatchPlayerParticipation, Player]] = (
            self.db.query(MatchPlayerParticipation, Player)
            .join(Player, MatchPlayerParticipation.player_id == Player.id)
            .filter(MatchPlayerParticipation.match_id == match_id)
            .order_by(Player.last_name.asc(), Player.first_name.asc())
            .all()
        )

        result: List[ParticipationWithPlayer] = []
        for part, player in rows:
            result.append(
                ParticipationWithPlayer(
                    player_id=player.id,
                    player_name=f"{player.first_name} {player.last_name}",
                    main_position=player.main_position,
                    is_starter=bool(part.is_starter),
                    is_captain=bool(part.is_captain),
                    minutes_played=part.minutes_played,
                    position_played=part.position_played,
                )
            )
        return result

    def _get_team_metrics(self, match_id: int) -> TeamMetricsBlock:
        """
        Fetch all raw team metrics for a match, split by side.

        Args:
            match_id: Match identifier.

        Returns:
            TeamMetricsBlock with OWN and OPPONENT lists.
        """
        rows: List[Tuple[TeamMatchMetricValue, MetricDefinition]] = (
            self.db.query(TeamMatchMetricValue, MetricDefinition)
            .join(
                MetricDefinition, TeamMatchMetricValue.metric_id == MetricDefinition.id
            )
            .filter(TeamMatchMetricValue.match_id == match_id)
            .order_by(MetricDefinition.category.asc(), MetricDefinition.slug.asc())
            .all()
        )

        own: List[TeamMetricCell] = []
        opp: List[TeamMetricCell] = []

        for value, metric in rows:
            cell = TeamMetricCell(
                metric_slug=metric.slug,
                metric_label=metric.label_fr,
                side=value.side,
                value=float(value.value_number),
                unit=metric.unit,
            )
            if value.side == MetricSide.OWN:
                own.append(cell)
            elif value.side == MetricSide.OPPONENT:
                opp.append(cell)
            else:
                # Team metrics should not be NONE, but keep safe behavior.
                own.append(cell)

        return TeamMetricsBlock(OWN=own, OPPONENT=opp)

    def _get_player_metrics_grid(self, match_id: int) -> PlayerMetricsGrid:
        """
        Fetch all raw player metrics for a match and build an Excel-like grid.

        The grid structure is:
        - players (rows)
        - columns (metric definitions)
        - values: {player_id(str): {metric_slug: value_or_null}}

        Args:
            match_id: Match identifier.

        Returns:
            PlayerMetricsGrid object.
        """
        # Fetch all player metric values for this match with joins
        rows: List[Tuple[PlayerMatchMetricValue, MetricDefinition, Player]] = (
            self.db.query(PlayerMatchMetricValue, MetricDefinition, Player)
            .join(
                MetricDefinition,
                PlayerMatchMetricValue.metric_id == MetricDefinition.id,
            )
            .join(Player, PlayerMatchMetricValue.player_id == Player.id)
            .filter(PlayerMatchMetricValue.match_id == match_id)
            .order_by(
                Player.last_name.asc(),
                Player.first_name.asc(),
                MetricDefinition.slug.asc(),
            )
            .all()
        )

        # Build unique players and columns (metrics)
        player_map: Dict[int, PlayerGridPlayer] = {}
        col_map: Dict[str, PlayerGridColumn] = {}

        # values[player_id_str][metric_slug] = value
        values: Dict[str, Dict[str, Optional[float]]] = {}

        for value, metric, player in rows:
            # players
            if player.id not in player_map:
                player_map[player.id] = PlayerGridPlayer(
                    id=player.id,
                    name=f"{player.first_name} {player.last_name}",
                    main_position=player.main_position,
                )
                values[str(player.id)] = {}

            # columns (player scope only)
            if metric.slug not in col_map:
                col_map[metric.slug] = PlayerGridColumn(
                    slug=metric.slug,
                    label=metric.label_fr,
                    unit=metric.unit,
                    category=(
                        metric.category.value
                        if hasattr(metric.category, "value")
                        else str(metric.category)
                    ),
                )

            values[str(player.id)][metric.slug] = float(value.value_number)

        # Sort players and columns for stable frontend rendering
        players_sorted = sorted(player_map.values(), key=lambda p: p.name.lower())
        columns_sorted = sorted(col_map.values(), key=lambda c: c.slug)

        # Fill missing metrics with null for each player (important for grid)
        for p in players_sorted:
            pid = str(p.id)
            if pid not in values:
                values[pid] = {}
            for col in columns_sorted:
                values[pid].setdefault(col.slug, None)

        return PlayerMetricsGrid(
            players=players_sorted,
            columns=columns_sorted,
            values=values,
        )

    # ---------------------------------------------------------------------
    # Mapping helpers
    # ---------------------------------------------------------------------

    @staticmethod
    def _map_match(match: Match) -> MatchSummaryMatch:
        """
        Map Match ORM object to MatchSummaryMatch schema.

        Args:
            match: Match ORM object.

        Returns:
            MatchSummaryMatch schema object.
        """
        return MatchSummaryMatch(
            id=match.id,
            team_id=match.team_id,
            season_id=match.season_id,
            date=match.date,
            opponent_name=match.opponent_name,
            is_home=bool(match.is_home),
            match_type=(
                match.match_type.value
                if hasattr(match.match_type, "value")
                else str(match.match_type)
            ),
            competition=match.competition,
            score_for=match.score_for,
            score_against=match.score_against,
            veo_title=match.veo_title,
            veo_url=match.veo_url,
            veo_duration=match.veo_duration,
            veo_camera=match.veo_camera,
        )
