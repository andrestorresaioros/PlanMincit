from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "planmincit-auth-sso"
    ENV: str = "dev"
    DEBUG: bool = True
    BASE_URL: str = "http://localhost:8000"

    DATABASE_URL: str = "sqlite:///./auth_sso.db"

    SESSION_SECRET: str
    SESSION_COOKIE_NAME: str = "auth_sso_session"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_MAX_AGE_SECONDS: int = 28800

    OAUTH_CODE_TTL_SECONDS: int = 60
    OAUTH_ACCESS_TOKEN_TTL_SECONDS: int = 3600

    JWT_ALG: str = "RS256"
    JWT_ISSUER: str
    JWT_AUDIENCE: str = "ndt,ndt_front"
    JWT_PRIVATE_KEY_PEM_PATH: str
    JWT_PUBLIC_KEY_PEM_PATH: str

    class Config:
        env_file = ".env"

settings = Settings()
