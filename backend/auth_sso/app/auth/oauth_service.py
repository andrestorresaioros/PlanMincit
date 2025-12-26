from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import gen_code, gen_jti, issue_access_token
from app.db.models import OAuthClient, OAuthAuthCode, OAuthAccessToken

def parse_redirects(redirect_field: str) -> list[str]:
    return [r.strip() for r in (redirect_field or "").split(",") if r.strip()]

def get_client(db: Session, client_id: int) -> OAuthClient | None:
    return db.get(OAuthClient, client_id)

def validate_redirect(client: OAuthClient, redirect_uri: str) -> bool:
    return redirect_uri in set(parse_redirects(client.redirect))

def create_auth_code(db: Session, user_id: int, client_id: int, redirect_uri: str, scopes: str = "") -> str:
    code = gen_code(24)
    expires = datetime.utcnow() + timedelta(seconds=settings.OAUTH_CODE_TTL_SECONDS)
    rec = OAuthAuthCode(
        id=code,
        user_id=user_id,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scopes=scopes or "",
        expires_at=expires,
        revoked=False,
        used=False,
    )
    db.add(rec)
    db.commit()
    return code

def exchange_code_for_token(db: Session, client: OAuthClient, code: str, redirect_uri: str) -> dict:
    rec = db.get(OAuthAuthCode, code)
    if not rec or rec.revoked or rec.used:
        raise ValueError("invalid_code")
    if rec.client_id != client.id:
        raise ValueError("invalid_code_client")
    if rec.redirect_uri != redirect_uri:
        raise ValueError("redirect_mismatch")
    if rec.expires_at < datetime.utcnow():
        raise ValueError("code_expired")

    rec.used = True
    db.add(rec)

    jti = gen_jti()
    token = issue_access_token(
        sub=str(rec.user_id),
        jti=jti,
        ttl_seconds=settings.OAUTH_ACCESS_TOKEN_TTL_SECONDS,
        extra={"client_id": str(client.id), "scope": rec.scopes or ""},
    )

    tok = OAuthAccessToken(
        id=jti,
        user_id=rec.user_id,
        client_id=client.id,
        scopes=rec.scopes or "",
        revoked=False,
        expires_at=datetime.utcnow() + timedelta(seconds=settings.OAUTH_ACCESS_TOKEN_TTL_SECONDS),
    )
    db.add(tok)
    db.commit()

    return {
        "token_type": "Bearer",
        "access_token": token,
        "expires_in": settings.OAUTH_ACCESS_TOKEN_TTL_SECONDS,
        "scope": rec.scopes or "",
    }
