"""Authentication endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import LoginRequest, Token, TokenRefresh, MeResponse, InstrumentAssignmentInfo
from app.services.auth_service import AuthService
from app.api.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.authority_instrument_assignment import AssignmentRole

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token)
async def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access + refresh tokens
    """
    user = AuthService.authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    tokens = AuthService.create_tokens(user)
    return tokens


@router.post("/refresh", response_model=dict)
async def refresh_token(
    refresh_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    return AuthService.refresh_access_token(refresh_data.refresh_token, db)


@router.get("/me", response_model=MeResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information including role and instrument assignments
    """
    response_data = {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "authority_type": None,
        "display_name": None,
        "instrument_assignments": []
    }
    
    # If user is authority, include profile and assignments
    if current_user.role == UserRole.AUTHORITY and current_user.authority_profile:
        profile = current_user.authority_profile
        response_data["authority_type"] = profile.authority_type
        response_data["display_name"] = profile.display_name
        
        # Get instrument assignments with role display names
        for assignment in current_user.instrument_assignments:
            role_display = "lider de planificacion" if assignment.assignment_role == AssignmentRole.LEADER_PLANNING else "aliado estrategico"
            
            response_data["instrument_assignments"].append(
                InstrumentAssignmentInfo(
                    instrument_code=assignment.instrument.code,
                    instrument_name=assignment.instrument.name,
                    role=assignment.assignment_role,
                    role_display=role_display
                )
            )
    
    return response_data
