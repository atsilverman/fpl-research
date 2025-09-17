"""
Database connection and utilities for FPL Vibe API
Handles Supabase REST API connection and query execution
"""

import os
import logging
from typing import Dict, Any, List, Optional
import httpx
import asyncio
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Database connection manager using Supabase REST API"""
    
    def __init__(self):
        # Supabase configuration
        self.supabase_url = "https://vgdhoezzjyjvekoulzfu.supabase.co"
        self.supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnZGhvZXp6anlqdmVrb3VsemZ1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODEzNjM2MSwiZXhwIjoyMDczNzEyMzYxfQ.qRmFXHvI6Li7dr52sHQ5e2yqfzW_r6MhPid6fX5pG54"
        
        # HTTP client
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                'apikey': self.supabase_key,
                'Authorization': f'Bearer {self.supabase_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'FPL-Vibe-API/1.0'
            }
        )
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    def _build_url(self, table: str, params: Dict[str, Any] = None) -> str:
        """Build Supabase REST API URL"""
        url = f"{self.supabase_url}/rest/v1/{table}"
        if params:
            query_string = urlencode(params, doseq=True)
            url = f"{url}?{query_string}"
        return url
    
    async def execute_query(self, table: str, select: str = "*", filters: Dict[str, Any] = None, 
                          order: str = None, limit: int = None, offset: int = None) -> List[Dict[str, Any]]:
        """Execute SELECT query using Supabase REST API"""
        try:
            params = {}
            if select != "*":
                params['select'] = select
            
            if filters:
                for key, value in filters.items():
                    if isinstance(value, list):
                        params[key] = f"in.({','.join(map(str, value))})"
                    else:
                        params[key] = f"eq.{value}"
            
            if order:
                params['order'] = order
            
            if limit:
                params['limit'] = str(limit)
            
            if offset:
                params['offset'] = str(offset)
            
            url = self._build_url(table, params)
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Database query error for table {table}: {e}")
            raise
    
    async def execute_scalar(self, table: str, select: str, filters: Dict[str, Any] = None) -> Any:
        """Execute query and return single value"""
        try:
            result = await self.execute_query(table, select, filters, limit=1)
            if result and len(result) > 0:
                # Return the first value from the first row
                return list(result[0].values())[0]
            return None
            
        except Exception as e:
            logger.error(f"Database scalar query error for table {table}: {e}")
            raise

# Global database instance
db_connection = DatabaseConnection()

async def get_database_connection():
    """Dependency to get database connection"""
    return db_connection

async def init_database():
    """Initialize database connection"""
    # HTTP client is already initialized in __init__
    pass

async def close_database():
    """Close database connection"""
    await db_connection.close()
