"""Authority endpoints - document management for authorities"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from urllib.parse import quote
import os
import json
from app.db.session import get_db
from app.models.user import User
from app.models.instrument import InstrumentCode
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentUpdate, AuthorityDocumentsResponse
from app.schemas.ndtt import NDTTInfoResponse
from app.services.document_service import DocumentService
from app.services.ndtt_service import NDTTService
from app.api.dependencies import require_authority, get_current_user
from app.utils.text_utils import normalize_text

router = APIRouter(prefix="/authority", tags=["authority"], dependencies=[Depends(require_authority)])

# Router público sin autenticación (sin prefijo para usar códigos directamente)
public_router = APIRouter(tags=["authority-public"])


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
        # Convertir file_path a URL pública: uploads/rural/file.pdf -> /uploads/rural/file.pdf
        # Codificar espacios y caracteres especiales
        download_url = f"/{quote(doc.file_path.replace(chr(92), '/'))}" if doc.file_path else None
        
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
                download_url=download_url,
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
    
    # Convertir file_path a URL pública
    download_url = f"/{quote(document.file_path.replace(chr(92), '/'))}" if document.file_path else None
    
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
        download_url=download_url,
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
    Users can only update their own documents (admin can update any).
    """
    document = DocumentService.update_document(db, current_user, document_id, data)
    
    # Convertir file_path a URL pública
    download_url = f"/{quote(document.file_path.replace(chr(92), '/'))}" if document.file_path else None
    
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
        download_url=download_url,
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
    Users can only delete their own documents (admin can delete any).
    """
    DocumentService.delete_document(db, current_user, document_id)
    return None


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download a document file.
    Users can only download their own documents (except admin).
    """
    document = DocumentService.get_document_by_id(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    # Check access: admin can download any, users can only download their own
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        if document.owner_authority_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes descargar tus propios documentos"
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


@public_router.get("/{codigo}/{instrument_code}/{phase}/{component}/documents", response_model=List[DocumentResponse])
async def get_documents_by_code(
    codigo: str,
    instrument_code: InstrumentCode,
    phase: str,
    component: str,
    current_user: User = Depends(require_authority),
    db: Session = Depends(get_db)
):
    """
    Get documents for the current authenticated authority filtered by instrument, phase, and component.
    Uses authority code (municipio/departamento/region/cedula) in URL.
    Phase and component are normalized (no accents, no spaces, uppercase).
    
    Examples: 
    - /17013/RURAL/ALISTAMIENTO/PARTICIPACIONSOCIAL/documents (municipio 5 dígitos)
    - /5308/RURAL/ALISTAMIENTO/PARTICIPACIONSOCIAL/documents (municipio 4 dígitos, depto=05)
    - /17/RURAL/ALISTAMIENTO/PARTICIPACIONSOCIAL/documents (departamento 2 dígitos)
    """
    # Verificar que el código coincida con el usuario autenticado
    authority_profile = current_user.authority_profile
    if not authority_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario sin perfil de autoridad"
        )
    
    # Validar que el código corresponda al usuario
    user_code = None
    
    # Determinar el código del usuario según su tipo
    if authority_profile.codigo_municipio:
        user_code = authority_profile.codigo_municipio
    elif authority_profile.codigo_departamento:
        user_code = authority_profile.codigo_departamento
    elif authority_profile.codigo_region:
        user_code = authority_profile.codigo_region
    elif authority_profile.cedula:
        user_code = authority_profile.cedula
    
    # Lógica para códigos de departamento:
    # - Código de 4 dígitos (ej: 5308): departamento = "05" (agregar 0 adelante)
    # - Código de 5 dígitos (ej: 17013): departamento = primeros 2 dígitos ("17")
    if len(codigo) == 2 and authority_profile.codigo_municipio:
        # El usuario pasa código de departamento directamente
        codigo_municipio = authority_profile.codigo_municipio
        if len(codigo_municipio) == 4:
            # Código de 4 dígitos: departamento = "0" + primer dígito
            codigo_depto = "0" + codigo_municipio[0]
        else:
            # Código de 5 dígitos: departamento = primeros 2 dígitos
            codigo_depto = codigo_municipio[:2]
            
        if codigo != codigo_depto:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El código de departamento no corresponde a tu autoridad (esperado: {codigo_depto}, recibido: {codigo})"
            )
    elif user_code != codigo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El código no corresponde a tu autoridad"
        )
    
    # Normalizar phase y component (desnormalizar para buscar en BD)
    # La BD puede tener "Alistamiento" o "Visión de futuro"
    # Buscamos comparando versiones normalizadas
    documents = db.query(Document).filter(
        Document.owner_authority_user_id == current_user.id
    ).join(Document.instrument).filter(
        Document.instrument.has(code=instrument_code)
    ).all()
    
    # Filtrar por phase y component normalizados
    phase_normalized = normalize_text(phase)
    component_normalized = normalize_text(component)
    
    filtered_docs = [
        doc for doc in documents
        if normalize_text(doc.phase or "") == phase_normalized
        and normalize_text(doc.component or "") == component_normalized
    ]
    
    result = []
    for doc in filtered_docs:
        # Convertir file_path a URL pública
        download_url = f"/{quote(doc.file_path.replace(chr(92), '/'))}" if doc.file_path else None
        
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
                download_url=download_url,
                content_type=doc.content_type,
                size_bytes=doc.size_bytes,
                phase=doc.phase,
                component=doc.component,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
        )
    
    return result


