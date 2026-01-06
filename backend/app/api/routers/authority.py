"""Authority endpoints - document management for authorities"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import json
from app.db.session import get_db
from app.models.user import User
from app.models.instrument import InstrumentCode
from app.schemas.document import DocumentResponse, DocumentUpdate
from app.schemas.ndtt import NDTTInfoResponse
from app.services.document_service import DocumentService
from app.services.ndtt_service import NDTTService
from app.api.dependencies import require_authority, get_current_user

router = APIRouter(prefix="/authority", tags=["authority"], dependencies=[Depends(require_authority)])


@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents_by_instrument(
    instrument: InstrumentCode = Query(..., description="Código del instrumento (RURAL, URBANO, REGION)"),
    current_user: User = Depends(require_authority),
    db: Session = Depends(get_db)
):
    """
    Get all documents for a specific instrument.
    User must have assignment to the instrument (leader or ally).
    """
    documents = DocumentService.get_documents_by_instrument(db, current_user, instrument)
    
    result = []
    for doc in documents:
        result.append(
            DocumentResponse(
                id=doc.id,
                instrument_id=doc.instrument_id,
                instrument_code=doc.instrument.code,
                owner_authority_user_id=doc.owner_authority_user_id,
                owner_email=doc.owner.email,
                owner_display_name=doc.owner.authority_profile.display_name if doc.owner.authority_profile else "N/A",
                title=doc.title,
                description=doc.description,
                original_filename=doc.original_filename,
                file_path=doc.file_path,
                content_type=doc.content_type,
                size_bytes=doc.size_bytes,
                phase=doc.phase,
                component=doc.component,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
        )
    
    return result


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    instrument_code: InstrumentCode = Form(..., description="Código del instrumento"),
    title: str = Form(..., description="Título del documento"),
    description: Optional[str] = Form(None, description="Descripción del documento"),
    phase: Optional[str] = Form(None, description="Fase del plan"),
    component: Optional[str] = Form(None, description="Componente del plan (slug)"),
    file: UploadFile = File(..., description="Archivo a subir"),
    current_user: User = Depends(require_authority),
    db: Session = Depends(get_db)
):
    """
    Upload a new document for an instrument.
    Only LEADERS can upload documents.
    """
    document = await DocumentService.create_document(
        db, current_user, instrument_code, title, description, file, phase, component
    )
    
    return DocumentResponse(
        id=document.id,
        instrument_id=document.instrument_id,
        instrument_code=document.instrument.code,
        owner_authority_user_id=document.owner_authority_user_id,
        owner_email=document.owner.email,
        owner_display_name=document.owner.authority_profile.display_name if document.owner.authority_profile else "N/A",
        title=document.title,
        description=document.description,
        original_filename=document.original_filename,
        file_path=document.file_path,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        phase=document.phase,
        component=document.component,
        created_at=document.created_at,
        updated_at=document.updated_at
    )


@router.patch("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    data: DocumentUpdate,
    current_user: User = Depends(require_authority),
    db: Session = Depends(get_db)
):
    """
    Update document metadata (title, description).
    Only LEADERS of the instrument can update.
    """
    document = DocumentService.update_document(db, current_user, document_id, data)
    
    return DocumentResponse(
        id=document.id,
        instrument_id=document.instrument_id,
        instrument_code=document.instrument.code,
        owner_authority_user_id=document.owner_authority_user_id,
        owner_email=document.owner.email,
        owner_display_name=document.owner.authority_profile.display_name if document.owner.authority_profile else "N/A",
        title=document.title,
        description=document.description,
        original_filename=document.original_filename,
        file_path=document.file_path,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        phase=document.phase,
        component=document.component,
        created_at=document.created_at,
        updated_at=document.updated_at
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: User = Depends(require_authority),
    db: Session = Depends(get_db)
):
    """
    Delete a document.
    Only LEADERS of the instrument can delete.
    """
    DocumentService.delete_document(db, current_user, document_id)
    return None


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: User = Depends(get_current_user),  # Leader, ally, or admin
    db: Session = Depends(get_db)
):
    """
    Download a document file.
    Accessible by leaders, allies of the instrument, or admin.
    """
    document = DocumentService.get_document_by_id(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    # Check access: admin or user with instrument assignment
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        assignment = DocumentService.check_user_has_instrument_access(
            db, current_user.id, document.instrument.code
        )
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a este documento"
            )
    
    # Check if file exists
    if not os.path.exists(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado en el servidor"
        )
    
    return FileResponse(
        path=document.file_path,
        filename=document.original_filename,
        media_type=document.content_type or "application/octet-stream"
    )


@router.get("/ndtt-report", response_model=NDTTInfoResponse)
async def get_ndtt_report(
    current_user: User = Depends(require_authority),
    db: Session = Depends(get_db)
):
    """
    Get NDTT report information for the current user's municipality.
    Searches by municipality name from the user's territory assignment.
    """
    # Obtener el nombre del territorio del usuario
    nombre_municipio = None
    
    if current_user.instrument_assignments:
        # Obtener el territorio de la primera asignación
        for assignment in current_user.instrument_assignments:
            if assignment.territory_name:
                nombre_municipio = assignment.territory_name.strip()
                break
    
    # Si no hay territorio en assignments, intentar desde additional_data
    if not nombre_municipio and current_user.authority_profile and current_user.authority_profile.additional_data:
        try:
            additional_data = json.loads(current_user.authority_profile.additional_data)
            nombre_municipio = additional_data.get("nombre_municipio")
        except (json.JSONDecodeError, AttributeError):
            pass
    
    if not nombre_municipio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo determinar el nombre del municipio para este usuario. "
                   "Por favor, contacte al administrador para actualizar su perfil."
        )
    
    # Buscar datos en la API de NDTT por nombre del municipio
    ndtt_data = NDTTService.get_municipio_info(nombre_municipio)
    
    if not ndtt_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró información NDTT para el municipio '{nombre_municipio}'"
        )
    
    return NDTTInfoResponse(
        cod_municipio=ndtt_data.get("cod_municipio"),
        nombre_municipio=ndtt_data.get("nombre_municipio"),
        url_pdfinforme=ndtt_data.get("url_pdfinforme")
    )
