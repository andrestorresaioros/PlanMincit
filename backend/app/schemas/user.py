"""User schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    is_active: bool = True
    role: UserRole


class UserCreate(UserBase):
    """Schema for creating a user"""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserWithProfile(UserResponse):
    """User response with authority profile if exists"""
    authority_profile: Optional["AuthorityProfileResponse"] = None
    
    class Config:
        from_attributes = True


# Avoid circular import
from app.schemas.authority import AuthorityProfileResponse
UserWithProfile.model_rebuild()
