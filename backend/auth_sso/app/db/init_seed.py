from sqlalchemy.orm import Session
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.db.models import User, OAuthClient
from app.core.security import hash_password

def init_db():
    Base.metadata.create_all(bind=engine)

def seed():
    db: Session = SessionLocal()
    try:
        # user demo
        if not db.query(User).filter(User.email == "admin@example.com").first():
            db.add(User(
                email="admin@example.com",
                name="Admin",
                password_hash=hash_password("admin123"),
                is_active=True
            ))

        # clients demo: AJUSTA secretos y redirects con los reales del SQL/infra
        if not db.get(OAuthClient, 3):
            db.add(OAuthClient(
                id=3,
                name="NDT Admin",
                secret="PUT_CLIENT_SECRET_3_HERE",
                redirect="http://ndttmincitnw143.edwcorp.com/callback",
                revoked=False
            ))

        if not db.get(OAuthClient, 4):
            db.add(OAuthClient(
                id=4,
                name="NDT Front",
                secret="PUT_CLIENT_SECRET_4_HERE",
                redirect="http://ndttmincitnw143.edwcorp.com/front/callback",
                revoked=False
            ))

        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    seed()
    print("DB initialized + seeded.")
