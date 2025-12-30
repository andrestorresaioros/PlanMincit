import uuid
from sqlalchemy import Column, DateTime, String, Boolean, Text, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base

class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)

    # GUARDAR HASH del secret, no el secret plano
    secret_hash = Column(String(255), nullable=False)

    # uno o varios redirect uris (para MVP, 1)
    redirect_uri = Column(Text, nullable=False)

    # opcional: "admin" o "municipio" para controlar qué tipo de user puede usar ese client
    client_type = Column(String(30), nullable=False)  # "admin" | "municipio"

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
