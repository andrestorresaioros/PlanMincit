from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.db.session import get_db
from app.schemas.oauth import OAuthTokenRequest, OAuthTokenResponse
from app.services.oauth_service import OAuthService
from app.services.auth_service import AuthService  # ya existe en tu proyecto

router = APIRouter(prefix="/oauth", tags=["oauth"])
templates = Jinja2Templates(directory="app/templates")

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
        return templates.TemplateResponse("oauth/login.html", {"request": request, "next": next, "error": "Credenciales inválidas"}, status_code=400)

    request.session["user_id"] = user.id
    return RedirectResponse(url=next, status_code=302)

@router.get("/authorize")
def oauth_authorize(request: Request, db: Session = Depends(get_db)):
    # params
    client_id = request.query_params.get("client_id")
    redirect_uri = request.query_params.get("redirect_uri")
    state = request.query_params.get("state")
    scope = request.query_params.get("scope", "")

    if request.query_params.get("response_type") != "code":
        return HTMLResponse("response_type no soportado", status_code=400)

    client = OAuthService.get_client(db, client_id)

    # sesión
    user_id = request.session.get("user_id")
    if not user_id:
        # mandar al login y volver
        return RedirectResponse(url=f"/oauth/login?next={request.url}", status_code=302)

    scopes = [s for s in scope.split(" ") if s.strip()] if scope else []
    code = OAuthService.create_auth_code(db, user_id=user_id, client=client, redirect_uri=redirect_uri, scopes=scopes)

    sep = "&" if "?" in redirect_uri else "?"
    redir = f"{redirect_uri}{sep}code={code}"
    if state:
        redir += f"&state={state}"
    return RedirectResponse(url=redir, status_code=302)

@router.post("/token", response_model=OAuthTokenResponse)
def oauth_token(data: OAuthTokenRequest, db: Session = Depends(get_db)):
    if data.grant_type != "authorization_code":
        return HTMLResponse("grant_type no soportado", status_code=400)

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
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return HTMLResponse("missing bearer token", status_code=401)

    token = auth.replace("Bearer ", "").strip()
    token_row = OAuthService.get_user_from_access_token(db, token)

    # Carga user y profile
    from app.models.user import User
    user = db.query(User).filter(User.id == token_row.user_id).first()

    role = "admin" if getattr(user, "is_admin", False) else "municipio"
    display_name = getattr(getattr(user, "authority_profile", None), "display_name", None)

    return {
        "id": user.id,
        "email": user.email,
        "role": role,
        "display_name": display_name,
        "scopes": (token_row.scopes.split(",") if token_row.scopes else [])
    }
