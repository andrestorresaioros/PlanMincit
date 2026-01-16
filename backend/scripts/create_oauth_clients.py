import secrets
from app.db.session import SessionLocal
from app.models.oauth_client import OAuthClient
from app.services.oauth_service import hash_value

def create_client(name: str, client_type: str, redirect_uri: str):
    db = SessionLocal()
    try:
        raw_secret = secrets.token_urlsafe(48)
        c = OAuthClient(
            name=name,
            client_type=client_type,
            redirect_uri=redirect_uri,
            secret_hash=hash_value(raw_secret)
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        print("==== CLIENT CREATED ====")
        print("name:", name)
        print("client_type:", client_type)
        print("client_id:", str(c.id))
        print("client_secret:", raw_secret)
        print("redirect_uri:", redirect_uri)
        print("========================")
    finally:
        db.close()

if __name__ == "__main__":
    # AJUSTA a las URLs reales del cliente
    create_client("Plan Cliente Municipio", "municipio", "https://CLIENTE/ssocallback/municipio")
    create_client("Plan Cliente Admin", "admin", "https://CLIENTE/ssocallback/admin")
    create_client("Plan Web Local", "admin", "http://localhost:3000/auth/callback")
