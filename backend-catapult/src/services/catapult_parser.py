import csv
from io import StringIO
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd


class CatapultCSVParser:
    """Parse Catapult GPS CSV files and extract player performance data"""
    
    # Column mapping from CSV to our model
    COLUMN_MAPPING = {
        "Date": "date",
        "Session Title": "session_title",
        "Player Name": "player_name",
        "Split Name": "split_name",
        "Tags": "tags",
        "Split Start Time": "split_start_time",
        "Split End Time": "split_end_time",
        "Duration": "duration",
        "Distance (km)": "distance_km",
        "Sprint Distance (m)": "sprint_distance_m",
        "Distance Per Min (m/min)": "distance_per_min",
        "Top Speed (m/s)": "top_speed",
        "Power Score (w/kg)": "power_score",
        "Hr Max (bpm)": "hr_max",
        "Player Load": "player_load",
        "Energy (kcal)": "energy_kcal",
        "Impacts": "impacts",
        "Power Plays": "power_plays",
        "Hr Load": "hr_load",
        "Time In Red Zone (min)": "time_in_red_zone_min",
        "Distance in Speed Zone 1  (km)": "speed_zone_1_km",
        "Distance in Speed Zone 2  (km)": "speed_zone_2_km",
        "Distance in Speed Zone 3  (km)": "speed_zone_3_km",
        "Distance in Speed Zone 4  (km)": "speed_zone_4_km",
        "Distance in Speed Zone 5  (km)": "speed_zone_5_km",
        "Time in Speed Zone 1 (secs)": "speed_zone_1_secs",
        "Time in Speed Zone 2 (secs)": "speed_zone_2_secs",
        "Time in Speed Zone 3 (secs)": "speed_zone_3_secs",
        "Time in Speed Zone 4 (secs)": "speed_zone_4_secs",
        "Time in Speed Zone 5 (secs)": "speed_zone_5_secs",
        "Max Acceleration (m/s/s)": "max_acceleration",
        "Max Deceleration (m/s/s)": "max_deceleration",
        "Work Ratio": "work_ratio",
    }
    
    @staticmethod
    def parse_csv(csv_content: str) -> List[Dict[str, Any]]:
        """
        Parse CSV content and return list of player session data
        
        Args:
            csv_content: Raw CSV file content as string
            
        Returns:
            List of dictionaries with parsed player data
        """
        # Use pandas for easier CSV parsing
        df = pd.read_csv(StringIO(csv_content))
        
        parsed_data = []
        
        for _, row in df.iterrows():
            player_data = {}
            
            # Map columns to our schema
            for csv_col, model_field in CatapultCSVParser.COLUMN_MAPPING.items():
                if csv_col in df.columns:
                    value = row[csv_col]
                    
                    # Handle empty/NaN values
                    if pd.isna(value) or value == '':
                        if model_field == "hr_max":
                            value = None
                        elif isinstance(value, (int, float)):
                            value = 0
                        else:
                            value = ""
                    
                    # Convert date to string (handles Excel serial numbers)
                    if model_field == "date":
                        value = str(value)
                    
                    # Convert duration from "MMSS" string to seconds
                    if model_field == "duration" and isinstance(value, str):
                        value = CatapultCSVParser._parse_duration(value)
                    
                    # Ensure numeric fields are properly typed
                    if model_field in ["duration", "impacts", "power_plays", "hr_load",
                                     "speed_zone_1_secs", "speed_zone_2_secs", 
                                     "speed_zone_3_secs", "speed_zone_4_secs", 
                                     "speed_zone_5_secs"]:
                        value = int(float(value)) if value not in [None, ""] else 0
                    elif model_field in ["distance_km", "sprint_distance_m", "distance_per_min",
                                       "top_speed", "power_score", "player_load", "energy_kcal",
                                       "time_in_red_zone_min", "speed_zone_1_km", "speed_zone_2_km",
                                       "speed_zone_3_km", "speed_zone_4_km", "speed_zone_5_km",
                                       "max_acceleration", "max_deceleration", "work_ratio",
                                       "split_start_time", "split_end_time"]:
                        value = float(value) if value not in [None, ""] else 0.0
                    
                    player_data[model_field] = value
            
            parsed_data.append(player_data)
        
        return parsed_data
    
    @staticmethod
    def _parse_duration(duration_str: str) -> int:
        """
        Convert duration string to seconds
        Examples: "5494" -> 5494 seconds
        """
        try:
            # Remove quotes and convert to int
            return int(duration_str.strip('"'))
        except (ValueError, AttributeError):
            return 0
    
    @staticmethod
    def group_by_player(parsed_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group parsed data by player name
        
        Args:
            parsed_data: List of parsed session data
            
        Returns:
            Dictionary with player names as keys and their sessions as values
        """
        grouped = {}
        
        for session in parsed_data:
            player_name = session.get("player_name", "Unknown")
            if player_name not in grouped:
                grouped[player_name] = []
            grouped[player_name].append(session)
        
        return grouped
    
    @staticmethod
    def get_session_summary(parsed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary statistics for a training session
        
        Args:
            parsed_data: List of parsed session data
            
        Returns:
            Dictionary with session summary statistics
        """
        if not parsed_data:
            return {}
        
        df = pd.DataFrame(parsed_data)
        
        summary = {
            "session_title": parsed_data[0].get("session_title", ""),
            "session_date": parsed_data[0].get("date", ""),
            "total_players": len(df),
            "avg_distance_km": float(df["distance_km"].mean()),
            "max_distance_km": float(df["distance_km"].max()),
            "avg_top_speed": float(df["top_speed"].mean()),
            "max_top_speed": float(df["top_speed"].max()),
            "avg_player_load": float(df["player_load"].mean()),
            "total_duration_minutes": int(df["duration"].mean() / 60),
        }
        
        return summary
