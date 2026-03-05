"""Main FastAPI application for Campus AI"""
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

# Import database
from database.connection import db_pool
from models import *  # noqa: F401,F403

# Import routes
from routes.admin_routes import router as admin_router
from routes.auth_routes import router as auth_router
from routes.chat_routes_adk import router as chat_adk_router
from routes.multi_agent_routes import router as multi_agent_router
from routes.resume_routes import router as resume_router
from routes.user_routes import router as user_router

# Import config
from utils.config import (
    API_HOST,
    API_PORT,
    APP_NAME,
    APP_VERSION,
    DB_POOL_MAX,
    DB_POOL_MIN,
    RELOAD,
    get_cors_config,
)

# Import ADK framework components
try:
    from tools.registration import initialize_tool_registry

    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    logger_init = logging.getLogger(__name__)
    logger_init.warning("[ADK] Tool registry not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""

    logger.info("=" * 50)
    logger.info("Starting %s v%s", APP_NAME, APP_VERSION)
    logger.info("=" * 50)

    try:
        db_pool.initialize_pool(minconn=DB_POOL_MIN, maxconn=DB_POOL_MAX)
        logger.info("Database initialized")

        SQLModel.metadata.create_all(db_pool._engine)
        logger.info("Database tables created")

        # ADK is mandatory in ADK-only mode.
        if not ADK_AVAILABLE:
            raise RuntimeError("ADK is required but not available")

        guardrails_path = os.path.join(os.path.dirname(__file__), "guardrails.json")
        initialize_tool_registry(guardrails_path)
        logger.info("ADK framework initialized (Tool Registry & Guardrails)")

        from routes.multi_agent_routes import initialize_router

        initialize_router()
        logger.info("Multi-agent router initialized (4 agents available)")

        logger.info("Application started on %s:%s", API_HOST, API_PORT)
    except Exception as e:
        logger.error("Failed to initialize application: %s", e)
        raise

    yield

    logger.info("=" * 50)
    logger.info("Shutting down application...")
    logger.info("=" * 50)

    try:
        db_pool.close_all_connections()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error("Error during shutdown: %s", e)


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Campus AI - AI-powered recruitment platform",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, **get_cors_config())

# ADK-first routing only.
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(resume_router)
app.include_router(chat_adk_router)
app.include_router(multi_agent_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"app": APP_NAME, "version": APP_VERSION, "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    adk_status = "enabled" if ADK_AVAILABLE else "disabled"
    return {
        "status": "healthy",
        "app": APP_NAME,
        "adk_framework": adk_status,
        "chat_endpoints": "/api/chat-adk/* (ADK-powered only)",
        "multi_agent": "/api/multi-agent/* (4 agents: requirements, resume_matching, user_profile, coordinator)",
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host=API_HOST, port=API_PORT, reload=RELOAD)
