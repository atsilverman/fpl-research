-- FPL Vibe Materialized Views Migration (Fixed)
-- Project: fpl-research
-- Created: 2025-09-17
-- Fixed: Removed RLS policies from materialized views (not supported in PostgreSQL)

-- =============================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- =============================================

-- Team gameweek fantasy sums (safe aggregation)
-- This view safely aggregates player statistics by team and gameweek
-- without inflating defensive statistics
CREATE MATERIALIZED VIEW mv_team_gw_fantasy_sums AS
SELECT 
    t.id as team_id,
    t.name as team_name,
    gw.id as gameweek_id,
    gw.name as gameweek_name,
    COALESCE(SUM(pgs.total_points), 0) as total_points,
    COALESCE(SUM(pgs.bonus), 0) as total_bonus,
    COALESCE(SUM(pgs.yellow_cards), 0) as total_yellow_cards,
    COALESCE(SUM(pgs.red_cards), 0) as total_red_cards,
    COALESCE(SUM(pgs.minutes), 0) as total_minutes,
    COALESCE(SUM(CASE WHEN p.element_type IN (1, 2) THEN pgs.clean_sheets ELSE 0 END), 0) as player_cs_awards_sum,
    COALESCE(SUM(pgs.goals_scored), 0) as total_goals_scored,
    COALESCE(SUM(pgs.assists), 0) as total_assists,
    COALESCE(SUM(pgs.saves), 0) as total_saves,
    COALESCE(SUM(pgs.bps), 0) as total_bps,
    COALESCE(AVG(pgs.ict_index), 0) as avg_ict_index,
    COUNT(p.id) as players_played,
    COUNT(CASE WHEN pgs.minutes >= 60 THEN 1 END) as players_60min_plus
FROM teams t
LEFT JOIN players p ON p.team_id = t.id
LEFT JOIN player_gw_stats pgs ON pgs.player_id = p.id
LEFT JOIN gameweeks gw ON gw.id = pgs.gameweek_id
GROUP BY t.id, t.name, gw.id, gw.name;

-- Create index on materialized view for performance
CREATE INDEX idx_mv_team_gw_fantasy_sums_team_gw ON mv_team_gw_fantasy_sums(team_id, gameweek_id);
CREATE INDEX idx_mv_team_gw_fantasy_sums_gameweek ON mv_team_gw_fantasy_sums(gameweek_id);

-- Team gameweek public view (fixture truth + fantasy sums)
-- This view combines fixture results with fantasy statistics
CREATE VIEW team_gw_public AS
SELECT 
    f.id as fixture_id,
    f.gameweek_id,
    gw.name as gameweek_name,
    f.home_team_id,
    ht.name as home_team_name,
    f.away_team_id,
    at.name as away_team_name,
    f.home_team_score as gf_home,
    f.away_team_score as ga_home,
    f.away_team_score as gf_away,
    f.home_team_score as ga_away,
    CASE 
        WHEN f.home_team_score > f.away_team_score THEN 'W'
        WHEN f.home_team_score < f.away_team_score THEN 'L'
        ELSE 'D'
    END as result_home,
    CASE 
        WHEN f.away_team_score > f.home_team_score THEN 'W'
        WHEN f.away_team_score < f.home_team_score THEN 'L'
        ELSE 'D'
    END as result_away,
    CASE WHEN f.away_team_score = 0 THEN TRUE ELSE FALSE END as clean_sheet_home,
    CASE WHEN f.home_team_score = 0 THEN TRUE ELSE FALSE END as clean_sheet_away,
    f.difficulty_home,
    f.difficulty_away,
    f.finished as fixture_finished,
    f.kickoff_time,
    -- Fantasy statistics
    COALESCE(fs_home.total_points, 0) as fantasy_points_home,
    COALESCE(fs_away.total_points, 0) as fantasy_points_away,
    COALESCE(fs_home.player_cs_awards_sum, 0) as player_cs_awards_home,
    COALESCE(fs_away.player_cs_awards_sum, 0) as player_cs_awards_away,
    COALESCE(fs_home.total_goals_scored, 0) as fantasy_goals_home,
    COALESCE(fs_away.total_goals_scored, 0) as fantasy_goals_away,
    COALESCE(fs_home.total_assists, 0) as fantasy_assists_home,
    COALESCE(fs_away.total_assists, 0) as fantasy_assists_away,
    COALESCE(fs_home.avg_ict_index, 0) as avg_ict_home,
    COALESCE(fs_away.avg_ict_index, 0) as avg_ict_away
FROM fixtures f
JOIN gameweeks gw ON gw.id = f.gameweek_id
JOIN teams ht ON ht.id = f.home_team_id
JOIN teams at ON at.id = f.away_team_id
LEFT JOIN mv_team_gw_fantasy_sums fs_home ON fs_home.team_id = f.home_team_id AND fs_home.gameweek_id = f.gameweek_id
LEFT JOIN mv_team_gw_fantasy_sums fs_away ON fs_away.team_id = f.away_team_id AND fs_away.gameweek_id = f.gameweek_id;

