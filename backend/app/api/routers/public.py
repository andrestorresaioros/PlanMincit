"""Public endpoints (no authentication required)"""
from fastapi import APIRouter

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/")
@router.get("/home")
async def public_home():
    """Public home endpoint - no authentication required"""
    return {
        "message": "Bienvenido a la Plataforma de Planificación Turística MinCIT",
        "description": "Sistema de gestión de planificación turística para autoridades territoriales",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "auth": "/auth/login"
        }
    }


@router.get("/info")
async def public_info():
    """General information about the platform"""
    return {
        "platform": "PlanMinCIT",
        "ministry": "Ministerio de Comercio, Industria y Turismo",
        "instruments": [
            {"code": "RURAL", "name": "Instrumento de Planificación Rural"},
            {"code": "URBANO", "name": "Instrumento de Planificación Urbano"},
            {"code": "REGION", "name": "Instrumento de Planificación Regional"}
        ],
        "authority_types": ["MUNICIPIO", "DEPARTAMENTO", "REGION", "INDEPENDIENTE"]
    }
