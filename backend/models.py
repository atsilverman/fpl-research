"""
Pydantic models for FPL Vibe API
Defines data structures for API requests and responses
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class Position(str, Enum):
    """Player positions in FPL"""
    GKP = "GKP"  # Goalkeeper
    DEF = "DEF"  # Defender
    MID = "MID"  # Midfielder
    FWD = "FWD"  # Forward

class Team(BaseModel):
    """Team model"""
    id: int
    name: str
    short_name: str
    code: int
    strength: int
    strength_attack_home: int
    strength_attack_away: int
    strength_defence_home: int
    strength_defence_away: int
    strength_overall_home: int
    strength_overall_away: int
    
    class Config:
        from_attributes = True

class Player(BaseModel):
    """Player model"""
    id: int
    first_name: str
    second_name: str
    web_name: str
    team_id: int
    team: Optional[Team] = None
    element_type: int  # 1=GK, 2=DEF, 3=MID, 4=FWD
    now_cost: int  # Price in 0.1M units (e.g., 100 = £10.0M)
    total_points: int
    form: float
    points_per_game: float
    value_form: float
    value_season: float
    chance_of_playing_next_round: Optional[int] = None
    news: Optional[str] = None
    news_added: Optional[datetime] = None
    status: str
    special: bool
    can_select: bool
    can_transact: bool
    in_dreamteam: bool
    removed: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PlayerResponse(BaseModel):
    """Player list response with pagination"""
    players: List[Player]
    total: int
    limit: int
    offset: int

class TeamResponse(BaseModel):
    """Team list response"""
    teams: List[Team]
    total: int

class Fixture(BaseModel):
    """Fixture model"""
    id: int
    gameweek_id: int
    home_team_id: int
    away_team_id: int
    home_team: Optional[Team] = None
    away_team: Optional[Team] = None
    home_team_score: Optional[int] = None
    away_team_score: Optional[int] = None
    finished: bool
    kickoff_time: Optional[datetime] = None
    difficulty_home: int
    difficulty_away: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class FixtureResponse(BaseModel):
    """Fixture list response with pagination"""
    fixtures: List[Fixture]
    total: int
    limit: int
    offset: int

class Gameweek(BaseModel):
    """Gameweek model"""
    id: int
    name: str
    deadline_time: datetime
    is_current: bool
    is_next: bool
    is_previous: bool
    finished: bool
    data_checked: bool
    highest_score: Optional[int] = None
    average_entry_score: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class GameweekResponse(BaseModel):
    """Gameweek list response"""
    gameweeks: List[Gameweek]
    total: int

class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
