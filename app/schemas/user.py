"""
User Schema Models
==================
User profile and information schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from .base import TimestampedBase


class UserInfoResponse(TimestampedBase):
    """User information response schema"""
    id: int = Field(..., description="User ID")
    fname: str = Field(..., description="First name")
    mname: Optional[str] = Field(None, description="Middle name")
    lname: str = Field(..., description="Last name")
    email: str = Field(..., description="Email")
    phone_number: str = Field(..., description="Phone number")
    user_type: str = Field(..., description="User type")
    account_type: str = Field(..., description="Account type")
    status: str = Field(..., description="Account status")
    verified: bool = Field(..., description="Verification status")
    avatar: Optional[str] = Field(None, description="Avatar URL")
    banner: Optional[str] = Field(None, description="Banner URL")
    
    # Student specific fields
    birth_date: Optional[datetime] = Field(None, description="Birth date")
    gender: Optional[str] = Field(None, description="Gender")
    bio: Optional[str] = Field(None, description="Biography")
    location: Optional[str] = Field(None, description="Location")
    education_level: Optional[str] = Field(None, description="Education level")
    interests: Optional[str] = Field(None, description="Interests")
    
    # Academy specific fields
    academy_name: Optional[str] = Field(None, description="Academy name")
    academy_id: Optional[str] = Field(None, description="Academy ID")
    about: Optional[str] = Field(None, description="Academy description")
    website: Optional[str] = Field(None, description="Academy website")
    established_year: Optional[int] = Field(None, description="Establishment year")
    accreditation: Optional[str] = Field(None, description="Accreditation info")
    courses_offered: Optional[str] = Field(None, description="Courses offered")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "fname": "Ahmed",
                "lname": "Ali",
                "email": "ahmed@example.com",
                "phone_number": "1234567890",
                "user_type": "student",
                "account_type": "local",
                "status": "active",
                "verified": True,
                "created_at": "2023-01-01T00:00:00Z"
            }
        }
    }


class UserProfileUpdate(BaseModel):
    """User profile update schema"""
    fname: Optional[str] = Field(None, min_length=2, max_length=255, description="First name")
    mname: Optional[str] = Field(None, max_length=255, description="Middle name")
    lname: Optional[str] = Field(None, min_length=2, max_length=255, description="Last name")
    phone_number: Optional[str] = Field(None, pattern="^[0-9]{10,15}$", description="Phone number")
    avatar: Optional[str] = Field(None, description="Avatar URL")
    banner: Optional[str] = Field(None, description="Banner URL")
    
    # Student specific fields
    birth_date: Optional[datetime] = Field(None, description="Birth date")
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$", description="Gender")
    bio: Optional[str] = Field(None, description="Biography")
    location: Optional[str] = Field(None, description="Location")
    education_level: Optional[str] = Field(None, description="Education level")
    interests: Optional[str] = Field(None, description="Interests")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "fname": "Ahmed",
                "lname": "Ali",
                "phone_number": "1234567890",
                "bio": "Computer Science student"
            }
        }
    } 