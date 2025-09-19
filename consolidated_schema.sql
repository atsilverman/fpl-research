-- FPL Vibe Database Schema - Complete Consolidated Version
-- Project: fpl-research
-- Created: 2025-01-27
-- Purpose: Single source of truth for the complete FPL Vibe database schema
-- Includes: Core tables, user features, gameweek history, and all necessary functions

-- =============================================
-- TIMEZONE CONFIGURATION
-- =============================================

-- Set timezone for the current session
SET timezone = 'America/Los_Angeles';

-- Set timezone for the database (persistent across all connections)
ALTER DATABASE postgres SET timezone = 'America/Los_Angeles';

-- Set timezone for the current user (persistent for this user)
ALTER USER postgres SET timezone = 'America/Los_Angeles';

-- =============================================
-- EXTENSIONS AND TYPES
-- =============================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types
CREATE TYPE player_position AS ENUM ('GK', 'DEF', 'MID', 'FWD');
CREATE TYPE match_result AS ENUM ('W', 'D', 'L');
CREATE TYPE player_status AS ENUM ('a', 'd', 'i', 'n', 's', 'u'); -- available, doubtful, injured, not available, suspended, unavailable

-- =============================================
-- CORE TABLES
-- =============================================

-- Teams table
CREATE TABLE teams (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(20),
    code INTEGER UNIQUE,
    position INTEGER,
    strength INTEGER,
    strength_overall_home INTEGER,
    strength_overall_away INTEGER,
    strength_attack_home INTEGER,
    strength_attack_away INTEGER,
    strength_defence_home INTEGER,
    strength_defence_away INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Players table
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    first_name VARCHAR(50),
    second_name VARCHAR(50),
    web_name VARCHAR(50) NOT NULL,
    team_id INTEGER REFERENCES teams(id),
    element_type INTEGER NOT NULL, -- 1=GK, 2=DEF, 3=MID, 4=FWD
    now_cost INTEGER NOT NULL, -- Price in 0.1M units (e.g., 100 = £10.0M)
    total_points INTEGER DEFAULT 0,
    form DECIMAL(4,2),
    points_per_game DECIMAL(4,2),
    value_form DECIMAL(4,2),
    value_season DECIMAL(4,2),
    chance_of_playing_next_round INTEGER,
    news TEXT,
    news_added TIMESTAMP WITH TIME ZONE,
    status player_status DEFAULT 'a',
    special BOOLEAN DEFAULT FALSE,
    can_select BOOLEAN DEFAULT TRUE,
    can_transact BOOLEAN DEFAULT TRUE,
    in_dreamteam BOOLEAN DEFAULT FALSE,
    removed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Gameweeks table
CREATE TABLE gameweeks (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    deadline_time TIMESTAMP WITH TIME ZONE NOT NULL,
    is_current BOOLEAN DEFAULT FALSE,
    is_next BOOLEAN DEFAULT FALSE,
    is_previous BOOLEAN DEFAULT FALSE,
    finished BOOLEAN DEFAULT FALSE,
    data_checked BOOLEAN DEFAULT FALSE,
    highest_score INTEGER,
    average_entry_score DECIMAL(4,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Fixtures table
CREATE TABLE fixtures (
    id INTEGER PRIMARY KEY,
    gameweek_id INTEGER REFERENCES gameweeks(id),
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    home_team_score INTEGER,
    away_team_score INTEGER,
    finished BOOLEAN DEFAULT FALSE,
    kickoff_time TIMESTAMP WITH TIME ZONE,
    difficulty_home INTEGER,
    difficulty_away INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Player gameweek stats table (with expected data columns)
CREATE TABLE player_gw_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    gameweek_id INTEGER REFERENCES gameweeks(id),
    fixture_id INTEGER REFERENCES fixtures(id),
    minutes INTEGER DEFAULT 0,
    goals_scored INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    clean_sheets INTEGER DEFAULT 0,
    goals_conceded INTEGER DEFAULT 0,
    own_goals INTEGER DEFAULT 0,
    penalties_saved INTEGER DEFAULT 0,
    penalties_missed INTEGER DEFAULT 0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    bonus INTEGER DEFAULT 0,
    bps INTEGER DEFAULT 0,
    influence DECIMAL(6,2),
    creativity DECIMAL(6,2),
    threat DECIMAL(6,2),
    ict_index DECIMAL(6,2),
    total_points INTEGER DEFAULT 0,
    -- Expected data columns (available in FPL API)
    expected_goals DECIMAL(6,2) DEFAULT 0,
    expected_assists DECIMAL(6,2) DEFAULT 0,
    expected_goal_involvements DECIMAL(6,2) DEFAULT 0,
    expected_goals_conceded DECIMAL(6,2) DEFAULT 0,
    clearances_blocks_interceptions INTEGER DEFAULT 0,
    recoveries INTEGER DEFAULT 0,
    tackles INTEGER DEFAULT 0,
    defensive_contribution INTEGER DEFAULT 0,
    starts INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(player_id, gameweek_id)
);

-- Team gameweek stats table (aggregated from player_gw_stats and fixtures)
CREATE TABLE team_gw_stats (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    gameweek_id INTEGER REFERENCES gameweeks(id),
    fixture_id INTEGER REFERENCES fixtures(id),
    
    -- Match context
    is_home BOOLEAN NOT NULL,
    opponent_team_id INTEGER REFERENCES teams(id),
    difficulty INTEGER, -- From fixture difficulty_home or difficulty_away
    
    -- Match results (from fixtures table)
    goals_for INTEGER DEFAULT 0,
    goals_against INTEGER DEFAULT 0,
    result VARCHAR(1), -- 'W', 'D', 'L'
    clean_sheets INTEGER DEFAULT 0, -- 1 if goals_against = 0, 0 otherwise
    
    -- Fantasy performance (aggregated from players)
    total_fantasy_points INTEGER DEFAULT 0,
    avg_fantasy_points DECIMAL(6,2) DEFAULT 0,
    players_played INTEGER DEFAULT 0,
    players_started INTEGER DEFAULT 0,
    
    -- Attacking stats (from player_gw_stats - FPL API available)
    goals_scored INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    own_goals INTEGER DEFAULT 0,
    penalties_missed INTEGER DEFAULT 0,
    
    -- Expected attacking stats (from player_gw_stats - FPL API available)
    expected_goals DECIMAL(6,2) DEFAULT 0,
    expected_assists DECIMAL(6,2) DEFAULT 0,
    expected_goal_involvements DECIMAL(6,2) DEFAULT 0,
    
    -- Defensive stats (from player_gw_stats - FPL API available)
    saves INTEGER DEFAULT 0,
    penalties_saved INTEGER DEFAULT 0,
    tackles INTEGER DEFAULT 0,
    clearances_blocks_interceptions INTEGER DEFAULT 0,
    recoveries INTEGER DEFAULT 0,
    defensive_contribution INTEGER DEFAULT 0,
    
    -- Discipline stats (from player_gw_stats - FPL API available)
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    
    -- ICT metrics (from player_gw_stats - FPL API available)
    total_influence DECIMAL(8,2) DEFAULT 0,
    total_creativity DECIMAL(8,2) DEFAULT 0,
    total_threat DECIMAL(8,2) DEFAULT 0,
    total_ict_index DECIMAL(8,2) DEFAULT 0,
    avg_influence DECIMAL(6,2) DEFAULT 0,
    avg_creativity DECIMAL(6,2) DEFAULT 0,
    avg_threat DECIMAL(6,2) DEFAULT 0,
    avg_ict_index DECIMAL(6,2) DEFAULT 0,
    
    -- Form and trends (calculated)
    form_6_gw DECIMAL(4,2) DEFAULT 0, -- Points per game over last 6 gameweeks
    form_3_gw DECIMAL(4,2) DEFAULT 0, -- Points per game over last 3 gameweeks
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(team_id, gameweek_id)
);

-- =============================================
-- USER TABLES
-- =============================================

-- User entries table (for ownership tracking)
CREATE TABLE user_entries (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    fpl_entry_id INTEGER UNIQUE,
    team_name VARCHAR(100),
    total_points INTEGER DEFAULT 0,
    overall_rank INTEGER,
    team_value INTEGER,
    bank INTEGER,
    
    -- Enhanced user features
    current_player_ids INTEGER[] DEFAULT '{}',  -- Array of player IDs currently owned
    previous_rank INTEGER,                       -- Previous gameweek rank
    rank_delta INTEGER,                          -- Rank change (+/-)
    current_gameweek_id INTEGER REFERENCES gameweeks(id),
    
    -- Current season summary
    best_rank INTEGER,
    worst_rank INTEGER,
    best_gameweek_id INTEGER REFERENCES gameweeks(id),
    worst_gameweek_id INTEGER REFERENCES gameweeks(id),
    total_transfers INTEGER DEFAULT 0,
    total_transfer_cost INTEGER DEFAULT 0,
    chips_used JSONB DEFAULT '[]'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User gameweek history table (enhanced version with chip usage)
CREATE TABLE user_gameweek_history (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    gameweek_id INTEGER REFERENCES gameweeks(id),
    
    -- Performance metrics
    points INTEGER NOT NULL DEFAULT 0,                    -- Points this gameweek
    total_points INTEGER NOT NULL DEFAULT 0,              -- Cumulative points
    overall_rank INTEGER,                                 -- Overall ranking
    gameweek_rank INTEGER,                                -- Rank for this gameweek
    percentile_rank INTEGER,                              -- Percentile (1-100)
    
    -- Team management
    bank INTEGER DEFAULT 0,                               -- Money in bank
    team_value INTEGER DEFAULT 0,                         -- Team value
    transfers_made INTEGER DEFAULT 0,                     -- Transfers this gameweek
    transfer_cost INTEGER DEFAULT 0,                      -- Cost of transfers
    points_on_bench INTEGER DEFAULT 0,                    -- Points left on bench
    
    -- Player data (stored as array for efficiency)
    player_ids INTEGER[] DEFAULT '{}',                    -- Array of player IDs in squad
    
    -- Chip usage (for advanced visualizations)
    chips_played JSONB DEFAULT '[]'::jsonb,               -- Chips used this gameweek
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(user_id, gameweek_id)
);

-- User transfers table (detailed transfer history)
CREATE TABLE user_transfers (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    gameweek_id INTEGER REFERENCES gameweeks(id),
    
    -- Transfer details
    player_in_id INTEGER REFERENCES players(id),          -- Player brought in
    player_out_id INTEGER REFERENCES players(id),         -- Player sold
    transfer_cost INTEGER DEFAULT 0,                      -- Cost of this transfer
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(user_id, gameweek_id, player_in_id, player_out_id)
);

-- =============================================
-- INDEXES FOR PERFORMANCE
-- =============================================

-- Players table indexes
CREATE INDEX idx_players_team_id ON players(team_id);
CREATE INDEX idx_players_element_type ON players(element_type);
CREATE INDEX idx_players_now_cost ON players(now_cost);
CREATE INDEX idx_players_total_points ON players(total_points);
CREATE INDEX idx_players_form ON players(form);
CREATE INDEX idx_players_status ON players(status);
CREATE INDEX idx_players_team_position ON players(team_id, element_type);

-- Player gameweek stats indexes
CREATE INDEX idx_player_gw_stats_player_id ON player_gw_stats(player_id);
CREATE INDEX idx_player_gw_stats_gameweek_id ON player_gw_stats(gameweek_id);
CREATE INDEX idx_player_gw_stats_player_gw ON player_gw_stats(player_id, gameweek_id);
CREATE INDEX idx_player_gw_stats_fixture_id ON player_gw_stats(fixture_id);
CREATE INDEX idx_player_gw_stats_expected_goals ON player_gw_stats(expected_goals);
CREATE INDEX idx_player_gw_stats_expected_assists ON player_gw_stats(expected_assists);
CREATE INDEX idx_player_gw_stats_expected_goal_involvements ON player_gw_stats(expected_goal_involvements);
CREATE INDEX idx_player_gw_stats_expected_goals_conceded ON player_gw_stats(expected_goals_conceded);

-- Team gameweek stats indexes
CREATE INDEX idx_team_gw_stats_team_id ON team_gw_stats(team_id);
CREATE INDEX idx_team_gw_stats_gameweek_id ON team_gw_stats(gameweek_id);
CREATE INDEX idx_team_gw_stats_team_gw ON team_gw_stats(team_id, gameweek_id);
CREATE INDEX idx_team_gw_stats_fixture_id ON team_gw_stats(fixture_id);
CREATE INDEX idx_team_gw_stats_is_home ON team_gw_stats(is_home);
CREATE INDEX idx_team_gw_stats_opponent ON team_gw_stats(opponent_team_id);
CREATE INDEX idx_team_gw_stats_difficulty ON team_gw_stats(difficulty);
CREATE INDEX idx_team_gw_stats_result ON team_gw_stats(result);
CREATE INDEX idx_team_gw_stats_fantasy_points ON team_gw_stats(total_fantasy_points);
CREATE INDEX idx_team_gw_stats_goals_scored ON team_gw_stats(goals_scored);
CREATE INDEX idx_team_gw_stats_expected_goals ON team_gw_stats(expected_goals);
CREATE INDEX idx_team_gw_stats_clean_sheets ON team_gw_stats(clean_sheets);

-- Fixtures indexes
CREATE INDEX idx_fixtures_gameweek_id ON fixtures(gameweek_id);
CREATE INDEX idx_fixtures_home_team_id ON fixtures(home_team_id);
CREATE INDEX idx_fixtures_away_team_id ON fixtures(away_team_id);
CREATE INDEX idx_fixtures_finished ON fixtures(finished);

-- Gameweeks indexes
CREATE INDEX idx_gameweeks_finished ON gameweeks(finished);
CREATE INDEX idx_gameweeks_is_current ON gameweeks(is_current);
CREATE INDEX idx_gameweeks_is_next ON gameweeks(is_next);

-- User entries indexes
CREATE INDEX idx_user_entries_user_id ON user_entries(user_id);
CREATE INDEX idx_user_entries_fpl_entry_id ON user_entries(fpl_entry_id);
CREATE INDEX idx_user_entries_player_ids ON user_entries USING GIN(current_player_ids);
CREATE INDEX idx_user_entries_rank_delta ON user_entries(rank_delta);

-- User gameweek history indexes
CREATE INDEX idx_user_gameweek_history_user_id ON user_gameweek_history(user_id);
CREATE INDEX idx_user_gameweek_history_gameweek_id ON user_gameweek_history(gameweek_id);
CREATE INDEX idx_user_gameweek_history_user_gameweek ON user_gameweek_history(user_id, gameweek_id);
CREATE INDEX idx_user_gameweek_history_overall_rank ON user_gameweek_history(overall_rank);
CREATE INDEX idx_user_gameweek_history_percentile ON user_gameweek_history(percentile_rank);
CREATE INDEX idx_user_gameweek_history_points ON user_gameweek_history(points);
CREATE INDEX idx_user_gameweek_history_player_ids ON user_gameweek_history USING GIN(player_ids);
CREATE INDEX idx_user_gameweek_history_chips ON user_gameweek_history USING GIN(chips_played);

-- User transfers indexes
CREATE INDEX idx_user_transfers_user_id ON user_transfers(user_id);
CREATE INDEX idx_user_transfers_gameweek_id ON user_transfers(gameweek_id);
CREATE INDEX idx_user_transfers_user_gameweek ON user_transfers(user_id, gameweek_id);
CREATE INDEX idx_user_transfers_player_in ON user_transfers(player_in_id);
CREATE INDEX idx_user_transfers_player_out ON user_transfers(player_out_id);

-- =============================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================

-- Enable RLS on all tables
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE players ENABLE ROW LEVEL SECURITY;
ALTER TABLE gameweeks ENABLE ROW LEVEL SECURITY;
ALTER TABLE fixtures ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_gw_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_gw_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_gameweek_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_transfers ENABLE ROW LEVEL SECURITY;

-- Public read access for core data
CREATE POLICY "Public read access for teams" ON teams FOR SELECT USING (true);
CREATE POLICY "Public read access for players" ON players FOR SELECT USING (true);
CREATE POLICY "Public read access for gameweeks" ON gameweeks FOR SELECT USING (true);
CREATE POLICY "Public read access for fixtures" ON fixtures FOR SELECT USING (true);
CREATE POLICY "Public read access for player_gw_stats" ON player_gw_stats FOR SELECT USING (true);
CREATE POLICY "Public read access for team_gw_stats" ON team_gw_stats FOR SELECT USING (true);

-- Service role full access for data sync
CREATE POLICY "Service role full access for teams" ON teams FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access for players" ON players FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access for gameweeks" ON gameweeks FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access for fixtures" ON fixtures FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access for player_gw_stats" ON player_gw_stats FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access for team_gw_stats" ON team_gw_stats FOR ALL USING (auth.role() = 'service_role');

-- User-specific access for user data
CREATE POLICY "Users can read their own entries" ON user_entries FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update their own entries" ON user_entries FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own entries" ON user_entries FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read their own gameweek history" ON user_gameweek_history FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update their own gameweek history" ON user_gameweek_history FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can read their own transfers" ON user_transfers FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update their own transfers" ON user_transfers FOR UPDATE USING (auth.uid() = user_id);

-- Service role can manage user data for sync
CREATE POLICY "Service role full access for user_entries" ON user_entries FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access for user_gameweek_history" ON user_gameweek_history FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access for user_transfers" ON user_transfers FOR ALL USING (auth.role() = 'service_role');

-- =============================================
-- FUNCTIONS AND TRIGGERS
-- =============================================

-- Function to always return Pacific Time
CREATE OR REPLACE FUNCTION now_pacific()
RETURNS TIMESTAMP WITH TIME ZONE AS $$
BEGIN
    RETURN NOW() AT TIME ZONE 'America/Los_Angeles';
END;
$$ LANGUAGE plpgsql;

-- Function to convert any timestamp to Pacific Time
CREATE OR REPLACE FUNCTION to_pacific_time(timestamp_with_tz TIMESTAMP WITH TIME ZONE)
RETURNS TIMESTAMP WITH TIME ZONE AS $$
BEGIN
    RETURN timestamp_with_tz AT TIME ZONE 'America/Los_Angeles';
END;
$$ LANGUAGE plpgsql;

-- Function to update updated_at timestamp in Pacific Time
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW() AT TIME ZONE 'America/Los_Angeles';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add updated_at triggers to all tables
CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_gameweeks_updated_at BEFORE UPDATE ON gameweeks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_fixtures_updated_at BEFORE UPDATE ON fixtures FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_player_gw_stats_updated_at BEFORE UPDATE ON player_gw_stats FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_team_gw_stats_updated_at BEFORE UPDATE ON team_gw_stats FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_entries_updated_at BEFORE UPDATE ON user_entries FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_gameweek_history_updated_at BEFORE UPDATE ON user_gameweek_history FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to map players to fixtures based on gameweek and team
CREATE OR REPLACE FUNCTION map_players_to_fixtures()
RETURNS void AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    -- Update player_gw_stats with fixture_id based on team and gameweek
    WITH updated AS (
        UPDATE player_gw_stats 
        SET fixture_id = f.id
        FROM fixtures f, players p
        WHERE p.id = player_gw_stats.player_id
        AND f.gameweek_id = player_gw_stats.gameweek_id
        AND (
            (p.team_id = f.home_team_id) OR 
            (p.team_id = f.away_team_id)
        )
        AND player_gw_stats.fixture_id IS NULL
        RETURNING 1
    )
    SELECT COUNT(*) INTO updated_count FROM updated;
    
    -- Log the number of records updated
    RAISE NOTICE 'Updated % player_gw_stats records with fixture_id', updated_count;
END;
$$ LANGUAGE plpgsql;

-- Function to automatically map fixture_id when new player_gw_stats are inserted
CREATE OR REPLACE FUNCTION auto_map_fixture_id()
RETURNS TRIGGER AS $$
BEGIN
    -- If fixture_id is not provided, try to find it
    IF NEW.fixture_id IS NULL THEN
        SELECT f.id INTO NEW.fixture_id
        FROM fixtures f, players p
        WHERE p.id = NEW.player_id
        AND f.gameweek_id = NEW.gameweek_id
        AND (
            (p.team_id = f.home_team_id) OR 
            (p.team_id = f.away_team_id)
        )
        LIMIT 1;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic fixture mapping
CREATE TRIGGER trigger_auto_map_fixture_id
    BEFORE INSERT ON player_gw_stats
    FOR EACH ROW
    EXECUTE FUNCTION auto_map_fixture_id();

-- Function to populate team_gw_stats from player_gw_stats and fixtures
CREATE OR REPLACE FUNCTION populate_team_gw_stats()
RETURNS void AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    -- Clear existing data using TRUNCATE
    TRUNCATE team_gw_stats RESTART IDENTITY;
    
    -- Insert aggregated team stats
    INSERT INTO team_gw_stats (
        team_id, gameweek_id, fixture_id, is_home, opponent_team_id, difficulty,
        goals_for, goals_against, result, clean_sheets,
        total_fantasy_points, avg_fantasy_points, players_played, players_started,
        goals_scored, assists, own_goals, penalties_missed,
        expected_goals, expected_assists, expected_goal_involvements,
        saves, penalties_saved, tackles, clearances_blocks_interceptions, 
        recoveries, defensive_contribution,
        yellow_cards, red_cards,
        total_influence, total_creativity, total_threat, total_ict_index,
        avg_influence, avg_creativity, avg_threat, avg_ict_index
    )
    SELECT 
        p.team_id,
        pgs.gameweek_id,
        pgs.fixture_id,
        CASE 
            WHEN f.home_team_id = p.team_id THEN true 
            ELSE false 
        END as is_home,
        CASE 
            WHEN f.home_team_id = p.team_id THEN f.away_team_id 
            ELSE f.home_team_id 
        END as opponent_team_id,
        CASE 
            WHEN f.home_team_id = p.team_id THEN f.difficulty_home 
            ELSE f.difficulty_away 
        END as difficulty,
        
        -- Match results (FROM FIXTURES TABLE)
        CASE 
            WHEN f.home_team_id = p.team_id THEN f.home_team_score 
            ELSE f.away_team_score 
        END as goals_for,
        CASE 
            WHEN f.home_team_id = p.team_id THEN f.away_team_score 
            ELSE f.home_team_score 
        END as goals_against,
        CASE 
            WHEN f.home_team_id = p.team_id AND f.home_team_score > f.away_team_score THEN 'W'
            WHEN f.home_team_id = p.team_id AND f.home_team_score < f.away_team_score THEN 'L'
            WHEN f.away_team_id = p.team_id AND f.away_team_score > f.home_team_score THEN 'W'
            WHEN f.away_team_id = p.team_id AND f.away_team_score < f.home_team_score THEN 'L'
            ELSE 'D'
        END as result,
        CASE 
            WHEN f.home_team_id = p.team_id AND f.away_team_score = 0 THEN 1
            WHEN f.away_team_id = p.team_id AND f.home_team_score = 0 THEN 1
            ELSE 0
        END as clean_sheets,
        
        -- Fantasy performance (FROM PLAYER_GW_STATS)
        SUM(pgs.total_points) as total_fantasy_points,
        ROUND(AVG(pgs.total_points), 2) as avg_fantasy_points,
        COUNT(CASE WHEN pgs.minutes > 0 THEN 1 END) as players_played,
        COUNT(CASE WHEN pgs.starts > 0 THEN 1 END) as players_started,
        
        -- Attacking stats (FROM PLAYER_GW_STATS)
        SUM(pgs.goals_scored) as goals_scored,
        SUM(pgs.assists) as assists,
        SUM(pgs.own_goals) as own_goals,
        SUM(pgs.penalties_missed) as penalties_missed,
        
        -- Expected attacking stats (FROM PLAYER_GW_STATS)
        ROUND(SUM(pgs.expected_goals), 2) as expected_goals,
        ROUND(SUM(pgs.expected_assists), 2) as expected_assists,
        ROUND(SUM(pgs.expected_goal_involvements), 2) as expected_goal_involvements,
        
        -- Defensive stats (FROM PLAYER_GW_STATS)
        SUM(pgs.saves) as saves,
        SUM(pgs.penalties_saved) as penalties_saved,
        SUM(pgs.tackles) as tackles,
        SUM(pgs.clearances_blocks_interceptions) as clearances_blocks_interceptions,
        SUM(pgs.recoveries) as recoveries,
        SUM(pgs.defensive_contribution) as defensive_contribution,
        
        -- Discipline stats (FROM PLAYER_GW_STATS)
        SUM(pgs.yellow_cards) as yellow_cards,
        SUM(pgs.red_cards) as red_cards,
        
        -- ICT metrics (FROM PLAYER_GW_STATS)
        ROUND(SUM(COALESCE(pgs.influence, 0)), 2) as total_influence,
        ROUND(SUM(COALESCE(pgs.creativity, 0)), 2) as total_creativity,
        ROUND(SUM(COALESCE(pgs.threat, 0)), 2) as total_threat,
        ROUND(SUM(COALESCE(pgs.ict_index, 0)), 2) as total_ict_index,
        ROUND(AVG(COALESCE(pgs.influence, 0)), 2) as avg_influence,
        ROUND(AVG(COALESCE(pgs.creativity, 0)), 2) as avg_creativity,
        ROUND(AVG(COALESCE(pgs.threat, 0)), 2) as avg_threat,
        ROUND(AVG(COALESCE(pgs.ict_index, 0)), 2) as avg_ict_index
        
    FROM player_gw_stats pgs
    JOIN players p ON pgs.player_id = p.id
    JOIN fixtures f ON pgs.fixture_id = f.id
    WHERE pgs.minutes > 0  -- Only include players who actually played
    GROUP BY p.team_id, pgs.gameweek_id, pgs.fixture_id, f.home_team_id, f.away_team_id, 
             f.home_team_score, f.away_team_score, f.difficulty_home, f.difficulty_away;
    
    -- Update form metrics
    UPDATE team_gw_stats 
    SET 
        form_6_gw = (
            SELECT ROUND(AVG(total_fantasy_points), 2)
            FROM team_gw_stats tgs2 
            WHERE tgs2.team_id = team_gw_stats.team_id 
            AND tgs2.gameweek_id <= team_gw_stats.gameweek_id 
            AND tgs2.gameweek_id > team_gw_stats.gameweek_id - 6
        ),
        form_3_gw = (
            SELECT ROUND(AVG(total_fantasy_points), 2)
            FROM team_gw_stats tgs2 
            WHERE tgs2.team_id = team_gw_stats.team_id 
            AND tgs2.gameweek_id <= team_gw_stats.gameweek_id 
            AND tgs2.gameweek_id > team_gw_stats.gameweek_id - 3
        );
    
    -- Get count of records created
    SELECT COUNT(*) INTO updated_count FROM team_gw_stats;
    
    -- Log the number of records created
    RAISE NOTICE 'Created % team_gw_stats records', updated_count;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh team_gw_stats
CREATE OR REPLACE FUNCTION refresh_team_statistics()
RETURNS void AS $$
BEGIN
    -- Populate team gameweek stats
    PERFORM populate_team_gw_stats();
    
    RAISE NOTICE 'Team statistics refreshed successfully';
END;
$$ LANGUAGE plpgsql;

-- Function to calculate rank delta for user entries
CREATE OR REPLACE FUNCTION calculate_rank_delta()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate rank delta (negative = improvement, positive = decline)
    IF NEW.overall_rank IS NOT NULL AND OLD.overall_rank IS NOT NULL THEN
        NEW.rank_delta = OLD.overall_rank - NEW.overall_rank;
        NEW.previous_rank = OLD.overall_rank;
    ELSE
        NEW.rank_delta = 0;
        NEW.previous_rank = NULL;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically calculate rank delta
CREATE TRIGGER trigger_calculate_rank_delta
    BEFORE UPDATE ON user_entries
    FOR EACH ROW
    EXECUTE FUNCTION calculate_rank_delta();

-- Function to update user_entries summary when history changes
CREATE OR REPLACE FUNCTION update_user_entries_summary()
RETURNS TRIGGER AS $$
DECLARE
    best_rank_record RECORD;
    worst_rank_record RECORD;
    total_transfers_count INTEGER;
    total_transfer_cost_sum INTEGER;
    chips_used_array JSONB;
BEGIN
    -- Get best and worst ranks for this user
    SELECT gameweek_id, overall_rank INTO best_rank_record
    FROM user_gameweek_history 
    WHERE user_id = NEW.user_id 
    AND overall_rank IS NOT NULL
    ORDER BY overall_rank ASC 
    LIMIT 1;
    
    SELECT gameweek_id, overall_rank INTO worst_rank_record
    FROM user_gameweek_history 
    WHERE user_id = NEW.user_id 
    AND overall_rank IS NOT NULL
    ORDER BY overall_rank DESC 
    LIMIT 1;
    
    -- Calculate total transfers and cost
    SELECT 
        COALESCE(SUM(transfers_made), 0),
        COALESCE(SUM(transfer_cost), 0)
    INTO total_transfers_count, total_transfer_cost_sum
    FROM user_gameweek_history 
    WHERE user_id = NEW.user_id;
    
    -- Collect all chips used
    SELECT COALESCE(jsonb_agg(DISTINCT chip_data), '[]'::jsonb)
    INTO chips_used_array
    FROM (
        SELECT jsonb_array_elements(chips_played) as chip_data
        FROM user_gameweek_history 
        WHERE user_id = NEW.user_id 
        AND chips_played != '[]'::jsonb
    ) chips;
    
    -- Update user_entries with summary data
    UPDATE user_entries 
    SET 
        best_rank = best_rank_record.overall_rank,
        best_gameweek_id = best_rank_record.gameweek_id,
        worst_rank = worst_rank_record.overall_rank,
        worst_gameweek_id = worst_rank_record.gameweek_id,
        total_transfers = total_transfers_count,
        total_transfer_cost = total_transfer_cost_sum,
        chips_used = chips_used_array,
        updated_at = NOW()
    WHERE user_id = NEW.user_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update summary when history changes
CREATE TRIGGER trigger_update_user_entries_summary
    AFTER INSERT OR UPDATE ON user_gameweek_history
    FOR EACH ROW
    EXECUTE FUNCTION update_user_entries_summary();

-- =============================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================

COMMENT ON TABLE teams IS 'Premier League teams with performance statistics';
COMMENT ON TABLE players IS 'FPL players with current season statistics';
COMMENT ON TABLE gameweeks IS 'FPL gameweeks with deadlines and status';
COMMENT ON TABLE fixtures IS 'Match fixtures between teams';
COMMENT ON TABLE player_gw_stats IS 'Player performance statistics per gameweek with expected data';
COMMENT ON TABLE team_gw_stats IS 'Team performance statistics per gameweek, aggregated from player_gw_stats and fixtures';
COMMENT ON TABLE user_entries IS 'User FPL team entries with enhanced ownership tracking and rank analysis';
COMMENT ON TABLE user_gameweek_history IS 'Historical manager performance data per gameweek with chip usage';
COMMENT ON TABLE user_transfers IS 'Detailed transfer history for each manager';

COMMENT ON COLUMN players.now_cost IS 'Player price in 0.1M units (e.g., 100 = £10.0M)';
COMMENT ON COLUMN players.element_type IS 'Player position: 1=GK, 2=DEF, 3=MID, 4=FWD';
COMMENT ON COLUMN players.status IS 'Player availability status: a=available, d=doubtful, i=injured, n=not available, s=suspended, u=unavailable';
COMMENT ON COLUMN player_gw_stats.expected_goals IS 'Expected goals for this player in this gameweek';
COMMENT ON COLUMN player_gw_stats.expected_assists IS 'Expected assists for this player in this gameweek';
COMMENT ON COLUMN player_gw_stats.expected_goal_involvements IS 'Expected goal involvements for this player in this gameweek';
COMMENT ON COLUMN player_gw_stats.expected_goals_conceded IS 'Expected goals conceded for this player in this gameweek';
COMMENT ON COLUMN player_gw_stats.clearances_blocks_interceptions IS 'Clearances, blocks, and interceptions combined';
COMMENT ON COLUMN player_gw_stats.recoveries IS 'Ball recoveries';
COMMENT ON COLUMN player_gw_stats.tackles IS 'Tackles attempted';
COMMENT ON COLUMN player_gw_stats.defensive_contribution IS 'Overall defensive contribution metric';
COMMENT ON COLUMN player_gw_stats.starts IS 'Number of starts in this gameweek';
COMMENT ON COLUMN player_gw_stats.fixture_id IS 'Reference to the specific fixture for home/away analysis';

COMMENT ON COLUMN team_gw_stats.is_home IS 'Whether the team played at home in this gameweek';
COMMENT ON COLUMN team_gw_stats.opponent_team_id IS 'ID of the opposing team';
COMMENT ON COLUMN team_gw_stats.difficulty IS 'Fixture difficulty rating for this team';
COMMENT ON COLUMN team_gw_stats.result IS 'Match result: W=Win, D=Draw, L=Loss';
COMMENT ON COLUMN team_gw_stats.clean_sheets IS 'Team clean sheet: 1 if goals_against = 0, 0 otherwise';
COMMENT ON COLUMN team_gw_stats.form_6_gw IS 'Average fantasy points over last 6 gameweeks';
COMMENT ON COLUMN team_gw_stats.form_3_gw IS 'Average fantasy points over last 3 gameweeks';

COMMENT ON COLUMN user_entries.current_player_ids IS 'Array of player IDs currently owned by this manager';
COMMENT ON COLUMN user_entries.previous_rank IS 'Overall rank from previous gameweek';
COMMENT ON COLUMN user_entries.rank_delta IS 'Rank change from previous gameweek (negative = improvement)';
COMMENT ON COLUMN user_entries.current_gameweek_id IS 'Current gameweek ID for this manager';
COMMENT ON COLUMN user_entries.best_rank IS 'Best overall rank achieved this season';
COMMENT ON COLUMN user_entries.worst_rank IS 'Worst overall rank achieved this season';
COMMENT ON COLUMN user_entries.chips_used IS 'Array of chips used this season: [{"chip": "wildcard", "used": true}]';

COMMENT ON COLUMN user_gameweek_history.player_ids IS 'Array of player IDs in manager squad for this gameweek';
COMMENT ON COLUMN user_gameweek_history.chips_played IS 'Array of chips used this gameweek: [{"chip": "wildcard", "used": true}]';
COMMENT ON COLUMN user_gameweek_history.percentile_rank IS 'Percentile ranking (1-100, where 1 is best)';
COMMENT ON COLUMN user_transfers.player_in_id IS 'Player ID of player brought in';
COMMENT ON COLUMN user_transfers.player_out_id IS 'Player ID of player sold';

COMMENT ON FUNCTION map_players_to_fixtures() IS 'Maps players to fixtures for proper home/away analysis';
COMMENT ON FUNCTION auto_map_fixture_id() IS 'Automatically maps fixture_id when new player_gw_stats are inserted';
COMMENT ON FUNCTION now_pacific() IS 'Returns current timestamp in Pacific Time';
COMMENT ON FUNCTION to_pacific_time(timestamp_with_tz) IS 'Converts any timestamp to Pacific Time';
COMMENT ON FUNCTION populate_team_gw_stats() IS 'Populates team_gw_stats table by aggregating player_gw_stats and fixtures data';
COMMENT ON FUNCTION refresh_team_statistics() IS 'Refreshes team statistics';
COMMENT ON FUNCTION calculate_rank_delta() IS 'Calculates rank change for user entries';
COMMENT ON FUNCTION update_user_entries_summary() IS 'Updates user_entries summary when gameweek history changes';

-- =============================================
-- VERIFICATION
-- =============================================

-- Log the consolidated schema creation
DO $$
BEGIN
    RAISE NOTICE 'FPL Vibe complete consolidated schema created successfully:';
    RAISE NOTICE '- All core tables created with proper relationships';
    RAISE NOTICE '- User management tables with enhanced features';
    RAISE NOTICE '- Indexes created for performance optimization';
    RAISE NOTICE '- RLS policies configured for security';
    RAISE NOTICE '- Pacific Time timezone configured';
    RAISE NOTICE '- Expected data columns included';
    RAISE NOTICE '- Automatic fixture mapping enabled';
    RAISE NOTICE '- Team gameweek stats aggregation included';
    RAISE NOTICE '- User gameweek history and transfer tracking included';
    RAISE NOTICE '- Complete schema ready for production';
END $$;
