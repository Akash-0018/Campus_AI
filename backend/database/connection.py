"""Database connection management for Campus AI"""
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool, QueuePool
from sqlmodel import Session, SQLModel
from contextlib import contextmanager
from utils.config import DATABASE_URL, DB_POOL_MIN, DB_POOL_MAX

logger = logging.getLogger(__name__)

class DatabasePool:
    """Database connection pool manager"""
    
    def __init__(self):
        self._engine = None
        self._session_factory = None
    
    def initialize_pool(self, minconn: int = 1, maxconn: int = 10):
        """Initialize database connection pool"""
        try:
            # Use QueuePool for SQLite with threading support
            is_sqlite = "sqlite" in DATABASE_URL
            
            if is_sqlite:
                # SQLite doesn't support connection pooling well, so use NullPool
                self._engine = create_engine(
                    DATABASE_URL,
                    echo=False,
                    poolclass=NullPool,
                    connect_args={"check_same_thread": False}
                )
            else:
                self._engine = create_engine(
                    DATABASE_URL,
                    echo=False,
                    poolclass=QueuePool,
                    pool_size=minconn,
                    max_overflow=maxconn - minconn
                )
            
            # Enable WAL mode for SQLite
            if is_sqlite:
                @event.listens_for(self._engine, "connect")
                def set_sqlite_pragma(dbapi_conn, connection_record):
                    cursor = dbapi_conn.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.close()
            
            # Create all tables
            SQLModel.metadata.create_all(self._engine)
            logger.info(f"Database pool initialized successfully with URL: {DATABASE_URL}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get database session"""
        if self._engine is None:
            raise RuntimeError("Database pool not initialized")
        return Session(self._engine)
    
    @contextmanager
    def get_session_context(self):
        """Context manager for database session"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def close_all_connections(self):
        """Close all database connections"""
        if self._engine:
            self._engine.dispose()
            logger.info("All database connections closed")

# Global database pool instance
db_pool = DatabasePool()

def get_db_session() -> Session:
    """Dependency for getting database session in routes"""
    session = db_pool.get_session()
    try:
        yield session
    finally:
        session.close()
