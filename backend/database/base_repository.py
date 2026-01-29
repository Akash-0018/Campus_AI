"""Base repository for Campus AI"""
from typing import TypeVar, Generic, Optional, List
from sqlmodel import Session, select
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")

class BaseRepository(Generic[T]):
    """Base repository for CRUD operations"""
    
    def __init__(self, session: Session, model: type[T]):
        self.session = session
        self.model = model
    
    def create(self, obj: T) -> T:
        """Create a new record"""
        try:
            self.session.add(obj)
            self.session.commit()
            self.session.refresh(obj)
            return obj
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise
    
    def read(self, id: int) -> Optional[T]:
        """Read a record by ID"""
        try:
            return self.session.get(self.model, id)
        except Exception as e:
            logger.error(f"Error reading {self.model.__name__} with id {id}: {e}")
            raise
    
    def read_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Read all records with pagination"""
        try:
            statement = select(self.model).offset(skip).limit(limit)
            return self.session.exec(statement).all()
        except Exception as e:
            logger.error(f"Error reading all {self.model.__name__}: {e}")
            raise
    
    def update(self, id: int, obj: T) -> Optional[T]:
        """Update a record"""
        try:
            existing = self.session.get(self.model, id)
            if not existing:
                return None
            
            obj_data = obj.dict(exclude_unset=True)
            for key, value in obj_data.items():
                setattr(existing, key, value)
            
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating {self.model.__name__} with id {id}: {e}")
            raise
    
    def delete(self, id: int) -> bool:
        """Delete a record"""
        try:
            existing = self.session.get(self.model, id)
            if not existing:
                return False
            
            self.session.delete(existing)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting {self.model.__name__} with id {id}: {e}")
            raise
