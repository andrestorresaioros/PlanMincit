"""Admin endpoints - authority and document management"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from urllib.parse import quote
from app.db.session import get_db
from app.models.user import User
from app.models.document import Document
from app.models.authority_instrument_assignment import AssignmentRole
from app.schemas.authority import (
    AuthorityCreateRequest, 
    AuthorityUpdateRequest, 
    AuthorityDetailResponse
)
from app.schemas.instrument import InstrumentAssignmentResponse
from app.schemas.document import DocumentResponse, DocumentUpdate
from app.services.authority_service import AuthorityService
from app.services.document_service import DocumentService
from app.api.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

from uuid import UUID
from app.schemas.oauth_client import (
    OAuthClientCreateRequest,
    OAuthClientCreateResponse,
    OAuthClientResponse,
    OAuthClientRevokeResponse,
)
from app.services.oauth_client_service import OAuthClientService

@router.post("/authorities", response_model=AuthorityDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_authority(
    data: AuthorityCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Create a new authority user with profile and instrument assignments.
    Only admins can create authorities.
    
    Validations:
    - Email must be unique
    - At least 1 instrument must be assigned (maximum 3)
    - Password must be at least 8 characters
    - Maximum 1 LEADER_PLANNING per instrument+territory
    - Maximum 10 STRATEGIC_ALLY per instrument+territory
    """
    user = AuthorityService.create_authority_user(db, data)
    
    # Build response
    profile = user.authority_profile
    assignments = []
    
    for assignment in user.instrument_assignments:
        role_display = "lider de planificacion" if assignment.assignment_role == AssignmentRole.LEADER_PLANNING else "aliado estrategico"
        assignments.append(
            InstrumentAssignmentResponse(
                id=assignment.id,
                instrument_id=assignment.instrument_id,
                instrument_code=assignment.instrument.code,
                instrument_name=assignment.instrument.name,
                assignment_role=assignment.assignment_role,
                role_display=role_display,
                territory_name=assignment.territory_name,
                created_at=assignment.created_at
            )
        )
    
    documents_count = db.query(func.count(Document.id)).filter(
        Document.owner_authority_user_id == user.id
    ).scalar()
    
    return AuthorityDetailResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        authority_type=profile.authority_type,
        display_name=profile.display_name,
        additional_data=profile.additional_data,
        codigo_municipio=profile.codigo_municipio,
        codigo_departamento=profile.codigo_departamento,
        codigo_region=profile.codigo_region,
        cedula=profile.cedula,
        instrument_assignments=assignments,
        documents_count=documents_count
    )


@router.get("/authorities", response_model=List[AuthorityDetailResponse])
async def list_authorities(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    List all authority users with their profiles and assignments.
    Only admins can access.
    """
    users = AuthorityService.get_authority_users(db)
    
    result = []
    for user in users:
        profile = user.authority_profile
        assignments = []
        
        for assignment in user.instrument_assignments:
            role_display = "lider de planificacion" if assignment.assignment_role == AssignmentRole.LEADER_PLANNING else "aliado estrategico"
            assignments.append(
                InstrumentAssignmentResponse(
                    id=assignment.id,
                    instrument_id=assignment.instrument_id,
                    instrument_code=assignment.instrument.code,
                    instrument_name=assignment.instrument.name,
                    assignment_role=assignment.assignment_role,
                    role_display=role_display,
                    territory_name=assignment.territory_name,
                    created_at=assignment.created_at
                )
            )
        
        documents_count = db.query(func.count(Document.id)).filter(
            Document.owner_authority_user_id == user.id
        ).scalar()
        
        result.append(
            AuthorityDetailResponse(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
                authority_type=profile.authority_type,
                display_name=profile.display_name,
                additional_data=profile.additional_data,
                codigo_municipio=profile.codigo_municipio,
                codigo_departamento=profile.codigo_departamento,
                codigo_region=profile.codigo_region,
                cedula=profile.cedula,
                instrument_assignments=assignments,
                documents_count=documents_count
            )
        )
    
    return result


@router.get("/authorities/{authority_id}", response_model=AuthorityDetailResponse)
async def get_authority_detail(
    authority_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Get detailed information about a specific authority user.
    Only admins can access.
    """
    user = AuthorityService.get_authority_by_id(db, authority_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Autoridad no encontrada"
        )
    
    profile = user.authority_profile
    assignments = []
    
    for assignment in user.instrument_assignments:
        role_display = "lider de planificacion" if assignment.assignment_role == AssignmentRole.LEADER_PLANNING else "aliado estrategico"
        assignments.append(
            InstrumentAssignmentResponse(
                id=assignment.id,
                instrument_id=assignment.instrument_id,
                instrument_code=assignment.instrument.code,
                instrument_name=assignment.instrument.name,
                assignment_role=assignment.assignment_role,
                role_display=role_display,
                territory_name=assignment.territory_name,
                created_at=assignment.created_at
            )
        )
    
    documents_count = db.query(func.count(Document.id)).filter(
        Document.owner_authority_user_id == user.id
    ).scalar()
    
    return AuthorityDetailResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        authority_type=profile.authority_type,
        display_name=profile.display_name,
        additional_data=profile.additional_data,
        codigo_municipio=profile.codigo_municipio,
        codigo_departamento=profile.codigo_departamento,
        codigo_region=profile.codigo_region,
        cedula=profile.cedula,
        instrument_assignments=assignments,
        documents_count=documents_count
    )


