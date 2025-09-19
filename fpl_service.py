#!/usr/bin/env python3
"""
FPL Unified Data Service

A single service that combines monitoring and data refresh capabilities.
Runs continuously on a server, checking for changes and refreshing data when needed.

Usage:
    python fpl_service.py                    # Start continuous service
    python fpl_service.py --test            # Test connections and logic
    python fpl_service.py --once            # Check once and exit
    python fpl_service.py --refresh         # Force immediate refresh
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import argparse
import requests
import pytz

# Configure logging with local timezone
class PacificTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=pytz.timezone('America/Los_Angeles'))
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            s = dt.strftime('%Y-%m-%d %H:%M:%S %Z')
        return s

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create formatter
formatter = PacificTimeFormatter('%(asctime)s - %(levelname)s - %(message)s')

# File handler
file_handler = logging.FileHandler('fpl_service.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class FPLService:
    """Unified FPL data monitoring and refresh service"""
    
    def __init__(self):
        # Supabase configuration
        self.supabase_url = "https://vgdhoezzjyjvekoulzfu.supabase.co"
        self.supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnZGhvZXp6anlqdmVrb3VsemZ1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODEzNjM2MSwiZXhwIjoyMDczNzEyMzYxfQ.qRmFXHvI6Li7dr52sHQ5e2yqfzW_r6MhPid6fX5pG54"
        
        # FPL API configuration
        self.fpl_base_url = "https://fantasy.premierleague.com/api"
        self.rate_limit_delay = 0.2
        
        # Monitoring configuration
        self.check_interval = 3600  # 1 hour in seconds
        self.state_file = 'service_state.json'
        
        # Configure timezone for easier debugging
        self.local_tz = pytz.timezone('America/Los_Angeles')  # Pacific Time
        self.utc_tz = pytz.UTC
        
        # HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FPL-Service/1.0',
            'Accept': 'application/json'
        })
    
    def now_local(self) -> datetime:
        """Get current time in local timezone (Pacific Time)"""
        return datetime.now(self.local_tz)
    
    def now_utc(self) -> datetime:
        """Get current time in UTC"""
        return datetime.now(self.utc_tz)
    
    def to_local(self, utc_dt: datetime) -> datetime:
        """Convert UTC datetime to local timezone"""
        if utc_dt.tzinfo is None:
            utc_dt = self.utc_tz.localize(utc_dt)
        return utc_dt.astimezone(self.local_tz)
    
    def to_utc(self, local_dt: datetime) -> datetime:
        """Convert local datetime to UTC"""
        if local_dt.tzinfo is None:
            local_dt = self.local_tz.localize(local_dt)
        return local_dt.astimezone(self.utc_tz)
    
    def fetch_fpl_data(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Fetch data from FPL API with rate limiting"""
        url = f"{self.fpl_base_url}{endpoint}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✓ Fetched {endpoint}")
            
            time.sleep(self.rate_limit_delay)
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch {endpoint}: {e}")
            return None
    
    def supabase_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make a request to Supabase API"""
        url = f"{self.supabase_url}/rest/v1{endpoint}"
        headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == 'PUT':
                response = self.session.put(url, headers=headers, json=data, timeout=30)
            elif method.upper() == 'PATCH':
                response = self.session.patch(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except Exception as e:
            # Suppress repetitive schema errors
            if hasattr(e, 'response') and e.response is not None:
                error_text = e.response.text
                if "clearances_blocks_interceptions" in error_text and not hasattr(self, '_schema_error_logged'):
                    logger.error(f"❌ Schema error: Missing 'clearances_blocks_interceptions' column (suppressing further errors)")
                    self._schema_error_logged = True
                    return None
            
            logger.error(f"❌ Supabase API error {method} {endpoint}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current key metrics from Supabase for change detection"""
        try:
            metrics = {}
            
            # Check finished gameweeks count
            finished_gws = self.supabase_request('GET', '/gameweeks?finished=eq.true&select=count')
            if finished_gws is not None:
                metrics['finished_gameweeks'] = len(finished_gws)
            else:
                logger.error("❌ Failed to get finished gameweeks count")
                return {}
            
            # Get current gameweek deadline for deadline-based refresh
            current_gw = self.supabase_request('GET', '/gameweeks?is_current=eq.true&select=id,deadline_time')
            if current_gw and len(current_gw) > 0:
                metrics['current_gameweek'] = current_gw[0]['id']
                metrics['current_deadline'] = current_gw[0]['deadline_time']
            else:
                logger.warning("⚠ No current gameweek found")
                metrics['current_gameweek'] = 0
                metrics['current_deadline'] = None
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to get current metrics: {e}")
            return {}
    
    def load_previous_state(self) -> Dict[str, Any]:
        """Load previous monitoring state from file"""
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                logger.info(f"✓ Loaded previous state")
                return state
        except FileNotFoundError:
            logger.info("ℹ No previous state found, starting fresh")
            return {}
        except Exception as e:
            logger.error(f"❌ Failed to load previous state: {e}")
            return {}
    
    def save_current_state(self, metrics: Dict[str, Any], refresh_triggered: bool = False) -> bool:
        """Save current monitoring state to file"""
        try:
            state = {
                'timestamp': self.now_utc().isoformat(),
                'metrics': metrics
            }
            
            # If refresh was triggered by deadline, mark it
            if refresh_triggered and 'current_deadline' in metrics:
                state['metrics']['last_deadline_refresh'] = metrics['current_deadline']
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save state: {e}")
            return False
    
    def detect_changes(self, current_metrics: Dict[str, Any], previous_metrics: Dict[str, Any]) -> bool:
        """Detect if significant changes have occurred that require a refresh"""
        try:
            changes_detected = False
            
            # 1. Check for new finished gameweeks (primary trigger)
            if 'finished_gameweeks' in current_metrics and 'finished_gameweeks' in previous_metrics:
                if current_metrics['finished_gameweeks'] > previous_metrics['finished_gameweeks']:
                    logger.info(f"✓ New finished gameweek: {previous_metrics['finished_gameweeks']} → {current_metrics['finished_gameweeks']}")
                    changes_detected = True
            
            # 2. Check for deadline + 1 hour trigger (secondary trigger for manager changes)
            if self.should_refresh_after_deadline(current_metrics, previous_metrics):
                logger.info("✓ Deadline + 1h refresh triggered")
                changes_detected = True
            
            if not changes_detected:
                logger.info("ℹ No changes detected")
            
            return changes_detected
            
        except Exception as e:
            logger.error(f"❌ Failed to detect changes: {e}")
            return False
    
    def should_refresh_after_deadline(self, current_metrics: Dict[str, Any], previous_metrics: Dict[str, Any]) -> bool:
        """Check if we should refresh 1 hour after deadline"""
        try:
            # Check if we have current deadline info
            if 'current_deadline' not in current_metrics or current_metrics['current_deadline'] is None:
                return False
            
            current_deadline = current_metrics['current_deadline']
            
            # Check if we've already refreshed for this deadline
            if 'last_deadline_refresh' in previous_metrics:
                if previous_metrics['last_deadline_refresh'] == current_deadline:
                    return False  # Already refreshed for this deadline
            
            # Parse deadline time
            deadline_utc = datetime.fromisoformat(current_deadline.replace('Z', '+00:00'))
            deadline_pacific = deadline_utc.astimezone(self.local_tz)
            
            # Check if deadline + 1 hour has passed
            trigger_time = deadline_pacific + timedelta(hours=1)
            now = self.now_local()
            
            if now >= trigger_time:
                logger.info(f"✓ Deadline + 1h trigger: {deadline_pacific.strftime('%m/%d %H:%M')} → {trigger_time.strftime('%m/%d %H:%M')}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to check deadline refresh: {e}")
            return False
    
    def upsert_data(self, table_name: str, data: List[Dict[str, Any]]) -> bool:
        """Upsert data to a table using individual upserts"""
        try:
            success_count = 0
            for record in data:
                # Try to update first
                update_result = self.supabase_request('PATCH', f'/{table_name}?id=eq.{record["id"]}', record)
                if update_result is not None:
                    success_count += 1
                else:
                    # If update fails, try insert
                    insert_result = self.supabase_request('POST', f'/{table_name}', record)
                    if insert_result is not None:
                        success_count += 1
            
            if success_count == len(data):
                logger.info(f"✓ Updated {success_count} {table_name} records")
            else:
                logger.warning(f"⚠ Updated {success_count}/{len(data)} {table_name} records")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to update {table_name}: {e}")
            return False
    
    def sync_teams(self, teams_data: List[Dict[str, Any]]) -> bool:
        """Sync teams data to Supabase"""
        try:
            teams = []
            for team in teams_data:
                teams.append({
                    'id': team['id'],
                    'name': team['name'],
                    'short_name': team.get('short_name'),
                    'code': team.get('code'),
                    'position': team.get('position'),
                    'strength': team.get('strength'),
                    'strength_overall_home': team.get('strength_overall_home'),
                    'strength_overall_away': team.get('strength_overall_away'),
                    'strength_attack_home': team.get('strength_attack_home'),
                    'strength_attack_away': team.get('strength_attack_away'),
                    'strength_defence_home': team.get('strength_defence_home'),
                    'strength_defence_away': team.get('strength_defence_away'),
                    'updated_at': self.now_utc().isoformat()
                })
            
            return self.upsert_data('teams', teams)
            
        except Exception as e:
            logger.error(f"❌ Failed to sync teams: {e}")
            return False
    
    def sync_players(self, players_data: List[Dict[str, Any]]) -> bool:
        """Sync players data to Supabase"""
        try:
            players = []
            for player in players_data:
                players.append({
                    'id': player['id'],
                    'first_name': player.get('first_name'),
                    'second_name': player.get('second_name'),
                    'web_name': player.get('web_name'),
                    'team_id': player.get('team'),
                    'element_type': player.get('element_type'),
                    'now_cost': player.get('now_cost'),
                    'total_points': player.get('total_points', 0),
                    'form': player.get('form'),
                    'points_per_game': player.get('points_per_game'),
                    'value_form': player.get('value_form'),
                    'value_season': player.get('value_season'),
                    'chance_of_playing_next_round': player.get('chance_of_playing_next_round'),
                    'news': player.get('news'),
                    'news_added': player.get('news_added'),
                    'status': player.get('status', 'a'),
                    'special': player.get('special', False),
                    'can_select': player.get('can_select', True),
                    'can_transact': player.get('can_transact', True),
                    'in_dreamteam': player.get('in_dreamteam', False),
                    'removed': player.get('removed', False),
                    'updated_at': self.now_utc().isoformat()
                })
            
            return self.upsert_data('players', players)
            
        except Exception as e:
            logger.error(f"❌ Failed to sync players: {e}")
            return False
    
    def sync_gameweeks(self, events_data: List[Dict[str, Any]]) -> bool:
        """Sync gameweeks data to Supabase"""
        try:
            gameweeks = []
            for event in events_data:
                gameweeks.append({
                    'id': event['id'],
                    'name': event.get('name'),
                    'deadline_time': event.get('deadline_time'),
                    'is_current': event.get('is_current', False),
                    'is_next': event.get('is_next', False),
                    'is_previous': event.get('is_previous', False),
                    'finished': event.get('finished', False),
                    'data_checked': event.get('data_checked', False),
                    'highest_score': event.get('highest_score'),
                    'average_entry_score': event.get('average_entry_score'),
                    'updated_at': self.now_utc().isoformat()
                })
            
            return self.upsert_data('gameweeks', gameweeks)
            
        except Exception as e:
            logger.error(f"❌ Failed to sync gameweeks: {e}")
            return False
    
    def sync_fixtures(self, fixtures_data: List[Dict[str, Any]]) -> bool:
        """Sync fixtures data to Supabase"""
        try:
            fixtures = []
            for fixture in fixtures_data:
                fixtures.append({
                    'id': fixture['id'],
                    'gameweek_id': fixture.get('event'),
                    'home_team_id': fixture.get('team_h'),
                    'away_team_id': fixture.get('team_a'),
                    'home_team_score': fixture.get('team_h_score'),
                    'away_team_score': fixture.get('team_a_score'),
                    'finished': fixture.get('finished', False),
                    'kickoff_time': fixture.get('kickoff_time'),
                    'difficulty_home': fixture.get('team_h_difficulty'),
                    'difficulty_away': fixture.get('team_a_difficulty'),
                    'updated_at': self.now_utc().isoformat()
                })
            
            return self.upsert_data('fixtures', fixtures)
            
        except Exception as e:
            logger.error(f"❌ Failed to sync fixtures: {e}")
            return False
    
    def sync_player_gw_stats_from_live(self, gameweek_id: int) -> bool:
        """Sync player gameweek stats from live gameweek endpoint"""
        try:
            live_data = self.fetch_fpl_data(f"/event/{gameweek_id}/live/")
            if not live_data or 'elements' not in live_data:
                logger.warning(f"⚠ No live data for GW{gameweek_id}")
                return False
            
            player_stats = []
            for player_data in live_data['elements']:
                player_id = player_data['id']
                stats = player_data.get('stats', {})
                
                if stats.get('minutes', 0) > 0:
                    player_stats.append({
                        'player_id': player_id,
                        'gameweek_id': gameweek_id,
                        'minutes': stats.get('minutes', 0),
                        'goals_scored': stats.get('goals_scored', 0),
                        'assists': stats.get('assists', 0),
                        'clean_sheets': stats.get('clean_sheets', 0),
                        'goals_conceded': stats.get('goals_conceded', 0),
                        'own_goals': stats.get('own_goals', 0),
                        'penalties_saved': stats.get('penalties_saved', 0),
                        'penalties_missed': stats.get('penalties_missed', 0),
                        'yellow_cards': stats.get('yellow_cards', 0),
                        'red_cards': stats.get('red_cards', 0),
                        'saves': stats.get('saves', 0),
                        'bonus': stats.get('bonus', 0),
                        'bps': stats.get('bps', 0),
                        'influence': stats.get('influence'),
                        'creativity': stats.get('creativity'),
                        'threat': stats.get('threat'),
                        'ict_index': stats.get('ict_index'),
                        'total_points': stats.get('total_points', 0),
                        # Expected data fields
                        'expected_goals': stats.get('expected_goals', 0),
                        'expected_assists': stats.get('expected_assists', 0),
                        'expected_goal_involvements': stats.get('expected_goal_involvements', 0),
                        'expected_goals_conceded': stats.get('expected_goals_conceded', 0),
                        'clearances_blocks_interceptions': stats.get('clearances_blocks_interceptions', 0),
                        'recoveries': stats.get('recoveries', 0),
                        'tackles': stats.get('tackles', 0),
                        'defensive_contribution': stats.get('defensive_contribution', 0),
                        'starts': stats.get('starts', 0),
                        'updated_at': self.now_utc().isoformat()
                    })
            
            if player_stats:
                # For player_gw_stats, we need to handle the composite key differently
                success_count = 0
                for stats in player_stats:
                    # Try to update first
                    update_result = self.supabase_request('PATCH', 
                        f'/player_gw_stats?player_id=eq.{stats["player_id"]}&gameweek_id=eq.{stats["gameweek_id"]}', 
                        stats)
                    if update_result is not None:
                        success_count += 1
                    else:
                        # If update fails, try insert
                        insert_result = self.supabase_request('POST', '/player_gw_stats', [stats])
                        if insert_result is not None:
                            success_count += 1
                
                if success_count == len(player_stats):
                    logger.info(f"✓ Updated {success_count} player stats for GW{gameweek_id}")
                else:
                    logger.warning(f"⚠ Updated {success_count}/{len(player_stats)} player stats for GW{gameweek_id}")
                return success_count > 0
            else:
                logger.warning(f"⚠ No player stats found for GW{gameweek_id}")
                return True
            
        except Exception as e:
            logger.error(f"❌ Failed to sync player stats for GW{gameweek_id}: {e}")
            return False
    
    def get_registered_manager_ids(self) -> List[int]:
        """Get all registered manager IDs from user_entries table"""
        try:
            result = self.supabase_request('GET', '/user_entries?select=fpl_entry_id')
            if result is None:
                logger.warning("⚠ No registered managers found")
                return []
            
            manager_ids = [entry['fpl_entry_id'] for entry in result if entry.get('fpl_entry_id')]
            if manager_ids:
                logger.info(f"✓ Found {len(manager_ids)} registered managers")
            return manager_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to get manager IDs: {e}")
            return []
    
    def sync_user_entries(self) -> bool:
        """Sync all user entries from registered manager IDs"""
        try:
            manager_ids = self.get_registered_manager_ids()
            if not manager_ids:
                logger.info("ℹ No registered managers to sync")
                return True
            
            success_count = 0
            for manager_id in manager_ids:
                if self.sync_single_user_entry(manager_id):
                    success_count += 1
            
            if success_count == len(manager_ids):
                logger.info(f"✓ Updated {success_count} user entries")
            else:
                logger.warning(f"⚠ Updated {success_count}/{len(manager_ids)} user entries")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to sync user entries: {e}")
            return False
    
    def sync_single_user_entry(self, manager_id: int) -> bool:
        """Sync single user's entry data"""
        try:
            entry_data = self.fetch_fpl_data(f"/entry/{manager_id}/")
            if not entry_data:
                logger.warning(f"⚠ No entry data for manager {manager_id}")
                return False
            
            # Find the user_id for this manager_id
            user_result = self.supabase_request('GET', f'/user_entries?fpl_entry_id=eq.{manager_id}&select=user_id')
            if not user_result or len(user_result) == 0:
                logger.warning(f"⚠ No user found for manager {manager_id}")
                return False
            
            user_id = user_result[0]['user_id']
            
            # Update user_entries table
            user_entry = {
                'user_id': user_id,
                'fpl_entry_id': manager_id,
                'team_name': entry_data.get('name'),
                'total_points': entry_data.get('summary_overall_points', 0),
                'overall_rank': entry_data.get('summary_overall_rank'),
                'team_value': entry_data.get('last_deadline_value'),
                'bank': entry_data.get('last_deadline_bank'),
                'updated_at': self.now_utc().isoformat()
            }
            
            # Upsert user entry
            update_result = self.supabase_request('PATCH', f'/user_entries?fpl_entry_id=eq.{manager_id}', user_entry)
            if update_result is not None:
                return True
            else:
                logger.warning(f"⚠ Failed to update manager {manager_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to sync manager {manager_id}: {e}")
            return False
    
    def sync_user_picks_for_gameweek(self, manager_id: int, gameweek_id: int) -> bool:
        """Sync user's picks for specific gameweek"""
        try:
            picks_data = self.fetch_fpl_data(f"/entry/{manager_id}/event/{gameweek_id}/picks/")
            if not picks_data or 'picks' not in picks_data:
                logger.warning(f"⚠ No picks data for manager {manager_id} GW{gameweek_id}")
                return False
            
            # Find the user_id for this manager_id
            user_result = self.supabase_request('GET', f'/user_entries?fpl_entry_id=eq.{manager_id}&select=user_id')
            if not user_result or len(user_result) == 0:
                logger.warning(f"⚠ No user found for manager {manager_id}")
                return False
            
            user_id = user_result[0]['user_id']
            
            # Clear existing picks for this user/gameweek
            self.supabase_request('DELETE', f'/user_player_ownership?user_id=eq.{user_id}&gameweek_id=eq.{gameweek_id}')
            
            # Insert new picks
            picks = picks_data['picks']
            success_count = 0
            
            for pick in picks:
                player_id = pick['element']
                ownership_record = {
                    'user_id': user_id,
                    'player_id': player_id,
                    'gameweek_id': gameweek_id,
                    'owned': True,
                    'created_at': self.now_utc().isoformat()
                }
                
                insert_result = self.supabase_request('POST', '/user_player_ownership', [ownership_record])
                if insert_result is not None:
                    success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to sync picks for manager {manager_id} GW{gameweek_id}: {e}")
            return False
    
    def sync_user_picks_for_all_managers(self, gameweek_id: int) -> bool:
        """Sync user picks for all registered managers for a specific gameweek"""
        try:
            manager_ids = self.get_registered_manager_ids()
            if not manager_ids:
                logger.info(f"ℹ No registered managers to sync for GW{gameweek_id}")
                return True
            
            success_count = 0
            for manager_id in manager_ids:
                if self.sync_user_picks_for_gameweek(manager_id, gameweek_id):
                    success_count += 1
            
            if success_count == len(manager_ids):
                logger.info(f"✓ Updated picks for {success_count} managers (GW{gameweek_id})")
            else:
                logger.warning(f"⚠ Updated picks for {success_count}/{len(manager_ids)} managers (GW{gameweek_id})")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to sync picks for GW{gameweek_id}: {e}")
            return False
    
    def sync_team_gw_stats(self) -> bool:
        """Sync team gameweek stats by calling the populate function"""
        try:
            # Call the populate function
            result = self.supabase_request('POST', '/rpc/populate_team_gw_stats', {})
            if result is not None:
                logger.info("✓ Updated team gameweek stats")
                return True
            else:
                logger.error("❌ Failed to populate team gameweek stats")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to sync team gameweek stats: {e}")
            return False
    
    def get_current_gameweek_id(self) -> Optional[int]:
        """Get current gameweek ID"""
        try:
            current_gw = self.supabase_request('GET', '/gameweeks?is_current=eq.true&select=id')
            if current_gw and len(current_gw) > 0:
                return current_gw[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error getting current gameweek ID: {e}")
            return None
    
    def get_gameweeks_to_refresh(self) -> List[int]:
        """Get gameweeks that need refreshing (current + previous gameweek only)"""
        try:
            # Get current gameweek
            current_gw = self.get_current_gameweek_id()
            if not current_gw:
                logger.warning("No current gameweek found, skipping player stats refresh")
                return []
            
            # Only refresh current + previous (2 total)
            # This optimizes performance by skipping completed gameweeks that won't change
            gameweeks_to_refresh = [current_gw - 1, current_gw] if current_gw > 1 else [current_gw]
            
            logger.info(f"Optimized refresh: only refreshing gameweeks {gameweeks_to_refresh} (current={current_gw})")
            return gameweeks_to_refresh
            
        except Exception as e:
            logger.error(f"Error getting gameweeks to refresh: {e}")
            return []
    
    def test_connections(self) -> bool:
        """Test all API connections"""
        logger.info("🔍 Testing connections...")
        
        # Test FPL API
        fpl_data = self.fetch_fpl_data("/bootstrap-static/")
        if not fpl_data:
            logger.error("❌ FPL API connection failed")
            return False
        else:
            logger.info("✓ FPL API connected")
        
        # Test Supabase
        result = self.supabase_request('GET', '/teams?select=count')
        if result is None:
            logger.error("❌ Supabase connection failed")
            return False
        else:
            logger.info("✓ Supabase connected")
        
        return True
    
    def perform_refresh(self) -> bool:
        """Perform complete data refresh"""
        logger.info("🚀 Starting FPL data refresh")
        
        try:
            # Test connections first
            if not self.test_connections():
                return False
            
            # Fetch bootstrap data
            bootstrap_data = self.fetch_fpl_data("/bootstrap-static/")
            if not bootstrap_data:
                logger.error("❌ Failed to fetch bootstrap data")
                return False
            
            # Sync core data
            logger.info("📊 Syncing core data...")
            
            teams_success = self.sync_teams(bootstrap_data.get('teams', []))
            players_success = self.sync_players(bootstrap_data.get('elements', []))
            gameweeks_success = self.sync_gameweeks(bootstrap_data.get('events', []))
            
            if not all([teams_success, players_success, gameweeks_success]):
                logger.error("❌ Core data sync failed")
                return False
            
            # Sync fixtures
            fixtures_data = self.fetch_fpl_data("/fixtures/")
            if not fixtures_data:
                logger.error("❌ No fixtures data available")
                return False
            
            if not self.sync_fixtures(fixtures_data):
                logger.error("❌ Fixtures sync failed")
                return False
            
            # Sync player gameweek stats (optimized - only current + previous gameweek)
            logger.info("⚽ Syncing player stats...")
            gameweeks_to_refresh = self.get_gameweeks_to_refresh()
            
            stats_success = True
            for gw in gameweeks_to_refresh:
                if not self.sync_player_gw_stats_from_live(gw):
                    stats_success = False
            
            if not stats_success:
                logger.warning("⚠ Some player stats failed")
            
            # Sync user data (entries and picks)
            logger.info("👥 Syncing user data...")
            user_entries_success = self.sync_user_entries()
            
            # Sync user picks for optimized gameweeks (current + previous)
            if gameweeks_to_refresh:
                user_picks_success = True
                for gw in gameweeks_to_refresh:
                    if not self.sync_user_picks_for_all_managers(gw):
                        user_picks_success = False
                
                if not user_picks_success:
                    logger.warning("⚠ Some user picks failed")
            
            if not user_entries_success:
                logger.warning("⚠ Some user entries failed")
            
            # Sync team gameweek stats (aggregated from player_gw_stats and fixtures)
            logger.info("🏆 Syncing team stats...")
            team_stats_success = self.sync_team_gw_stats()
            if not team_stats_success:
                logger.warning("⚠ Team stats failed")
            
            logger.info("✅ Data refresh completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Refresh failed: {e}")
            return False
    
    def check_once(self) -> bool:
        """Perform a single check for changes and refresh if needed"""
        logger.info("🔍 Checking for changes...")
        
        # Get current metrics
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            logger.error("❌ Failed to get current metrics")
            return False
        
        # Load previous state
        previous_state = self.load_previous_state()
        previous_metrics = previous_state.get('metrics', {})
        
        # Detect changes
        changes_detected = self.detect_changes(current_metrics, previous_metrics)
        
        if changes_detected:
            logger.info("🔄 Changes detected, refreshing...")
            refresh_success = self.perform_refresh()
            
            if refresh_success:
                # Save new state after successful refresh
                self.save_current_state(current_metrics, refresh_triggered=True)
                return True
            else:
                logger.error("❌ Refresh failed, not updating state")
                return False
        else:
            # Still save current state for next check
            self.save_current_state(current_metrics)
            return True
    
    def start_service(self):
        """Start continuous monitoring service"""
        logger.info("🚀 Starting FPL data service")
        logger.info(f"⏰ Check interval: {self.check_interval/3600:.1f} hours")
        
        try:
            while True:
                logger.info("─" * 50)
                logger.info(f"🕐 Service check at {datetime.now().strftime('%m/%d %H:%M:%S')}")
                
                # Perform check
                success = self.check_once()
                
                if not success:
                    logger.error("❌ Check failed, retrying next interval")
                
                # Wait for next check
                logger.info(f"⏳ Next check in {self.check_interval/3600:.1f} hours")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Service stopped by user")
        except Exception as e:
            logger.error(f"❌ Service error: {e}")
            logger.info("🛑 Service stopped")
    
    def test_monitoring(self) -> bool:
        """Test monitoring logic without triggering refresh"""
        logger.info("🧪 Testing monitoring logic...")
        
        # Get current metrics
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            logger.error("❌ Failed to get current metrics")
            return False
        
        logger.info(f"📊 Current: {current_metrics}")
        
        # Load previous state
        previous_state = self.load_previous_state()
        previous_metrics = previous_state.get('metrics', {})
        
        if previous_metrics:
            logger.info(f"📊 Previous: {previous_metrics}")
            changes_detected = self.detect_changes(current_metrics, previous_metrics)
            logger.info(f"🔄 Changes detected: {changes_detected}")
        else:
            logger.info("ℹ No previous state, would trigger refresh on first run")
        
        return True
    
    def test_team_gw_stats(self) -> bool:
        """Test team gameweek stats functionality"""
        logger.info("🧪 Testing team gameweek stats...")
        
        try:
            # Test if team_gw_stats table exists and has data
            result = self.supabase_request('GET', '/team_gw_stats?select=count')
            if result is not None:
                count = len(result) if isinstance(result, list) else 0
                logger.info(f"✓ Team stats table: {count} records")
                
                # Test a sample query
                sample = self.supabase_request('GET', '/team_gw_stats?limit=3&select=team_id,gameweek_id,is_home,goals_for,goals_against,total_fantasy_points')
                if sample:
                    logger.info(f"✓ Sample data: {sample}")
                    return True
                else:
                    logger.warning("⚠ No sample data found")
                    return False
            else:
                logger.error("❌ Team stats table not accessible")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to test team stats: {e}")
            return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='FPL Unified Data Service')
    parser.add_argument('--test', action='store_true', help='Test connections and monitoring logic only')
    parser.add_argument('--test-team-stats', action='store_true', help='Test team gameweek stats functionality')
    parser.add_argument('--once', action='store_true', help='Check once and exit')
    parser.add_argument('--refresh', action='store_true', help='Force immediate refresh')
    
    args = parser.parse_args()
    
    service = FPLService()
    
    try:
        if args.test:
            success = service.test_monitoring()
        elif args.test_team_stats:
            success = service.test_team_gw_stats()
        elif args.refresh:
            success = service.perform_refresh()
        elif args.once:
            success = service.check_once()
        else:
            service.start_service()
            success = True
        
        if not success:
            exit(1)
            
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
