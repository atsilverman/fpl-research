# FPL Research - Fantasy Premier League Data Service

A comprehensive Fantasy Premier League data monitoring and API service that provides real-time player statistics, team data, fixtures, and gameweek information for iOS app development.

## Features
- **Automated Data Sync**: Continuous monitoring of FPL API for data changes with intelligent refresh triggers
- **RESTful API**: FastAPI-based backend serving structured FPL data with filtering, sorting, and pagination
- **Real-time Monitoring**: Detects gameweek completions, fixture updates, and player stat changes
- **Supabase Integration**: Robust database storage with materialized views for optimized queries
- **iOS-Ready**: CORS-enabled API designed for mobile app consumption

## Architecture
- **Data Service** (`fpl_service.py`): Monitors FPL API and syncs data to Supabase
- **API Backend** (`backend/`): FastAPI server with endpoints for players, teams, fixtures, and gameweeks
- **Database**: Supabase PostgreSQL with automated migrations and materialized views

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Test the service:
   ```bash
   python3 fpl_service.py --test
   ```

3. Start the unified service:
   ```bash
   python3 fpl_service.py
   ```

4. For one-time check:
   ```bash
   python3 fpl_service.py --once
   ```

5. For forced refresh:
   ```bash
   python3 fpl_service.py --refresh
   ```

## Database Setup

Run the SQL migrations in your Supabase project:
1. `supabase_migrations/001_initial_schema.sql`
2. `supabase_migrations/002_materialized_views.sql`

## Production Deployment

See `DEPLOYMENT.md` for detailed server deployment instructions including:
- DigitalOcean droplet setup
- Service configuration
- Monitoring and troubleshooting

## Tech Stack
- Python (FastAPI, asyncio, requests)
- Supabase (PostgreSQL)
- FPL Official API
- Automated monitoring and data refresh

Perfect for FPL enthusiasts building mobile apps or data analysis tools that need reliable, up-to-date Premier League fantasy data.
