"""
Analytics service for computing derived metrics and aggregations
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Dict, Optional, Tuple
from datetime import date, timedelta
from app.models import (
    Match, Player, MetricDefinition, TeamMatchMetricValue, PlayerMatchMetricValue,
    MetricScope, MetricSide, MatchPlayerParticipation
)

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def _get_metric_by_slug(self, slug: str) -> Optional[MetricDefinition]:
        """Get metric definition by slug"""
        return self.db.query(MetricDefinition).filter_by(slug=slug).first()

    def _get_team_metric_value(self, match_id: int, metric_slug: str, side: MetricSide) -> float:
        """Get stored team metric value"""
        metric = self._get_metric_by_slug(metric_slug)
        if not metric:
            return 0.0

        value = self.db.query(TeamMatchMetricValue).filter(
            and_(
                TeamMatchMetricValue.match_id == match_id,
                TeamMatchMetricValue.metric_id == metric.id,
                TeamMatchMetricValue.side == side
            )
        ).first()

        return value.value_number if value else 0.0

    def _get_player_metric_value(self, match_id: int, player_id: int, metric_slug: str) -> float:
        """Get stored player metric value"""
        metric = self._get_metric_by_slug(metric_slug)
        if not metric:
            return 0.0

        value = self.db.query(PlayerMatchMetricValue).filter(
            and_(
                PlayerMatchMetricValue.match_id == match_id,
                PlayerMatchMetricValue.player_id == player_id,
                PlayerMatchMetricValue.metric_id == metric.id
            )
        ).first()

        return value.value_number if value else 0.0

    def compute_team_derived_metric(self, match_id: int, metric_slug: str) -> float:
        """Compute derived team metric on the fly"""
        match = self.db.query(Match).get(match_id)
        if not match:
            return 0.0

        if metric_slug == "team_attempts":
            goals = self._get_team_metric_value(match_id, "team_goals_scored", MetricSide.OWN)
            shots = self._get_team_metric_value(match_id, "team_shots", MetricSide.OWN)
            return goals + shots

        elif metric_slug == "team_conversion_rate":
            attempts = self.compute_team_derived_metric(match_id, "team_attempts")
            if attempts == 0:
                return 0.0
            goals = self._get_team_metric_value(match_id, "team_goals_scored", MetricSide.OWN)
            return (goals / attempts) * 100

        elif metric_slug == "team_attempts_conceded":
            goals = self._get_team_metric_value(match_id, "team_goals_conceded", MetricSide.OPPONENT)
            shots = self._get_team_metric_value(match_id, "team_shots_conceded", MetricSide.OPPONENT)
            return goals + shots

        elif metric_slug == "team_offensive_events":
            goals = self._get_team_metric_value(match_id, "team_goals_scored", MetricSide.OWN)
            corners = self._get_team_metric_value(match_id, "team_corners", MetricSide.OWN)
            free_kicks = self._get_team_metric_value(match_id, "team_free_kicks", MetricSide.OWN)
            shots = self._get_team_metric_value(match_id, "team_shots", MetricSide.OWN)
            return goals + corners + free_kicks + shots

        elif metric_slug == "team_defensive_events":
            goals = self._get_team_metric_value(match_id, "team_goals_conceded", MetricSide.OPPONENT)
            shots = self._get_team_metric_value(match_id, "team_shots_conceded", MetricSide.OPPONENT)
            return goals + shots

        return 0.0

    def compute_player_derived_metric(self, match_id: int, player_id: int, metric_slug: str) -> float:
        """Compute derived player metric on the fly"""
        if metric_slug == "player_attempts":
            goals = self._get_player_metric_value(match_id, player_id, "player_goals")
            shots = self._get_player_metric_value(match_id, player_id, "player_shots")
            return goals + shots

        elif metric_slug == "player_conversion_rate":
            attempts = self.compute_player_derived_metric(match_id, player_id, "player_attempts")
            if attempts == 0:
                return 0.0
            goals = self._get_player_metric_value(match_id, player_id, "player_goals")
            return (goals / attempts) * 100

        elif metric_slug == "player_goal_involvements":
            goals = self._get_player_metric_value(match_id, player_id, "player_goals")
            assists = self._get_player_metric_value(match_id, player_id, "player_goal_assists")
            return goals + assists

        return 0.0

    def get_team_kpis(
        self,
        team_id: int,
        metric_slugs: List[str],
        season_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        compute_delta: bool = False
    ) -> List[Dict]:
        """Compute aggregated KPIs for team"""
        # Build query for matches
        query = self.db.query(Match).filter(Match.team_id == team_id)

        if season_id:
            query = query.filter(Match.season_id == season_id)
        if date_from:
            query = query.filter(Match.date >= date_from)
        if date_to:
            query = query.filter(Match.date <= date_to)

        matches = query.all()
        match_ids = [m.id for m in matches]

        if not match_ids:
            return []

        results = []
        for slug in metric_slugs:
            metric_def = self._get_metric_by_slug(slug)
            if not metric_def:
                continue

            # Compute aggregate value
            if metric_def.is_derived:
                # Sum derived values across matches
                total = sum(self.compute_team_derived_metric(mid, slug) for mid in match_ids)
                # Average for rates/percentages
                if metric_def.datatype.value == "PERCENT":
                    value = total / len(match_ids) if match_ids else 0
                else:
                    value = total
            else:
                # Query stored values
                values = self.db.query(func.sum(TeamMatchMetricValue.value_number)).filter(
                    and_(
                        TeamMatchMetricValue.match_id.in_(match_ids),
                        TeamMatchMetricValue.metric_id == metric_def.id,
                        TeamMatchMetricValue.side == metric_def.side
                    )
                ).scalar()

                # Average for percentages
                if metric_def.datatype.value == "PERCENT":
                    avg = self.db.query(func.avg(TeamMatchMetricValue.value_number)).filter(
                        and_(
                            TeamMatchMetricValue.match_id.in_(match_ids),
                            TeamMatchMetricValue.metric_id == metric_def.id,
                            TeamMatchMetricValue.side == metric_def.side
                        )
                    ).scalar()
                    value = float(avg) if avg else 0.0
                else:
                    value = float(values) if values else 0.0

            delta = None
            if compute_delta and date_from and date_to:
                # Compute previous period delta
                period_days = (date_to - date_from).days
                prev_from = date_from - timedelta(days=period_days)
                prev_to = date_from - timedelta(days=1)

                prev_kpis = self.get_team_kpis(
                    team_id, [slug], season_id, prev_from, prev_to, compute_delta=False
                )
                if prev_kpis:
                    prev_value = prev_kpis[0]["value"]
                    if prev_value > 0:
                        delta = ((value - prev_value) / prev_value) * 100

            results.append({
                "metric_slug": slug,
                "metric_label": metric_def.label_fr,
                "value": round(value, 2),
                "unit": metric_def.unit,
                "delta": round(delta, 2) if delta is not None else None
            })

        return results

    def get_team_timeseries(
        self,
        team_id: int,
        metric_slug: str,
        last_n: int = 10
    ) -> List[Dict]:
        """Get time series data for a metric"""
        metric_def = self._get_metric_by_slug(metric_slug)
        if not metric_def:
            return []

        matches = self.db.query(Match).filter(
            Match.team_id == team_id
        ).order_by(Match.date.desc()).limit(last_n).all()

        matches = list(reversed(matches))  # Chronological order

        data = []
        for match in matches:
            if metric_def.is_derived:
                value = self.compute_team_derived_metric(match.id, metric_slug)
            else:
                value = self._get_team_metric_value(match.id, metric_slug, metric_def.side)

            data.append({
                "match_id": match.id,
                "match_date": match.date,
                "opponent_name": match.opponent_name,
                "value": round(value, 2)
            })

        return {
            "metric_slug": metric_slug,
            "metric_label": metric_def.label_fr,
            "unit": metric_def.unit,
            "data": data
        }

    def get_team_radar(
        self,
        team_id: int,
        metric_slugs: List[str],
        date_from_a: date,
        date_to_a: date,
        date_from_b: date,
        date_to_b: date
    ) -> Dict:
        """Compare two time periods on multiple metrics (radar chart)"""
        kpis_a = self.get_team_kpis(team_id, metric_slugs, None, date_from_a, date_to_a, False)
        kpis_b = self.get_team_kpis(team_id, metric_slugs, None, date_from_b, date_to_b, False)

        metrics_map_a = {k["metric_slug"]: k["value"] for k in kpis_a}
        metrics_map_b = {k["metric_slug"]: k["value"] for k in kpis_b}

        metrics = []
        for slug in metric_slugs:
            metric_def = self._get_metric_by_slug(slug)
            if not metric_def:
                continue

            metrics.append({
                "metric_slug": slug,
                "metric_label": metric_def.label_fr,
                "value_a": metrics_map_a.get(slug, 0.0),
                "value_b": metrics_map_b.get(slug, 0.0),
                "unit": metric_def.unit
            })

        return {
            "label_a": f"{date_from_a} to {date_to_a}",
            "label_b": f"{date_from_b} to {date_to_b}",
            "metrics": metrics
        }

    def get_player_leaderboard(
        self,
        team_id: int,
        metric_slug: str,
        season_id: Optional[int] = None,
        top_n: int = 10
    ) -> Dict:
        """Get top players for a metric"""
        metric_def = self._get_metric_by_slug(metric_slug)
        if not metric_def or metric_def.scope != MetricScope.PLAYER:
            return {"metric_slug": metric_slug, "entries": []}

        # Get matches for filtering
        query = self.db.query(Match).filter(Match.team_id == team_id)
        if season_id:
            query = query.filter(Match.season_id == season_id)
        matches = query.all()
        match_ids = [m.id for m in matches]

        if not match_ids:
            return {"metric_slug": metric_slug, "entries": []}

        # Get all players
        players = self.db.query(Player).filter(Player.team_id == team_id).all()

        leaderboard = []
        for player in players:
            # Count matches played
            matches_played = self.db.query(MatchPlayerParticipation).filter(
                and_(
                    MatchPlayerParticipation.player_id == player.id,
                    MatchPlayerParticipation.match_id.in_(match_ids)
                )
            ).count()

            if matches_played == 0:
                continue

            # Compute total value
            if metric_def.is_derived:
                total = sum(
                    self.compute_player_derived_metric(mid, player.id, metric_slug)
                    for mid in match_ids
                )
            else:
                total_query = self.db.query(func.sum(PlayerMatchMetricValue.value_number)).filter(
                    and_(
                        PlayerMatchMetricValue.player_id == player.id,
                        PlayerMatchMetricValue.match_id.in_(match_ids),
                        PlayerMatchMetricValue.metric_id == metric_def.id
                    )
                ).scalar()
                total = float(total_query) if total_query else 0.0

            leaderboard.append({
                "player_id": player.id,
                "player_name": f"{player.first_name} {player.last_name}",
                "value": round(total, 2),
                "matches_played": matches_played
            })

        # Sort by value descending
        leaderboard.sort(key=lambda x: x["value"], reverse=True)

        return {
            "metric_slug": metric_slug,
            "metric_label": metric_def.label_fr,
            "unit": metric_def.unit,
            "entries": leaderboard[:top_n]
        }

    def compute_team_win_rate(
        self,
        team_id: int,
        season_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> float:
        """Compute win rate for team"""
        query = self.db.query(Match).filter(Match.team_id == team_id)

        if season_id:
            query = query.filter(Match.season_id == season_id)
        if date_from:
            query = query.filter(Match.date >= date_from)
        if date_to:
            query = query.filter(Match.date <= date_to)

        matches = query.all()
        if not matches:
            return 0.0

        wins = sum(1 for m in matches if m.score_for and m.score_against and m.score_for > m.score_against)
        return (wins / len(matches)) * 100
