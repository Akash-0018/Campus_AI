"""
Configuration settings for Campus AI application
"""
import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application Configuration"""
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_ENV: str = os.getenv("API_ENV", "development")
    RELOAD: bool = os.getenv("RELOAD", "true").lower() == "true"
    
    # Application Info
    APP_NAME: str = os.getenv("APP_NAME", "Campus AI")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./campus_ai.db")
    DB_POOL_MIN: int = int(os.getenv("DB_POOL_MIN", "5"))
    DB_POOL_MAX: int = int(os.getenv("DB_POOL_MAX", "20"))
    
    # Google Cloud Configuration
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    GCP_CREDENTIALS_PATH: str = os.getenv("GCP_CREDENTIALS_PATH", "")
    
    # JWT Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-super-secret-key-change-this")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_DAYS: int = int(os.getenv("JWT_EXPIRATION_DAYS", "30"))
    
    # ChromaDB & Embeddings
    CHROMA_PERSISTENT_PATH: str = os.getenv("CHROMA_PERSISTENT_PATH", "./chroma_data")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # LLM Configuration (Google Gemini)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # CORS Configuration
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
    
    class Config:
        case_sensitive = True
        env_file = ".env"

# Load settings
settings = Settings()

# Helper functions for exported configuration
APP_NAME = settings.APP_NAME
APP_VERSION = settings.APP_VERSION
DEBUG = settings.DEBUG
API_HOST = settings.API_HOST
API_PORT = settings.API_PORT
RELOAD = settings.RELOAD
DATABASE_URL = settings.DATABASE_URL
DB_POOL_MIN = settings.DB_POOL_MIN
DB_POOL_MAX = settings.DB_POOL_MAX
JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_EXPIRATION_DAYS = settings.JWT_EXPIRATION_DAYS
CHROMA_PERSISTENT_PATH = settings.CHROMA_PERSISTENT_PATH
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
GCP_PROJECT_ID = settings.GCP_PROJECT_ID
GCP_CREDENTIALS_PATH = settings.GCP_CREDENTIALS_PATH
LLM_PROVIDER = settings.LLM_PROVIDER
GOOGLE_API_KEY = settings.GOOGLE_API_KEY
OPENAI_API_KEY = settings.OPENAI_API_KEY
FRONTEND_URL = settings.FRONTEND_URL
BACKEND_URL = settings.BACKEND_URL

def get_cors_config() -> dict:
    """Get CORS configuration"""
    origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]
    return {
        "allow_origins": origins,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
