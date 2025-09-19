#!/usr/bin/env python3
"""
FPL Vibe API - FastAPI Backend
Fantasy Premier League data API for iOS app consumption
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from contextlib import asynccontextmanager

# Import our modules
from models import (
    Player, PlayerResponse, Team, TeamResponse, 
    Fixture, FixtureResponse, Gameweek, GameweekResponse,
    TeamGameweekStats, TeamGameweekStatsResponse, TeamFormTrends, 
    TeamSeasonSummary, TeamHomeAwayStats
)
from database import get_database_connection, init_database, close_database
from services import PlayerService, TeamService, FixtureService, GameweekService, TeamGameweekStatsService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    logger.info("FPL Vibe API started successfully")
    yield
    # Shutdown
    await close_database()
    logger.info("FPL Vibe API shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="FPL Vibe API",
    description="Fantasy Premier League data API for iOS app",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware for iOS app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your iOS app's bundle identifier
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Players endpoints
@app.get("/players", response_model=PlayerResponse)
async def get_players(
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    position: Optional[str] = Query(None, description="Filter by position (GKP, DEF, MID, FWD)"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    search: Optional[str] = Query(None, description="Search by player name"),
    sort_by: Optional[str] = Query("total_points", description="Sort by field"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
    limit: Optional[int] = Query(50, description="Number of results"),
    offset: Optional[int] = Query(0, description="Offset for pagination"),
    db=Depends(get_database_connection)
):
    """Get players with filtering, sorting, and pagination"""
    try:
        service = PlayerService(db)
        players, total = await service.get_players(
            team_id=team_id,
            position=position,
            min_price=min_price,
            max_price=max_price,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset
        )
        
        return PlayerResponse(
            players=players,
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error fetching players: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/players/{player_id}", response_model=Player)
async def get_player(player_id: int, db=Depends(get_database_connection)):
    """Get specific player by ID"""
    try:
        service = PlayerService(db)
        player = await service.get_player_by_id(player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        return player
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching player {player_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Teams endpoints
@app.get("/teams", response_model=TeamResponse)
async def get_teams(
    sort_by: Optional[str] = Query("name", description="Sort by field"),
    sort_order: Optional[str] = Query("asc", description="Sort order (asc/desc)"),
    db=Depends(get_database_connection)
):
    """Get all teams with stats"""
    try:
        service = TeamService(db)
        teams = await service.get_teams(sort_by=sort_by, sort_order=sort_order)
        
        return TeamResponse(teams=teams, total=len(teams))
    except Exception as e:
        logger.error(f"Error fetching teams: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Enhanced team statistics endpoints (must come before /teams/{team_id})
# Removed materialized view endpoints - using team_gw_stats instead

# Team Gameweek Stats endpoints (must come before /teams/{team_id})
@app.get("/teams/gameweek-stats", response_model=TeamGameweekStatsResponse)
async def get_team_gameweek_stats(
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    gameweek_start: Optional[int] = Query(None, description="Start gameweek (inclusive)"),
    gameweek_end: Optional[int] = Query(None, description="End gameweek (inclusive)"),
    is_home: Optional[bool] = Query(None, description="Filter by home/away"),
    opponent_id: Optional[int] = Query(None, description="Filter by opponent team ID"),
    min_difficulty: Optional[int] = Query(None, description="Minimum fixture difficulty"),
    max_difficulty: Optional[int] = Query(None, description="Maximum fixture difficulty"),
    sort_by: Optional[str] = Query("gameweek_id", description="Sort by field"),
    sort_order: Optional[str] = Query("asc", description="Sort order (asc/desc)"),
    limit: Optional[int] = Query(50, description="Number of results"),
    offset: Optional[int] = Query(0, description="Offset for pagination"),
    db=Depends(get_database_connection)
):
    """Get team gameweek statistics with filtering"""
    try:
        service = TeamGameweekStatsService(db)
        stats, total = await service.get_team_gameweek_stats(
            team_id=team_id,
            gameweek_start=gameweek_start,
            gameweek_end=gameweek_end,
            is_home=is_home,
            opponent_id=opponent_id,
            min_difficulty=min_difficulty,
            max_difficulty=max_difficulty,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset
        )
        
        return TeamGameweekStatsResponse(
            data=stats,
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error fetching team gameweek stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/teams/form-trends")
async def get_team_form_trends(
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    gameweek_start: Optional[int] = Query(None, description="Start gameweek (inclusive)"),
    gameweek_end: Optional[int] = Query(None, description="End gameweek (inclusive)"),
    limit: Optional[int] = Query(50, description="Number of results"),
    offset: Optional[int] = Query(0, description="Offset for pagination"),
    db=Depends(get_database_connection)
):
    """Get team form trends with opponent and difficulty information"""
    try:
        service = TeamGameweekStatsService(db)
        trends = await service.get_team_form_trends(
            team_id=team_id,
            gameweek_start=gameweek_start,
            gameweek_end=gameweek_end,
            limit=limit,
            offset=offset
        )
        return {"trends": trends, "total": len(trends)}
    except Exception as e:
        logger.error(f"Error fetching team form trends: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/teams/season-summary")
async def get_team_season_summary(db=Depends(get_database_connection)):
    """Get team season summary statistics"""
    try:
        service = TeamGameweekStatsService(db)
        summaries = await service.get_team_season_summary()
        return {"teams": summaries, "total": len(summaries)}
    except Exception as e:
        logger.error(f"Error fetching team season summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/teams/home-away-stats")
async def get_team_home_away_stats(
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    db=Depends(get_database_connection)
):
    """Get team home/away performance statistics"""
    try:
        service = TeamGameweekStatsService(db)
        stats = await service.get_team_home_away_stats(team_id=team_id)
        return {"stats": stats, "total": len(stats)}
    except Exception as e:
        logger.error(f"Error fetching team home/away stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/teams/{team_id}", response_model=Team)
async def get_team(team_id: int, db=Depends(get_database_connection)):
    """Get specific team by ID"""
    try:
        service = TeamService(db)
        team = await service.get_team_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return team
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Fixtures endpoints
@app.get("/fixtures", response_model=FixtureResponse)
async def get_fixtures(
    gameweek: Optional[int] = Query(None, description="Filter by gameweek"),
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: Optional[int] = Query(100, description="Number of results"),
    offset: Optional[int] = Query(0, description="Offset for pagination"),
    db=Depends(get_database_connection)
):
    """Get fixtures with filtering"""
    try:
        service = FixtureService(db)
        fixtures, total = await service.get_fixtures(
            gameweek=gameweek,
            team_id=team_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return FixtureResponse(
            fixtures=fixtures,
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error fetching fixtures: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Gameweeks endpoints
@app.get("/gameweeks", response_model=GameweekResponse)
async def get_gameweeks(db=Depends(get_database_connection)):
    """Get all gameweeks"""
    try:
        service = GameweekService(db)
        gameweeks = await service.get_gameweeks()
        
        return GameweekResponse(gameweeks=gameweeks, total=len(gameweeks))
    except Exception as e:
        logger.error(f"Error fetching gameweeks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/gameweeks/current", response_model=Gameweek)
async def get_current_gameweek(db=Depends(get_database_connection)):
    """Get current gameweek"""
    try:
        service = GameweekService(db)
        gameweek = await service.get_current_gameweek()
        if not gameweek:
            raise HTTPException(status_code=404, detail="No current gameweek found")
        return gameweek
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching current gameweek: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Duplicate routes removed - defined earlier in file

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
