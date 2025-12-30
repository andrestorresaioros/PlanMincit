from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash

def main():
    db = SessionLocal()

    email = "admin@planmincit.local"
    password = "Admin123!"

    # Verifica si ya existe
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print("❗ El usuario ya existe:", email)
        return

    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        role=UserRole.ADMIN,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    print("✅ Usuario admin creado")
    print("   email:", email)
    print("   password:", password)
    print("   id:", user.id)

if __name__ == "__main__":
    main()
