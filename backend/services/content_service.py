from __future__ import annotations
from datetime import datetime, timezone
import re
from typing import Iterable, Optional

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.content import Content, ContentStatus, ContentType
from app.models.user import User, UserRole

# ----------------------
# Utilidades
# ----------------------

_slug_pattern = re.compile(r"[^a-z0-9\-]+")

def slugify(text: str) -> str:
    """
    Convierte un título en slug básico: minúsculas, guiones, sin acentos.
    """
    # Normalización simple (sin unicodedata por mantener dependencias mínimas)
    t = text.strip().lower()
    t = t.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    t = re.sub(r"\s+", "-", t)
    t = _slug_pattern.sub("-", t)
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t or "item"

def _ensure_unique_slug(db: Session, type_value: str, slug_base: str, content_id_to_exclude: Optional[int] = None) -> str:
    """
    Garantiza unicidad (type, slug). Si existe, añade sufijos -2, -3, ...
    """
    slug = slug_base
    i = 2
    while True:
        stmt = select(Content.id).where(
            and_(
                Content.type == type_value,
                Content.slug == slug,
                Content.id != (content_id_to_exclude or 0),
            )
        )
        exists = db.execute(stmt).scalar_one_or_none()
        if not exists:
            return slug
        slug = f"{slug_base}-{i}"
        i += 1

def _require_owner_or_admin(user: User, content: Content) -> None:
    if user.role != UserRole.SUPER_ADMIN.value and content.author_id != user.id:
        raise HTTPException(status_code=403, detail="No puedes operar sobre recursos que no son tuyos")

def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)  # almacenamos naive UTC en DB

# ----------------------
# Capa de servicio
# ----------------------

