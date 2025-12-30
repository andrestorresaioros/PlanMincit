import secrets
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_client_secret() -> str:
    return secrets.token_urlsafe(48)


def hash_secret(secret: str) -> str:
    return pwd_context.hash(secret)


def verify_secret(secret: str, secret_hash: str) -> bool:
    return pwd_context.verify(secret, secret_hash)


def generate_code() -> str:
    return secrets.token_urlsafe(32)


def generate_access_token() -> str:
    return secrets.token_urlsafe(48)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)
