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

class PlayerGameweekStats(BaseModel):
    """Player gameweek stats model"""
    id: int
    player_id: int
    gameweek_id: int
    fixture_id: Optional[int] = None
    minutes: int
    goals_scored: int
    assists: int
    clean_sheets: int
    goals_conceded: int
    own_goals: int
    penalties_saved: int
    penalties_missed: int
    yellow_cards: int
    red_cards: int
    saves: int
    bonus: int
    bps: int
    influence: Optional[float] = None
    creativity: Optional[float] = None
    threat: Optional[float] = None
    ict_index: Optional[float] = None
    total_points: int
    # Expected data fields
    expected_goals: float
    expected_assists: float
    expected_goal_involvements: float
    expected_goals_conceded: float
    clearances_blocks_interceptions: int
    recoveries: int
    tackles: int
    defensive_contribution: int
    starts: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PlayerGameweekStatsResponse(BaseModel):
    """Player gameweek stats response with pagination"""
    stats: List[PlayerGameweekStats]
    total: int
    limit: int
    offset: int

class TeamGameweekStats(BaseModel):
    """Team gameweek stats model"""
    id: int
    team_id: int
    gameweek_id: int
    fixture_id: Optional[int] = None
    is_home: bool
    opponent_team_id: Optional[int] = None
    difficulty: Optional[int] = None
    
    # Match results
    goals_for: int
    goals_against: int
    result: Optional[str] = None  # 'W', 'D', 'L'
    
    # Fantasy performance
    total_fantasy_points: int
    avg_fantasy_points: float
    players_played: int
    players_started: int
    
    # Attacking stats
    goals_scored: int
    assists: int
    own_goals: int = 0
    penalties_missed: int = 0
    
    # Expected attacking stats
    expected_goals: float
    expected_assists: float
    expected_goal_involvements: float
    
    # Defensive stats
    clean_sheets: int
    saves: int
    penalties_saved: int = 0
    tackles: int
    clearances_blocks_interceptions: int = 0
    recoveries: int = 0
    defensive_contribution: int = 0
    
    # Discipline stats
    yellow_cards: int
    red_cards: int
    
    # ICT metrics
    total_influence: float
    total_creativity: float
    total_threat: float
    total_ict_index: float
    avg_influence: float
    avg_creativity: float
    avg_threat: float
    avg_ict_index: float
    
    # Form and trends
    form_6_gw: float
    form_3_gw: float
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TeamGameweekStatsResponse(BaseModel):
    """Team gameweek stats response with pagination"""
    data: List[TeamGameweekStats]
    total: int
    limit: int
    offset: int

class TeamFormTrends(BaseModel):
    """Team form trends model"""
    team_id: int
    team_name: str
    gameweek_id: int
    gameweek_name: str
    is_home: bool
    opponent_team_id: Optional[int] = None
    opponent_name: Optional[str] = None
    difficulty: Optional[int] = None
    goals_for: int
    goals_against: int
    result: Optional[str] = None
    total_fantasy_points: int
    form_6_gw: float
    form_3_gw: float
    expected_goals: float
    expected_goals_conceded: float
    clean_sheets: int

class TeamSeasonSummary(BaseModel):
    """Team season summary model"""
    team_id: int
    team_name: str
    games_played: int
    wins: int
    draws: int
    losses: int
    total_goals_for: int
    total_goals_against: int
    goal_difference: int
    avg_fantasy_points: float
    total_fantasy_points: int
    avg_expected_goals: float
    avg_expected_goals_conceded: float
    total_clean_sheets: int
    current_form_6_gw: float
    current_form_3_gw: float

class TeamHomeAwayStats(BaseModel):
    """Team home/away stats model"""
    team_id: int
    team_name: str
    is_home: bool
    games_played: int
    wins: int
    draws: int
    losses: int
    avg_fantasy_points: float
    avg_expected_goals: float
    avg_expected_goals_conceded: float
    total_clean_sheets: int

class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
