"""Admin endpoints - authority and document management"""
from typing import List, Dict
from uuid import UUID
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.authority_instrument_assignment import AssignmentRole
from app.models.document import Document
from app.models.user import User
from app.schemas.authority import (
    AuthorityCreateRequest,
    AuthorityDetailResponse,
    AuthorityUpdateRequest,
)
from app.schemas.document import DocumentResponse, DocumentUpdate
from app.schemas.instrument import InstrumentAssignmentResponse
from app.schemas.oauth_client import (
    OAuthClientCreateRequest,
    OAuthClientCreateResponse,
    OAuthClientResponse,
    OAuthClientRevokeResponse,
)
from app.services.authority_service import AuthorityService
from app.services.document_service import DocumentService
from app.services.oauth_client_service import OAuthClientService
from app.data_sources.diccionario_municipios import MUNICIPIOS_COLOMBIA, DEPARTAMENTOS_COLOMBIA

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# -------------------------
# Helpers (anti-None / anti-mismatch)
# -------------------------

def _safe_profile(user: User):
    """authority_profile can be None depending on seed/data. Return it safely."""
    return getattr(user, "authority_profile", None)


def _safe_instrument_fields(assignment):
    """
    assignment.instrument can be None or lazy-load issues.
    Return (instrument_code, instrument_name).
    """
    inst = getattr(assignment, "instrument", None)
    return (
        getattr(inst, "code", None),
        getattr(inst, "name", None),
    )


def _safe_territory_name(assignment):
    """
    Your DB currently may NOT have authority_instrument_assignments.territory_name.
    Accessing assignment.territory_name triggers a SELECT including that column -> crash.
    So we must NOT touch it if column doesn't exist.

    Best-effort:
    - If ORM already loaded attribute in memory, getattr might still trigger lazy load.
    - The only safe way without changing relationship loading strategy is: try/except around
      attribute access, and return None if it fails.
    """
    try:
        return getattr(assignment, "territory_name", None)
    except Exception:
        # avoids crashing if column doesn't exist in DB
        return None


def _build_assignments(user: User) -> List[InstrumentAssignmentResponse]:
    assignments: List[InstrumentAssignmentResponse] = []
    for assignment in getattr(user, "instrument_assignments", []) or []:
        role = getattr(assignment, "assignment_role", None)
        role_display = (
            "lider de planificacion"
            if role == AssignmentRole.LEADER_PLANNING
            else "aliado estrategico"
        )
        instrument_code, instrument_name = _safe_instrument_fields(assignment)

        assignments.append(
            InstrumentAssignmentResponse(
                id=getattr(assignment, "id", None),
                instrument_id=getattr(assignment, "instrument_id", None),
                instrument_code=instrument_code,
                instrument_name=instrument_name,
                assignment_role=role,
                role_display=role_display,
                territory_name=_safe_territory_name(assignment),
                created_at=getattr(assignment, "created_at", None),
            )
        )
    return assignments


def _documents_count(db: Session, user_id: int) -> int:
    return (
        db.query(func.count(Document.id))
        .filter(Document.owner_authority_user_id == user_id)
        .scalar()
        or 0
    )


def _build_authority_detail_response(db: Session, user: User) -> AuthorityDetailResponse:
    """
    Centralize response building to avoid repeating logic and to guard None values.
    """
    import json
    
    profile = _safe_profile(user)
    assignments = _build_assignments(user)
    docs_count = _documents_count(db, user.id)
    
    # Extraer contact_email del additional_data si existe
    contact_email = None
    additional_data = getattr(profile, "additional_data", None)
    if additional_data:
        try:
            data_dict = json.loads(additional_data) if isinstance(additional_data, str) else {}
            contact_email = data_dict.get('contact_email')
        except:
            pass
    
    # Determinar qué email mostrar
    display_email = user.email
    authority_type = getattr(profile, "authority_type", None)
    
    # Para MUNICIPIO y DEPARTAMENTO, mostrar el contact_email si existe
    if authority_type in ['MUNICIPIO', 'DEPARTAMENTO'] and contact_email:
        display_email = contact_email

    return AuthorityDetailResponse(
        id=user.id,
        email=display_email,
        is_active=user.is_active,

        # profile can be None
        authority_type=authority_type,
        display_name=getattr(profile, "display_name", None),
        additional_data=getattr(profile, "additional_data", None),
        codigo_municipio=getattr(profile, "codigo_municipio", None),
        codigo_departamento=getattr(profile, "codigo_departamento", None),
        codigo_region=getattr(profile, "codigo_region", None),
        cedula=getattr(profile, "cedula", None),

        instrument_assignments=assignments,
        documents_count=docs_count,
    )


