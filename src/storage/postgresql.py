import asyncpg
from typing import Dict, Any, List, Optional
import structlog
from src.config import settings

logger = structlog.get_logger()

class PostgresClient:
    def __init__(self):
        self.pool = None
        
    async def init_pool(self):
        """Initialize connection pool"""
        self.pool = await asyncpg.create_pool(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            host=settings.POSTGRES_SERVER
        )
        
    async def init_tables(self):
        """Initialize database tables"""
        async with self.pool.acquire() as conn:
            # Create content_metadata table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS content_metadata (
                    id SERIAL PRIMARY KEY,
                    content_id VARCHAR(255) NOT NULL UNIQUE,
                    url TEXT NOT NULL,
                    title TEXT,
                    content_type VARCHAR(50),
                    word_count INTEGER,
                    media_count INTEGER,
                    parent_id VARCHAR(255),
                    hierarchy_level INTEGER DEFAULT 0,
                    hierarchy_path TEXT[],
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create migration_status table for future Contentful migration tracking
                CREATE TABLE IF NOT EXISTS migration_status (
                    id SERIAL PRIMARY KEY,
                    content_id VARCHAR(255) NOT NULL UNIQUE,
                    contentful_entry_id VARCHAR(255),
                    status VARCHAR(50) NOT NULL,  -- pending, in_progress, completed, failed
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    last_attempt TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (content_id) REFERENCES content_metadata(content_id) ON DELETE CASCADE
                );
                
                -- Indexes for better performance
                CREATE INDEX IF NOT EXISTS idx_content_metadata_content_id 
                ON content_metadata(content_id);
                CREATE INDEX IF NOT EXISTS idx_content_metadata_parent_id 
                ON content_metadata(parent_id);
                CREATE INDEX IF NOT EXISTS idx_migration_status_status 
                ON migration_status(status);
                CREATE INDEX IF NOT EXISTS idx_migration_status_content_id 
                ON migration_status(content_id);
            """)
            
            logger.info("Database tables initialized")
    
    async def store_content_metadata(
        self,
        content_id: str,
        url: str,
        metadata: Dict[str, Any],
        hierarchy: Optional[Dict[str, Any]] = None
    ):
        """Store content metadata with hierarchy information"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO content_metadata (
                    content_id, url, title, content_type, word_count,
                    media_count, parent_id, hierarchy_level, hierarchy_path
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (content_id) 
                DO UPDATE SET
                    title = EXCLUDED.title,
                    content_type = EXCLUDED.content_type,
                    word_count = EXCLUDED.word_count,
                    media_count = EXCLUDED.media_count,
                    parent_id = EXCLUDED.parent_id,
                    hierarchy_level = EXCLUDED.hierarchy_level,
                    hierarchy_path = EXCLUDED.hierarchy_path,
                    updated_at = CURRENT_TIMESTAMP
            """,
                content_id,
                url,
                metadata.get('title'),
                metadata.get('content_type'),
                metadata.get('word_count', 0),
                len(metadata.get('media', [])),
                hierarchy.get('parent_id') if hierarchy else None,
                hierarchy.get('level', 0) if hierarchy else 0,
                hierarchy.get('path', []) if hierarchy else []
            )
            
            logger.info(
                "Stored content metadata",
                content_id=content_id,
                url=url
            )
    
    async def get_content_hierarchy(self, content_id: str) -> Dict[str, Any]:
        """Get content hierarchy information"""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow("""
                SELECT 
                    content_id,
                    parent_id,
                    hierarchy_level,
                    hierarchy_path
                FROM content_metadata
                WHERE content_id = $1
            """, content_id)
            
            if record:
                return dict(record)
            return None
    
    async def get_content_stats(self) -> Dict[str, int]:
        """Get content statistics"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_pages,
                    COUNT(DISTINCT parent_id) as total_sections,
                    AVG(word_count) as avg_word_count,
                    SUM(media_count) as total_media
                FROM content_metadata
            """)
            
            return dict(stats)
    
    # Methods for future migration status tracking
    async def init_migration_status(self, content_id: str):
        """Initialize migration status for a content item"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO migration_status (content_id, status)
                VALUES ($1, 'pending')
                ON CONFLICT (content_id) DO NOTHING
            """, content_id)
    
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
        """Close database connection pool"""
        if self.pool:
            await self.pool.close() 