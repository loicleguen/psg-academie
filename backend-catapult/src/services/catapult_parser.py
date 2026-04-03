import logging
import re
from io import StringIO
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
from dateutil import parser as dateutil_parser
from sqlmodel import Session, select
from ..models.user import User
from ..services.auth import AuthService

# Mapping CSV header -> canonical model field
COLUMN_MAPPING = {
    "date": "date",
    "session title": "session_title",
    "player name": "player_name",
    "player": "player_name",
    "split name": "split_name",
    "tags": "tags",
    "split start time": "split_start_time",
    "split end time": "split_end_time",
    "distance (km)": "distance_km",
    "sprint distance (m)": "sprint_distance_m",
    "distance per min (m/min)": "distance_per_min",
    "top speed (m/s)": "top_speed",
    "power score (w/kg)": "power_score",
    "hr max (bpm)": "hr_max",
    "player load": "player_load",
    "energy (kcal)": "energy_kcal",
    "impacts": "impacts",
    "power plays": "power_plays",
    "hr load": "hr_load",
    "time in red zone (min)": "time_in_red_zone_min",
    "distance in speed zone 1  (km)": "speed_zone_1_km",
    "distance in speed zone 2  (km)": "speed_zone_2_km",
    "distance in speed zone 3  (km)": "speed_zone_3_km",
    "distance in speed zone 4  (km)": "speed_zone_4_km",
    "distance in speed zone 5  (km)": "speed_zone_5_km",
    "time in speed zone 1 (secs)": "speed_zone_1_secs",
    "time in speed zone 2 (secs)": "speed_zone_2_secs",
    "time in speed zone 3 (secs)": "speed_zone_3_secs",
    "time in speed zone 4 (secs)": "speed_zone_4_secs",
    "time in speed zone 5 (secs)": "speed_zone_5_secs",
    "max acceleration (m/s/s)": "max_acceleration",
    "max deceleration (m/s/s)": "max_deceleration",
    "work ratio": "work_ratio",
}

NUMERIC_FIELDS_INT = {
    "hr_max",
    "hr_load",
    "speed_zone_1_secs",
    "speed_zone_2_secs",
    "speed_zone_3_secs",
    "speed_zone_4_secs",
    "speed_zone_5_secs",
}

NUMERIC_FIELDS_FLOAT = {
    "distance_km",
    "sprint_distance_m",
    "distance_per_min",
    "top_speed",
    "power_score",
    "player_load",
    "energy_kcal",
    "time_in_red_zone_min",
    "speed_zone_1_km",
    "speed_zone_2_km",
    "speed_zone_3_km",
    "speed_zone_4_km",
    "speed_zone_5_km",
    "max_acceleration",
    "max_deceleration",
    "work_ratio",
    "split_start_time",
    "split_end_time",
}

_normalize_whitespace_re = re.compile(r"\s+")
_non_alnum_re = re.compile(r"[^a-z0-9\-_.]")

def _col_key(name: str) -> str:
    """Normalize csv header for lookup (lower, strip, collapse spaces)."""
    if name is None:
        return ""
    s = str(name).strip().lower()
    s = _normalize_whitespace_re.sub(" ", s)
    return s

def _map_columns(df_columns: List[str]) -> Dict[str, str]:
    """
    Attempt to map dataframe columns to canonical CSV keys defined in COLUMN_MAPPING.
    Returns dict: original_col -> canonical_key (one of keys in COLUMN_MAPPING).
    """
    col_map = {}
    lowercase_mapping = {_col_key(k): k for k in COLUMN_MAPPING.keys()}
    for col in df_columns:
        k = _col_key(col)
        mapped = None
        # exact match
        if k in lowercase_mapping:
            mapped = lowercase_mapping[k]
        else:
            # try partial or contains match
            for cand in lowercase_mapping.keys():
                if cand in k or k in cand:
                    mapped = lowercase_mapping[cand]
                    break
        # fallback using tokens
        if not mapped:
            if "player" in k:
                mapped = "Player Name"
            elif "date" in k:
                mapped = "Date"
            elif "duration" in k or ":" in k or re.search(r"\bmin\b|\bsec\b", k):
                mapped = "Duration"
            elif "distance" in k:
                # pick the generic distance if ambiguous
                if "sprint" in k:
                    mapped = "Sprint Distance (m)"
                elif "per min" in k or "per_min" in k:
                    mapped = "Distance Per Min (m/min)"
                else:
                    mapped = "Distance (km)"
        if mapped:
            col_map[col] = mapped
    return col_map

