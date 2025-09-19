# FPL Research - Database & Service Architecture

A comprehensive Fantasy Premier League data analysis system with automated data synchronization, user management, and performance tracking.

## 🏗️ Database Architecture

### Core Tables

#### **`teams`** (14 columns)
Premier League teams with performance statistics
- **Key Fields**: `id`, `name`, `short_name`, `code`, `strength_*` (home/away/attack/defence)
- **Update Logic**: Refreshed from FPL API `/bootstrap-static/` endpoint
- **Frequency**: On every service run (teams rarely change)

#### **`players`** (23 columns) 
FPL players with current season statistics and pricing
- **Key Fields**: `id`, `web_name`, `team_id`, `element_type`, `now_cost`, `total_points`, `form`, `status`
- **Update Logic**: Refreshed from FPL API `/bootstrap-static/` endpoint
- **Frequency**: On every service run (player data changes frequently)

#### **`gameweeks`** (12 columns)
FPL gameweeks with deadlines and completion status
- **Key Fields**: `id`, `name`, `deadline_time`, `is_current`, `is_next`, `finished`
- **Update Logic**: Refreshed from FPL API `/bootstrap-static/` endpoint
- **Frequency**: On every service run (deadlines and status change)

#### **`fixtures`** (12 columns)
Match fixtures between teams with scores and difficulty ratings
- **Key Fields**: `id`, `gameweek_id`, `home_team_id`, `away_team_id`, `home_team_score`, `away_team_score`, `finished`
- **Update Logic**: Refreshed from FPL API `/bootstrap-static/` endpoint
- **Frequency**: On every service run (scores update after matches)

#### **`player_gw_stats`** (33 columns)
Player performance statistics per gameweek with expected data
- **Key Fields**: `player_id`, `gameweek_id`, `fixture_id`, `minutes`, `goals_scored`, `assists`, `total_points`, `expected_*` columns
- **Update Logic**: Refreshed from FPL API `/element-summary/{player_id}/` endpoints
- **Frequency**: Only for current/previous gameweeks when data changes
- **Unique Constraint**: `(player_id, gameweek_id)` prevents duplicates

#### **`team_gw_stats`** (42 columns)
Team performance statistics per gameweek, aggregated from player data
- **Key Fields**: `team_id`, `gameweek_id`, `fixture_id`, `is_home`, `opponent_team_id`, `goals_for`, `goals_against`, `result`
- **Update Logic**: **Automatically calculated** using `populate_team_gw_stats()` function
- **Frequency**: Regenerated after player_gw_stats updates
- **Data Source**: Aggregated from `player_gw_stats` and `fixtures` tables

### User Management Tables

#### **`user_entries`** (Enhanced)
User FPL team entries with ownership tracking and rank analysis
- **Key Fields**: `user_id`, `fpl_entry_id`, `team_name`, `total_points`, `overall_rank`, `current_player_ids[]`, `rank_delta`
- **Update Logic**: Refreshed from FPL API `/entry/{entry_id}/` endpoints
- **Frequency**: On every service run for active users
- **Enhanced Features**: 
  - `current_player_ids[]` - Array of currently owned player IDs
  - `rank_delta` - Automatic rank change calculation (negative = improvement)

#### **`user_gameweek_history`** (Historical Performance)
Historical manager performance data per gameweek with chip usage
- **Key Fields**: `user_id`, `gameweek_id`, `points`, `total_points`, `overall_rank`, `player_ids[]`, `chips_played[]`
- **Update Logic**: Refreshed from FPL API `/entry/{entry_id}/history/` endpoints
- **Frequency**: Only for new gameweeks or when historical data changes
- **Features**: Chip usage tracking, percentile rankings, transfer history

#### **`user_transfers`** (Transfer History)
Detailed transfer history for each manager
- **Key Fields**: `user_id`, `gameweek_id`, `player_in_id`, `player_out_id`, `transfer_cost`
- **Update Logic**: Refreshed from FPL API `/entry/{entry_id}/transfers/` endpoints
- **Frequency**: Only when new transfers are detected

