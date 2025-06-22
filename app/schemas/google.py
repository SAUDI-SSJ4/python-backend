"""
Google OAuth Schema Models
===========================
Google authentication and registration schemas
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from .base import BaseResponse


class GoogleLoginRequest(BaseModel):
    """Google login request schema"""
    google_token: str = Field(..., description="Google ID token from frontend")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjY..."
            }
        }
    }


class GoogleRegisterRequest(BaseModel):
    """Google registration request schema"""
    google_token: str = Field(..., description="Google ID token from frontend")
    user_type: str = Field(..., pattern="^(student|academy)$", description="User type")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjY...",
                "user_type": "student"
            }
        }
    }


class GoogleAuthRequest(BaseModel):
    """Google authentication request schema - Legacy support"""
    # Google tokens (preferred method)
    id_token: Optional[str] = Field(None, description="Google ID token from client")
    
    # Manual data (fallback when tokens are not available)
    email: Optional[EmailStr] = Field(None, description="Google email")
    name: Optional[str] = Field(None, description="Google name") 
    picture: Optional[str] = Field(None, description="Google profile picture")
    google_id: Optional[str] = Field(None, description="Google ID")
    
    user_type: str = Field(..., pattern="^(student|academy)$", description="User type")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@gmail.com",
                "name": "Ahmed Ali",
                "picture": "https://lh3.googleusercontent.com/...",
                "google_id": "123456789",
                "user_type": "student"
            }
        }
    }


class GoogleUserData(BaseModel):
    """Google user data schema for internal processing"""
    id: str = Field(..., description="Google ID")
    email: str = Field(..., description="Email address")
    name: Optional[str] = Field(None, description="Full name")
    given_name: Optional[str] = Field(None, description="First name")
    family_name: Optional[str] = Field(None, description="Last name")
    picture: Optional[str] = Field(None, description="Profile picture URL")
    verified_email: Optional[bool] = Field(None, description="Email verification status")
    locale: Optional[str] = Field(None, description="User locale")


class GoogleTokenVerificationResponse(BaseResponse):
    """Google token verification response"""
    user_data: Optional[GoogleUserData] = Field(None, description="Verified user data")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "message": "Token verified successfully",
                "user_data": {
                    "id": "123456789",
                    "email": "user@gmail.com",
                    "name": "Ahmed Ali",
                    "picture": "https://lh3.googleusercontent.com/..."
                }
            }
        }
    } 