@router.patch("/authorities/{authority_id}", response_model=AuthorityDetailResponse)
async def update_authority(
    authority_id: int,
    data: AuthorityUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Update authority user information.
    Can update profile info, active status, and instrument assignments.
    Only admins can update.
    """
    update_data = data.model_dump(exclude_unset=True)
    user = AuthorityService.update_authority(db, authority_id, update_data)
    
    profile = user.authority_profile
    assignments = []
    
    for assignment in user.instrument_assignments:
        role_display = "lider de planificacion" if assignment.assignment_role == AssignmentRole.LEADER_PLANNING else "aliado estrategico"
        assignments.append(
            InstrumentAssignmentResponse(
                id=assignment.id,
                instrument_id=assignment.instrument_id,
                instrument_code=assignment.instrument.code,
                instrument_name=assignment.instrument.name,
                assignment_role=assignment.assignment_role,
                role_display=role_display,
                territory_name=assignment.territory_name,
                created_at=assignment.created_at
            )
        )
    
    documents_count = db.query(func.count(Document.id)).filter(
        Document.owner_authority_user_id == user.id
    ).scalar()
    
    return AuthorityDetailResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        authority_type=profile.authority_type,
        display_name=profile.display_name,
        additional_data=profile.additional_data,
        codigo_municipio=profile.codigo_municipio,
        codigo_departamento=profile.codigo_departamento,
        codigo_region=profile.codigo_region,
        cedula=profile.cedula,
        instrument_assignments=assignments,
        documents_count=documents_count
    )


@router.delete("/authorities/{authority_id}", status_code=status.HTTP_200_OK)
async def delete_authority(
    authority_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Delete an authority user and all their associated data.
    Returns information about deleted documents.
    Only admins can delete authorities.
    """
    result = AuthorityService.delete_authority(db, authority_id)
    return {
        "message": "Autoridad eliminada correctamente",
        "deleted_user_id": result["deleted_user_id"],
        "documents_deleted": result["documents_deleted"]
    }


@router.get("/documents", response_model=List[DocumentResponse])
async def list_all_documents(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    List all documents in the system.
    Only admins can access.
    """
    documents = DocumentService.get_all_documents(db)
    
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
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
        )
    
    return result


@router.patch("/documents/{document_id}", response_model=DocumentResponse)
async def update_document_admin(
    document_id: int,
    data: DocumentUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update document metadata.
    Only admins can update any document.
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
        created_at=document.created_at,
        updated_at=document.updated_at
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_admin(
    document_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a document.
    Only admins can delete any document.
    """
    DocumentService.delete_document(db, current_user, document_id)
    return None


@router.delete("/authorities/{authority_id}/instruments/{instrument_code}/documents", status_code=status.HTTP_204_NO_CONTENT)
async def delete_authority_instrument_documents(
    authority_id: int,
    instrument_code: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete all documents for a specific authority and instrument.
    Only admins can delete documents.
    """
    from app.models.instrument import Instrument
    
    # Verificar que el instrumento existe
    instrument = db.query(Instrument).filter(Instrument.code == instrument_code).first()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument with code '{instrument_code}' not found")
    
    # Verificar que la autoridad existe
    authority = db.query(User).filter(User.id == authority_id).first()
    if not authority:
        raise HTTPException(status_code=404, detail=f"Authority with id {authority_id} not found")
    
    # Buscar y eliminar todos los documentos de esta autoridad para este instrumento
    documents = db.query(Document).filter(
        Document.owner_authority_user_id == authority_id,
        Document.instrument_id == instrument.id
    ).all()
    
    # Eliminar archivos físicos y registros de BD
    for document in documents:
        DocumentService.delete_document(db, current_user, document.id)
    
    return None


@router.post("/oauth/clients", response_model=OAuthClientCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_oauth_client(
    data: OAuthClientCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Crea un OAuth Client (client_id + client_secret).
    IMPORTANTE: el client_secret se retorna SOLO UNA VEZ.
    """
    client, secret = OAuthClientService.create_client(db, data.name, data.redirect_uris)
    return OAuthClientCreateResponse(
        client_id=client.id,
        client_secret=secret,
        name=client.name,
        redirect_uris=client.redirect_uris,
    )


@router.get("/oauth/clients", response_model=List[OAuthClientResponse])
async def list_oauth_clients(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    clients = OAuthClientService.list_clients(db)
    return [
        OAuthClientResponse(
            client_id=c.id,
            name=c.name,
            redirect_uris=c.redirect_uris,
            revoked=c.revoked,
        )
        for c in clients
    ]


@router.post("/oauth/clients/{client_id}/revoke", response_model=OAuthClientRevokeResponse)
async def revoke_oauth_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    client = OAuthClientService.revoke_client(db, client_id)
    return OAuthClientRevokeResponse(client_id=client.id, revoked=client.revoked)