def _try_parse_excel_serial(val: Any) -> Optional[datetime]:
    """
    Convert Excel serial date (number) to datetime.date.
    Excel uses 1899-12-30 base (note: Excel leap year bug treated by pandas too).
    """
    try:
        f = float(val)
    except Exception:
        return None
    # ignore small numbers that are probably not dates
    if f < 60:
        return None
    base = datetime(1899, 12, 30)
    try:
        return (base + timedelta(days=int(f))).date()
    except Exception:
        return None

def _parse_mixed_date(val: Any) -> Optional[str]:
    """
    Parse many date formats and return ISO date string 'YYYY-MM-DD' or None.
    Handles Excel serial numbers, common date strings, pandas timestamps.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)) or (isinstance(val, str) and val.strip() == ""):
        return None
    # Excel serial
    excel = _try_parse_excel_serial(val)
    if excel:
        return excel.isoformat()
    # pandas Timestamp
    try:
        if hasattr(val, "to_pydatetime"):
            return pd.to_datetime(val).date().isoformat()
    except Exception:
        pass
    s = str(val).strip()
    # try dateutil
    try:
        d = dateutil_parser.parse(s, dayfirst=True)
        return d.date().isoformat()
    except Exception:
        pass
    # pandas parser fallback
    try:
        d = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if not pd.isna(d):
            return d.date().isoformat()
    except Exception:
        pass
    return None

def _parse_duration_to_seconds(val: Any) -> int:
    """
    Parse durations into integer seconds.
    Accepts:
      - numeric seconds (int/float)
      - "MM:SS" or "HH:MM:SS"
      - "MMS S" or "5494" numeric-string
    Returns 0 on failure.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)) or (isinstance(val, str) and val.strip() == ""):
        return 0
    # numeric
    try:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return int(val)
        s = str(val).strip().strip('"').strip("'")
        # colon format
        if ":" in s:
            parts = [int(p) if p.isdigit() else 0 for p in s.split(":")]
            parts = parts[::-1]  # seconds, minutes, hours
            seconds = 0
            mul = 1
            for p in parts:
                seconds += p * mul
                mul *= 60
            return seconds
        # plain digits: if length 4 interpret as MMSS else treat as seconds
        if s.isdigit():
            if len(s) == 4:
                # MMSS -> convert
                mm = int(s[:-2])
                ss = int(s[-2:])
                return mm * 60 + ss
            return int(s)
        # fallback: try float
        return int(float(s))
    except Exception:
        return 0

