"""Document model"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, BigInteger, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class Document(Base):
    """Document model - files uploaded by authorities"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False)
    owner_authority_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)  # Ruta en sistema de archivos
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    size_bytes = Column(BigInteger, nullable=False)
    phase = Column(String(100), nullable=True)  # Fase del plan (Alistamiento, Diagnóstico, etc.)
    component = Column(String(100), nullable=True)  # Componente del plan (slug)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    instrument = relationship("Instrument", back_populates="documents")
    owner = relationship("User", back_populates="documents")
    
    def __repr__(self):
        return f"<Document {self.title} (instrument_id={self.instrument_id})>"
