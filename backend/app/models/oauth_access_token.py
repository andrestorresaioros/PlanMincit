import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base

class OAuthAccessToken(Base):
    __tablename__ = "oauth_access_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(ForeignKey("users.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("oauth_clients.id"), nullable=False)

    access_token_hash = Column(String(255), nullable=False)
    refresh_token_hash = Column(String(255), nullable=False)

    scopes = Column(String(500), nullable=True)  # CSV simple para MVP
    revoked = Column(Boolean, nullable=False, default=False)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
