"""
FastAPI main application
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.api.routers import (
    public,
    auth,
    admin,
    authority,
    oauth,      # ⬅️ NUEVO: router SSO / OAuth
)

# ======================================================
# Create FastAPI app
# ======================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de gestión de planificación turística para autoridades territoriales",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ======================================================
# Middlewares
# ======================================================

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Sessions (CRÍTICO para SSO) ----
# Permite:
# - recordar usuario autenticado
# - saltar login si ya hay sesión
# - flujo /oauth/authorize → redirect_uri
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,   # 🔐 usa una key fuerte en prod
    same_site="lax",
    https_only=False,                 # ⚠️ en EC2 + HTTPS => True
)

# ======================================================
# Static files (uploads)
# ======================================================
uploads_path = Path(settings.UPLOAD_DIR)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads",
    StaticFiles(directory=str(uploads_path)),
    name="uploads",
)

# ======================================================
# Routers
# ======================================================
app.include_router(public.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(authority.router)
app.include_router(authority.public_router)  # Router público sin autenticación

# ---- OAuth / SSO ----
# Rutas:
# - /oauth/authorize
# - /oauth/token
# - /oauth/login
# - /oauth/userinfo
app.include_router(oauth.router)

# ======================================================
# Root & health
# ======================================================
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "PlanMinCIT API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "sso": {
            "authorize": "/oauth/authorize",
            "token": "/oauth/token",
            "userinfo": "/oauth/userinfo",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# ======================================================
# Local run
# ======================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
