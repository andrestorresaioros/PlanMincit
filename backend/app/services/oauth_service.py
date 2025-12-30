import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from passlib.context import CryptContext

from app.models.oauth_client import OAuthClient
from app.models.oauth_auth_code import OAuthAuthCode
from app.models.oauth_access_token import OAuthAccessToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TTL_SECONDS = 3600
REFRESH_TTL_DAYS = 30

def hash_value(v: str) -> str:
    return pwd_context.hash(v)

def verify_hash(v: str, h: str) -> bool:
    return pwd_context.verify(v, h)

class OAuthService:
    @staticmethod
    def get_client(db: Session, client_id: str) -> OAuthClient:
        from uuid import UUID
        try:
            cid = UUID(client_id)
        except Exception:
            raise HTTPException(status_code=400, detail="client_id inválido")

        client = db.query(OAuthClient).filter(OAuthClient.id == cid, OAuthClient.is_active == True).first()
        if not client:
            raise HTTPException(status_code=401, detail="client no válido")
        return client

    @staticmethod
    def validate_client_secret(client: OAuthClient, client_secret: str):
        if not verify_hash(client_secret, client.secret_hash):
            raise HTTPException(status_code=401, detail="client_secret inválido")

    @staticmethod
    def create_auth_code(db: Session, user_id: int, client: OAuthClient, redirect_uri: str, scopes: list[str]) -> str:
        if redirect_uri.strip() != client.redirect_uri.strip():
            raise HTTPException(status_code=400, detail="redirect_uri no coincide")

        code = secrets.token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        db.add(OAuthAuthCode(
            code=code,
            user_id=user_id,
            client_id=client.id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            revoked=False,
            expires_at=expires_at
        ))
        db.commit()
        return code

    @staticmethod
    def exchange_code_for_tokens(db: Session, client: OAuthClient, code: str, redirect_uri: str):
        auth_code = db.query(OAuthAuthCode).filter(OAuthAuthCode.code == code).first()
        if not auth_code or auth_code.revoked:
            raise HTTPException(status_code=400, detail="code inválido")

        if auth_code.client_id != client.id:
            raise HTTPException(status_code=400, detail="code no pertenece a este client")

        if auth_code.redirect_uri.strip() != redirect_uri.strip():
            raise HTTPException(status_code=400, detail="redirect_uri no coincide")

        if auth_code.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="code expirado")

        # consumir code
        auth_code.revoked = True

        access_token = secrets.token_urlsafe(48)
        refresh_token = secrets.token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ACCESS_TTL_SECONDS)

        db.add(OAuthAccessToken(
            user_id=auth_code.user_id,
            client_id=client.id,
            access_token_hash=hash_value(access_token),
            refresh_token_hash=hash_value(refresh_token),
            scopes=",".join(auth_code.scopes or []),
            revoked=False,
            expires_at=expires_at
        ))
        db.commit()

        return access_token, refresh_token, ACCESS_TTL_SECONDS

    @staticmethod
    def get_user_from_access_token(db: Session, access_token: str) -> OAuthAccessToken:
        # Como el token está hasheado, toca buscar comparando contra los no revocados.
        # MVP: iterar últimos tokens (mejorable luego).
        tokens = db.query(OAuthAccessToken).filter(OAuthAccessToken.revoked == False).order_by(OAuthAccessToken.created_at.desc()).limit(200).all()
        for t in tokens:
            if verify_hash(access_token, t.access_token_hash):
                if t.expires_at <= datetime.now(timezone.utc):
                    raise HTTPException(status_code=401, detail="token expirado")
                return t
        raise HTTPException(status_code=401, detail="token inválido")
