from fastapi import APIRouter, Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_token
from app.db.models import User, OAuthAccessToken

router = APIRouter()

@router.get("/api/user")
def api_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing_bearer_token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(401, "invalid_token")

    jti = payload.get("jti")
    sub = payload.get("sub")
    if not jti or not sub:
        raise HTTPException(401, "invalid_token")

    tok = db.get(OAuthAccessToken, jti)
    if not tok or tok.revoked:
        raise HTTPException(401, "revoked_token")

    user = db.get(User, int(sub))
    if not user:
        raise HTTPException(404, "user_not_found")

    return {"id": user.id, "name": user.name, "email": user.email}
