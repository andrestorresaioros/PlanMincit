# services/convocatoria_service.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.convocatoria import Convocatoria, ConvocatoriaSolicitud

# ------------------ Constantes ------------------
ESTADO_PENDIENTE = "PENDIENTE"
ESTADO_APROBADA  = "APROBADA"
ESTADO_RECHAZADA = "RECHAZADA"


# ================== CREADOR ==================

def crear_solicitud(db: Session, user_id: int, data: Dict[str, Any]) -> ConvocatoriaSolicitud:
    """
    Crea la solicitud y queda ENVIADA de una vez:
    - estado = PENDIENTE
    - submitted_at = now
    - NO editable
    - Eliminable mientras siga PENDIENTE
    """
    for required in ("nombre_convocatoria", "entidad_convocante", "url_oficial"):
        if not data.get(required):
            raise HTTPException(status_code=400, detail=f"{required} es obligatorio")

    obj = ConvocatoriaSolicitud(
        created_by=user_id,
        estado=ESTADO_PENDIENTE,
        submitted_at=datetime.utcnow(),
        motivo_rechazo=None,
        **{k: v for k, v in data.items() if hasattr(ConvocatoriaSolicitud, k)}
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def actualizar_solicitud(db: Session, solicitud_id: int, user_id: int, data: Dict[str, Any]) -> ConvocatoriaSolicitud:
    """
    Ya NO existen borradores. Toda solicitud nace enviada.
    => Nunca es editable.
    """
    obj = db.get(ConvocatoriaSolicitud, solicitud_id)
    if not obj or obj.created_by != user_id:
        raise HTTPException(status_code=404, detail="No encontrado")
    raise HTTPException(status_code=400, detail="No editable (la solicitud se envía al crear)")

def eliminar_solicitud(db: Session, solicitud_id: int, user_id: int, is_admin: bool = False) -> None:
    """
    Eliminable:
    - CREATOR: Puede eliminar sus propias solicitudes en cualquier estado (PENDIENTE, APROBADA, RECHAZADA)
    - SUPER_ADMIN: Puede eliminar cualquier solicitud en cualquier estado
    """
    obj = db.get(ConvocatoriaSolicitud, solicitud_id)
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

# ================== ADMIN ==================

def listar_pendientes(db: Session) -> List[ConvocatoriaSolicitud]:
    """Lista solicitudes pendientes"""
    items = db.scalars(
        select(ConvocatoriaSolicitud)
        .where(ConvocatoriaSolicitud.estado == ESTADO_PENDIENTE)
        .order_by(ConvocatoriaSolicitud.submitted_at.desc())
    ).all()
    return list(items)

def listar_todas_solicitudes(db: Session) -> List[ConvocatoriaSolicitud]:
    """Lista todas las solicitudes (PENDIENTE, APROBADA, RECHAZADA)"""
    items = db.scalars(
        select(ConvocatoriaSolicitud)
        .order_by(ConvocatoriaSolicitud.submitted_at.desc())
    ).all()
    return list(items)


def aprobar_solicitud(db: Session, solicitud_id: int, overrides: Dict[str, Any], admin_id: int) -> Convocatoria:
    """
    Aprueba solicitud => Copia a tabla convocatoria
    Permite overrides de campos si el admin quiere ajustar al aprobar.
    """
    obj = db.get(ConvocatoriaSolicitud, solicitud_id)
    if not obj:
        raise ValueError("Solicitud no encontrada")
    if obj.estado != ESTADO_PENDIENTE:
        raise ValueError(f"Solicitud ya procesada: {obj.estado}")

    # Construir datos finales (solicitud + overrides)
    final_data = {
        "nombre_convocatoria": obj.nombre_convocatoria,
        "entidad_convocante": obj.entidad_convocante,
        "url_oficial": obj.url_oficial,
        "pais_region": obj.pais_region,
        "nivel_geografico": obj.nivel_geografico,
        "ambito_tematico": obj.ambito_tematico,
        "publico_objetivo": obj.publico_objetivo,
        "etapa_proyecto": obj.etapa_proyecto,
        "frecuencia_ciclo": obj.frecuencia_ciclo,
        "fechas_aproximadas": obj.fechas_aproximadas,
        "financiamiento_beneficio": obj.financiamiento_beneficio,
        "formato_participacion": obj.formato_participacion,
        "observaciones": obj.observaciones,
        "imagen_url": obj.imagen_url,
    }
    # Aplicar overrides
    for k, v in overrides.items():
        if k in final_data and v is not None:
            final_data[k] = v

    # Crear convocatoria publicada
    convocatoria = Convocatoria(
        created_by=obj.created_by,
        published_at=datetime.utcnow(),
        **final_data
    )
    db.add(convocatoria)

    # Marcar solicitud como aprobada
    obj.estado = ESTADO_APROBADA
    obj.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(convocatoria)
    return convocatoria

def rechazar_solicitud(db: Session, solicitud_id: int, motivo: str) -> ConvocatoriaSolicitud:
    """
    Rechaza solicitud => NO copia a tabla convocatoria
    """
    obj = db.get(ConvocatoriaSolicitud, solicitud_id)
    if not obj:
        raise ValueError("Solicitud no encontrada")
    if obj.estado != ESTADO_PENDIENTE:
        raise ValueError(f"Solicitud ya procesada: {obj.estado}")

    obj.estado = ESTADO_RECHAZADA
    obj.motivo_rechazo = motivo
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


def rechazar_solicitud(
    db: Session,
    solicitud_id: int,
    motivo_rechazo: Optional[str],
    user_email: str
) -> ConvocatoriaSolicitud:
    """
    Rechaza una solicitud de convocatoria (SUPER_ADMIN).
    Cambia el estado a RECHAZADA y opcionalmente guarda el motivo.
    """
    # Verificar que el admin existe
    admin = db.scalars(select(User).where(User.email == user_email)).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Obtener la solicitud
    solicitud = db.get(ConvocatoriaSolicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if solicitud.estado != "PENDIENTE":
        raise HTTPException(
            status_code=400,
            detail=f"La solicitud ya fue procesada (estado: {solicitud.estado})"
        )
    
    # Actualizar estado
    solicitud.estado = "RECHAZADA"
    solicitud.motivo_rechazo = motivo_rechazo
    solicitud.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(solicitud)
    
    return solicitud


# ================== ADMIN - CRUD DIRECTO ==================

def crear_convocatoria_directa(db: Session, user_id: int, data: Dict[str, Any]) -> Convocatoria:
    """
    SUPER_ADMIN crea convocatoria directamente (sin solicitud)
    """
    for required in ("nombre_convocatoria", "entidad_convocante", "url_oficial"):
        if not data.get(required):
            raise HTTPException(status_code=400, detail=f"{required} es obligatorio")

    obj = Convocatoria(
        created_by=user_id,
        published_at=datetime.utcnow(),
        **{k: v for k, v in data.items() if hasattr(Convocatoria, k)}
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def actualizar_convocatoria(db: Session, convocatoria_id: int, data: Dict[str, Any]) -> Convocatoria:
    """
    SUPER_ADMIN actualiza convocatoria publicada
    """
    obj = db.get(Convocatoria, convocatoria_id)
    if not obj:
        raise ValueError("Convocatoria no encontrada")
    
    for k, v in data.items():
        if hasattr(obj, k) and v is not None:
            setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj

def eliminar_convocatoria(db: Session, convocatoria_id: int) -> None:
    """
    SUPER_ADMIN elimina convocatoria publicada
    """
    obj = db.get(Convocatoria, convocatoria_id)
    if not obj:
        raise ValueError("Convocatoria no encontrada")
    db.delete(obj)
    db.commit()

def listar_convocatorias(db: Session) -> List[Convocatoria]:
    """
    Lista todas las convocatorias publicadas
    """
    items = db.scalars(
        select(Convocatoria).order_by(Convocatoria.created_at.desc())
    ).all()
    return list(items)
