from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.oauth_client import OAuthClient
from app.core.oauth_security import generate_client_secret, hash_secret


def _validate_redirect_uri(uri: str) -> None:
    if not (uri.startswith("https://") or uri.startswith("http://")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"redirect_uri inválida: {uri} (debe iniciar con http:// o https://)"
        )


class OAuthClientService:
    @staticmethod
    def create_client(db: Session, name: str, client_type: str, redirect_uri: str) -> tuple[OAuthClient, str]:
        _validate_redirect_uri(redirect_uri)

        client_secret = generate_client_secret()
        client = OAuthClient(
            name=name,
            client_type=client_type,
            redirect_uri=redirect_uri,
            secret_hash=hash_secret(client_secret),
            is_active=True,
        )
        db.add(client)
        db.commit()
        db.refresh(client)
        return client, client_secret

    @staticmethod
    def list_clients(db: Session):
        return db.query(OAuthClient).order_by(OAuthClient.created_at.desc()).all()

    @staticmethod
    def revoke_client(db: Session, client_id: UUID) -> OAuthClient:
        client = db.query(OAuthClient).filter(OAuthClient.id == client_id).first()
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client no encontrado")
        client.is_active = False
        db.add(client)
        db.commit()
        db.refresh(client)
        return client
