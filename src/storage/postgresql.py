from asyncpg import create_pool, Pool
from typing import Dict, Any, List, Optional
import structlog
from src.config import settings

logger = structlog.get_logger()

class PostgresClient:
    def __init__(self):
        self.pool: Optional[Pool] = None
        
    async def init_pool(self):
        """Initialize connection pool"""
        if not self.pool:
            self.pool = await create_pool(
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                host=settings.POSTGRES_SERVER,
                min_size=5,
                max_size=20
            )
            
    async def init_tables(self):
        """Initialize database tables"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS migration_status (
                    id SERIAL PRIMARY KEY,
                    content_id VARCHAR(255) NOT NULL,
                    url TEXT NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    error_message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS content_hierarchy (
                    id SERIAL PRIMARY KEY,
                    content_id VARCHAR(255) NOT NULL,
                    parent_id VARCHAR(255),
                    level INTEGER NOT NULL,
                    path TEXT[] NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_migration_status_content_id 
                ON migration_status(content_id);
                
                CREATE INDEX IF NOT EXISTS idx_content_hierarchy_content_id 
                ON content_hierarchy(content_id);
            """)
            
    async def update_migration_status(
        self, 
        content_id: str, 
        url: str, 
        status: str, 
        error_message: Optional[str] = None
    ):
        """Update migration status for content"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO migration_status (content_id, url, status, error_message)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (content_id) DO UPDATE
                SET status = $3,
                    error_message = $4,
                    updated_at = CURRENT_TIMESTAMP
            """, content_id, url, status, error_message)
            
    async def store_hierarchy(
        self, 
        content_id: str, 
        parent_id: Optional[str],
        level: int, 
        path: List[str]
    ):
        """Store content hierarchy information"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO content_hierarchy 
                (content_id, parent_id, level, path)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (content_id) DO UPDATE
                SET parent_id = $2,
                    level = $3,
                    path = $4
            """, content_id, parent_id, level, path)
            
    async def get_migration_stats(self) -> Dict[str, int]:
        """Get migration statistics"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetch("""
                SELECT status, COUNT(*) as count
                FROM migration_status
                GROUP BY status
            """)
            return {row['status']: row['count'] for row in stats}
    
    async def close(self):
        """Close the database pool"""
        if self.pool:
            await self.pool.close() 