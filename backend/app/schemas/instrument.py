"""Instrument schemas"""
from datetime import datetime
from pydantic import BaseModel
from app.models.instrument import InstrumentCode
from app.models.authority_instrument_assignment import AssignmentRole


class InstrumentBase(BaseModel):
    """Base instrument schema"""
    code: InstrumentCode
    name: str


class InstrumentResponse(InstrumentBase):
    """Schema for instrument response"""
    id: int
    
    class Config:
        from_attributes = True


class InstrumentAssignmentCreate(BaseModel):
    """Schema for creating instrument assignment"""
    authority_user_id: int
    instrument_id: int
    assignment_role: AssignmentRole


class InstrumentAssignmentResponse(BaseModel):
    """Schema for instrument assignment response"""
    id: int
    instrument_id: int
    instrument_code: InstrumentCode
    instrument_name: str
    assignment_role: AssignmentRole
    role_display: str  # "lider de planificacion" o "aliado estrategico"
    created_at: datetime
    
    class Config:
        from_attributes = True
