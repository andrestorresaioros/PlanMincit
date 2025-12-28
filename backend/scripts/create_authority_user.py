"""Script to create a sample authority user for testing"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.models.authority_profile import AuthorityProfile, AuthorityType
from app.models.instrument import Instrument, InstrumentCode
from app.models.authority_instrument_assignment import (
    AuthorityInstrumentAssignment,
    AssignmentRole
)
from app.core.security import get_password_hash


def create_authority_user():
    """Create a sample authority user with instrument assignments"""
    db = SessionLocal()
    
    try:
        # Check if authority user already exists
        existing_user = db.query(User).filter(
            User.email == "autoridad.prueba@bogota.gov.co"
        ).first()
        
        if existing_user:
            print("✅ Authority user already exists!")
            print(f"   Email: {existing_user.email}")
            print(f"   Role: {existing_user.role}")
            return
        
        # Get instruments
        rural_instrument = db.query(Instrument).filter(
            Instrument.code == InstrumentCode.RURAL
        ).first()
        urbano_instrument = db.query(Instrument).filter(
            Instrument.code == InstrumentCode.URBANO
        ).first()
        
        if not rural_instrument or not urbano_instrument:
            print("❌ Error: Instruments not found. Run seed.py first!")
            return
        
        # Create user
        user = User(
            email="autoridad.prueba@bogota.gov.co",
            hashed_password=get_password_hash("Autoridad123!"),
            role=UserRole.AUTHORITY,
            is_active=True
        )
        db.add(user)
        db.flush()
        
        # Create authority profile
        profile = AuthorityProfile(
            user_id=user.id,
            display_name="Alcaldía Mayor de Bogotá D.C.",
            authority_type=AuthorityType.MUNICIPIO,
            additional_data=None
        )
        db.add(profile)
        db.flush()
        
        # Assign RURAL instrument as LEADER_PLANNING
        assignment1 = AuthorityInstrumentAssignment(
            authority_user_id=user.id,
            instrument_id=rural_instrument.id,
            assignment_role=AssignmentRole.LEADER_PLANNING
        )
        db.add(assignment1)
        
        # Assign URBANO instrument as STRATEGIC_ALLY
        assignment2 = AuthorityInstrumentAssignment(
            authority_user_id=user.id,
            instrument_id=urbano_instrument.id,
            assignment_role=AssignmentRole.STRATEGIC_ALLY
        )
        db.add(assignment2)
        
        db.commit()
        
        print("✅ Authority user created successfully!")
        print(f"   Email: {user.email}")
        print(f"   Password: Autoridad123!")
        print(f"   Entity: {profile.display_name}")
        print(f"   Type: {profile.authority_type}")
        print(f"   Instruments:")
        print(f"      - {rural_instrument.name} (LEADER_PLANNING)")
        print(f"      - {urbano_instrument.name} (STRATEGIC_ALLY)")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating authority user: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    create_authority_user()
