"""
Seed script for MetricDefinition data
Run with: python -m app.seed
"""
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.models import MetricDefinition, MetricScope, MetricCategory, MetricDataType, MetricSide, Base

PLAYER_METRICS = [
    # GENERAL
    {
        "slug": "player_matches",
        "label_fr": "Matchs",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.GENERAL,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    {
        "slug": "player_starts",
        "label_fr": "Titulaire",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.GENERAL,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    {
        "slug": "player_captaincies",
        "label_fr": "Capitanats",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.GENERAL,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    {
        "slug": "player_motm",
        "label_fr": "Meilleur joueur du match",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.GENERAL,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    # EVENTS
    {
        "slug": "player_total_events",
        "label_fr": "Nombre total d'événements",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    {
        "slug": "player_goals",
        "label_fr": "Buts",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    {
        "slug": "player_shots",
        "label_fr": "Tirs",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    {
        "slug": "player_corners",
        "label_fr": "Corners",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    {
        "slug": "player_free_kicks",
        "label_fr": "Coups francs",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    {
        "slug": "player_goal_kicks",
        "label_fr": "Coups de pied de but",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    {
        "slug": "player_penalties",
        "label_fr": "Penaltys",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    {
        "slug": "player_goal_assists",
        "label_fr": "Goal assists",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    {
        "slug": "player_throw_ins",
        "label_fr": "Throw-ins",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": False,
    },
    # COMBINATIONS (DERIVED)
    {
        "slug": "player_attempts",
        "label_fr": "Nombre de tentatives",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.COMBINATIONS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": True,
        "formula": "goals + shots",
    },
    {
        "slug": "player_conversion_rate",
        "label_fr": "Taux de conversion",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.COMBINATIONS,
        "datatype": MetricDataType.PERCENT,
        "unit": "%",
        "side": MetricSide.NONE,
        "is_derived": True,
        "formula": "goals / attempts * 100",
    },
    {
        "slug": "player_goal_involvements",
        "label_fr": "Goal involvements",
        "scope": MetricScope.PLAYER,
        "category": MetricCategory.COMBINATIONS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.NONE,
        "is_derived": True,
        "formula": "goals + assists",
    },
]

TEAM_METRICS = [
    # POSSESSION
    {
        "slug": "team_possession_pct",
        "label_fr": "Possession (%)",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.POSSESSION,
        "datatype": MetricDataType.PERCENT,
        "unit": "%",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_possession_minutes",
        "label_fr": "Possession (minutes)",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.POSSESSION,
        "datatype": MetricDataType.FLOAT,
        "unit": "minutes",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_possession_won",
        "label_fr": "Possessions gagnées",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.POSSESSION,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_possession_third_def_pct",
        "label_fr": "Possession tiers défensif (%)",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.POSSESSION,
        "datatype": MetricDataType.PERCENT,
        "unit": "%",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_possession_third_mid_pct",
        "label_fr": "Possession tiers milieu (%)",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.POSSESSION,
        "datatype": MetricDataType.PERCENT,
        "unit": "%",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_possession_third_att_pct",
        "label_fr": "Possession tiers attaque (%)",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.POSSESSION,
        "datatype": MetricDataType.PERCENT,
        "unit": "%",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    # PASSES
    {
        "slug": "team_pass_zone_def_pct",
        "label_fr": "Passes zone défensive (%)",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.PASSES,
        "datatype": MetricDataType.PERCENT,
        "unit": "%",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_pass_zone_mid_pct",
        "label_fr": "Passes zone milieu (%)",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.PASSES,
        "datatype": MetricDataType.PERCENT,
        "unit": "%",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_pass_zone_att_pct",
        "label_fr": "Passes zone attaque (%)",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.PASSES,
        "datatype": MetricDataType.PERCENT,
        "unit": "%",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_passes_completed",
        "label_fr": "Passes réussies",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.PASSES,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_sequences_3_5",
        "label_fr": "Séquences 3-5 passes",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.PASSES,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_sequences_6_plus",
        "label_fr": "Séquences 6+ passes",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.PASSES,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_longest_sequence",
        "label_fr": "Séquence la plus longue",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.PASSES,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    # EVENTS
    {
        "slug": "team_goals_scored",
        "label_fr": "Buts marqués",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_goals_conceded",
        "label_fr": "Buts encaissés",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OPPONENT,
        "is_derived": False,
    },
    {
        "slug": "team_free_kicks",
        "label_fr": "Coups francs",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_shots",
        "label_fr": "Tirs",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_shots_conceded",
        "label_fr": "Tirs encaissés",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OPPONENT,
        "is_derived": False,
    },
    {
        "slug": "team_corners",
        "label_fr": "Corners",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_goal_kicks",
        "label_fr": "Coups de pied de but",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    {
        "slug": "team_throw_ins",
        "label_fr": "Throw-ins",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.EVENTS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": False,
    },
    # COMBINATIONS (DERIVED)
    {
        "slug": "team_attempts",
        "label_fr": "Tentatives totales",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.COMBINATIONS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": True,
        "formula": "goals_scored + shots",
    },
    {
        "slug": "team_conversion_rate",
        "label_fr": "Taux de conversion",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.COMBINATIONS,
        "datatype": MetricDataType.PERCENT,
        "unit": "%",
        "side": MetricSide.OWN,
        "is_derived": True,
        "formula": "goals_scored / attempts * 100",
    },
    {
        "slug": "team_attempts_conceded",
        "label_fr": "Tentatives encaissées",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.COMBINATIONS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OPPONENT,
        "is_derived": True,
        "formula": "goals_conceded + shots_conceded",
    },
    {
        "slug": "team_offensive_events",
        "label_fr": "Événements offensifs",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.COMBINATIONS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OWN,
        "is_derived": True,
        "formula": "goals_scored + corners + free_kicks + shots",
    },
    {
        "slug": "team_defensive_events",
        "label_fr": "Événements défensifs",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.COMBINATIONS,
        "datatype": MetricDataType.INT,
        "unit": "count",
        "side": MetricSide.OPPONENT,
        "is_derived": True,
        "formula": "goals_conceded + shots_conceded",
    },
    {
        "slug": "team_win_rate",
        "label_fr": "Taux de victoire",
        "scope": MetricScope.TEAM,
        "category": MetricCategory.COMBINATIONS,
        "datatype": MetricDataType.PERCENT,
        "unit": "%",
        "side": MetricSide.OWN,
        "is_derived": True,
        "formula": "wins / total_matches * 100",
    },
]

def seed_metrics(db: Session):
    """Seed metric definitions into the database"""
    print("Seeding metric definitions...")

    all_metrics = PLAYER_METRICS + TEAM_METRICS

    for metric_data in all_metrics:
        # Check if metric already exists
        existing = db.query(MetricDefinition).filter_by(slug=metric_data["slug"]).first()
        if existing:
            print(f"  ✓ Metric {metric_data['slug']} already exists, skipping")
            continue

        metric = MetricDefinition(**metric_data)
        db.add(metric)
        print(f"  + Added metric: {metric_data['slug']}")

    db.commit()
    print(f"✓ Seeded {len(all_metrics)} metric definitions")

def main():
    """Main seed function"""
    db = SessionLocal()
    try:
        seed_metrics(db)
        print("\n✓ Database seeding completed successfully!")
    except Exception as e:
        print(f"\n✗ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
