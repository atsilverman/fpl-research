# FPL Data Service

Production-ready unified service for monitoring and synchronizing Fantasy Premier League data to Supabase.

## Files

- `fpl_service.py` - **Unified monitoring and refresh service** (recommended)
- `requirements.txt` - Python dependencies
- `supabase_migrations/` - Database schema files
- `DEPLOYMENT.md` - Server deployment guide

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
