"""Authentication routes for Campus AI"""
import logging
import hashlib
import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlmodel import Session
from database.connection import get_db_session
from database.user_repository import get_user_repository
from models.user import User, UserRole
from utils.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_DAYS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

class RegisterRequest(BaseModel):
    """Register request model"""
    username: str
    email: EmailStr
    password: str
    full_name: str
    role: str = UserRole.USER.value

class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str
    user_id: int
    username: str
    role: str

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(user_id: int, role: str) -> str:
    """Create JWT access token"""
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, session: Session = Depends(get_db_session)):
    """User registration endpoint"""
    try:
        user_repo = get_user_repository(session)
        
        # Check if user already exists
        existing_user = user_repo.get_by_email(request.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        existing_username = user_repo.get_by_username(request.username)
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Create new user
        user = User(
            username=request.username,
            email=request.email,
            password_hash=hash_password(request.password),
            full_name=request.full_name,
            role=request.role,
            is_active=True,
            is_verified=False
        )
        
        user = user_repo.create(user)
        
        # Generate token
        token = create_access_token(user.user_id, user.role)
        
        logger.info(f"User registered successfully: {user.email}")
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.user_id,
            username=user.username,
            role=user.role
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in registration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, session: Session = Depends(get_db_session)):
    """User login endpoint"""
    try:
        user_repo = get_user_repository(session)
        
        user = user_repo.get_by_email(request.email)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if user.password_hash != hash_password(request.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not user.is_active:
            raise HTTPException(status_code=401, detail="User account is inactive")
        
        # Update last login
        user_repo.update_last_login(user.user_id)
        
        # Generate token
        token = create_access_token(user.user_id, user.role)
        
        logger.info(f"User logged in: {user.email}")
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.user_id,
            username=user.username,
            role=user.role
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

def get_current_user(token: str, session: Session = Depends(get_db_session)) -> User:
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
        user_repo = get_user_repository(session)
        user = user_repo.read(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
