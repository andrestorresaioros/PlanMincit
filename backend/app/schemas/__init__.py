"""Pydantic schemas"""
from app.schemas.user import (
    UserBase, UserCreate, UserUpdate, UserResponse, UserWithProfile
)
from app.schemas.auth import (
    Token, TokenRefresh, LoginRequest, MeResponse
)
from app.schemas.authority import (
    AuthorityProfileCreate, AuthorityProfileUpdate, AuthorityProfileResponse,
    AuthorityCreateRequest, AuthorityUpdateRequest, AuthorityDetailResponse
)
from app.schemas.instrument import (
    InstrumentResponse, InstrumentAssignmentCreate, InstrumentAssignmentResponse
)
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentResponse, DocumentListResponse
)

from .oauth_client import (
    OAuthClientCreateRequest,
    OAuthClientCreateResponse,
    OAuthClientResponse,
    OAuthClientRevokeResponse,
)

__all__ = [
    "UserBase", "UserCreate", "UserUpdate", "UserResponse", "UserWithProfile",
    "Token", "TokenRefresh", "LoginRequest", "MeResponse",
    "AuthorityProfileCreate", "AuthorityProfileUpdate", "AuthorityProfileResponse",
    "AuthorityCreateRequest", "AuthorityUpdateRequest", "AuthorityDetailResponse",
    "InstrumentResponse", "InstrumentAssignmentCreate", "InstrumentAssignmentResponse",
    "DocumentCreate", "DocumentUpdate", "DocumentResponse", "DocumentListResponse",
]
