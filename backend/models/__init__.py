"""Models module for Campus AI"""
from sqlmodel import SQLModel
from .user import User, UserRole
from .resume import Resume
from .requirement import Requirement
from .match_result import MatchResult

__all__ = [
    "SQLModel",
    "User",
    "UserRole",
    "Resume",
    "Requirement",
    "MatchResult"
]
