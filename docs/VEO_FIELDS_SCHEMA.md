# VEO Fields, Schemas, and Reporting Blueprint

This document defines a practical schema blueprint for manual Veo data entry.
It is built from:
- official Veo feature documentation (events, lineup, analytics views),
- the current `backend-veo` data model and seeded metrics.

## 1. Current Repo Baseline

- `backend-veo` already stores:
  - match metadata (`matches`),
  - participations (`match_player_participations`),
  - team/player metric values (raw + derived definitions).
- A form-oriented catalog endpoint is available:
  - `GET /metrics/entry-schema`
  - Returns match fields, participation fields, and grouped metric catalogs.

## 2. Veo Match Field Families (Official Product Surface)

Veo workflows expose these functional field groups:

- Match setup:
  - title, date/time, location, home/away context,
  - competition and period setup.
- Lineup and formation:
  - starters/substitutes, captain, positions, player cards.
- Event log:
  - event type, timestamp, team side, related player.
- Team analytics:
  - possession, passes, shot map, momentum, outcomes.
- Player analytics:
  - event-derived player contributions and match-to-match form.

## 3. Canonical Internal Data Schema

### 3.1 Match context (single row per match)

Use existing fields from `matches`:
- `date`
- `opponent_name`
- `is_home`
- `match_type`
- `competition`
- `score_for`
- `score_against`
- `veo_title`
- `veo_url`
- `veo_duration`
- `veo_camera`

### 3.2 Participation (one row per player per match)

Use existing fields from `match_player_participations`:
- `player_id`
- `is_starter`
- `is_captain`
- `minutes_played`
- `position_played`

### 3.3 Team metric inputs (raw values only)

Use `team_match_metric_values` with `metric_definitions` catalog.
Current seed supports categories:
- `POSSESSION`
- `PASSES`
- `EVENTS`

Derived team metrics are computed server-side and not stored.

### 3.4 Player metric inputs (raw values only)

Use `player_match_metric_values` with `metric_definitions` catalog.
Current seed supports categories:
- `GENERAL`
- `EVENTS`

Derived player metrics are computed server-side and not stored.

### 3.5 Recommended V2 extension (for full event-level parity)

Add a dedicated event table to preserve full Veo event granularity:
- `match_id`
- `period`
- `timestamp_seconds`
- `event_type`
- `team_side`
- `player_id` (nullable)
- optional pitch coordinates (`x`, `y`)
- source metadata (`manual`, `copied_text`, etc.)

This is the best base for future advanced reports and smart paste parsing.

## 4. Report Layers (User-Friendly)

Organize reports into four views:

- Match recap:
  - context, score, lineup summary, key counts.
- Team performance:
  - possession/passes/events blocks,
  - own vs opponent split where relevant.
- Player contribution:
  - per-player grid with sortable metrics.
- Trends:
  - KPI cards, time series, radar comparison, leaderboards.

## 5. Form UX Structure (Manual Entry)

Recommended flow:

1. Match context
2. Lineup / participations
3. Team metrics (grouped by category)
4. Player metrics (grid)
5. Validation + summary

Backend support for step 3/4 catalog:
- `GET /metrics/entry-schema`

## 6. Smart Paste Readiness (Future)

To support intelligent copy/paste later:

- keep stable metric slugs as canonical mapping keys,
- centralize field descriptors (input type, unit, category),
- validate percentages and non-negative values server-side,
- return structured per-field errors for correction loops.

### 6.1 Expected "Intelligent Paste" Text Format

Planned source text blocks (from analyst output) should follow these section headers:

- `Match summary`
- `Game plan analysis`
- `Scoring efficiency analysis`
- `Trends and patterns`
- `Training drill suggestion`

Recommended extraction targets from that text:

- Match context:
  - opponent name,
  - match date,
  - final score.
- Team KPI values:
  - possession percentage,
  - attempts / shots,
  - conversion percentage,
  - offensive-third possession/passes percentages.
- Tactical narrative:
  - strengths,
  - weaknesses,
  - tactical recommendations.
- Training proposal:
  - drill title,
  - theme,
  - description,
  - progressions.

This structure is compatible with the current VEO form and with a future parser that auto-fills:
- existing numeric fields directly into metric inputs,
- free-text analysis sections into a dedicated narrative/report layer.

## 7. Official Veo Sources Used

- https://support.veo.co/hc/en-us/articles/17206803882513-What-are-Match-Stats-in-Analytics-Studio
- https://support.veo.co/hc/en-us/articles/22872597383057-Match-Event-Capabilities-by-Sport
- https://support.veo.co/hc/en-us/articles/28592084344209-How-to-add-and-edit-Events-in-Veo-Editor
- https://support.veo.co/hc/en-us/articles/30766930923921-How-to-use-Shot-map-in-Analytics-Studio
- https://support.veo.co/hc/en-us/articles/30768406415633-How-to-use-Pass-Strings-in-Analytics-Studio
- https://support.veo.co/hc/en-us/articles/30767084053521-How-to-use-Pass-Location-in-Analytics-Studio
- https://support.veo.co/hc/en-us/articles/29149424933649-How-to-use-Match-Momentum-in-Analytics-Studio
- https://support.veo.co/hc/en-us/articles/19761637060113-How-to-use-Lineup-and-Formation-in-Veo-Editor
- https://support.veo.co/hc/en-us/articles/37389571950353-How-to-setup-football-match-details-for-Veo-Cam-3
