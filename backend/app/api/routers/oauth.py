from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.db.session import get_db
from app.schemas.oauth import OAuthTokenRequest, OAuthTokenResponse
from app.services.oauth_service import OAuthService
from app.services.auth_service import AuthService
from app.core.security import decode_token
from app.models.user import User
from urllib.parse import quote

router = APIRouter(prefix="/oauth", tags=["oauth"])
templates = Jinja2Templates(directory="app/templates")


# ======================================================
# 1) (Opcional) Login HTML fallback (mientras migras a React)
# ======================================================

@router.get("/login", response_class=HTMLResponse)
def oauth_login_form(request: Request):
    next_url = request.query_params.get("next", "/")
    return templates.TemplateResponse("oauth/login.html", {"request": request, "next": next_url})


@router.post("/login")
def oauth_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    user = AuthService.authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(
            "oauth/login.html",
            {"request": request, "next": next, "error": "Credenciales inválidas"},
            status_code=400,
        )

    # ✅ sesión SSO
    request.session["user_id"] = user.id
    return RedirectResponse(url=next, status_code=302)


# ======================================================
# 2) Puente REAL: React login (JWT) -> Sesión SSO (cookie)
# ======================================================

@router.post("/session")
def oauth_session(request: Request, db: Session = Depends(get_db)):
    """
    Crea sesión SSO (cookie) a partir de un JWT del login normal (/auth/login).
    Uso típico: React hace login -> recibe access_token -> llama este endpoint.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    jwt_token = auth.replace("Bearer ", "").strip()
    payload = decode_token(jwt_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    request.session["user_id"] = user.id
    return {"ok": True}


@router.post("/logout")
def oauth_logout(request: Request):
    """
    Limpia la sesión SSO (cookie).
    """
    request.session.pop("user_id", None)
    return {"ok": True}


# ======================================================
# 3) OAuth Authorization Code Flow
# ======================================================

@router.get("/authorize")
def oauth_authorize(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint OAuth authorize:
    - Valida cliente
    - Verifica sesión del usuario (cookie)
    - Emite code y redirige al redirect_uri del cliente
    """
    client_id = request.query_params.get("client_id")
    redirect_uri = request.query_params.get("redirect_uri")
    state = request.query_params.get("state")
    scope = request.query_params.get("scope", "")
    response_type = request.query_params.get("response_type")

    if response_type != "code":
        return HTMLResponse("response_type no soportado", status_code=400)

    if not client_id or not redirect_uri:
        return HTMLResponse("client_id y redirect_uri son obligatorios", status_code=400)

    # ✅ valida cliente y que redirect_uri coincida
    client = OAuthService.get_client(db, client_id)

    # sesión requerida
    user_id = request.session.get("user_id")
    if not user_id:
        next_url = quote(str(request.url), safe="")
        return RedirectResponse(url=f"/oauth/login?next={next_url}", status_code=302)

    scopes = [s for s in scope.split(" ") if s.strip()] if scope else []
    code = OAuthService.create_auth_code(
        db,
        user_id=user_id,
        client=client,
        redirect_uri=redirect_uri,
        scopes=scopes
    )

    sep = "&" if "?" in redirect_uri else "?"
    redir = f"{redirect_uri}{sep}code={code}"
    if state:
        redir += f"&state={state}"

    return RedirectResponse(url=redir, status_code=302)


@router.post("/token", response_model=OAuthTokenResponse)
def oauth_token(data: OAuthTokenRequest, db: Session = Depends(get_db)):
    """
    Intercambia code -> access_token + refresh_token
    Lo llama el backend del portal cliente (Cristian/otros portales).
    """
    if data.grant_type != "authorization_code":
        return HTMLResponse("grant_type no soportado", status_code=400)

    if not data.client_id or not data.client_secret or not data.code or not data.redirect_uri:
        raise HTTPException(status_code=400, detail="Faltan campos requeridos")

    client = OAuthService.get_client(db, data.client_id)
    OAuthService.validate_client_secret(client, data.client_secret)

    access_token, refresh_token, ttl = OAuthService.exchange_code_for_tokens(
        db=db,
        client=client,
        code=data.code,
        redirect_uri=data.redirect_uri
    )

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ttl
    )


@router.get("/userinfo")
def oauth_userinfo(request: Request, db: Session = Depends(get_db)):
    """
    Devuelve información del usuario autenticado usando el access_token del OAuth flow.
    Lo usan los portales clientes para crear sesión local.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return HTMLResponse("missing bearer token", status_code=401)

    token = auth.replace("Bearer ", "").strip()
    token_row = OAuthService.get_user_from_access_token(db, token)

    user = db.query(User).filter(User.id == token_row.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # usa tu sistema real de roles
    role = getattr(user, "role", None)
    role_value = role.value if hasattr(role, "value") else str(role) if role else "unknown"

    display_name = getattr(getattr(user, "authority_profile", None), "display_name", None)

    return {
        "id": user.id,
        "email": user.email,
        "role": role_value,
        "display_name": display_name,
        "scopes": (token_row.scopes.split(",") if token_row.scopes else [])
    }
