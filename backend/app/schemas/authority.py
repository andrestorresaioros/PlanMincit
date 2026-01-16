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
    codigo_municipio: Optional[str] = Field(None, max_length=10)
    codigo_departamento: Optional[str] = Field(None, max_length=10)
    codigo_region: Optional[str] = Field(None, max_length=10)
    cedula: Optional[str] = Field(None, max_length=20)


class AuthorityProfileCreate(AuthorityProfileBase):
    """Schema for creating authority profile"""
    pass


class AuthorityProfileUpdate(BaseModel):
    """Schema for updating authority profile"""
    authority_type: Optional[AuthorityType] = None
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    additional_data: Optional[str] = None
    codigo_municipio: Optional[str] = Field(None, max_length=10)
    codigo_departamento: Optional[str] = Field(None, max_length=10)
    codigo_region: Optional[str] = Field(None, max_length=10)
    cedula: Optional[str] = Field(None, max_length=20)


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
    territory_name: Optional[str] = None


class AuthorityCreateRequest(BaseModel):
    """Schema for creating a new authority user (admin only)"""
    email: Optional[EmailStr] = None  # Opcional: se genera automáticamente para MUNICIPIO y DEPARTAMENTO
    password: str = Field(..., min_length=8, description="La contraseña debe tener al menos 8 caracteres")
    authority_type: AuthorityType
    display_name: str = Field(..., min_length=1, max_length=255)
    additional_data: Optional[str] = None
    main_territory: Optional[str] = Field(None, description="Territorio principal que representa (para MUNICIPIO/DEPARTAMENTO)")
    codigo_municipio: Optional[str] = Field(None, max_length=10)
    codigo_departamento: Optional[str] = Field(None, max_length=10)
    codigo_region: Optional[str] = Field(None, max_length=10)
    cedula: Optional[str] = Field(None, max_length=20)
    instrument_assignments: List[InstrumentAssignment] = Field(..., min_items=1, max_items=3)


class AuthorityUpdateRequest(BaseModel):
    """Schema for updating an authority user"""
    authority_type: Optional[AuthorityType] = None
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    additional_data: Optional[str] = None
    codigo_municipio: Optional[str] = Field(None, max_length=10)
    codigo_departamento: Optional[str] = Field(None, max_length=10)
    codigo_region: Optional[str] = Field(None, max_length=10)
    cedula: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    # Opcional: permitir reasignación de instrumentos (permite múltiples asignaciones)
    instrument_assignments: Optional[List[InstrumentAssignment]] = Field(None, min_items=1)


class AuthorityDetailResponse(BaseModel):
    """Detailed authority response with assignments and documents count"""
    id: int
    email: str
    is_active: bool
    authority_type: AuthorityType
    display_name: str
    additional_data: Optional[str]
    codigo_municipio: Optional[str]
    codigo_departamento: Optional[str]
    codigo_region: Optional[str]
    cedula: Optional[str]
    instrument_assignments: List["InstrumentAssignmentResponse"]
    documents_count: int = 0
    
    class Config:
        from_attributes = True


# Avoid circular import
from app.schemas.instrument import InstrumentAssignmentResponse
AuthorityDetailResponse.model_rebuild()
