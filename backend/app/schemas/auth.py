"""Authentication schemas"""
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole
from app.models.authority_profile import AuthorityType
from app.models.authority_instrument_assignment import AssignmentRole
from app.models.instrument import InstrumentCode


class LoginRequest(BaseModel):
    """Login request schema"""
    email: str = Field(..., description="Usuario (código DIVIPOLA o correo electrónico)")
    password: str


class Token(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token refresh request"""
    refresh_token: str


class InstrumentAssignmentInfo(BaseModel):
    """Instrument assignment info for Me response"""
    instrument_code: InstrumentCode
    instrument_name: str
    role: AssignmentRole
    role_display: str  # "lider de planificacion" o "aliado estrategico"
    territory_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class MeResponse(BaseModel):
    """Response for /auth/me endpoint"""
    id: int
    email: str
    role: UserRole
    is_active: bool
    
    # Authority specific fields (null for admin)
    authority_type: Optional[AuthorityType] = None
    display_name: Optional[str] = None
    instrument_assignments: List[InstrumentAssignmentInfo] = []
    
    class Config:
        from_attributes = True
