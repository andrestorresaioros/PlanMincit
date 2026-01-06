# app/services/idear_service.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import re
import unicodedata

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.models.idear import Idear, IdearSolicitud

# ------------------ Constantes ------------------
ESTADO_PENDIENTE = "PENDIENTE"
ESTADO_APROBADA  = "APROBADA"
ESTADO_RECHAZADA = "RECHAZADA"

# ------------------ Helpers ------------------
def _slugify(s: str) -> str:
    """Genera slug normalizado desde un string"""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9\-]+", "-", s.strip().lower())
    s = re.sub(r"-{2,}", "-", s).strip("-")
    # Truncar a 300 caracteres para dejar espacio para el sufijo numérico
    s = s[:300] if s else "herramienta"
    return s or "herramienta"

def _unique_slug(db: Session, base: Optional[str]) -> str:
    """Genera un slug único verificando contra la BD"""
    base_slug = _slugify(base or "herramienta")
    slug = base_slug
    n = 1
    while db.scalar(
        select(func.count()).select_from(Idear).where(Idear.slug == slug)
    ):
        slug = f"{base_slug}-{n}"
        n += 1
    return slug

# ================== CREADOR ==================

def crear_solicitud(db: Session, user_id: int, data: Dict[str, Any]) -> IdearSolicitud:
    """
    Crea la solicitud y queda ENVIADA de una vez:
    - estado = PENDIENTE
    - submitted_at = now
    - NO editable
    - Eliminable mientras siga PENDIENTE
    """
    for required in ("nombre_herramienta", "url"):
        if not data.get(required):
            raise HTTPException(status_code=400, detail=f"{required} es obligatorio")

    obj = IdearSolicitud(
        created_by=user_id,
        estado=ESTADO_PENDIENTE,
        submitted_at=datetime.utcnow(),
        motivo_rechazo=None,
        **{k: v for k, v in data.items() if hasattr(IdearSolicitud, k)}
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def actualizar_solicitud(db: Session, solicitud_id: int, user_id: int, data: Dict[str, Any]) -> IdearSolicitud:
    """
    Ya NO existen borradores. Toda solicitud nace enviada.
    => Nunca es editable.
    """
    obj = db.get(IdearSolicitud, solicitud_id)
    if not obj or obj.created_by != user_id:
        raise HTTPException(status_code=404, detail="No encontrado")
    raise HTTPException(status_code=400, detail="No editable (la solicitud se envía al crear)")

def eliminar_solicitud(db: Session, solicitud_id: int, user_id: int, is_admin: bool = False) -> None:
    """
    Eliminable:
    - CREATOR: Puede eliminar sus propias solicitudes en cualquier estado (PENDIENTE, APROBADA, RECHAZADA)
    - SUPER_ADMIN: Puede eliminar cualquier solicitud en cualquier estado
    """
    obj = db.get(IdearSolicitud, solicitud_id)
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

def enviar_solicitud(db: Session, solicitud_id: int, user_id: int) -> IdearSolicitud:
    """
    Compatibilidad si existe el endpoint /enviar:
    ya no aplica porque la solicitud se "envía" al crear.
    """
    obj = db.get(IdearSolicitud, solicitud_id)
    if not obj or obj.created_by != user_id:
        raise HTTPException(status_code=404, detail="No encontrado")
    raise HTTPException(status_code=400, detail="No aplicable: las solicitudes se envían al crear")

# ================== ADMIN ==================

def listar_pendientes(db: Session) -> List[IdearSolicitud]:
    """
    Lista TODAS las solicitudes PENDIENTE (ya enviadas al crear),
    ordenadas por fecha de envío más reciente.
    """
    stmt = (
        select(IdearSolicitud)
        .where(IdearSolicitud.estado == ESTADO_PENDIENTE)
        .order_by(IdearSolicitud.submitted_at.desc())
    )
    return list(db.execute(stmt).scalars())

def listar_todas_solicitudes(db: Session) -> List[IdearSolicitud]:
    """
    Lista TODAS las solicitudes (PENDIENTE, APROBADA, RECHAZADA),
    ordenadas por fecha de actualización más reciente.
    """
    stmt = (
        select(IdearSolicitud)
        .order_by(IdearSolicitud.updated_at.desc())
    )
    return list(db.execute(stmt).scalars())

def rechazar_solicitud(db: Session, solicitud_id: int, motivo: str) -> IdearSolicitud:
    obj = db.get(IdearSolicitud, solicitud_id)
    if not obj:
        raise HTTPException(status_code=404, detail="No encontrado")
    if obj.estado != ESTADO_PENDIENTE:
        raise HTTPException(status_code=400, detail="Solo se pueden rechazar solicitudes PENDIENTE")

    obj.estado = ESTADO_RECHAZADA
    obj.motivo_rechazo = motivo or "Sin motivo"
    obj.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(obj)
    return obj

def aprobar_solicitud(db: Session, solicitud_id: int, overrides: Dict[str, Any], approver_id: int) -> Idear:
    obj = db.get(IdearSolicitud, solicitud_id)
    if not obj:
        raise HTTPException(status_code=404, detail="No encontrado")
    if obj.estado != ESTADO_PENDIENTE:
        raise HTTPException(status_code=400, detail="Solo se pueden aprobar solicitudes PENDIENTE")

    # Merge de campos (overrides > solicitud)
    data = {
        "nombre_herramienta": overrides.get("nombre_herramienta", obj.nombre_herramienta),
        "url": overrides.get("url", obj.url),
        "descripcion_breve": overrides.get("descripcion_breve", obj.descripcion_breve),
        "paquete": overrides.get("paquete", obj.paquete),
        "publico_objetivo": overrides.get("publico_objetivo", obj.publico_objetivo),
        "subfase": overrides.get("subfase", obj.subfase),
        "objetivo": overrides.get("objetivo", obj.objetivo),
        "nivel_madurez": overrides.get("nivel_madurez", obj.nivel_madurez),
        "imagen_url": overrides.get("imagen_url", obj.imagen_url),
    }

    # Requisitos mínimos
    if not data["nombre_herramienta"] or not data["url"]:
        raise HTTPException(status_code=400, detail="nombre_herramienta y url son obligatorios")

    # Slug
    slug = overrides.get("slug") or _unique_slug(
        db, obj.nombre_herramienta or obj.url
    )

    # ---- PRECHECKS para 409 explícitos ----
    # URL duplicada ya publicada
    existing = db.scalar(select(Idear).where(Idear.url == data["url"]))
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe una herramienta publicada con esa URL (ID={existing.id})"
        )

    # Slug duplicado (raro, pero posible si override manual)
    existing_slug = db.scalar(select(Idear).where(Idear.slug == slug))
    if existing_slug:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe una herramienta con ese slug (ID={existing_slug.id})"
        )

    # Crear en tabla idear
    publicado = Idear(
        slug=slug,
        created_by=approver_id,
        published_at=datetime.utcnow(),
        **data
    )
    db.add(publicado)

    # Marcar solicitud como APROBADA
    obj.estado = ESTADO_APROBADA
    obj.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(publicado)
    return publicado

# ================== PÚBLICO ==================

def listar_publicos(
    db: Session,
    paquete: Optional[str],
    q: Optional[str],
    limit: int,
    offset: int
) -> Tuple[List[Idear], int]:
    """Lista herramientas publicadas con filtros opcionales"""
    stmt = select(Idear)
    
    if paquete:
        stmt = stmt.where(Idear.paquete.ilike(f"%{paquete}%"))
    
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Idear.nombre_herramienta.ilike(like))
            | (Idear.descripcion_breve.ilike(like))
            | (Idear.objetivo.ilike(like))
            | (Idear.paquete.ilike(like))
        )
    
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = list(
        db.execute(
            stmt.order_by(Idear.published_at.desc()).limit(limit).offset(offset)
        ).scalars()
    )
    return items, total or 0

def obtener_por_slug(db: Session, slug: str) -> Optional[Idear]:
    """Obtiene herramienta por slug"""
    return db.scalar(select(Idear).where(Idear.slug == slug))
