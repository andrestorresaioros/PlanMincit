from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class OAuthClient(Base):
    __tablename__ = "oauth_clients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # client_id
    name: Mapped[str] = mapped_column(String(255), default="")
    secret: Mapped[str] = mapped_column(String(255))           # fase 2: hash
    redirect: Mapped[str] = mapped_column(Text)                # CSV (o JSON string)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class OAuthAuthCode(Base):
    __tablename__ = "oauth_auth_codes"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)  # code
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("oauth_clients.id"), index=True)
    redirect_uri: Mapped[str] = mapped_column(Text)
    scopes: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

class OAuthAccessToken(Base):
    __tablename__ = "oauth_access_tokens"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # jti
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("oauth_clients.id"), index=True)
    scopes: Mapped[str] = mapped_column(Text, default="")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
