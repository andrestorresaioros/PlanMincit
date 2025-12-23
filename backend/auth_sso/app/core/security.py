import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(p: str) -> str:
    return pwd.hash(p)

def verify_password(p: str, hashed: str) -> bool:
    return pwd.verify(p, hashed)

def load_private_key() -> str:
    return Path(settings.JWT_PRIVATE_KEY_PEM_PATH).read_text(encoding="utf-8")

def load_public_key() -> str:
    return Path(settings.JWT_PUBLIC_KEY_PEM_PATH).read_text(encoding="utf-8")

def gen_code(n: int = 32) -> str:
    return secrets.token_urlsafe(n)

def gen_jti() -> str:
    return secrets.token_urlsafe(24)

def issue_access_token(sub: str, jti: str, ttl_seconds: int, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    aud = [a.strip() for a in settings.JWT_AUDIENCE.split(",") if a.strip()]

    payload = {
        "iss": settings.JWT_ISSUER,
        "sub": sub,
        "aud": aud,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        "jti": jti,
    }
    if extra:
        payload.update(extra)

    if settings.JWT_ALG.upper().startswith("RS"):
        return jwt.encode(payload, load_private_key(), algorithm=settings.JWT_ALG)

    raise ValueError("This template enables RS* algorithms only")
    
def decode_token(token: str) -> dict:
    aud = [a.strip() for a in settings.JWT_AUDIENCE.split(",") if a.strip()]
    return jwt.decode(
        token,
        load_public_key(),
        algorithms=[settings.JWT_ALG],
        audience=aud,
        issuer=settings.JWT_ISSUER,
    )
