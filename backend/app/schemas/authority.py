"""Authority schemas"""
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.models.authority_profile import AuthorityType
from app.models.instrument import InstrumentCode
from app.models.authority_instrument_assignment import AssignmentRole


class AuthorityProfileBase(BaseModel):
    """Base authority profile schema"""
    authority_type: AuthorityType
    display_name: str = Field(..., min_length=1, max_length=255)
    additional_data: Optional[str] = None


class AuthorityProfileCreate(AuthorityProfileBase):
    """Schema for creating authority profile"""
    pass


class AuthorityProfileUpdate(BaseModel):
    """Schema for updating authority profile"""
    authority_type: Optional[AuthorityType] = None
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    additional_data: Optional[str] = None


class AuthorityProfileResponse(AuthorityProfileBase):
    """Schema for authority profile response"""
    id: int
    user_id: int
    
    class Config:
        from_attributes = True


class InstrumentAssignment(BaseModel):
    """Instrument assignment for authority creation"""
    instrument_code: InstrumentCode
    role: AssignmentRole


class AuthorityCreateRequest(BaseModel):
    """Schema for creating a new authority user (admin only)"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    authority_type: AuthorityType
    display_name: str = Field(..., min_length=1, max_length=255)
    additional_data: Optional[str] = None
    instrument_assignments: List[InstrumentAssignment] = Field(..., min_items=3, max_items=3)


class AuthorityUpdateRequest(BaseModel):
    """Schema for updating an authority user"""
    authority_type: Optional[AuthorityType] = None
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    additional_data: Optional[str] = None
    is_active: Optional[bool] = None
    # Opcional: permitir reasignación de instrumentos (requiere validación compleja)
    instrument_assignments: Optional[List[InstrumentAssignment]] = Field(None, min_items=3, max_items=3)


class AuthorityDetailResponse(BaseModel):
    """Detailed authority response with assignments and documents count"""
    id: int
    email: str
    is_active: bool
    authority_type: AuthorityType
    display_name: str
    additional_data: Optional[str]
    instrument_assignments: List["InstrumentAssignmentResponse"]
    documents_count: int = 0
    
    class Config:
        from_attributes = True


# Avoid circular import
from app.schemas.instrument import InstrumentAssignmentResponse
AuthorityDetailResponse.model_rebuild()