class CatapultCSVParser:
    """Parse Catapult GPS CSV files and extract player performance data"""

    @staticmethod
    def parse_csv(csv_content: str) -> List[Dict[str, Any]]:
        """
        Parse CSV content and return list of player session dicts with normalized keys.
        - Normalizes headers
        - Parses dates to ISO strings when possible (YYYY-MM-DD)
        - Converts durations to integer seconds
        - Casts numeric columns to int/float where applicable
        """
        # Use pandas for robust CSV support
        logger = logging.getLogger(__name__)
        # Strip BOM if present
        if csv_content.startswith('﻿'):
            csv_content = csv_content[1:]
        df = pd.read_csv(StringIO(csv_content), dtype=object, keep_default_na=False)
        # If only 1 column detected, the file might be wrapped in quotes or use a different separator
        if len(df.columns) < 5:
            logger.warning(f"⚠️ Only {len(df.columns)} columns detected, retrying with sep=None (auto-detect)")
            try:
                df = pd.read_csv(StringIO(csv_content), dtype=object, keep_default_na=False, sep=None, engine='python')
            except Exception as e_retry:
                logger.warning(f"⚠️ Auto-detect sep failed: {e_retry}, trying sep=';'")
                df = pd.read_csv(StringIO(csv_content), dtype=object, keep_default_na=False, sep=';')
        logger.warning(f"📋 CSV Columns detected: {list(df.columns)}")

        # Detect "Excel single-cell" format: headers are split into many columns,
        # but data rows have all values jammed into the first column as a quoted CSV string.
        # This happens when Excel saves a file where data cells contain commas.
        if len(df.columns) >= 5 and len(df) > 0:
            first_col = df.columns[0]
            first_val = str(df[first_col].iloc[0])
            # If the first data cell contains many commas, it's a row-in-a-cell situation
            if first_val.count(',') >= 5:
                logger.warning(f"⚠️ Detected Excel 'row-in-a-cell' format, re-parsing data rows using header columns")
                col_names = list(df.columns)
                new_rows = []
                for _, row in df.iterrows():
                    raw = str(row.iloc[0])
                    try:
                        import csv as csv_mod
                        values = next(csv_mod.reader([raw]))
                    except Exception:
                        values = raw.split(',')
                    # Pad or truncate to match number of columns
                    if len(values) < len(col_names):
                        values += [''] * (len(col_names) - len(values))
                    new_rows.append(dict(zip(col_names, values[:len(col_names)])))
                df = pd.DataFrame(new_rows, dtype=object).fillna('')
                logger.warning(f"✅ Re-parsed {len(df)} rows from single-cell format")

        # Map raw columns to canonical CSV column names
        rename_map = {}
        col_map = _map_columns(list(df.columns))
        for original_col, canonical_csv_key in col_map.items():
            # map canonical CSV header -> model field
            model_field = COLUMN_MAPPING.get(canonical_csv_key.lower(), None)
            if model_field is None:
                # try lookup case-insensitive
                model_field = COLUMN_MAPPING.get(canonical_csv_key, None)
            if model_field:
                rename_map[original_col] = model_field

        # If no mapping found, try to map by raw lower-case header names
        if not rename_map:
            for col in df.columns:
                k = _col_key(col)
                if "player" in k:
                    rename_map[col] = "player_name"
                elif "date" in k:
                    rename_map[col] = "date"
                elif "duration" in k:
                    rename_map[col] = "duration"
                elif k == "distance (km)" or (k.startswith("distance") and "zone" not in k and "speed" not in k):
                    rename_map[col] = "distance_km"

        logger.warning(f"🔄 Column rename_map: {rename_map}")
        impacts_cols = [col for col in df.columns if "impact" in col.lower() or "power" in col.lower()]
        logger.warning(f"🔍 Columns with impact/power: {impacts_cols}")

        # Calculate totals from zones BEFORE renaming columns
        impact_zone_cols = [col for col in df.columns if "impact zones:" in col.lower() and "(impacts)" in col.lower()]
        power_zone_cols = [col for col in df.columns if "power play duration zones:" in col.lower() and "(power plays)" in col.lower()]
        logger.warning(f"🔍 Found {len(impact_zone_cols)} impact zones, {len(power_zone_cols)} power play zones")

        # Acceleration / Deceleration zone counts (for VOL)
        accel_count_cols = [col for col in df.columns if "accelerations zone count:" in col.lower()]
        decel_count_cols = [col for col in df.columns if "deceleration zone count:" in col.lower()]
        decel_high_cols  = [col for col in df.columns if "deceleration zone count: > 4" in col.lower()]

        # TEMPS A/D = time in accel zones >=1 m/s/s + decel zones >=1 m/s/s (for INT)
        decel_time_cols = [col for col in df.columns
                           if "time in deceleration zones:" in col.lower() and "(secs)" in col.lower()
                           and not col.lower().startswith("time in deceleration zones: 0")]
        accel_time_cols = [col for col in df.columns
                           if "time in acceleration zones:" in col.lower() and "(secs)" in col.lower()
                           and not col.lower().startswith("time in acceleration zones: 0")]

        def _sum_cols(cols):
            if not cols:
                return pd.Series([0] * len(df))
            return df[cols].apply(lambda x: sum(pd.to_numeric(x, errors='coerce').fillna(0)), axis=1)

        # Add calculated total columns to dataframe BEFORE renaming
        df['_calculated_total_impacts'] = _sum_cols(impact_zone_cols).astype(int)
        df['_calculated_total_power_plays'] = _sum_cols(power_zone_cols).astype(int)
        df['_calculated_accel_count'] = _sum_cols(accel_count_cols).astype(int)
        df['_calculated_decel_count']      = _sum_cols(decel_count_cols).astype(int)
        df['_calculated_decel_high_count'] = _sum_cols(decel_high_cols).astype(int)
        df['_calculated_temps_ad_secs']    = (_sum_cols(decel_time_cols) + _sum_cols(accel_time_cols)).astype(float)
        logger.warning(f"🔍 Found {len(accel_count_cols)} accel count cols, {len(decel_count_cols)} decel count cols, {len(decel_time_cols)} decel time cols, {len(accel_time_cols)} accel time cols")
        
        logger.warning(f"📊 Sample impacts total: {df['_calculated_total_impacts'].iloc[0] if len(df) > 0 else 'N/A'}")
        logger.warning(f"📊 Sample power plays total: {df['_calculated_total_power_plays'].iloc[0] if len(df) > 0 else 'N/A'}")

        # Rename df to use model field names
        df = df.rename(columns=rename_map)


        parsed_rows: List[Dict[str, Any]] = []
        for _, raw_row in df.iterrows():
            row = dict(raw_row.to_dict())
            parsed: Dict[str, Any] = {}

            # Normalize player name
            pname = row.get("player_name", "")
            pname = str(pname).strip()
            parsed["player_name"] = pname if pname != "" else None

            # Date: keep original string but try to normalize to ISO date
            parsed_date = _parse_mixed_date(row.get("date"))
            parsed["date"] = parsed_date or (str(row.get("date")).strip() or "")

            # Duration -> seconds
            # Recalculer depuis split_start_time et split_end_time si disponible (plus fiable)
            logger = logging.getLogger(__name__)
            start_time = row.get("split_start_time")
            end_time = row.get("split_end_time")
            
            duration_calculated = False
            if start_time is not None and end_time is not None and start_time != "" and end_time != "":
                try:
                    start = float(start_time)
                    end = float(end_time)
                    # Les times sont en format Excel (jours depuis 1900)
                    # Convertir en secondes: (diff en jours) * 86400
                    calculated_duration = int((end - start) * 86400)
                    if calculated_duration > 0:
                        parsed["duration"] = calculated_duration
                        duration_calculated = True
                        logger.warning(f"✅ Calculated duration for {row.get('player_name')}: {calculated_duration}s")
                    else:
                        logger.warning(f"Negative duration calculated: {calculated_duration}s for {row.get('player_name')}")
                except Exception as e:
                    logger.error(f"ERROR calculating duration for {row.get('player_name')}: {e}")
                    logger.error(f"  start_time={start_time}, end_time={end_time}")
            else:
                logger.warning(f"No split times for {row.get('player_name')}, using CSV duration")
            
            if not duration_calculated:
                # Fallback au CSV
                parsed["duration"] = _parse_duration_to_seconds(row.get("duration"))

            # Use pre-calculated totals from dataframe
            parsed["impacts"] = int(row.get("_calculated_total_impacts", 0))
            parsed["power_plays"] = int(row.get("_calculated_total_power_plays", 0))
            parsed["accel_count"] = int(row.get("_calculated_accel_count", 0))
            parsed["decel_count"]      = int(row.get("_calculated_decel_count", 0))
            parsed["decel_high_count"] = int(row.get("_calculated_decel_high_count", 0))
            parsed["temps_ad_secs"]    = float(row.get("_calculated_temps_ad_secs", 0.0))
            if parsed["impacts"] > 0 or parsed["power_plays"] > 0:
                logger.warning(f"📊 {row.get('player_name')}: impacts={parsed['impacts']}, power_plays={parsed['power_plays']}")

            # Numeric int fields
            for f in NUMERIC_FIELDS_INT:
                val = row.get(f, None)
                try:
                    parsed[f] = int(float(val)) if val not in [None, ""] else 0
                except Exception:
                    parsed[f] = 0


            # Debug log
            logger.warning(f"Player {row.get('player_name')}: parsed impacts={parsed.get('impacts', 0)}, power_plays={parsed.get('power_plays', 0)} | raw: i={row.get('impacts')}, pp={row.get('power_plays')}")

            # Numeric float fields
            for f in NUMERIC_FIELDS_FLOAT:
                val = row.get(f, None)
                try:
                    parsed[f] = float(val) if val not in [None, ""] else 0.0
                except Exception:
                    parsed[f] = 0.0

            # Copy over remaining mapped fields (strings, tags, titles...)
            for original_col, model_field in rename_map.items():
                if model_field in parsed:
                    continue
                parsed[model_field] = row.get(model_field, None)

            parsed_rows.append(parsed)

        return parsed_rows

    @staticmethod
    def group_by_player(parsed_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group parsed data by normalized player key (lowercase, collapsed spaces).
        Returns mapping normalized_name -> list[sessions].
        """
        grouped = {}
        for session in parsed_data:
            name = session.get("player_name") or "unknown"
            key = _normalize_whitespace_re.sub(" ", str(name)).strip().lower()
            grouped.setdefault(key, []).append(session)
        return grouped

    @staticmethod
    def get_session_summary(parsed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Produce a compact session summary from parsed rows.
        """
        if not parsed_data:
            return {}
        df = pd.DataFrame(parsed_data)
        # defensive defaults
        def safe_mean(col):
            try:
                return float(df[col].mean())
            except Exception:
                return 0.0
        def safe_max(col):
            try:
                return float(df[col].max())
            except Exception:
                return 0.0

        summary = {
            "session_title": parsed_data[0].get("session_title", ""),
            "session_date": parsed_data[0].get("date", ""),
            "total_players": len(df),
            "avg_distance_km": safe_mean("distance_km"),
            "max_distance_km": safe_max("distance_km"),
            "avg_top_speed": safe_mean("top_speed"),
            "max_top_speed": safe_max("top_speed"),
            "avg_player_load": safe_mean("player_load"),
            "total_duration_minutes": int(safe_mean("duration") / 60) if "duration" in df.columns else 0,
        }
        return summary
    

def create_or_update_users(session: Session, parsed_rows: List[Dict[str, Any]], default_team_id: int = 1) -> Dict[str, int]:
    """
    Crée ou met à jour des Users à partir de parsed_rows.
    NE fait PAS de commit() — le caller (route) gère le commit.
    Retourne mapping normalized_player_name -> user.id
    """
    name_to_user_id: Dict[str, int] = {}
    for data in parsed_rows:
        player_fullname = (data.get("player_name") or "").strip()
        if not player_fullname:
            continue

        normalized = re.sub(r'\s+', ' ', player_fullname).strip().lower()
        parts = re.split(r"\s+", player_fullname)
        first = parts[0] if parts else "player"
        last = parts[-1] if len(parts) > 1 else first

        def _normalize_part(s: str) -> str:
            return re.sub(r'[^a-z0-9]', '', s.lower()) or "user"

        safe_first = _normalize_part(first)
        safe_last = _normalize_part(last)
        email = f"{safe_first}.{safe_last}@import.local"

        existing = session.exec(select(User).where(User.email == email)).first()
        if not existing:
            hashed = AuthService.get_password_hash(first)
            db_user = User(
                email=email,
                hashed_password=hashed,
                full_name=player_fullname,
                role="player",
                player_name=player_fullname,
                team_id=default_team_id
            )
            session.add(db_user)
            try:
                session.flush()
                session.refresh(db_user)
            except Exception:
                session.rollback()
                continue
        else:
            db_user = existing
            changed = False
            if not db_user.player_name and player_fullname:
                db_user.player_name = player_fullname
                changed = True
            if not db_user.team_id:
                db_user.team_id = default_team_id
                changed = True
            if changed:
                session.add(db_user)

        if db_user and getattr(db_user, "id", None):
            name_to_user_id[normalized] = db_user.id

    return name_to_user_id
