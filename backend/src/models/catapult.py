from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class CatapultSession(SQLModel, table=True):
    """Store Catapult GPS training session data"""
    id: Optional[int] = Field(default=None, primary_key=True)
    date: str
    session_title: str
    player_id: Optional[int] = Field(default=None, foreign_key="player.id", ondelete="CASCADE")
    player_name: str
    split_name: str
    tags: str
    split_start_time: float
    split_end_time: float
    duration: int  # in seconds
    
    # Distance metrics
    distance_km: float = Field(alias="distance")
    sprint_distance_m: float = Field(alias="sprint_distance")
    distance_per_min: float
    
    # Performance metrics
    top_speed: float  # m/s
    power_score: float  # w/kg
    hr_max: Optional[int] = None  # bpm
    player_load: float
    energy_kcal: float = Field(alias="energy")
    
    # Zones
    impacts: int
    power_plays: int
    hr_load: int
    time_in_red_zone_min: float = Field(alias="time_in_red_zone")
    
    # Speed zones - distance (km)
    speed_zone_1_km: float
    speed_zone_2_km: float
    speed_zone_3_km: float
    speed_zone_4_km: float
    speed_zone_5_km: float
    
    # Speed zones - time (seconds)
    speed_zone_1_secs: int
    speed_zone_2_secs: int
    speed_zone_3_secs: int
    speed_zone_4_secs: int
    speed_zone_5_secs: int
    
    # Acceleration/Deceleration
    max_acceleration: float  # m/s/s
    max_deceleration: float  # m/s/s
    
    # Work ratio
    work_ratio: float
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class CatapultSessionCreate(SQLModel):
    """Schema for creating a Catapult session entry"""
    date: str
    session_title: str
    player_id: Optional[int] = None
    player_name: str
    split_name: str
    tags: str
    split_start_time: float
    split_end_time: float
    duration: int
    distance_km: float
    sprint_distance_m: float
    distance_per_min: float
    top_speed: float
    power_score: float
    hr_max: Optional[int] = None
    player_load: float
    energy_kcal: float
    impacts: int
    power_plays: int
    hr_load: int
    time_in_red_zone_min: float
    speed_zone_1_km: float
    speed_zone_2_km: float
    speed_zone_3_km: float
    speed_zone_4_km: float
    speed_zone_5_km: float
    speed_zone_1_secs: int
    speed_zone_2_secs: int
    speed_zone_3_secs: int
    speed_zone_4_secs: int
    speed_zone_5_secs: int
    max_acceleration: float
    max_deceleration: float
    work_ratio: float


class ProcessedSplit(SQLModel):
    """Schema for a processed split with metadata"""
    split_number: int
    split_type: str  # "warm-up", "first-half", "half-time", "second-half", "cool-down"
    start_time: float
    end_time: float
    duration: int
    distance_km: float
    avg_speed: float
    max_speed: float
    player_load: float
    energy_kcal: float
