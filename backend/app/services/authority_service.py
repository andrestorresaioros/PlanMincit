"""Authority service - handles authority user creation and management"""
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.models.authority_profile import AuthorityProfile, AuthorityType
from app.models.instrument import Instrument, InstrumentCode
from app.models.authority_instrument_assignment import AuthorityInstrumentAssignment, AssignmentRole
from app.core.security import get_password_hash
from app.schemas.authority import AuthorityCreateRequest, InstrumentAssignment
from app.services.ndtt_service import NDTTService


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
        - At least 1 instrument must be assigned
        - Only 1 LEADER per instrument+territory combination
        - Maximum 10 STRATEGIC_ALLY per instrument+territory combination
        """
        if len(assignments) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe asignar al menos 1 instrumento"
            )
        
        # Check for duplicate instruments in request
        # Handle both dict and Pydantic objects
        instrument_codes = [a.get('instrument_code') if isinstance(a, dict) else a.instrument_code for a in assignments]
        if len(instrument_codes) != len(set(instrument_codes)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puede asignar el mismo instrumento más de una vez"
            )
        
        # Validate each assignment
        for assignment in assignments:
            # Handle both dict and Pydantic objects
            instrument_code = assignment.get('instrument_code') if isinstance(assignment, dict) else assignment.instrument_code
            assignment_role = assignment.get('role') if isinstance(assignment, dict) else assignment.role
            territory_name = assignment.get('territory_name') if isinstance(assignment, dict) else getattr(assignment, 'territory_name', None)
            
            instrument = db.query(Instrument).filter(
                Instrument.code == instrument_code
            ).first()
            
            if not instrument:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Instrumento '{instrument_code.value}' no encontrado"
                )
            
            # Validar restricción de líder: máximo 1 por instrumento + territorio
            if assignment_role == AssignmentRole.LEADER_PLANNING:
                leaders_count_query = db.query(AuthorityInstrumentAssignment).filter(
                    AuthorityInstrumentAssignment.instrument_id == instrument.id,
                    AuthorityInstrumentAssignment.assignment_role == AssignmentRole.LEADER_PLANNING,
                    AuthorityInstrumentAssignment.territory_name == territory_name
                )
                if exclude_user_id:
                    leaders_count_query = leaders_count_query.filter(
                        AuthorityInstrumentAssignment.authority_user_id != exclude_user_id
                    )
                
                leaders_count = leaders_count_query.count()
                if leaders_count >= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Ya existe un líder de planificación para el instrumento '{instrument_code.value}' en el territorio '{territory_name}'. Solo se permite 1 líder por instrumento y territorio."
                    )
            
            # Validar restricción de aliados: máximo 10 por instrumento + territorio
            if assignment_role == AssignmentRole.STRATEGIC_ALLY:
                allies_count_query = db.query(AuthorityInstrumentAssignment).filter(
                    AuthorityInstrumentAssignment.instrument_id == instrument.id,
                    AuthorityInstrumentAssignment.assignment_role == AssignmentRole.STRATEGIC_ALLY,
                    AuthorityInstrumentAssignment.territory_name == territory_name
                )
                if exclude_user_id:
                    allies_count_query = allies_count_query.filter(
                        AuthorityInstrumentAssignment.authority_user_id != exclude_user_id
                    )
                
                allies_count = allies_count_query.count()
                if allies_count >= 10:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Ya hay 10 aliados estratégicos para el instrumento '{instrument_code.value}' en el territorio '{territory_name}' (máximo permitido)"
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
        
        # Determinar códigos según el tipo de autoridad y el territorio de las asignaciones
        codigo_municipio = data.codigo_municipio
        codigo_departamento = data.codigo_departamento
        codigo_region = data.codigo_region
        cedula = data.cedula
        
        # Obtener el territorio de la primera asignación (si existe)
        territorio = None
        if data.instrument_assignments and len(data.instrument_assignments) > 0:
            territorio = data.instrument_assignments[0].territory_name
        
        # MUNICIPIO: Buscar código DANE desde el territorio (para NDTT y endpoint)
        if data.authority_type == AuthorityType.MUNICIPIO and territorio and not codigo_municipio:
            try:
                codigo_municipio = NDTTService.get_codigo_municipio(territorio)
            except:
                # Si no se encuentra automáticamente, dejar vacío
                pass
        
        # DEPARTAMENTO: Buscar código desde el territorio (solo para endpoint, no NDTT)
        if data.authority_type == AuthorityType.DEPARTAMENTO and territorio and not codigo_departamento:
            try:
                codigo_departamento = NDTTService.get_codigo_departamento(territorio)
            except:
                # Si no se encuentra automáticamente, dejar vacío
                pass
        
        # REGION: El código debe venir del campo codigo_region (manual)
        # No se busca automáticamente
        
        # INDEPENDIENTE: El código es la cédula (para endpoint)
        # Ya viene en data.cedula
        
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
            additional_data=data.additional_data,
            codigo_municipio=codigo_municipio,
            codigo_departamento=codigo_departamento,
            codigo_region=codigo_region,
            cedula=cedula
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
                assignment_role=assignment.role,
                territory_name=assignment.territory_name
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
        profile_fields = [
            "authority_type", "display_name", "additional_data",
            "codigo_municipio", "codigo_departamento", "codigo_region", "cedula"
        ]
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
                # Handle both dict and Pydantic objects
                instrument_code = assignment.get('instrument_code') if isinstance(assignment, dict) else assignment.instrument_code
                assignment_role = assignment.get('role') if isinstance(assignment, dict) else assignment.role
                territory_name = assignment.get('territory_name') if isinstance(assignment, dict) else getattr(assignment, 'territory_name', None)
                
                instrument = db.query(Instrument).filter(
                    Instrument.code == instrument_code
                ).first()
                
                assignment_obj = AuthorityInstrumentAssignment(
                    authority_user_id=user_id,
                    instrument_id=instrument.id,
                    assignment_role=assignment_role,
                    territory_name=territory_name
                )
                db.add(assignment_obj)
        
        db.commit()
        db.refresh(user)
        return user
