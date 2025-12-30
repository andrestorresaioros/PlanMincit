from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.session import Base


class OAuthAuthCode(Base):
    __tablename__ = "oauth_auth_codes"

    code = Column(String(120), primary_key=True)  # similar a Passport
    user_id = Column(ForeignKey("users.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("oauth_clients.id"), nullable=False)

    redirect_uri = Column(Text, nullable=False)
    scopes = Column(JSONB, nullable=False, default=list)

    revoked = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
