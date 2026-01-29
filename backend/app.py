"""Main FastAPI application for Campus AI"""
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# Import database
from database.connection import db_pool
from models import *
from sqlmodel import SQLModel

# Import routes
from routes.auth_routes import router as auth_router
from routes.user_routes import router as user_router
from routes.resume_routes import router as resume_router
from routes.chat_routes_new import router as chat_router
from routes.admin_routes import router as admin_router

# Import config
from utils.config import (
    API_HOST,
    API_PORT,
    RELOAD,
    APP_NAME,
    APP_VERSION,
    get_cors_config,
    DB_POOL_MIN,
    DB_POOL_MAX
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    
    # Startup
    logger.info("=" * 50)
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    logger.info("=" * 50)
    
    try:
        # Initialize database
        db_pool.initialize_pool(minconn=DB_POOL_MIN, maxconn=DB_POOL_MAX)
        logger.info("✓ Database initialized")
        
        # Create tables
        SQLModel.metadata.create_all(db_pool._engine)
        logger.info("✓ Database tables created")
        
        logger.info(f"✓ Application started on {API_HOST}:{API_PORT}")
    except Exception as e:
        logger.error(f"✗ Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("=" * 50)
    logger.info("Shutting down application...")
    logger.info("=" * 50)
    
    try:
        db_pool.close_all_connections()
        logger.info("✓ Application shutdown complete")
    except Exception as e:
        logger.error(f"✗ Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Campus AI - AI-powered recruitment platform",
    redoc_url=None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    **get_cors_config()
)

# Include routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(resume_router)
app.include_router(chat_router)
app.include_router(admin_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "status": "running"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": APP_NAME
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=API_HOST,
        port=API_PORT,
        reload=RELOAD
    )
