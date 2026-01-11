"""Document schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.instrument import InstrumentCode


class DocumentBase(BaseModel):
    """Base document schema"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    phase: Optional[str] = Field(None, max_length=100)
    component: Optional[str] = Field(None, max_length=100)


class DocumentCreate(DocumentBase):
    """Schema for creating document (used in service layer)"""
    instrument_code: InstrumentCode
    original_filename: str
    file_path: str
    content_type: Optional[str]
    size_bytes: int


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    phase: Optional[str] = Field(None, max_length=100)
    component: Optional[str] = Field(None, max_length=100)


class DocumentResponse(DocumentBase):
    """Schema for document response"""
    id: int
    instrument_id: int
    instrument_code: InstrumentCode
    owner_authority_user_id: int
    owner_email: str
    owner_display_name: str
    original_filename: str
    file_path: str
    download_url: str  # URL pública para descargar
    content_type: Optional[str]
    size_bytes: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentItemResponse(BaseModel):
    """Schema for simple document item in hierarchical response"""
    nombre: str
    urlfiledoc: str


class CriterioDocumentResponse(BaseModel):
    """Schema for criterion with its documents"""
    nombre_criterio: str
    criterios_documentos: list[DocumentItemResponse]


class EjeDocumentResponse(BaseModel):
    """Schema for axis (eje) with its criteria and documents"""
    eje: str
    criterios: list[CriterioDocumentResponse]


class AuthorityDocumentsResponse(BaseModel):
    """Schema for hierarchical documents response by authority"""
    cod_municipio: Optional[str] = None
    cod_departamento: Optional[str] = None
    cod_region: Optional[str] = None
    cedula: Optional[str] = None
    nombre_autoridad: str
    respuesta: list[EjeDocumentResponse]


class DocumentListResponse(BaseModel):
    """Schema for document list response"""
    total: int
    documents: list[DocumentResponse]
