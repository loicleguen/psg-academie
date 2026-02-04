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
        
        # Use intensity to guess split type
        duration = session_data.get("duration", 0)
        player_load = session_data.get("player_load", 0)
        
        if duration > 0:
            load_per_min = player_load / (duration / 60)
            
            # Low intensity = warm-up or cool-down
            if load_per_min < 3.0:
                if duration < SplitDetector.WARMUP_DURATION_MAX:
                    return "warm-up"
                else:
                    return "cool-down"
        
        return "other"
    
    @staticmethod
    def analyze_player_splits(
        player_sessions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze all splits for a single player
        
        Args:
            player_sessions: List of session data for one player
            
        Returns:
            Analysis with split breakdown and recommendations
        """
        if not player_sessions:
            return {}
        
        df = pd.DataFrame(player_sessions)
        
        # Sort by start time
        df = df.sort_values("split_start_time")
        
        # Calculate metrics for each split
        splits = []
        for _, row in df.iterrows():
            split_info = {
                "split_name": row["split_name"],
                "duration_min": row["duration"] / 60,
                "distance_km": row["distance_km"],
                "avg_speed_kmh": (row["distance_km"] / (row["duration"] / 3600)) if row["duration"] > 0 else 0,
                "max_speed_kmh": row["top_speed"] * 3.6,  # m/s to km/h
                "player_load": row["player_load"],
                "energy_kcal": row["energy_kcal"],
                "intensity": row["player_load"] / (row["duration"] / 60) if row["duration"] > 0 else 0,
            }
            splits.append(split_info)
        
        # Overall analysis
        analysis = {
            "player_name": player_sessions[0]["player_name"],
            "session_title": player_sessions[0]["session_title"],
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
