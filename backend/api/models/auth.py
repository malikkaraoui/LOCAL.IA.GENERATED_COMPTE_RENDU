"""Modèles pour l'authentification JWT."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UserBase(BaseModel):
    """Base user model."""
    email: str
    username: str
    is_active: bool = True
    is_admin: bool = False


class UserCreate(UserBase):
    """User creation model."""
    password: str


class User(UserBase):
    """User model with ID."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserInDB(User):
    """User model with hashed password."""
    hashed_password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """Token payload data."""
    username: Optional[str] = None
    exp: Optional[datetime] = None


class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str
