"""Authority Profile model"""
import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class AuthorityType(str, enum.Enum):
    """Authority subtypes"""
    MUNICIPIO = "MUNICIPIO"
    DEPARTAMENTO = "DEPARTAMENTO"
    REGION = "REGION"
    INDEPENDIENTE = "INDEPENDIENTE"


class AuthorityProfile(Base):
    """Authority profile - extends User for authority-specific data"""
    __tablename__ = "authority_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    authority_type = Column(SQLEnum(AuthorityType), nullable=False)
    display_name = Column(String(255), nullable=False)  # Nombre de la entidad
    additional_data = Column(Text, nullable=True)  # JSON opcional para info adicional
    
    # Códigos de identificación según tipo de autoridad
    codigo_municipio = Column(String(10), nullable=True, index=True)  # Para MUNICIPIO
    codigo_departamento = Column(String(10), nullable=True, index=True)  # Para DEPARTAMENTO
    codigo_region = Column(String(10), nullable=True, index=True)  # Para REGION
    cedula = Column(String(20), nullable=True, index=True)  # Para INDEPENDIENTE
    
    # Relationships
    user = relationship("User", back_populates="authority_profile")
    
    def __repr__(self):
        return f"<AuthorityProfile {self.display_name} ({self.authority_type})>"
