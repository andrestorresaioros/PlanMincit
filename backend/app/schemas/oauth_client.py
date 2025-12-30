from typing import List
from uuid import UUID
from pydantic import BaseModel, Field


class OAuthClientCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    redirect_uris: List[str] = Field(default_factory=list)


class OAuthClientCreateResponse(BaseModel):
    client_id: UUID
    client_secret: str  # solo se retorna una vez
    name: str
    redirect_uris: List[str]


class OAuthClientResponse(BaseModel):
    client_id: UUID
    name: str
    redirect_uris: List[str]
    revoked: bool


class OAuthClientRevokeResponse(BaseModel):
    client_id: UUID
    revoked: bool
