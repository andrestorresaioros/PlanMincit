from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import settings

from app.auth.routes_auth import router as auth_router
from app.auth.routes_oauth import router as oauth_router
from app.auth.routes_api import router as api_router

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET,
    session_cookie=settings.SESSION_COOKIE_NAME,
    max_age=settings.SESSION_COOKIE_MAX_AGE_SECONDS,
    same_site=settings.SESSION_COOKIE_SAMESITE,
    https_only=settings.SESSION_COOKIE_SECURE,
)

app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(api_router)

@app.get("/healthz")
def healthz():
    return {"ok": True, "env": settings.ENV}

@app.get("/")
def root():
    return {"service": settings.APP_NAME, "login": "/login", "health": "/healthz"}
