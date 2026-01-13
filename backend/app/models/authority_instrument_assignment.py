"""Authority Instrument Assignment model"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SQLEnum, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.db.session import Base


class AssignmentRole(str, enum.Enum):
    """Assignment roles for instruments"""
    LEADER_PLANNING = "LEADER_PLANNING"  # Líder de planificación (1 por instrumento+territorio)
    STRATEGIC_ALLY = "STRATEGIC_ALLY"    # Aliado estratégico (max 10 por instrumento+territorio)


class AuthorityInstrumentAssignment(Base):
    """Assignment of authority users to instruments with specific roles"""
    __tablename__ = "authority_instrument_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    authority_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False)
    assignment_role = Column(SQLEnum(AssignmentRole), nullable=False)
    territory_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    authority_user = relationship("User", back_populates="instrument_assignments")
    instrument = relationship("Instrument", back_populates="assignments")
    
    # Constraints
    __table_args__ = (
        # Cada autoridad puede tener solo una asignación por instrumento
        UniqueConstraint('authority_user_id', 'instrument_id', name='uq_authority_instrument'),
        # Índice para facilitar búsqueda de líder por instrumento
        Index('ix_instrument_leader', 'instrument_id', 'assignment_role'),
    )
    
    def __repr__(self):
        return f"<Assignment user_id={self.authority_user_id} instrument_id={self.instrument_id} role={self.assignment_role}>"
