from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User
from app.core.security import verify_password
from app.auth.session_auth import login_user_session, logout_user_session

router = APIRouter()

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str | None = None):
    next_val = next or "/"
    return f"""
    <html>
      <body>
        <h3>PlanMincit - Auth SSO Login</h3>
        <form method="post" action="/login">
          <input type="hidden" name="next" value="{next_val}"/>
          <input name="email" placeholder="email" /><br/>
          <input name="password" type="password" placeholder="password" /><br/>
          <button type="submit">Login</button>
        </form>
      </body>
    </html>
    """

@router.post("/login")
def do_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(401, "invalid_credentials")

    login_user_session(request, {"id": user.id, "email": user.email, "name": user.name})
    return RedirectResponse(url=next or "/", status_code=302)

@router.post("/logout")
def do_logout(request: Request):
    logout_user_session(request)
    return RedirectResponse(url="/login", status_code=302)
