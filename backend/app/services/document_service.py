"""Document service - handles document management"""
import os
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile
from app.models.document import Document
from app.models.instrument import Instrument, InstrumentCode
from app.models.authority_instrument_assignment import AuthorityInstrumentAssignment, AssignmentRole
from app.models.user import User, UserRole
from app.core.config import settings
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentService:
    """Service for managing documents"""
    
    @staticmethod
    def check_user_has_instrument_access(
        db: Session, 
        user_id: int, 
        instrument_code: InstrumentCode
    ) -> Optional[AuthorityInstrumentAssignment]:
        """Check if user has access to instrument (leader or ally)"""
        instrument = db.query(Instrument).filter(Instrument.code == instrument_code).first()
        if not instrument:
            return None
        
        assignment = db.query(AuthorityInstrumentAssignment).filter(
            AuthorityInstrumentAssignment.authority_user_id == user_id,
            AuthorityInstrumentAssignment.instrument_id == instrument.id
        ).first()
        
        return assignment
    
    @staticmethod
    def check_user_is_instrument_leader(
        db: Session, 
        user_id: int, 
        instrument_code: InstrumentCode
    ) -> bool:
        """Check if user is leader of instrument"""
        assignment = DocumentService.check_user_has_instrument_access(db, user_id, instrument_code)
        return assignment and assignment.assignment_role == AssignmentRole.LEADER_PLANNING
    
    @staticmethod
    async def save_uploaded_file(file: UploadFile, instrument_code: str) -> tuple[str, int]:
        """Save uploaded file to disk and return (file_path, size_bytes)"""
        # Create upload directory if not exists
        upload_dir = Path(settings.UPLOAD_DIR) / instrument_code.lower()
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix
        timestamp = int(datetime.utcnow().timestamp())
        filename = f"{timestamp}_{file.filename}"
        file_path = upload_dir / filename
        
        # Check file extension
        if file_extension.lower() not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de archivo no permitido. Extensiones permitidas: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        # Save file
        size_bytes = 0
        with open(file_path, "wb") as f:
            while chunk := await file.read(8192):  # Read in 8KB chunks
                size_bytes += len(chunk)
                if size_bytes > settings.MAX_UPLOAD_SIZE:
                    # Delete partial file
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Archivo demasiado grande. Tamaño máximo: {settings.MAX_UPLOAD_SIZE / (1024*1024)}MB"
                    )
                f.write(chunk)
        
        return str(file_path), size_bytes
    
    @staticmethod
    async def create_document(
        db: Session,
        user: User,
        instrument_code: InstrumentCode,
        title: str,
        description: Optional[str],
        file: UploadFile
    ) -> Document:
        """Create a new document (only leaders can create)"""
        # Check if user is leader of this instrument
        if user.role != UserRole.ADMIN and not DocumentService.check_user_is_instrument_leader(db, user.id, instrument_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el líder de planificación puede crear documentos para este instrumento"
            )
        
        # Get instrument
        instrument = db.query(Instrument).filter(Instrument.code == instrument_code).first()
        if not instrument:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instrumento no encontrado"
            )
        
        # Save file
        file_path, size_bytes = await DocumentService.save_uploaded_file(file, instrument_code.value)
        
        # Create document
        document = Document(
            instrument_id=instrument.id,
            owner_authority_user_id=user.id,
            title=title,
            description=description,
            file_path=file_path,
            original_filename=file.filename,
            content_type=file.content_type,
            size_bytes=size_bytes
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
    
    @staticmethod
    def get_documents_by_instrument(
        db: Session,
        user: User,
        instrument_code: InstrumentCode
    ) -> List[Document]:
        """Get all documents for an instrument (if user has access)"""
        # Admin can see all
        if user.role == UserRole.ADMIN:
            instrument = db.query(Instrument).filter(Instrument.code == instrument_code).first()
            if not instrument:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Instrumento no encontrado"
                )
            return db.query(Document).filter(Document.instrument_id == instrument.id).all()
        
        # Authority must have assignment to this instrument
        assignment = DocumentService.check_user_has_instrument_access(db, user.id, instrument_code)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a este instrumento"
            )
        
        return db.query(Document).filter(Document.instrument_id == assignment.instrument_id).all()
    
    @staticmethod
    def get_all_documents(db: Session) -> List[Document]:
        """Get all documents (admin only)"""
        return db.query(Document).all()
    
    @staticmethod
    def get_document_by_id(db: Session, document_id: int) -> Optional[Document]:
        """Get document by ID"""
        return db.query(Document).filter(Document.id == document_id).first()
    
    @staticmethod
    def update_document(
        db: Session,
        user: User,
        document_id: int,
        update_data: DocumentUpdate
    ) -> Document:
        """Update document metadata (only leader or admin)"""
        document = DocumentService.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento no encontrado"
            )
        
        # Check permissions
        instrument_code = document.instrument.code
        if user.role != UserRole.ADMIN and not DocumentService.check_user_is_instrument_leader(db, user.id, instrument_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el líder o admin puede editar documentos"
            )
        
        # Update fields
        if update_data.title is not None:
            document.title = update_data.title
        if update_data.description is not None:
            document.description = update_data.description
        
        db.commit()
        db.refresh(document)
        return document
    
    @staticmethod
    def delete_document(db: Session, user: User, document_id: int) -> None:
        """Delete document (only leader or admin)"""
        document = DocumentService.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento no encontrado"
            )
        
        # Check permissions
        instrument_code = document.instrument.code
        if user.role != UserRole.ADMIN and not DocumentService.check_user_is_instrument_leader(db, user.id, instrument_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el líder o admin puede eliminar documentos"
            )
        
        # Delete file from disk
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete from database
        db.delete(document)
        db.commit()


# Import datetime for file naming
from datetime import datetime