# -------------------------
# Authorities
# -------------------------

@router.post(
    "/authorities",
    response_model=AuthorityDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_authority(
    data: AuthorityCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Create a new authority user with profile and instrument assignments.
    Only admins can create authorities.
    """
    user = AuthorityService.create_authority_user(db, data)
    return _build_authority_detail_response(db, user)


@router.get("/authorities", response_model=List[AuthorityDetailResponse])
async def list_authorities(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    List all authority users with their profiles and assignments.
    Only admins can access.
    """
    users = AuthorityService.get_authority_users(db)
    return [_build_authority_detail_response(db, u) for u in users]


@router.get("/authorities/{authority_id}", response_model=AuthorityDetailResponse)
async def get_authority_detail(
    authority_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Get detailed information about a specific authority user.
    Only admins can access.
    """
    user = AuthorityService.get_authority_by_id(db, authority_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Autoridad no encontrada",
        )
    return _build_authority_detail_response(db, user)


@router.patch("/authorities/{authority_id}", response_model=AuthorityDetailResponse)
async def update_authority(
    authority_id: int,
    data: AuthorityUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
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
    _: User = Depends(require_admin),
):
    """
    List all documents in the system.
    Only admins can access.
    """
    documents = DocumentService.get_all_documents(db)

    result: List[DocumentResponse] = []
    for doc in documents:
        # Convertir file_path a URL pública
        download_url = (
            f"/{quote(doc.file_path.replace(chr(92), '/'))}"
            if getattr(doc, "file_path", None)
            else None
        )

        owner = getattr(doc, "owner", None)
        owner_profile = getattr(owner, "authority_profile", None) if owner else None

        instrument = getattr(doc, "instrument", None)

        result.append(
            DocumentResponse(
                id=doc.id,
                instrument_id=getattr(doc, "instrument_id", None),
                instrument_code=getattr(instrument, "code", None),
                owner_authority_user_id=getattr(doc, "owner_authority_user_id", None),
                owner_email=getattr(owner, "email", None),
                owner_display_name=getattr(owner_profile, "display_name", None) or "N/A",
                title=getattr(doc, "title", None),
                description=getattr(doc, "description", None),
                original_filename=getattr(doc, "original_filename", None),
                file_path=getattr(doc, "file_path", None),
                download_url=download_url,
                content_type=getattr(doc, "content_type", None),
                size_bytes=getattr(doc, "size_bytes", None),
                created_at=getattr(doc, "created_at", None),
                updated_at=getattr(doc, "updated_at", None),
            )
        )

    return result


@router.patch("/documents/{document_id}", response_model=DocumentResponse)
async def update_document_admin(
    document_id: int,
    data: DocumentUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update document metadata.
    Only admins can update any document.
    """
    document = DocumentService.update_document(db, current_user, document_id, data)

    download_url = (
        f"/{quote(document.file_path.replace(chr(92), '/'))}"
        if getattr(document, "file_path", None)
        else None
    )

    owner = getattr(document, "owner", None)
    owner_profile = getattr(owner, "authority_profile", None) if owner else None
    instrument = getattr(document, "instrument", None)

    return DocumentResponse(
        id=document.id,
        instrument_id=getattr(document, "instrument_id", None),
        instrument_code=getattr(instrument, "code", None),
        owner_authority_user_id=getattr(document, "owner_authority_user_id", None),
        owner_email=getattr(owner, "email", None),
        owner_display_name=getattr(owner_profile, "display_name", None) or "N/A",
        title=getattr(document, "title", None),
        description=getattr(document, "description", None),
        original_filename=getattr(document, "original_filename", None),
        file_path=getattr(document, "file_path", None),
        download_url=download_url,
        content_type=getattr(document, "content_type", None),
        size_bytes=getattr(document, "size_bytes", None),
        created_at=getattr(document, "created_at", None),
        updated_at=getattr(document, "updated_at", None),
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_admin(
    document_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Delete a document.
    Only admins can delete any document.
    """
    DocumentService.delete_document(db, current_user, document_id)
    return None


@router.delete(
    "/authorities/{authority_id}/instruments/{instrument_code}/documents",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_authority_instrument_documents(
    authority_id: int,
    instrument_code: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Delete all documents for a specific authority and instrument.
    Only admins can delete documents.
    """
    from app.models.instrument import Instrument

    instrument = db.query(Instrument).filter(Instrument.code == instrument_code).first()
    if not instrument:
        raise HTTPException(
            status_code=404,
            detail=f"Instrument with code '{instrument_code}' not found",
        )

    authority = db.query(User).filter(User.id == authority_id).first()
    if not authority:
        raise HTTPException(
            status_code=404,
            detail=f"Authority with id {authority_id} not found",
        )

    documents = (
        db.query(Document)
        .filter(
            Document.owner_authority_user_id == authority_id,
            Document.instrument_id == instrument.id,
        )
        .all()
    )

    for document in documents:
        DocumentService.delete_document(db, current_user, document.id)

    return None


# -------------------------
# OAuth Clients
# -------------------------

@router.post(
    "/oauth/clients",
    response_model=OAuthClientCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_oauth_client(
    data: OAuthClientCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Crea un OAuth Client (client_id + client_secret).
    IMPORTANTE: el client_secret se retorna SOLO UNA VEZ.
    """
    client, secret = OAuthClientService.create_client(
        db, data.name, data.client_type, data.redirect_uri
    )
    return OAuthClientCreateResponse(
        client_id=client.id,
        client_secret=secret,
        name=client.name,
        client_type=client.client_type,
        redirect_uri=client.redirect_uri,
    )


@router.get("/oauth/clients", response_model=List[OAuthClientResponse])
async def list_oauth_clients(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    clients = OAuthClientService.list_clients(db)
    return [
        OAuthClientResponse(
            client_id=c.id,
            name=c.name,
            client_type=c.client_type,
            redirect_uri=c.redirect_uri,
            is_active=c.is_active,
        )
        for c in clients
    ]


@router.post(
    "/oauth/clients/{client_id}/revoke",
    response_model=OAuthClientRevokeResponse,
)
async def revoke_oauth_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    client = OAuthClientService.revoke_client(db, client_id)
    return OAuthClientRevokeResponse(client_id=client.id, is_active=client.is_active)


@router.get("/territorios", response_model=Dict)
async def get_territorios(
    _: User = Depends(require_admin)
):
    """
    Obtiene la lista de municipios y departamentos del DIVIPOLA.
    Solo accesible para administradores.
    
    Returns:
        - municipios: Lista de objetos con {nombre, codigo} ordenados alfabéticamente
        - departamentos: Lista de objetos con {nombre, codigo} ordenados alfabéticamente
    """
    # Convertir diccionarios a listas de objetos ordenados
    municipios = [
        {"nombre": nombre, "codigo": codigo} 
        for nombre, codigo in sorted(MUNICIPIOS_COLOMBIA.items(), key=lambda x: x[0])
    ]
    
    departamentos = [
        {"nombre": nombre, "codigo": codigo}
        for nombre, codigo in sorted(DEPARTAMENTOS_COLOMBIA.items(), key=lambda x: x[0])
    ]
    
    return {
        "municipios": municipios,
        "departamentos": departamentos
    }