class ContentService:
    """
    Servicio con las operaciones de negocio y transiciones de estado.
    Se levanta HTTPException para que los routers no tengan que repetir lógica de errores.
    """

    # ------- CREATE / UPDATE / DELETE (CREATOR & ADMIN) -------

    @staticmethod
    def create(db: Session, author: User, *, type_value: str, title: str, summary: str | None, slug: str | None, payload: dict | None) -> Content:
        if author.role not in (UserRole.CREATOR.value, UserRole.SUPER_ADMIN.value):
            raise HTTPException(status_code=403, detail="Permisos insuficientes")

        if type_value not in (t.value for t in ContentType):
            raise HTTPException(status_code=422, detail="Tipo de contenido inválido")

        base_slug = slugify(slug or title)
        final_slug = _ensure_unique_slug(db, type_value, base_slug)

        obj = Content(
            type=type_value,
            status=ContentStatus.DRAFT.value,
            title=title.strip(),
            slug=final_slug,
            summary=(summary or "").strip() or None,
            author_id=author.id,
            payload=payload or None,
        )
        db.add(obj)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # En teoría _ensure_unique_slug ya evita choques, pero por si acaso
            raise HTTPException(status_code=409, detail="Conflicto al crear el contenido (slug/índice único)")
        db.refresh(obj)
        return obj

    @staticmethod
    def update_by_author(db: Session, author: User, content_id: int, *, title: str | None, summary: str | None, slug: str | None, payload: dict | None) -> Content:
        obj = db.get(Content, content_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Contenido no encontrado")

        _require_owner_or_admin(author, obj)

        if obj.status not in (ContentStatus.DRAFT.value, ContentStatus.REVIEW.value) and author.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=409, detail="No puedes editar contenidos que no estén en DRAFT o REVIEW")

        # Actualiza campos
        if title is not None:
            obj.title = title.strip()
        if summary is not None:
            obj.summary = (summary or "").strip() or None
        if payload is not None:
            obj.payload = payload

        # Slug opcional (recalcular unicidad)
        if slug is not None:
            base_slug = slugify(slug or obj.title)
            obj.slug = _ensure_unique_slug(db, obj.type, base_slug, content_id_to_exclude=obj.id)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Conflicto al actualizar (slug/índice único)")
        db.refresh(obj)
        return obj

    @staticmethod
    def delete_by_author(db: Session, author: User, content_id: int) -> None:
        obj = db.get(Content, content_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Contenido no encontrado")
        _require_owner_or_admin(author, obj)

        if obj.status not in (ContentStatus.DRAFT.value, ContentStatus.REVIEW.value) and author.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=409, detail="No puedes eliminar contenidos que no estén en DRAFT o REVIEW")

        db.delete(obj)
        db.commit()

    # ------- TRANSICIONES -------

    @staticmethod
    def submit_for_review(db: Session, author: User, content_id: int, comment: str | None = None) -> Content:
        obj = db.get(Content, content_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Contenido no encontrado")
        _require_owner_or_admin(author, obj)

        if author.role == UserRole.CREATOR.value and obj.author_id != author.id:
            # Ya protegido por _require_owner_or_admin, pero dejamos claro:
            raise HTTPException(status_code=403, detail="No puedes enviar a revisión contenidos de otros autores")

        if obj.status != ContentStatus.DRAFT.value:
            raise HTTPException(status_code=409, detail="Solo puedes enviar a revisión contenidos en DRAFT")

        obj.status = ContentStatus.REVIEW.value
        obj.submitted_at = _now_utc()
        obj.rejected_reason = None  # limpiar rechazo previo si existía
        # (Si implementas ContentLog, aquí registrarías el comentario)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def publish(db: Session, admin: User, content_id: int) -> Content:
        if admin.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Solo el Super Admin puede publicar")

        obj = db.get(Content, content_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Contenido no encontrado")
        if obj.status != ContentStatus.REVIEW.value:
            raise HTTPException(status_code=409, detail="Solo se pueden publicar contenidos en REVIEW")

        obj.status = ContentStatus.PUBLISHED.value
        obj.published_at = _now_utc()
        obj.rejected_reason = None
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def reject(db: Session, admin: User, content_id: int, reason: str) -> Content:
        if admin.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Solo el Super Admin puede rechazar")

        obj = db.get(Content, content_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Contenido no encontrado")
        if obj.status != ContentStatus.REVIEW.value:
            raise HTTPException(status_code=409, detail="Solo se pueden rechazar contenidos en REVIEW")

        obj.status = ContentStatus.REJECTED.value
        obj.rejected_reason = reason.strip()
        db.commit()
        db.refresh(obj)
        return obj

    # ------- QUERIES -------

    @staticmethod
    def list_public(db: Session, type_value: str, *, limit: int = 20, offset: int = 0) -> list[Content]:
        if type_value not in (t.value for t in ContentType):
            raise HTTPException(status_code=422, detail="Tipo de contenido inválido")

        stmt = (
            select(Content)
            .where(
                and_(
                    Content.type == type_value,
                    Content.status == ContentStatus.PUBLISHED.value,
                )
            )
            .order_by(Content.published_at.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        return list(db.execute(stmt).scalars())

    @staticmethod
    def get_public_by_slug(db: Session, type_value: str, slug: str) -> Content:
        if type_value not in (t.value for t in ContentType):
            raise HTTPException(status_code=422, detail="Tipo de contenido inválido")

        stmt = select(Content).where(
            and_(
                Content.type == type_value,
                Content.status == ContentStatus.PUBLISHED.value,
                Content.slug == slug,
            )
        )
        obj = db.execute(stmt).scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="Contenido no encontrado o no publicado")
        return obj

    @staticmethod
    def list_my_contents(db: Session, author: User, *, status: Optional[str] = None) -> list[Content]:
        conditions = [Content.author_id == author.id]
        if status:
            conditions.append(Content.status == status)
        stmt = select(Content).where(and_(*conditions)).order_by(Content.created_at.desc())
        return list(db.execute(stmt).scalars())

    @staticmethod
    def list_review_queue(db: Session) -> list[Content]:
        stmt = select(Content).where(Content.status == ContentStatus.REVIEW.value).order_by(Content.submitted_at.asc().nulls_last())
        return list(db.execute(stmt).scalars())

    @staticmethod
    def list_all_contents(db: Session, *, status: Optional[str] = None) -> list[Content]:
        """Lista todo el contenido del sistema (solo para admins). Opcionalmente filtra por estado."""
        conditions = []
        if status:
            conditions.append(Content.status == status)
        stmt = select(Content).where(and_(*conditions) if conditions else True).order_by(Content.created_at.desc())
        return list(db.execute(stmt).scalars())

    @staticmethod
    def admin_update(db: Session, admin: User, content_id: int, *, title: str | None, summary: str | None, slug: str | None, payload: dict | None) -> Content:
        if admin.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")

        obj = db.get(Content, content_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Contenido no encontrado")

        if title is not None:
            obj.title = title.strip()
        if summary is not None:
            obj.summary = (summary or "").strip() or None
        if payload is not None:
            obj.payload = payload
        if slug is not None:
            base_slug = slugify(slug or obj.title)
            obj.slug = _ensure_unique_slug(db, obj.type, base_slug, content_id_to_exclude=obj.id)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Conflicto al actualizar (slug/índice único)")
        db.refresh(obj)
        return obj

    @staticmethod
    def admin_delete(db: Session, admin: User, content_id: int) -> None:
        if admin.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        obj = db.get(Content, content_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Contenido no encontrado")
        db.delete(obj)
        db.commit()
