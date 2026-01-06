"""NDTT schemas"""
from pydantic import BaseModel
from typing import Optional


class NDTTInfoResponse(BaseModel):
    """Response model for NDTT municipality information"""
    cod_municipio: str
    nombre_municipio: str
    url_pdfinforme: Optional[str] = None
    
    class Config:
        from_attributes = True
