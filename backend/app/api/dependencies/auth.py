"""Security dependencies for authentication and authorization"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.models.instrument import InstrumentCode
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = AuthService.get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    return user


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to require admin role
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador"
        )
    return current_user


async def require_authority(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to require authority role
    """
    if current_user.role != UserRole.AUTHORITY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere ser una autoridad turística"
        )
    return current_user


def require_instrument_access(instrument_code: InstrumentCode):
    """
    Factory function that returns a dependency to check if user has access to instrument
    (either as leader or ally). Admin always has access.
    """
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        # Admin has access to all
        if current_user.role == UserRole.ADMIN:
            return current_user
        
        # Check if authority has assignment to this instrument
        assignment = DocumentService.check_user_has_instrument_access(
            db, current_user.id, instrument_code
        )
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tiene acceso al instrumento {instrument_code.value}"
            )
        
        return current_user
    
    return dependency


def require_instrument_leader(instrument_code: InstrumentCode):
    """
    Factory function that returns a dependency to check if user is leader of instrument.
    Admin always passes.
    """
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        # Admin has full access
        if current_user.role == UserRole.ADMIN:
            return current_user
        
        # Check if authority is leader of this instrument
        is_leader = DocumentService.check_user_is_instrument_leader(
            db, current_user.id, instrument_code
        )
        
        if not is_leader:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Solo el líder de planificación puede realizar esta acción en el instrumento {instrument_code.value}"
            )
        
        return current_user
    
    return dependency
