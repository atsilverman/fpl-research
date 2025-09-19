"""
Business logic services for FPL Vibe API
Handles data processing and business rules
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from models import Player, Team, Fixture, Gameweek, Position, TeamGameweekStats, TeamFormTrends, TeamSeasonSummary, TeamHomeAwayStats
from database import DatabaseConnection

logger = logging.getLogger(__name__)

class PlayerService:
    """Service for player-related operations"""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def _element_type_to_position(self, element_type: int) -> str:
        """Convert element_type to position string"""
        mapping = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
        return mapping.get(element_type, "UNK")
    
    def _element_type_to_position_name(self, element_type: int) -> str:
        """Convert element_type to full position name"""
        mapping = {1: "Goalkeeper", 2: "Defender", 3: "Midfielder", 4: "Forward"}
        return mapping.get(element_type, "Unknown")
    
    def _position_to_element_type(self, position: str) -> int:
        """Convert position string to element_type"""
        mapping = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
        return mapping.get(position.upper(), 0)
    
    async def get_players(
        self,
        team_id: Optional[int] = None,
        position: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        search: Optional[str] = None,
        sort_by: str = "total_points",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Player], int]:
        """Get players with filtering, sorting, and pagination"""
        
        # Build filters for Supabase REST API
        filters = {}
        
        if team_id is not None:
            filters['team_id'] = team_id
        
        if position is not None:
            element_type = self._position_to_element_type(position)
            if element_type > 0:
                filters['element_type'] = element_type
        
        if min_price is not None:
            # Convert to 0.1M units
            min_cost = int(min_price * 10)
            filters['now_cost'] = f"gte.{min_cost}"
        
        if max_price is not None:
            # Convert to 0.1M units
            max_cost = int(max_price * 10)
            filters['now_cost'] = f"lte.{max_cost}"
        
        # For search, we'll need to handle this differently with Supabase
        # For now, we'll get all players and filter in Python
        # In production, you'd want to use Supabase's full-text search
        
        # Validate sort_by field
        valid_sort_fields = [
            "total_points", "form", "points_per_game", "price", "selected_by_percent",
            "ict_index", "influence", "creativity", "threat", "goals_scored", "assists"
        ]
        if sort_by not in valid_sort_fields:
            sort_by = "total_points"
        
        # Validate sort_order
        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "desc"
        
        try:
            # Get players with team data using Supabase's select syntax
            select_fields = "*,teams(*)"
            order_by = f"{sort_by}.{sort_order}"
            
            players_data = await self.db.execute_query(
                table="players",
                select=select_fields,
                filters=filters,
                order=order_by,
                limit=limit,
                offset=offset
            )
            
            # Get total count for pagination
            total_result = await self.db.execute_scalar(
                table="players",
                select="count",
                filters=filters
            )
            
            # Convert to Player objects
            players = []
            for row in players_data:
                # Create team object if team data exists
                team = None
                if row.get('teams'):
                    team_data = row['teams']
                    team = Team(
                        id=team_data['id'],
                        name=team_data['name'],
                        short_name=team_data['short_name'],
                        code=team_data['code'],
                        strength=team_data['strength'],
                        strength_attack_home=team_data['strength_attack_home'],
                        strength_attack_away=team_data['strength_attack_away'],
                        strength_defence_home=team_data['strength_defence_home'],
                        strength_defence_away=team_data['strength_defence_away'],
                        strength_overall_home=team_data['strength_overall_home'],
                        strength_overall_away=team_data['strength_overall_away']
                    )
                
                player = Player(
                    id=row['id'],
                    first_name=row['first_name'],
                    second_name=row['second_name'],
                    web_name=row['web_name'],
                    team_id=row['team_id'],
                    team=team,
                    element_type=row['element_type'],
                    now_cost=row['now_cost'],
                    total_points=row['total_points'],
                    form=row['form'],
                    points_per_game=row['points_per_game'],
                    value_form=row['value_form'],
                    value_season=row['value_season'],
                    chance_of_playing_next_round=row['chance_of_playing_next_round'],
                    news=row['news'],
                    news_added=row['news_added'],
                    status=row['status'],
                    special=row['special'],
                    can_select=row['can_select'],
                    can_transact=row['can_transact'],
                    in_dreamteam=row['in_dreamteam'],
                    removed=row['removed'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                
                # Apply search filter if specified
                if search is None or self._matches_search(player, search):
                    players.append(player)
            
            return players, total_result or 0
            
        except Exception as e:
            logger.error(f"Error fetching players: {e}")
            raise
    
    def _matches_search(self, player: Player, search_term: str) -> bool:
        """Check if player matches search term"""
        search_lower = search_term.lower()
        return (
            search_lower in player.first_name.lower() or
            search_lower in player.second_name.lower() or
            search_lower in player.web_name.lower()
        )
    
    async def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """Get specific player by ID"""
        try:
            result = await self.db.execute_query(
                table="players",
                select="*,teams(*)",
                filters={'id': player_id},
                limit=1
            )
            
            if not result:
                return None
            
            row = result[0]
            
            # Create team object if team data exists
            team = None
            if row.get('teams'):
                team_data = row['teams']
                team = Team(
                    id=team_data['id'],
                    name=team_data['name'],
                    short_name=team_data['short_name'],
                    code=team_data['code'],
                    strength=team_data['strength'],
                    strength_attack_home=team_data['strength_attack_home'],
                    strength_attack_away=team_data['strength_attack_away'],
                    strength_defence_home=team_data['strength_defence_home'],
                    strength_defence_away=team_data['strength_defence_away'],
                    strength_overall_home=team_data['strength_overall_home'],
                    strength_overall_away=team_data['strength_overall_away']
                )
            
            return Player(
                id=row['id'],
                first_name=row['first_name'],
                second_name=row['second_name'],
                web_name=row['web_name'],
                team_id=row['team_id'],
                team=team,
                element_type=row['element_type'],
                now_cost=row['now_cost'],
                total_points=row['total_points'],
                form=row['form'],
                points_per_game=row['points_per_game'],
                value_form=row['value_form'],
                value_season=row['value_season'],
                chance_of_playing_next_round=row['chance_of_playing_next_round'],
                news=row['news'],
                news_added=row['news_added'],
                status=row['status'],
                special=row['special'],
                can_select=row['can_select'],
                can_transact=row['can_transact'],
                in_dreamteam=row['in_dreamteam'],
                removed=row['removed'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
        except Exception as e:
            logger.error(f"Error fetching player {player_id}: {e}")
            raise

class TeamService:
    """Service for team-related operations"""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    async def get_teams(self, sort_by: str = "name", sort_order: str = "asc") -> List[Team]:
        """Get all teams"""
        valid_sort_fields = ["name", "short_name", "code", "strength"]
        if sort_by not in valid_sort_fields:
            sort_by = "name"
        
        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "asc"
        
        try:
            result = await self.db.execute_query(
                table="teams",
                order=f"{sort_by}.{sort_order}"
            )
            
            teams = []
            for row in result:
                team = Team(
                    id=row['id'],
                    name=row['name'],
                    short_name=row['short_name'],
                    code=row['code'],
                    strength=row['strength'],
                    strength_attack_home=row['strength_attack_home'],
                    strength_attack_away=row['strength_attack_away'],
                    strength_defence_home=row['strength_defence_home'],
                    strength_defence_away=row['strength_defence_away'],
                    strength_overall_home=row['strength_overall_home'],
                    strength_overall_away=row['strength_overall_away']
                )
                teams.append(team)
            
            return teams
            
        except Exception as e:
            logger.error(f"Error fetching teams: {e}")
            raise
    
    async def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """Get specific team by ID"""
        try:
            result = await self.db.execute_query(
                table="teams",
                filters={'id': team_id},
                limit=1
            )
            
            if not result:
                return None
            
            row = result[0]
            return Team(
                id=row['id'],
                name=row['name'],
                short_name=row['short_name'],
                code=row['code'],
                strength=row['strength'],
                strength_attack_home=row['strength_attack_home'],
                strength_attack_away=row['strength_attack_away'],
                strength_defence_home=row['strength_defence_home'],
                strength_defence_away=row['strength_defence_away'],
                strength_overall_home=row['strength_overall_home'],
                strength_overall_away=row['strength_overall_away']
            )
            
        except Exception as e:
            logger.error(f"Error fetching team {team_id}: {e}")
            raise

class FixtureService:
    """Service for fixture-related operations"""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    async def get_fixtures(
        self,
        gameweek: Optional[int] = None,
        team_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Fixture], int]:
        """Get fixtures with filtering"""
        
        filters = {}
        
        if gameweek is not None:
            filters['gameweek_id'] = gameweek
        
        if team_id is not None:
            # For team filtering, we need to handle this differently with Supabase
            # We'll filter in Python for now
            pass
        
        if status is not None:
            filters['finished'] = status.lower() == 'finished'
        
        try:
            # Get fixtures with team data
            select_fields = "*,home_team:teams!home_team_id(*),away_team:teams!away_team_id(*)"
            
            fixtures_data = await self.db.execute_query(
                table="fixtures",
                select=select_fields,
                filters=filters,
                order="kickoff_time.asc",
                limit=limit,
                offset=offset
            )
            
            # Get total count
            total_result = await self.db.execute_scalar(
                table="fixtures",
                select="count",
                filters=filters
            )
            
            fixtures = []
            for row in fixtures_data:
                # Create home team
                home_team = None
                if row.get('home_team'):
                    team_data = row['home_team']
                    home_team = Team(
                        id=team_data['id'],
                        name=team_data['name'],
                        short_name=team_data['short_name'],
                        code=team_data['code'],
                        strength=team_data['strength'],
                        strength_attack_home=team_data['strength_attack_home'],
                        strength_attack_away=team_data['strength_attack_away'],
                        strength_defence_home=team_data['strength_defence_home'],
                        strength_defence_away=team_data['strength_defence_away'],
                        strength_overall_home=team_data['strength_overall_home'],
                        strength_overall_away=team_data['strength_overall_away']
                    )
                
                # Create away team
                away_team = None
                if row.get('away_team'):
                    team_data = row['away_team']
                    away_team = Team(
                        id=team_data['id'],
                        name=team_data['name'],
                        short_name=team_data['short_name'],
                        code=team_data['code'],
                        strength=team_data['strength'],
                        strength_attack_home=team_data['strength_attack_home'],
                        strength_attack_away=team_data['strength_attack_away'],
                        strength_defence_home=team_data['strength_defence_home'],
                        strength_defence_away=team_data['strength_defence_away'],
                        strength_overall_home=team_data['strength_overall_home'],
                        strength_overall_away=team_data['strength_overall_away']
                    )
                
                fixture = Fixture(
                    id=row['id'],
                    gameweek_id=row['gameweek_id'],
                    home_team_id=row['home_team_id'],
                    away_team_id=row['away_team_id'],
                    home_team=home_team,
                    away_team=away_team,
                    home_team_score=row['home_team_score'],
                    away_team_score=row['away_team_score'],
                    finished=row['finished'],
                    kickoff_time=row['kickoff_time'],
                    difficulty_home=row['difficulty_home'],
                    difficulty_away=row['difficulty_away'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                
                # Apply team filter if specified
                if team_id is None or (fixture.home_team_id == team_id or fixture.away_team_id == team_id):
                    fixtures.append(fixture)
            
            return fixtures, total_result or 0
            
        except Exception as e:
            logger.error(f"Error fetching fixtures: {e}")
            raise

class GameweekService:
    """Service for gameweek-related operations"""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    async def get_gameweeks(self) -> List[Gameweek]:
        """Get all gameweeks"""
        try:
            result = await self.db.execute_query(
                table="gameweeks",
                order="id.asc"
            )
            
            gameweeks = []
            for row in result:
                gameweek = Gameweek(
                    id=row['id'],
                    name=row['name'],
                    deadline_time=row['deadline_time'],
                    is_current=row['is_current'],
                    is_next=row['is_next'],
                    is_previous=row['is_previous'],
                    finished=row['finished'],
                    data_checked=row['data_checked'],
                    highest_score=row['highest_score'],
                    average_entry_score=row['average_entry_score'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                gameweeks.append(gameweek)
            
            return gameweeks
            
        except Exception as e:
            logger.error(f"Error fetching gameweeks: {e}")
            raise
    
    async def get_current_gameweek(self) -> Optional[Gameweek]:
        """Get current gameweek"""
        try:
            result = await self.db.execute_query(
                table="gameweeks",
                filters={'is_current': True},
                limit=1
            )
            
            if not result:
                return None
            
            row = result[0]
            return Gameweek(
                id=row['id'],
                name=row['name'],
                deadline_time=row['deadline_time'],
                is_current=row['is_current'],
                is_next=row['is_next'],
                is_previous=row['is_previous'],
                finished=row['finished'],
                data_checked=row['data_checked'],
                highest_score=row['highest_score'],
                average_entry_score=row['average_entry_score'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
        except Exception as e:
            logger.error(f"Error fetching current gameweek: {e}")
            raise

class TeamGameweekStatsService:
    """Service for team gameweek statistics operations"""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    async def get_team_gameweek_stats(
        self,
        team_id: Optional[int] = None,
        gameweek_start: Optional[int] = None,
        gameweek_end: Optional[int] = None,
        is_home: Optional[bool] = None,
        opponent_id: Optional[int] = None,
        min_difficulty: Optional[int] = None,
        max_difficulty: Optional[int] = None,
        sort_by: str = "gameweek_id",
        sort_order: str = "asc",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[TeamGameweekStats], int]:
        """Get team gameweek stats with filtering"""
        
        filters = {}
        
        if team_id is not None:
            filters['team_id'] = team_id
        
        if gameweek_start is not None:
            filters['gameweek_id'] = f"gte.{gameweek_start}"
        
        if gameweek_end is not None:
            if 'gameweek_id' in filters:
                # Combine with existing filter
                filters['gameweek_id'] = f"gte.{gameweek_start},lte.{gameweek_end}"
            else:
                filters['gameweek_id'] = f"lte.{gameweek_end}"
        
        if is_home is not None:
            filters['is_home'] = is_home
        
        if opponent_id is not None:
            filters['opponent_team_id'] = opponent_id
        
        if min_difficulty is not None:
            filters['difficulty'] = f"gte.{min_difficulty}"
        
        if max_difficulty is not None:
            if 'difficulty' in filters:
                filters['difficulty'] = f"gte.{min_difficulty},lte.{max_difficulty}"
            else:
                filters['difficulty'] = f"lte.{max_difficulty}"
        
        # Validate sort fields
        valid_sort_fields = [
            "gameweek_id", "total_fantasy_points", "goals_for", "goals_against",
            "expected_goals", "expected_goals_conceded", "form_6_gw", "form_3_gw",
            "difficulty", "is_home"
        ]
        if sort_by not in valid_sort_fields:
            sort_by = "gameweek_id"
        
        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "asc"
        
        try:
            order_by = f"{sort_by}.{sort_order}"
            
            stats_data = await self.db.execute_query(
                table="team_gw_stats",
                filters=filters,
                order=order_by,
                limit=limit,
                offset=offset
            )
            
            # Get total count
            total_result = await self.db.execute_scalar(
                table="team_gw_stats",
                select="count",
                filters=filters
            )
            
            # Convert to TeamGameweekStats objects
            stats = []
            for row in stats_data:
                stat = TeamGameweekStats(
                    id=row['id'],
                    team_id=row['team_id'],
                    gameweek_id=row['gameweek_id'],
                    fixture_id=row['fixture_id'],
                    is_home=row['is_home'],
                    opponent_team_id=row['opponent_team_id'],
                    difficulty=row['difficulty'],
                    goals_for=row['goals_for'],
                    goals_against=row['goals_against'],
                    result=row['result'],
                    total_fantasy_points=row['total_fantasy_points'],
                    avg_fantasy_points=float(row['avg_fantasy_points']),
                    players_played=row['players_played'],
                    players_started=row['players_started'],
                    goals_scored=row['goals_scored'],
                    assists=row['assists'],
                    own_goals=row.get('own_goals', 0),
                    penalties_missed=row.get('penalties_missed', 0),
                    expected_goals=float(row['expected_goals']),
                    expected_assists=float(row['expected_assists']),
                    expected_goal_involvements=float(row['expected_goal_involvements']),
                    clean_sheets=row['clean_sheets'],
                    saves=row['saves'],
                    penalties_saved=row.get('penalties_saved', 0),
                    tackles=row['tackles'],
                    clearances_blocks_interceptions=row.get('clearances_blocks_interceptions', 0),
                    recoveries=row.get('recoveries', 0),
                    defensive_contribution=row.get('defensive_contribution', 0),
                    yellow_cards=row['yellow_cards'],
                    red_cards=row['red_cards'],
                    total_influence=float(row['total_influence']),
                    total_creativity=float(row['total_creativity']),
                    total_threat=float(row['total_threat']),
                    total_ict_index=float(row['total_ict_index']),
                    avg_influence=float(row['avg_influence']),
                    avg_creativity=float(row['avg_creativity']),
                    avg_threat=float(row['avg_threat']),
                    avg_ict_index=float(row['avg_ict_index']),
                    form_6_gw=float(row['form_6_gw']),
                    form_3_gw=float(row['form_3_gw']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                stats.append(stat)
            
            return stats, total_result or 0
            
        except Exception as e:
            logger.error(f"Error fetching team gameweek stats: {e}")
            raise
    
    async def get_team_form_trends(
        self,
        team_id: Optional[int] = None,
        gameweek_start: Optional[int] = None,
        gameweek_end: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[TeamFormTrends], int]:
        """Get team form trends from materialized view"""
        
        filters = {}
        
        if team_id is not None:
            filters['team_id'] = team_id
        
        if gameweek_start is not None:
            filters['gameweek_id'] = f"gte.{gameweek_start}"
        
        if gameweek_end is not None:
            if 'gameweek_id' in filters:
                filters['gameweek_id'] = f"gte.{gameweek_start},lte.{gameweek_end}"
            else:
                filters['gameweek_id'] = f"lte.{gameweek_end}"
        
        try:
            trends_data = await self.db.execute_query(
                table="mv_team_form_trends",
                filters=filters,
                order="team_id.asc,gameweek_id.asc",
                limit=limit,
                offset=offset
            )
            
            # Get total count
            total_result = await self.db.execute_scalar(
                table="mv_team_form_trends",
                select="count",
                filters=filters
            )
            
            # Convert to TeamFormTrends objects
            trends = []
            for row in trends_data:
                trend = TeamFormTrends(
                    team_id=row['team_id'],
                    team_name=row['team_name'],
                    gameweek_id=row['gameweek_id'],
                    gameweek_name=row['gameweek_name'],
                    is_home=row['is_home'],
                    opponent_team_id=row['opponent_team_id'],
                    opponent_name=row['opponent_name'],
                    difficulty=row['difficulty'],
                    goals_for=row['goals_for'],
                    goals_against=row['goals_against'],
                    result=row['result'],
                    total_fantasy_points=row['total_fantasy_points'],
                    form_6_gw=float(row['form_6_gw']),
                    form_3_gw=float(row['form_3_gw']),
                    expected_goals=float(row['expected_goals']),
                    expected_goals_conceded=float(row['expected_goals_conceded']),
                    clean_sheets=row['clean_sheets']
                )
                trends.append(trend)
            
            return trends, total_result or 0
            
        except Exception as e:
            logger.error(f"Error fetching team form trends: {e}")
            raise
    
    async def get_team_season_summary(self) -> List[TeamSeasonSummary]:
        """Get team season summary from materialized view"""
        
        try:
            summary_data = await self.db.execute_query(
                table="mv_team_season_summary",
                order="wins.desc,goal_difference.desc"
            )
            
            # Convert to TeamSeasonSummary objects
            summaries = []
            for row in summary_data:
                summary = TeamSeasonSummary(
                    team_id=row['team_id'],
                    team_name=row['team_name'],
                    games_played=row['games_played'],
                    wins=row['wins'],
                    draws=row['draws'],
                    losses=row['losses'],
                    total_goals_for=row['total_goals_for'],
                    total_goals_against=row['total_goals_against'],
                    goal_difference=row['goal_difference'],
                    avg_fantasy_points=float(row['avg_fantasy_points']),
                    total_fantasy_points=row['total_fantasy_points'],
                    avg_expected_goals=float(row['avg_expected_goals']),
                    avg_expected_goals_conceded=float(row['avg_expected_goals_conceded']),
                    total_clean_sheets=row['total_clean_sheets'],
                    current_form_6_gw=float(row['current_form_6_gw']),
                    current_form_3_gw=float(row['current_form_3_gw'])
                )
                summaries.append(summary)
            
            return summaries
            
        except Exception as e:
            logger.error(f"Error fetching team season summary: {e}")
            raise
    
    async def get_team_home_away_stats(self, team_id: Optional[int] = None) -> List[TeamHomeAwayStats]:
        """Get team home/away stats from materialized view"""
        
        filters = {}
        if team_id is not None:
            filters['team_id'] = team_id
        
        try:
            stats_data = await self.db.execute_query(
                table="mv_team_home_away_stats",
                filters=filters,
                order="team_id.asc,is_home.desc"
            )
            
            # Convert to TeamHomeAwayStats objects
            stats = []
            for row in stats_data:
                stat = TeamHomeAwayStats(
                    team_id=row['team_id'],
                    team_name=row['team_name'],
                    is_home=row['is_home'],
                    games_played=row['games_played'],
                    wins=row['wins'],
                    draws=row['draws'],
                    losses=row['losses'],
                    avg_fantasy_points=float(row['avg_fantasy_points']),
                    avg_expected_goals=float(row['avg_expected_goals']),
                    avg_expected_goals_conceded=float(row['avg_expected_goals_conceded']),
                    total_clean_sheets=row['total_clean_sheets']
                )
                stats.append(stat)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error fetching team home/away stats: {e}")
            raise
