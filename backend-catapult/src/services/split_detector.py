from typing import List, Dict, Any, Tuple
import pandas as pd
from datetime import datetime, timedelta


class SplitDetector:
    """Automatically detect training splits (warm-up, halves, breaks, cool-down)"""
    
    # Thresholds for split detection
    PAUSE_THRESHOLD_SECONDS = 180  # 3 minutes of low activity = pause
    LOW_SPEED_THRESHOLD = 1.0  # m/s - below this is considered stationary
    WARMUP_DURATION_MAX = 900  # 15 minutes max for warm-up
    HALFTIME_DURATION_MIN = 300  # 5 minutes minimum for halftime
    HALFTIME_DURATION_MAX = 900  # 15 minutes maximum for halftime
    
    @staticmethod
    def detect_splits_from_timeline(
        raw_data: pd.DataFrame,
        velocity_col: str = "velocity",
        time_col: str = "timestamp"
    ) -> List[Dict[str, Any]]:
        """
        Detect splits from raw GPS timeline data (if available)
        
        This would work with second-by-second GPS data showing velocity over time.
        For now, this is a placeholder for future implementation.
        
        Args:
            raw_data: DataFrame with timestamp and velocity columns
            velocity_col: Name of velocity column
            time_col: Name of timestamp column
            
        Returns:
            List of detected splits with metadata
        """
        # TODO: Implement timeline-based split detection
        # This would analyze velocity patterns to find:
        # - Low activity periods (pauses, halftime)
        # - High intensity periods (match play)
        # - Gradual ramp-up (warm-up) and ramp-down (cool-down)
        
        splits = []
        return splits
    
    @staticmethod
    def detect_splits_from_aggregated(
        session_data: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect splits from aggregated session data
        
        Analyzes the existing split data to categorize splits by type
        (warm-up, first half, halftime, second half, cool-down)
        
        Args:
            session_data: List of player session dictionaries with split info
            
        Returns:
            Dictionary mapping split types to session data
        """
        if not session_data:
            return {}
        
        # Group by split name
        splits_by_name = {}
        for session in session_data:
            split_name = session.get("split_name", "unknown")
            if split_name not in splits_by_name:
                splits_by_name[split_name] = []
            splits_by_name[split_name].append(session)
        
        # Categorize splits
        categorized = {
            "warm-up": [],
            "first-half": [],
            "halftime": [],
            "second-half": [],
            "cool-down": [],
            "other": []
        }
        
        for split_name, sessions in splits_by_name.items():
            split_type = SplitDetector._categorize_split(split_name, sessions[0])
            categorized[split_type].extend(sessions)
        
        return categorized
    
    @staticmethod
    def _categorize_split(split_name: str, session_data: Dict[str, Any]) -> str:
        """
        Categorize a split based on its name and characteristics
        
        Args:
            split_name: Name of the split from CSV
            session_data: Session data dictionary
            
        Returns:
            Split category
        """
        split_lower = split_name.lower()
        
        # Check for common split names
        if "warm" in split_lower or "echauff" in split_lower:
            return "warm-up"
        elif "cool" in split_lower or "retour" in split_lower:
            return "cool-down"
        elif "mi-temps" in split_lower or "halftime" in split_lower or "pause" in split_lower:
            return "halftime"
        elif "1" in split_lower or "first" in split_lower or "premier" in split_lower:
            return "first-half"
        elif "2" in split_lower or "second" in split_lower or "deuxième" in split_lower:
            return "second-half"
        elif split_lower == "all":
            # "all" is the entire session
            return "other"


    @staticmethod
    def is_real_effort(split: dict, min_load_per_min: float = 3.0, min_dist_per_min: float = 30.0, min_top_speed: float = 5.0) -> bool:
        """Return True if `split` corresponds to real training/match effort."""
        if not split:
            return False
        try:
            duration = float(split.get('duration') or 0)
        except Exception:
            return False
        if duration <= 0:
            return False
        def to_float(v):
            try:
                return float(v or 0)
            except Exception:
                return 0.0
        player_load = to_float(split.get('player_load'))
        dist_per_min = to_float(split.get('distance_per_min'))
        top_speed = to_float(split.get('top_speed'))
        load_per_min = player_load / (duration / 60) if duration > 0 else 0.0
        name = str(split.get('split_name') or '').lower()
        if any(k in name for k in ['warm','échauff','echauff','cool','retour','pause','crop']):
            return False
        if load_per_min >= min_load_per_min:
            return True
        if dist_per_min >= min_dist_per_min:
            return True
        if top_speed >= min_top_speed:
            return True
        return False

    @staticmethod
    def analyze_player_splits(
        player_sessions: list
    ) -> dict:
        """
        Analyze all splits for a single player
        """
        if not player_sessions:
            return {}
        import pandas as pd
        df = pd.DataFrame(player_sessions)
        df = df.sort_values("split_start_time")
        splits = []
        for _, row in df.iterrows():
            split_info = {
                "split_name": row.get("split_name"),
                "duration_min": row.get("duration",0) / 60,
                "distance_km": row.get("distance_km",0),
                "avg_speed_kmh": (row.get("distance_km",0) / (row.get("duration",1) / 3600)) if row.get("duration",0) > 0 else 0,
                "max_speed_kmh": row.get("top_speed",0) * 3.6,
                "player_load": row.get("player_load",0),
                "energy_kcal": row.get("energy_kcal",0),
                "intensity": (row.get("player_load",0) / (row.get("duration",1) / 60)) if row.get("duration",0) > 0 else 0,
            }
            splits.append(split_info)
        analysis = {
            "player_name": player_sessions[0].get("player_name"),
            "session_title": player_sessions[0].get("session_title"),
            "total_splits": len(splits),
            "splits": splits,
            "total_distance_km": float(df["distance_km"].sum()),
            "total_duration_min": float(df["duration"].sum() / 60),
            "avg_intensity": float(df["player_load"].sum() / (df["duration"].sum() / 60)) if df["duration"].sum() > 0 else 0,
            "peak_speed_kmh": float(df["top_speed"].max() * 3.6),
            "total_energy_kcal": float(df["energy_kcal"].sum()),
        }
        return analysis

    @staticmethod
    def compare_splits_across_players(
        all_sessions: List[Dict[str, Any]],
        split_name: str = None
    ) -> pd.DataFrame:
        """
        Compare performance metrics across players for a specific split or entire session
        
        Args:
            all_sessions: All session data from CSV
            split_name: Optional - specific split to analyze (None = all splits)
            
        Returns:
            DataFrame with player comparison
        """
        df = pd.DataFrame(all_sessions)
        
        if split_name:
            df = df[df["split_name"] == split_name]
        
        # Group by player and calculate metrics
        comparison = df.groupby("player_name").agg({
            "distance_km": "sum",
            "duration": "sum",
            "top_speed": "max",
            "player_load": "sum",
            "energy_kcal": "sum",
            "sprint_distance_m": "sum",
            "max_acceleration": "max",
            "max_deceleration": "max",
        }).reset_index()
        
        # Add calculated metrics
        comparison["avg_speed_kmh"] = (comparison["distance_km"] / (comparison["duration"] / 3600))
        comparison["duration_min"] = comparison["duration"] / 60
        comparison["top_speed_kmh"] = comparison["top_speed"] * 3.6
        
        # Sort by total distance
        comparison = comparison.sort_values("distance_km", ascending=False)
        
        return comparison