-- Team form view (last 6 gameweeks)
-- This view calculates rolling form statistics for teams
CREATE MATERIALIZED VIEW mv_team_gw_form AS
WITH team_gw_results AS (
    SELECT 
        team_id,
        team_name,
        gameweek_id,
        gameweek_name,
        gf,
        ga,
        result,
        clean_sheet,
        fantasy_points,
        player_cs_awards
    FROM (
        SELECT 
            home_team_id as team_id, 
            home_team_name as team_name,
            gameweek_id, 
            gameweek_name,
            gf_home as gf, 
            ga_home as ga, 
            result_home as result, 
            clean_sheet_home as clean_sheet, 
            fantasy_points_home as fantasy_points,
            player_cs_awards_home as player_cs_awards
        FROM team_gw_public
        WHERE fixture_finished = TRUE
        UNION ALL
        SELECT 
            away_team_id as team_id, 
            away_team_name as team_name,
            gameweek_id, 
            gameweek_name,
            gf_away as gf, 
            ga_away as ga, 
            result_away as result, 
            clean_sheet_away as clean_sheet, 
            fantasy_points_away as fantasy_points,
            player_cs_awards_away as player_cs_awards
        FROM team_gw_public
        WHERE fixture_finished = TRUE
    ) combined
),
ranked_results AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY gameweek_id DESC) as rn
    FROM team_gw_results
)
SELECT 
    team_id,
    team_name,
    AVG(CASE WHEN rn <= 6 THEN gf ELSE NULL END) as avg_goals_for_6gw,
    AVG(CASE WHEN rn <= 6 THEN ga ELSE NULL END) as avg_goals_against_6gw,
    AVG(CASE WHEN rn <= 6 THEN fantasy_points ELSE NULL END) as avg_fantasy_points_6gw,
    COUNT(CASE WHEN rn <= 6 AND result = 'W' THEN 1 END) as wins_6gw,
    COUNT(CASE WHEN rn <= 6 AND result = 'D' THEN 1 END) as draws_6gw,
    COUNT(CASE WHEN rn <= 6 AND result = 'L' THEN 1 END) as losses_6gw,
    COUNT(CASE WHEN rn <= 6 AND clean_sheet = TRUE THEN 1 END) as clean_sheets_6gw,
    AVG(CASE WHEN rn <= 6 THEN player_cs_awards ELSE NULL END) as avg_player_cs_awards_6gw,
    -- Form calculation (points: W=3, D=1, L=0)
    (COUNT(CASE WHEN rn <= 6 AND result = 'W' THEN 1 END) * 3 + 
     COUNT(CASE WHEN rn <= 6 AND result = 'D' THEN 1 END) * 1) as form_points_6gw
FROM ranked_results
GROUP BY team_id, team_name;

-- Create index on form view
CREATE INDEX idx_mv_team_gw_form_team_id ON mv_team_gw_form(team_id);

-- Player form view (last 6 gameweeks)
-- This view calculates rolling form statistics for players
CREATE MATERIALIZED VIEW mv_player_gw_form AS
WITH player_gw_ranked AS (
    SELECT 
        p.id as player_id,
        p.web_name,
        p.team_id,
        t.name as team_name,
        p.element_type,
        pgs.gameweek_id,
        pgs.total_points,
        pgs.minutes,
        pgs.goals_scored,
        pgs.assists,
        pgs.clean_sheets,
        pgs.bonus,
        pgs.ict_index,
        ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY pgs.gameweek_id DESC) as rn
    FROM players p
    JOIN teams t ON t.id = p.team_id
    JOIN player_gw_stats pgs ON pgs.player_id = p.id
    WHERE pgs.minutes > 0  -- Only include gameweeks where player played
)
SELECT 
    player_id,
    web_name,
    team_id,
    team_name,
    element_type,
    AVG(CASE WHEN rn <= 6 THEN total_points ELSE NULL END) as avg_points_6gw,
    AVG(CASE WHEN rn <= 6 THEN minutes ELSE NULL END) as avg_minutes_6gw,
    AVG(CASE WHEN rn <= 6 THEN goals_scored ELSE NULL END) as avg_goals_6gw,
    AVG(CASE WHEN rn <= 6 THEN assists ELSE NULL END) as avg_assists_6gw,
    AVG(CASE WHEN rn <= 6 THEN clean_sheets ELSE NULL END) as avg_clean_sheets_6gw,
    AVG(CASE WHEN rn <= 6 THEN bonus ELSE NULL END) as avg_bonus_6gw,
    AVG(CASE WHEN rn <= 6 THEN ict_index ELSE NULL END) as avg_ict_6gw,
    COUNT(CASE WHEN rn <= 6 THEN 1 END) as games_played_6gw
FROM player_gw_ranked
GROUP BY player_id, web_name, team_id, team_name, element_type;

-- Create index on player form view
CREATE INDEX idx_mv_player_gw_form_player_id ON mv_player_gw_form(player_id);
CREATE INDEX idx_mv_player_gw_form_team_id ON mv_player_gw_form(team_id);
CREATE INDEX idx_mv_player_gw_form_element_type ON mv_player_gw_form(element_type);

-- =============================================
-- REFRESH FUNCTIONS
-- =============================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_team_gw_fantasy_sums;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_team_gw_form;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_player_gw_form;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh team-specific materialized views
CREATE OR REPLACE FUNCTION refresh_team_materialized_views(team_id_param INTEGER)
RETURNS void AS $$
BEGIN
    -- For now, refresh all views since we can't selectively refresh
    -- In production, you might want to implement more granular refresh logic
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_team_gw_fantasy_sums;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_team_gw_form;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================

COMMENT ON MATERIALIZED VIEW mv_team_gw_fantasy_sums IS 'Safe aggregation of player statistics by team and gameweek without inflating defensive stats';
COMMENT ON VIEW team_gw_public IS 'Combined fixture results and fantasy statistics for public consumption';
COMMENT ON MATERIALIZED VIEW mv_team_gw_form IS 'Rolling 6-gameweek form statistics for teams';
COMMENT ON MATERIALIZED VIEW mv_player_gw_form IS 'Rolling 6-gameweek form statistics for players';

COMMENT ON FUNCTION refresh_all_materialized_views() IS 'Refreshes all materialized views concurrently';
COMMENT ON FUNCTION refresh_team_materialized_views(INTEGER) IS 'Refreshes team-specific materialized views';
