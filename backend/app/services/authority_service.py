"""Authority service - handles authority user creation and management"""
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.models.authority_profile import AuthorityProfile
from app.models.instrument import Instrument, InstrumentCode
from app.models.authority_instrument_assignment import AuthorityInstrumentAssignment, AssignmentRole
from app.core.security import get_password_hash
from app.schemas.authority import AuthorityCreateRequest, InstrumentAssignment


class AuthorityService:
    """Service for managing authority users"""
    
    @staticmethod
    def validate_instrument_assignments(
        db: Session,
        assignments: List[InstrumentAssignment],
        exclude_user_id: Optional[int] = None
    ) -> None:
        """
        Validate instrument assignments against business rules:
        - Exactly 3 instruments must be assigned
        - Only 1 LEADER per instrument globally
        - Maximum 8 STRATEGIC_ALLY per instrument globally
        """
        if len(assignments) != 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe asignar exactamente 3 instrumentos"
            )
        
        # Check for duplicate instruments in request
        instrument_codes = [a.instrument_code for a in assignments]
        if len(instrument_codes) != len(set(instrument_codes)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puede asignar el mismo instrumento más de una vez"
            )
        
        # Validate each assignment
        for assignment in assignments:
            instrument = db.query(Instrument).filter(
                Instrument.code == assignment.instrument_code
            ).first()
            
            if not instrument:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Instrumento {assignment.instrument_code} no encontrado"
                )
            
            if assignment.role == AssignmentRole.LEADER_PLANNING:
                # Check if there's already a leader for this instrument
                existing_leader_query = db.query(AuthorityInstrumentAssignment).filter(
                    AuthorityInstrumentAssignment.instrument_id == instrument.id,
                    AuthorityInstrumentAssignment.assignment_role == AssignmentRole.LEADER_PLANNING
                )
                if exclude_user_id:
                    existing_leader_query = existing_leader_query.filter(
                        AuthorityInstrumentAssignment.authority_user_id != exclude_user_id
                    )
                
                existing_leader = existing_leader_query.first()
                if existing_leader:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Ya existe un líder para el instrumento {assignment.instrument_code}"
                    )
            
            elif assignment.role == AssignmentRole.STRATEGIC_ALLY:
                # Check if there are already 8 allies for this instrument
                allies_count_query = db.query(AuthorityInstrumentAssignment).filter(
                    AuthorityInstrumentAssignment.instrument_id == instrument.id,
                    AuthorityInstrumentAssignment.assignment_role == AssignmentRole.STRATEGIC_ALLY
                )
                if exclude_user_id:
                    allies_count_query = allies_count_query.filter(
                        AuthorityInstrumentAssignment.authority_user_id != exclude_user_id
                    )
                
                allies_count = allies_count_query.count()
                if allies_count >= 8:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Ya hay 8 aliados para el instrumento {assignment.instrument_code} (máximo permitido)"
                    )
    
    @staticmethod
    def create_authority_user(db: Session, data: AuthorityCreateRequest) -> User:
        """Create a new authority user with profile and instrument assignments"""
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado"
            )
        
        # Validate instrument assignments
        AuthorityService.validate_instrument_assignments(db, data.instrument_assignments)
        
        # Create user
        user = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            role=UserRole.AUTHORITY,
            is_active=True
        )
        db.add(user)
        db.flush()  # Get user.id
        
        # Create authority profile
        profile = AuthorityProfile(
            user_id=user.id,
            authority_type=data.authority_type,
            display_name=data.display_name,
            additional_data=data.additional_data
        )
        db.add(profile)
        
        # Create instrument assignments
        for assignment in data.instrument_assignments:
            instrument = db.query(Instrument).filter(
                Instrument.code == assignment.instrument_code
            ).first()
            
            assignment_obj = AuthorityInstrumentAssignment(
                authority_user_id=user.id,
                instrument_id=instrument.id,
                assignment_role=assignment.role
            )
            db.add(assignment_obj)
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_authority_users(db: Session) -> List[User]:
        """Get all authority users"""
        return db.query(User).filter(User.role == UserRole.AUTHORITY).all()
    
    @staticmethod
    def get_authority_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get authority user by ID"""
        return db.query(User).filter(
            User.id == user_id,
            User.role == UserRole.AUTHORITY
        ).first()
    
    @staticmethod
    def update_authority(db: Session, user_id: int, update_data: dict) -> User:
        """Update authority user"""
        user = AuthorityService.get_authority_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Autoridad no encontrada"
            )
        
        # Update user fields
        if "is_active" in update_data:
            user.is_active = update_data["is_active"]
        
        # Update profile fields
        profile_fields = ["authority_type", "display_name", "additional_data"]
        profile_updates = {k: v for k, v in update_data.items() if k in profile_fields and v is not None}
        if profile_updates and user.authority_profile:
            for key, value in profile_updates.items():
                setattr(user.authority_profile, key, value)
        
        # Update instrument assignments if provided
        if "instrument_assignments" in update_data and update_data["instrument_assignments"]:
            AuthorityService.validate_instrument_assignments(
                db, 
                update_data["instrument_assignments"],
                exclude_user_id=user_id
            )
            
            # Delete old assignments
            db.query(AuthorityInstrumentAssignment).filter(
                AuthorityInstrumentAssignment.authority_user_id == user_id
            ).delete()
            
            # Create new assignments
            for assignment in update_data["instrument_assignments"]:
                instrument = db.query(Instrument).filter(
                    Instrument.code == assignment.instrument_code
                ).first()
                
                assignment_obj = AuthorityInstrumentAssignment(
                    authority_user_id=user_id,
                    instrument_id=instrument.id,
                    assignment_role=assignment.role
                )
                db.add(assignment_obj)
        
        db.commit()
        db.refresh(user)
        return user
