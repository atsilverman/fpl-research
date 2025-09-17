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
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import argparse
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fpl_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
        
        # HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FPL-Service/1.0',
            'Accept': 'application/json'
        })
    
    def fetch_fpl_data(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Fetch data from FPL API with rate limiting"""
        url = f"{self.fpl_base_url}{endpoint}"
        
        try:
            logger.info(f"Fetching {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched {endpoint}")
            
            time.sleep(self.rate_limit_delay)
            return data
            
        except Exception as e:
            logger.error(f"Error fetching {endpoint}: {e}")
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
            logger.error(f"Supabase API error {method} {endpoint}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            return None
    
    def get_current_metrics(self) -> Dict[str, int]:
        """Get current key metrics from Supabase for change detection"""
        try:
            metrics = {}
            
            # Check finished gameweeks count
            finished_gws = self.supabase_request('GET', '/gameweeks?finished=eq.true&select=count')
            if finished_gws is not None:
                metrics['finished_gameweeks'] = len(finished_gws)
            else:
                logger.error("Failed to get finished gameweeks count")
                return {}
            
            # Check total fixtures count
            fixtures = self.supabase_request('GET', '/fixtures?select=count')
            if fixtures is not None:
                metrics['total_fixtures'] = len(fixtures)
            else:
                logger.error("Failed to get fixtures count")
                return {}
            
            # Check total player stats count
            player_stats = self.supabase_request('GET', '/player_gw_stats?select=count')
            if player_stats is not None:
                metrics['total_player_stats'] = len(player_stats)
            else:
                logger.error("Failed to get player stats count")
                return {}
            
            # Check current gameweek
            current_gw = self.supabase_request('GET', '/gameweeks?is_current=eq.true&select=id')
            if current_gw and len(current_gw) > 0:
                metrics['current_gameweek'] = current_gw[0]['id']
            else:
                logger.warning("No current gameweek found")
                metrics['current_gameweek'] = 0
            
            # Check next gameweek
            next_gw = self.supabase_request('GET', '/gameweeks?is_next=eq.true&select=id')
            if next_gw and len(next_gw) > 0:
                metrics['next_gameweek'] = next_gw[0]['id']
            else:
                logger.warning("No next gameweek found")
                metrics['next_gameweek'] = 0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting current metrics: {e}")
            return {}
    
    def load_previous_state(self) -> Dict[str, int]:
        """Load previous monitoring state from file"""
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                logger.info(f"Loaded previous state: {state}")
                return state
        except FileNotFoundError:
            logger.info("No previous state file found, starting fresh")
            return {}
        except Exception as e:
            logger.error(f"Error loading previous state: {e}")
            return {}
    
    def save_current_state(self, metrics: Dict[str, int]) -> bool:
        """Save current monitoring state to file"""
        try:
            state = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metrics': metrics
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"Saved current state: {metrics}")
            return True
        except Exception as e:
            logger.error(f"Error saving current state: {e}")
            return False
    
    def detect_changes(self, current_metrics: Dict[str, int], previous_metrics: Dict[str, int]) -> bool:
        """Detect if significant changes have occurred that require a refresh"""
        try:
            changes_detected = False
            
            # Check for new finished gameweeks
            if 'finished_gameweeks' in current_metrics and 'finished_gameweeks' in previous_metrics:
                if current_metrics['finished_gameweeks'] > previous_metrics['finished_gameweeks']:
                    logger.info(f"New finished gameweek detected: {previous_metrics['finished_gameweeks']} -> {current_metrics['finished_gameweeks']}")
                    changes_detected = True
            
            # Check for new fixtures
            if 'total_fixtures' in current_metrics and 'total_fixtures' in previous_metrics:
                if current_metrics['total_fixtures'] > previous_metrics['total_fixtures']:
                    logger.info(f"New fixtures detected: {previous_metrics['total_fixtures']} -> {current_metrics['total_fixtures']}")
                    changes_detected = True
            
            # Check for current gameweek change
            if 'current_gameweek' in current_metrics and 'current_gameweek' in previous_metrics:
                if current_metrics['current_gameweek'] != previous_metrics['current_gameweek']:
                    logger.info(f"Current gameweek changed: {previous_metrics['current_gameweek']} -> {current_metrics['current_gameweek']}")
                    changes_detected = True
            
            # Check for next gameweek change
            if 'next_gameweek' in current_metrics and 'next_gameweek' in previous_metrics:
                if current_metrics['next_gameweek'] != previous_metrics['next_gameweek']:
                    logger.info(f"Next gameweek changed: {previous_metrics['next_gameweek']} -> {current_metrics['next_gameweek']}")
                    changes_detected = True
            
            if not changes_detected:
                logger.info("No significant changes detected")
            
            return changes_detected
            
        except Exception as e:
            logger.error(f"Error detecting changes: {e}")
            return False
    
    def upsert_data(self, table_name: str, data: List[Dict[str, Any]]) -> bool:
        """Upsert data to a table using individual upserts"""
        try:
            logger.info(f"Upserting {len(data)} records to {table_name}")
            
            success_count = 0
            for record in data:
                # Try to update first
                update_result = self.supabase_request('PATCH', f'/{table_name}?id=eq.{record["id"]}', record)
                if update_result is not None:
                    success_count += 1
                else:
                    # If update fails, try insert
                    insert_result = self.supabase_request('POST', f'/{table_name}', [record])
                    if insert_result is not None:
                        success_count += 1
            
            logger.info(f"Successfully upserted {success_count}/{len(data)} records to {table_name}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error upserting data to {table_name}: {e}")
            return False
    
    def sync_teams(self, teams_data: List[Dict[str, Any]]) -> bool:
        """Sync teams data to Supabase"""
        try:
            logger.info(f"Syncing {len(teams_data)} teams")
            
            teams = []
            for team in teams_data:
                teams.append({
                    'id': team['id'],
                    'name': team['name'],
                    'short_name': team.get('short_name'),
                    'code': team.get('code'),
                    'form': team.get('form'),
                    'points': team.get('points', 0),
                    'position': team.get('position'),
                    'played': team.get('played', 0),
                    'win': team.get('win', 0),
                    'draw': team.get('draw', 0),
                    'loss': team.get('loss', 0),
                    'goals_for': team.get('goals_for', 0),
                    'goals_against': team.get('goals_against', 0),
                    'goal_difference': team.get('goal_difference', 0),
                    'strength': team.get('strength'),
                    'strength_overall_home': team.get('strength_overall_home'),
                    'strength_overall_away': team.get('strength_overall_away'),
                    'strength_attack_home': team.get('strength_attack_home'),
                    'strength_attack_away': team.get('strength_attack_away'),
                    'strength_defence_home': team.get('strength_defence_home'),
                    'strength_defence_away': team.get('strength_defence_away'),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })
            
            return self.upsert_data('teams', teams)
            
        except Exception as e:
            logger.error(f"Error syncing teams: {e}")
            return False
    
    def sync_players(self, players_data: List[Dict[str, Any]]) -> bool:
        """Sync players data to Supabase"""
        try:
            logger.info(f"Syncing {len(players_data)} players")
            
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
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })
            
            return self.upsert_data('players', players)
            
        except Exception as e:
            logger.error(f"Error syncing players: {e}")
            return False
    
    def sync_gameweeks(self, events_data: List[Dict[str, Any]]) -> bool:
        """Sync gameweeks data to Supabase"""
        try:
            logger.info(f"Syncing {len(events_data)} gameweeks")
            
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
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })
            
            return self.upsert_data('gameweeks', gameweeks)
            
        except Exception as e:
            logger.error(f"Error syncing gameweeks: {e}")
            return False
    
    def sync_fixtures(self, fixtures_data: List[Dict[str, Any]]) -> bool:
        """Sync fixtures data to Supabase"""
        try:
            logger.info(f"Syncing {len(fixtures_data)} fixtures")
            
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
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })
            
            return self.upsert_data('fixtures', fixtures)
            
        except Exception as e:
            logger.error(f"Error syncing fixtures: {e}")
            return False
    
    def sync_player_gw_stats_from_live(self, gameweek_id: int) -> bool:
        """Sync player gameweek stats from live gameweek endpoint"""
        try:
            logger.info(f"Syncing player stats for gameweek {gameweek_id}")
            
            live_data = self.fetch_fpl_data(f"/event/{gameweek_id}/live/")
            if not live_data or 'elements' not in live_data:
                logger.warning(f"No live data available for gameweek {gameweek_id}")
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
                        'value': stats.get('value'),
                        'selected_by_percent': stats.get('selected_by_percent'),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    })
            
            if player_stats:
                logger.info(f"Upserting {len(player_stats)} player stats for gameweek {gameweek_id}")
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
                
                logger.info(f"Successfully upserted {success_count}/{len(player_stats)} player stats for gameweek {gameweek_id}")
                return success_count > 0
            else:
                logger.warning(f"No player stats found for gameweek {gameweek_id}")
                return True
            
        except Exception as e:
            logger.error(f"Error syncing player stats for gameweek {gameweek_id}: {e}")
            return False
    
    def test_connections(self) -> bool:
        """Test all API connections"""
        logger.info("Testing connections...")
        
        # Test FPL API
        fpl_data = self.fetch_fpl_data("/bootstrap-static/")
        if not fpl_data:
            logger.error("❌ Failed to connect to FPL API")
            return False
        else:
            logger.info("✅ FPL API connection successful")
        
        # Test Supabase
        result = self.supabase_request('GET', '/teams?select=count')
        if result is None:
            logger.error("❌ Failed to connect to Supabase")
            return False
        else:
            logger.info("✅ Supabase connection successful")
        
        return True
    
    def perform_refresh(self) -> bool:
        """Perform complete data refresh"""
        logger.info("Starting complete FPL data refresh")
        
        try:
            # Test connections first
            if not self.test_connections():
                return False
            
            # Fetch bootstrap data
            bootstrap_data = self.fetch_fpl_data("/bootstrap-static/")
            if not bootstrap_data:
                logger.error("Failed to fetch bootstrap data")
                return False
            
            # Sync core data
            logger.info("Refreshing core tables...")
            
            teams_success = self.sync_teams(bootstrap_data.get('teams', []))
            players_success = self.sync_players(bootstrap_data.get('elements', []))
            gameweeks_success = self.sync_gameweeks(bootstrap_data.get('events', []))
            
            if not all([teams_success, players_success, gameweeks_success]):
                logger.error("Failed to sync core data")
                return False
            
            # Sync fixtures
            fixtures_data = self.fetch_fpl_data("/fixtures/")
            if fixtures_data:
                fixtures_success = self.sync_fixtures(fixtures_data)
                if not fixtures_success:
                    logger.error("Failed to sync fixtures")
                    return False
            else:
                logger.error("No fixtures data available")
                return False
            
            # Sync player gameweek stats (for completed gameweeks)
            logger.info("Syncing player gameweek stats...")
            completed_gws = [gw for gw in bootstrap_data.get('events', []) if gw.get('finished', False)]
            max_gw = max([gw['id'] for gw in completed_gws]) if completed_gws else 4
            
            stats_success = True
            for gw in range(1, max_gw + 1):
                if not self.sync_player_gw_stats_from_live(gw):
                    logger.warning(f"Failed to sync gameweek {gw} stats")
                    stats_success = False
            
            if not stats_success:
                logger.warning("Some player stats failed to sync")
            
            logger.info("Complete data refresh finished successfully")
            return True
            
        except Exception as e:
            logger.error(f"Complete refresh failed: {e}")
            return False
    
    def check_once(self) -> bool:
        """Perform a single check for changes and refresh if needed"""
        logger.info("Performing single change check...")
        
        # Get current metrics
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            logger.error("Failed to get current metrics")
            return False
        
        # Load previous state
        previous_state = self.load_previous_state()
        previous_metrics = previous_state.get('metrics', {})
        
        # Detect changes
        changes_detected = self.detect_changes(current_metrics, previous_metrics)
        
        if changes_detected:
            logger.info("Changes detected, performing refresh...")
            refresh_success = self.perform_refresh()
            
            if refresh_success:
                # Save new state after successful refresh
                self.save_current_state(current_metrics)
                return True
            else:
                logger.error("Refresh failed, not updating state")
                return False
        else:
            logger.info("No changes detected, no refresh needed")
            # Still save current state for next check
            self.save_current_state(current_metrics)
            return True
    
    def start_service(self):
        """Start continuous monitoring service"""
        logger.info("Starting FPL unified data service")
        logger.info(f"Check interval: {self.check_interval} seconds ({self.check_interval/3600:.1f} hours)")
        
        try:
            while True:
                logger.info("=" * 50)
                logger.info(f"Service check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Perform check
                success = self.check_once()
                
                if not success:
                    logger.error("Check failed, will retry on next interval")
                
                # Wait for next check
                logger.info(f"Waiting {self.check_interval} seconds until next check...")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
        except Exception as e:
            logger.error(f"Service error: {e}")
            logger.info("Service stopped")
    
    def test_monitoring(self) -> bool:
        """Test monitoring logic without triggering refresh"""
        logger.info("Testing monitoring logic...")
        
        # Get current metrics
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            logger.error("Failed to get current metrics")
            return False
        
        logger.info(f"Current metrics: {current_metrics}")
        
        # Load previous state
        previous_state = self.load_previous_state()
        previous_metrics = previous_state.get('metrics', {})
        
        if previous_metrics:
            logger.info(f"Previous metrics: {previous_metrics}")
            changes_detected = self.detect_changes(current_metrics, previous_metrics)
            logger.info(f"Changes detected: {changes_detected}")
        else:
            logger.info("No previous state found, would trigger refresh on first run")
        
        return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='FPL Unified Data Service')
    parser.add_argument('--test', action='store_true', help='Test connections and monitoring logic only')
    parser.add_argument('--once', action='store_true', help='Check once and exit')
    parser.add_argument('--refresh', action='store_true', help='Force immediate refresh')
    
    args = parser.parse_args()
    
    service = FPLService()
    
    try:
        if args.test:
            success = service.test_monitoring()
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
