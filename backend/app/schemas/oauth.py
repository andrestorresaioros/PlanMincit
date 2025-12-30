from pydantic import BaseModel, Field
from typing import Optional

class OAuthAuthorizeQuery(BaseModel):
    response_type: str = "code"
    client_id: str
    redirect_uri: str
    scope: Optional[str] = None
    state: Optional[str] = None

class OAuthTokenRequest(BaseModel):
    grant_type: str = Field(..., examples=["authorization_code"])
    client_id: str
    client_secret: str
    code: str
    redirect_uri: str

class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str
