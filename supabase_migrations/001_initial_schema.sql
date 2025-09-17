-- FPL Vibe Database Schema Migration
-- Project: fpl-research
-- Created: 2025-09-17

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
    form DECIMAL(4,2),
    points INTEGER DEFAULT 0,
    position INTEGER,
    played INTEGER DEFAULT 0,
    win INTEGER DEFAULT 0,
    draw INTEGER DEFAULT 0,
    loss INTEGER DEFAULT 0,
    goals_for INTEGER DEFAULT 0,
    goals_against INTEGER DEFAULT 0,
    goal_difference INTEGER DEFAULT 0,
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

-- Player gameweek stats table
CREATE TABLE player_gw_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    gameweek_id INTEGER REFERENCES gameweeks(id),
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
    value DECIMAL(4,2),
    selected_by_percent DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(player_id, gameweek_id)
);

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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User player ownership table
CREATE TABLE user_player_ownership (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    player_id INTEGER REFERENCES players(id),
    gameweek_id INTEGER REFERENCES gameweeks(id),
    owned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, player_id, gameweek_id)
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

-- Fixtures indexes
CREATE INDEX idx_fixtures_gameweek_id ON fixtures(gameweek_id);
CREATE INDEX idx_fixtures_home_team_id ON fixtures(home_team_id);
CREATE INDEX idx_fixtures_away_team_id ON fixtures(away_team_id);
CREATE INDEX idx_fixtures_finished ON fixtures(finished);

-- Gameweeks indexes
CREATE INDEX idx_gameweeks_finished ON gameweeks(finished);
CREATE INDEX idx_gameweeks_is_current ON gameweeks(is_current);
CREATE INDEX idx_gameweeks_is_next ON gameweeks(is_next);

-- User ownership indexes
CREATE INDEX idx_user_player_ownership_user_id ON user_player_ownership(user_id);
CREATE INDEX idx_user_player_ownership_player_id ON user_player_ownership(player_id);
CREATE INDEX idx_user_player_ownership_gameweek_id ON user_player_ownership(gameweek_id);

-- =============================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================

-- Enable RLS on all tables
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE players ENABLE ROW LEVEL SECURITY;
ALTER TABLE gameweeks ENABLE ROW LEVEL SECURITY;
ALTER TABLE fixtures ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_gw_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_player_ownership ENABLE ROW LEVEL SECURITY;

-- Public read access for core data (teams, players, gameweeks, fixtures, player_gw_stats)
CREATE POLICY "Public read access for teams" ON teams FOR SELECT USING (true);
CREATE POLICY "Public read access for players" ON players FOR SELECT USING (true);
CREATE POLICY "Public read access for gameweeks" ON gameweeks FOR SELECT USING (true);
CREATE POLICY "Public read access for fixtures" ON fixtures FOR SELECT USING (true);
CREATE POLICY "Public read access for player_gw_stats" ON player_gw_stats FOR SELECT USING (true);

-- Service role full access for data sync
CREATE POLICY "Service role full access for teams" ON teams FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access for players" ON players FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access for gameweeks" ON gameweeks FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access for fixtures" ON fixtures FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access for player_gw_stats" ON player_gw_stats FOR ALL USING (auth.role() = 'service_role');

-- User-specific access for user data
CREATE POLICY "Users can read their own entries" ON user_entries FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update their own entries" ON user_entries FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own entries" ON user_entries FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read their own ownership" ON user_player_ownership FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update their own ownership" ON user_player_ownership FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own ownership" ON user_player_ownership FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Service role can manage user data for sync
CREATE POLICY "Service role full access for user_entries" ON user_entries FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access for user_player_ownership" ON user_player_ownership FOR ALL USING (auth.role() = 'service_role');

-- =============================================
-- FUNCTIONS AND TRIGGERS
-- =============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers to all tables
CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_gameweeks_updated_at BEFORE UPDATE ON gameweeks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_fixtures_updated_at BEFORE UPDATE ON fixtures FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_player_gw_stats_updated_at BEFORE UPDATE ON player_gw_stats FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_entries_updated_at BEFORE UPDATE ON user_entries FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================

COMMENT ON TABLE teams IS 'Premier League teams with performance statistics';
COMMENT ON TABLE players IS 'FPL players with current season statistics';
COMMENT ON TABLE gameweeks IS 'FPL gameweeks with deadlines and status';
COMMENT ON TABLE fixtures IS 'Match fixtures between teams';
COMMENT ON TABLE player_gw_stats IS 'Player performance statistics per gameweek';
COMMENT ON TABLE user_entries IS 'User FPL team entries and ownership';
COMMENT ON TABLE user_player_ownership IS 'Player ownership tracking per user per gameweek';

COMMENT ON COLUMN players.now_cost IS 'Player price in 0.1M units (e.g., 100 = £10.0M)';
COMMENT ON COLUMN players.element_type IS 'Player position: 1=GK, 2=DEF, 3=MID, 4=FWD';
COMMENT ON COLUMN players.status IS 'Player availability status: a=available, d=doubtful, i=injured, n=not available, s=suspended, u=unavailable';
