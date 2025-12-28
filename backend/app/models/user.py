"""User model"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.session import Base


class UserRole(str, enum.Enum):
    """User roles enum"""
    ADMIN = "ADMIN"
    AUTHORITY = "AUTHORITY"


class User(Base):
    """User model - base user for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    authority_profile = relationship("AuthorityProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    instrument_assignments = relationship("AuthorityInstrumentAssignment", back_populates="authority_user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
