"""
Authentication Schema Models
============================
Login, registration, and token schemas
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime

from .base import BaseUserData, BasePassword, BaseLogin, BaseResponse


class UnifiedLogin(BaseLogin):
    """Unified login schema for all user types"""
    user_type: str = Field(..., pattern="^(student|academy)$", description="User type")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "password123",
                "user_type": "student"
            }
        }
    }


class UnifiedRegister(BaseUserData, BasePassword):
    """Unified registration schema for all user types"""
    user_type: str = Field(..., pattern="^(student|academy)$", description="User type")
    
    # Student specific fields
    birth_date: Optional[datetime] = Field(None, description="Birth date (students only)")
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$", description="Gender (students only)")
    
    # Academy specific fields
    academy_name: Optional[str] = Field(None, min_length=2, max_length=200, description="Academy name (academies only)")
    academy_about: Optional[str] = Field(None, description="Academy description")
    
    # Optional fields
    refere_id: Optional[int] = Field(None, description="Referrer user ID")
    picture: Optional[str] = Field(None, description="Profile picture URL")
    
    @validator('academy_name')
    def validate_academy_fields(cls, v, values):
        if values.get('user_type') == 'academy' and not v:
            raise ValueError('Academy name is required for academy registration')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "fname": "Ahmed",
                "lname": "Ali",
                "email": "ahmed@example.com",
                "phone_number": "1234567890",
                "password": "password123",
                "password_confirm": "password123",
                "user_type": "student",
                "birth_date": "1995-01-01T00:00:00Z",
                "gender": "male"
            }
        }
    }


class Token(BaseResponse):
    """Authentication token response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    user_type: str = Field(..., description="User type")
    user_data: Dict[str, Any] = Field(..., description="User information")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "user_type": "student",
                "status": "success",
                "message": "Login successful",
                "user_data": {
                    "id": 1,
                    "email": "user@example.com",
                    "fname": "Ahmed",
                    "lname": "Ali"
                }
            }
        }
    }


class TokenRefresh(BaseModel):
    """Token refresh schema"""
    refresh_token: str = Field(..., description="Valid refresh token")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
            }
        }
    }


class TokenData(BaseModel):
    """Token data schema for internal use"""
    user_id: Optional[int] = None
    user_type: Optional[str] = None
    email: Optional[str] = None
    exp: Optional[datetime] = None 