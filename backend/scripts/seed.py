"""Seed script to initialize database with instruments and admin user"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.instrument import Instrument, InstrumentCode
from app.core.security import get_password_hash
from app.core.config import settings


def seed_instruments(db: Session) -> None:
    """Seed initial instruments"""
    instruments_data = [
        {"code": InstrumentCode.RURAL, "name": "Instrumento de Planificación Rural"},
        {"code": InstrumentCode.URBANO, "name": "Instrumento de Planificación Urbano"},
        {"code": InstrumentCode.REGION, "name": "Instrumento de Planificación Regional"},
    ]
    
    for data in instruments_data:
        existing = db.query(Instrument).filter(Instrument.code == data["code"]).first()
        if not existing:
            instrument = Instrument(**data)
            db.add(instrument)
            print(f"✓ Creado instrumento: {data['name']}")
        else:
            print(f"- Instrumento ya existe: {data['name']}")
    
    db.commit()


def seed_admin_user(db: Session) -> None:
    """Seed initial admin user"""
    existing_admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
    
    if not existing_admin:
        admin_user = User(
            email=settings.ADMIN_EMAIL,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        print(f"✓ Creado usuario administrador: {settings.ADMIN_EMAIL}")
        print(f"  Password: {settings.ADMIN_PASSWORD}")
        print("  ⚠️  IMPORTANTE: Cambia esta contraseña en producción!")
    else:
        print(f"- Usuario administrador ya existe: {settings.ADMIN_EMAIL}")


def main():
    """Main seed function"""
    print("\n🌱 Iniciando seed de base de datos...\n")
    
    # Create tables
    print("Creando tablas...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tablas creadas\n")
    
    # Create session
    db = SessionLocal()
    
    try:
        # Seed instruments
        print("Creando instrumentos...")
        seed_instruments(db)
        print()
        
        # Seed admin user
        print("Creando usuario administrador...")
        seed_admin_user(db)
        print()
        
        print("✅ Seed completado exitosamente!\n")
        
    except Exception as e:
        print(f"❌ Error durante seed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