# Mantener el endpoint anterior por compatibilidad (deprecated)


@router.get("/{instrument_code}/{phase}/{component}/documents", response_model=List[DocumentResponse])
async def get_my_documents_by_phase_component(
    instrument_code: InstrumentCode,
    phase: str,
    component: str,
    current_user: User = Depends(require_authority),
    db: Session = Depends(get_db)
):
    """
    Get documents for the current authenticated authority filtered by instrument, phase, and component.
    Returns simple list of documents.
    """
    # Obtener documentos del usuario actual filtrados
    documents = db.query(Document).filter(
        Document.owner_authority_user_id == current_user.id,
        Document.phase == phase,
        Document.component == component
    ).join(Document.instrument).filter(
        Document.instrument.has(code=instrument_code)
    ).all()
    
    result = []
    for doc in documents:
        # Convertir file_path a URL pública
        download_url = f"/{quote(doc.file_path.replace(chr(92), '/'))}" if doc.file_path else None
        
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
                download_url=download_url,
                content_type=doc.content_type,
                size_bytes=doc.size_bytes,
                phase=doc.phase,
                component=doc.component,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
        )
    
    return result


@public_router.get("/documents-by-authority", response_model=AuthorityDocumentsResponse)
async def get_documents_by_authority(
    instrument_code: InstrumentCode = Query(..., description="Código del instrumento (RURAL, URBANO, REGION)"),
    phase: str = Query(..., description="Fase del plan"),
    component: str = Query(..., description="Componente del plan"),
    codigo_municipio: Optional[str] = Query(None, description="Código del municipio"),
    codigo_departamento: Optional[str] = Query(None, description="Código del departamento"),
    codigo_region: Optional[str] = Query(None, description="Código de la región"),
    cedula: Optional[str] = Query(None, description="Cédula para autoridad independiente"),
    db: Session = Depends(get_db)
):
    """
    Get documents for a specific authority filtered by instrument, phase, and component.
    Returns hierarchical structure with ejes -> criterios -> documents.
    """
    from app.services.document_service import DocumentService
    
    # Validar que se proporcione al menos un parámetro de identificación
    if not any([codigo_municipio, codigo_departamento, codigo_region, cedula]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar al menos uno de: codigo_municipio, codigo_departamento, codigo_region, o cedula"
        )
    
    result = DocumentService.get_documents_by_authority_hierarchical(
        db=db,
        instrument_code=instrument_code,
        phase=phase,
        component=component,
        codigo_municipio=codigo_municipio,
        codigo_departamento=codigo_departamento,
        codigo_region=codigo_region,
        cedula=cedula
    )
    
    return result
