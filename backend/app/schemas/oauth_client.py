from uuid import UUID
from pydantic import BaseModel, Field


class OAuthClientCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    client_type: str = Field(..., description='Ej: "admin" o "municipio"')
    redirect_uri: str = Field(..., min_length=8)


class OAuthClientCreateResponse(BaseModel):
    client_id: UUID
    client_secret: str  # solo se retorna una vez
    name: str
    client_type: str
    redirect_uri: str


class OAuthClientResponse(BaseModel):
    client_id: UUID
    name: str
    client_type: str
    redirect_uri: str
    is_active: bool


class OAuthClientRevokeResponse(BaseModel):
    client_id: UUID
    is_active: bool
