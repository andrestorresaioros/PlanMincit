"""Instrument model"""
import enum
from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.session import Base


class InstrumentCode(str, enum.Enum):
    """Instrument codes"""
    RURAL = "RURAL"
    URBANO = "URBANO"
    REGION = "REGION"


class Instrument(Base):
    """Instrument model - represents planning instruments"""
    __tablename__ = "instruments"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(SQLEnum(InstrumentCode), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    
    # Relationships
    assignments = relationship("AuthorityInstrumentAssignment", back_populates="instrument", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="instrument", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Instrument {self.code} - {self.name}>"