## 🔄 Data Update Mechanisms

### **FPL Service (`fpl_service.py`)**
The main service that orchestrates all data updates with intelligent change detection.

#### **Update Logic**
1. **Change Detection**: Compares current FPL API data with stored state
2. **Selective Updates**: Only updates tables when data actually changes
3. **Dependency Management**: Updates dependent tables after core data changes
4. **Error Handling**: Continues running even if individual operations fail

#### **Update Frequency**
- **Continuous Mode**: Checks every hour, updates only when changes detected
- **One-time Mode**: Single check and update
- **Test Mode**: Validates connections without making changes

#### **State Management**
- **File-based State**: `service_state.json` tracks last update timestamps
- **Change Detection**: Compares API responses with stored state
- **Efficient Updates**: Only processes changed data

### **Automatic Functions**

#### **`auto_map_fixture_id()`**
- **Purpose**: Automatically links player stats to specific fixtures
- **Trigger**: Before inserting new `player_gw_stats` records
- **Logic**: Matches player team + gameweek to fixture home/away teams

#### **`populate_team_gw_stats()`**
- **Purpose**: Aggregates team statistics from player data
- **Trigger**: Called after player_gw_stats updates
- **Logic**: 
  - Clears existing team stats
  - Aggregates player stats by team and gameweek
  - Calculates form metrics (3-gameweek and 6-gameweek averages)

#### **`calculate_rank_delta()`**
- **Purpose**: Tracks rank changes for user entries
- **Trigger**: Before updating `user_entries` records
- **Logic**: Calculates difference between old and new overall rank

#### **`update_user_entries_summary()`**
- **Purpose**: Updates summary statistics when gameweek history changes
- **Trigger**: After inserting/updating `user_gameweek_history`
- **Logic**: Recalculates best/worst ranks, total transfers, chips used

## 🔒 Security & Performance

### **Row Level Security (RLS)**
- **Public Tables**: `teams`, `players`, `gameweeks`, `fixtures`, `player_gw_stats`, `team_gw_stats`
- **User Tables**: `user_entries`, `user_gameweek_history`, `user_transfers` (user-specific access)
- **Service Role**: Full access for data synchronization

### **Performance Indexes**
- **Primary Lookups**: All foreign keys and unique constraints
- **Query Optimization**: Composite indexes for common query patterns
- **Array Operations**: GIN indexes for `player_ids[]` and `chips_played[]` columns

### **Timezone Configuration**
- **Pacific Time**: All timestamps stored and displayed in `America/Los_Angeles`
- **Consistent Handling**: Functions ensure timezone consistency across all operations

## 🚀 Usage

### **Database Setup**
1. Run `consolidated_schema.sql` in Supabase SQL editor
2. Configure environment variables for FPL API and Supabase
3. Start the service: `python fpl_service.py`

### **Service Modes**
```bash
python fpl_service.py           # Continuous monitoring
python fpl_service.py --once    # Single check
python fpl_service.py --test    # Test connections
python fpl_service.py --refresh # Force immediate refresh
```

### **Backend API**
The `backend/` directory contains a FastAPI service for iOS app integration with endpoints for querying the database.

## 📊 Key Features

- **Intelligent Monitoring**: Only updates when data changes
- **Automatic Aggregation**: Team stats calculated from player data
- **User Management**: Complete ownership tracking and rank analysis
- **Historical Tracking**: Gameweek-by-gameweek performance history
- **Chip Usage**: Detailed tracking of FPL chips (wildcard, free hit, etc.)
- **Transfer History**: Complete transfer tracking with costs
- **Rank Analysis**: Automatic rank change calculations
- **Expected Data**: Full support for FPL's expected goals/assists metrics
- **Pacific Timezone**: Consistent timezone handling throughout

## 🔧 Maintenance

- **Logs**: Service logs provide detailed update information
- **State Files**: `service_state.json` tracks update timestamps
- **Error Handling**: Service continues running even if individual operations fail
- **Monitoring**: Built-in health checks and connection validation