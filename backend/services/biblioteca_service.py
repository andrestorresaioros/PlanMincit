# app/services/biblioteca_service.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.models.biblioteca import Biblioteca, BibliotecaSolicitud

# ------------------ Constantes ------------------
ESTADO_PENDIENTE = "PENDIENTE"
ESTADO_APROBADA  = "APROBADA"
ESTADO_RECHAZADA = "RECHAZADA"

# ------------------ Helpers ------------------
def _slugify(s: str) -> str:
    import re, unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9\-]+", "-", s.strip().lower())
    s = re.sub(r"-{2,}", "-", s).strip("-")
    # Truncar a 300 caracteres para dejar espacio para el sufijo numérico
    s = s[:300] if s else "recurso"
    return s or "recurso"

def _unique_slug(db: Session, base: Optional[str]) -> str:
    base_slug = _slugify(base or "recurso")
    slug = base_slug
    n = 1
    while db.scalar(
        select(func.count()).select_from(Biblioteca).where(Biblioteca.slug == slug)
    ):
        n += 1
        slug = f"{base_slug}-{n}"
    return slug

# ================== CREADOR ==================

def crear_solicitud(db: Session, user_id: int, data: Dict[str, Any]) -> BibliotecaSolicitud:
    """
    Crea la solicitud y queda ENVIADA de una vez:
    - estado = PENDIENTE
    - submitted_at = now
    - NO editable
    - Eliminable mientras siga PENDIENTE
    """
    for required in ("tipo_recurso", "enlace", "imagen_url"):
        if not data.get(required):
            raise HTTPException(status_code=400, detail=f"{required} es obligatorio.")

    obj = BibliotecaSolicitud(
        created_by=user_id,
        estado=ESTADO_PENDIENTE,
        submitted_at=datetime.utcnow(),   # Se envía inmediatamente
        motivo_rechazo=None,
        **{k: v for k, v in data.items() if hasattr(BibliotecaSolicitud, k)}
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def actualizar_solicitud(db: Session, solicitud_id: int, user_id: int, data: Dict[str, Any]) -> BibliotecaSolicitud:
    """
    Ya NO existen borradores. Toda solicitud nace enviada.
    => Nunca es editable.
    """
    obj = db.get(BibliotecaSolicitud, solicitud_id)
    if not obj or obj.created_by != user_id:
        raise HTTPException(status_code=404, detail="No encontrado")
    raise HTTPException(status_code=400, detail="No editable (la solicitud se envía al crear)")

def eliminar_solicitud(db: Session, solicitud_id: int, user_id: int, is_admin: bool = False) -> None:
    """
    Eliminable:
    - CREATOR: Puede eliminar sus propias solicitudes en cualquier estado (PENDIENTE, APROBADA, RECHAZADA)
    - SUPER_ADMIN: Puede eliminar cualquier solicitud en cualquier estado
    """
    obj = db.get(BibliotecaSolicitud, solicitud_id)
    if not obj:
        raise ValueError("No encontrado")

    # Verificar permisos
    if not is_admin:
        # CREATOR: solo puede eliminar sus propias solicitudes (en cualquier estado)
        if obj.created_by != user_id:
            raise ValueError("No encontrado")
    # ADMIN puede eliminar cualquier solicitud en cualquier estado

    db.delete(obj)
    db.commit()

def enviar_solicitud(db: Session, solicitud_id: int, user_id: int) -> BibliotecaSolicitud:
    """
    Compatibilidad si existe el endpoint /enviar:
    ya no aplica porque la solicitud se “envía” al crear.
    """
    obj = db.get(BibliotecaSolicitud, solicitud_id)
    if not obj or obj.created_by != user_id:
        raise HTTPException(status_code=404, detail="No encontrado")
    raise HTTPException(status_code=400, detail="No aplicable: las solicitudes se envían al crear")

# ================== ADMIN ==================

def listar_pendientes(db: Session) -> List[BibliotecaSolicitud]:
    """
    Lista TODAS las solicitudes PENDIENTE (ya enviadas al crear),
    ordenadas por fecha de envío más reciente.
    """
    stmt = (
        select(BibliotecaSolicitud)
        .where(BibliotecaSolicitud.estado == ESTADO_PENDIENTE)
        .order_by(BibliotecaSolicitud.submitted_at.desc())
    )
    return list(db.execute(stmt).scalars())

def listar_todas_solicitudes(db: Session) -> List[BibliotecaSolicitud]:
    """
    Lista TODAS las solicitudes (PENDIENTE, APROBADA, RECHAZADA),
    ordenadas por fecha de actualización más reciente.
    """
    stmt = (
        select(BibliotecaSolicitud)
        .order_by(BibliotecaSolicitud.updated_at.desc())
    )
    return list(db.execute(stmt).scalars())

def rechazar_solicitud(db: Session, solicitud_id: int, motivo: str) -> BibliotecaSolicitud:
    obj = db.get(BibliotecaSolicitud, solicitud_id)
    if not obj:
        raise ValueError("No encontrada")
    if obj.estado != ESTADO_PENDIENTE:
        raise ValueError("No rechazable (no enviada o ya procesada)")

    obj.estado = ESTADO_RECHAZADA
    obj.motivo_rechazo = motivo or "Sin motivo"
    obj.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(obj)
    return obj

def aprobar_solicitud(db: Session, solicitud_id: int, overrides: Dict[str, Any], approver_id: int) -> Biblioteca:
    obj = db.get(BibliotecaSolicitud, solicitud_id)
    if not obj:
        raise ValueError("No encontrada")
    if obj.estado != ESTADO_PENDIENTE:
        raise ValueError("No aprobable (no enviada o ya procesada)")

    # Merge de campos (overrides > solicitud)
    data = {
        "tipo_recurso": overrides.get("tipo_recurso", obj.tipo_recurso),
        "enlace": overrides.get("enlace", obj.enlace),
        "descripcion_uso": overrides.get("descripcion_uso", obj.descripcion_uso),
        "descripcion_breve": overrides.get("descripcion_breve", obj.descripcion_breve),
        "categoria_tematica": overrides.get("categoria_tematica", obj.categoria_tematica),
        "publico_objetivo": overrides.get("publico_objetivo", obj.publico_objetivo),
        "nivel_madurez": overrides.get("nivel_madurez", obj.nivel_madurez),
        "anio": overrides.get("anio", obj.anio),
        "autores": overrides.get("autores", obj.autores),
        "formato": overrides.get("formato", obj.formato),
        "imagen_url": overrides.get("imagen_url", obj.imagen_url),
    }

    # Requisitos mínimos
    if not data["tipo_recurso"] or not data["enlace"] or not data["imagen_url"]:
        raise ValueError("tipo_recurso, enlace e imagen_url son obligatorios para publicar")

    # Slug
    slug = overrides.get("slug") or _unique_slug(
        db, obj.descripcion_uso or obj.autores or obj.enlace
    )

    # ---- PRECHECKS para 409 explícitos ----
    # Enlace duplicado ya publicado
    existing = db.scalar(select(Biblioteca).where(Biblioteca.enlace == data["enlace"]))
    if existing:
        # Verificar si esta solicitud ya fue aprobada antes
        if obj.estado == ESTADO_APROBADA:
            raise HTTPException(
                status_code=409,
                detail="Esta solicitud ya fue aprobada anteriormente. El recurso ya está publicado en la biblioteca."
            )
        else:
            raise HTTPException(
                status_code=409, 
                detail=f"Ya existe un recurso publicado con este enlace. No se puede aprobar esta solicitud porque el enlace está duplicado."
            )

    # Slug duplicado ya publicado
    if db.scalar(select(func.count()).select_from(Biblioteca).where(Biblioteca.slug == slug)):
        # Si hay conflicto de slug, generamos uno nuevo único
        slug = _unique_slug(db, f"{slug}-{solicitud_id}")

    publicado = Biblioteca(
        slug=slug,
        created_by=approver_id,
        published_at=datetime.utcnow(),
        **data
    )
    db.add(publicado)

    try:
        obj.estado = ESTADO_APROBADA
        obj.updated_at = datetime.utcnow()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="conflict")
    else:
        db.refresh(publicado)
        return publicado

# ================== PÚBLICO ==================

def listar_publicos(
    db: Session,
    tipo_recurso: Optional[str],
    q: Optional[str],
    limit: int,
    offset: int
) -> Tuple[List[Biblioteca], int]:
    stmt = select(Biblioteca)
    if tipo_recurso:
        stmt = stmt.where(Biblioteca.tipo_recurso.ilike(f"%{tipo_recurso}%"))
    if q:
        like = f"%{q}%"
        B = Biblioteca
        stmt = stmt.where(
            (B.descripcion_uso.ilike(like)) |
            (B.categoria_tematica.ilike(like)) |
            (B.autores.ilike(like)) |
            (B.formato.ilike(like))
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = list(db.execute(
        stmt.order_by(Biblioteca.published_at.desc()).limit(limit).offset(offset)
    ).scalars())
    return items, int(total or 0)

def obtener_por_slug(db: Session, slug: str) -> Optional[Biblioteca]:
    return db.execute(
        select(Biblioteca).where(Biblioteca.slug == slug)
    ).scalar_one_or_none()
