from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.session_auth import get_current_user_session
from app.auth.oauth_service import get_client, validate_redirect, create_auth_code, exchange_code_for_token

router = APIRouter()

@router.get("/oauth/authorize")
def oauth_authorize(
    request: Request,
    client_id: int,
    redirect_uri: str,
    response_type: str = "code",
    state: str | None = None,
    scope: str | None = None,
    db: Session = Depends(get_db),
):
    user = get_current_user_session(request)
    if not user:
        return RedirectResponse(url=f"/login?next={request.url.path}?{request.url.query}", status_code=302)

    client = get_client(db, client_id)
    if not client or client.revoked:
        raise HTTPException(400, "invalid_client")
    if not validate_redirect(client, redirect_uri):
        raise HTTPException(400, "invalid_redirect_uri")
    if response_type != "code":
        raise HTTPException(400, "unsupported_response_type")
    if not state:
        raise HTTPException(400, "missing_state")

    code = create_auth_code(db, int(user["id"]), client_id, redirect_uri, scope or "")
    sep = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(url=f"{redirect_uri}{sep}code={code}&state={state}", status_code=302)

@router.post("/oauth/token")
def oauth_token(
    grant_type: str = Form(...),
    client_id: int = Form(...),
    client_secret: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    db: Session = Depends(get_db),
):
    if grant_type != "authorization_code":
        raise HTTPException(400, "unsupported_grant_type")

    client = get_client(db, client_id)
    if not client or client.revoked:
        raise HTTPException(401, "invalid_client")

    # fase 2: hash
    if client.secret != client_secret:
        raise HTTPException(401, "invalid_client_secret")

    if not validate_redirect(client, redirect_uri):
        raise HTTPException(400, "invalid_redirect_uri")

    try:
        return exchange_code_for_token(db, client, code, redirect_uri)
    except ValueError as e:
        raise HTTPException(400, str(e))
