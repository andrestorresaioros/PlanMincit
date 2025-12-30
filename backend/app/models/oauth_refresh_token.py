import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class OAuthRefreshToken(Base):
    __tablename__ = "oauth_refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    access_token_id = Column(
        UUID(as_uuid=True),
        ForeignKey("oauth_access_tokens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    refresh_token_hash = Column(String(255), nullable=False)

    revoked = Column(Boolean, nullable=False, default=False)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
