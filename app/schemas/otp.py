"""
OTP Schema Models
=================
OTP request and verification schemas
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional

from .base import BaseResponse


class OTPRequest(BaseModel):
    """OTP request schema"""
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, pattern="^[0-9]{10,15}$", description="Phone number")
    purpose: str = Field(..., pattern="^(login|password_reset|email_verification|transaction_confirmation)$", description="OTP purpose")
    
    @validator('email')
    def validate_email_or_phone(cls, v, values):
        if not v and not values.get('phone'):
            raise ValueError('Either email or phone is required')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "purpose": "email_verification"
            }
        }
    }


class OTPVerify(BaseModel):
    """OTP verification schema"""
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, pattern="^[0-9]{10,15}$", description="Phone number")
    otp: str = Field(..., min_length=4, max_length=6, description="OTP code")
    purpose: str = Field(..., pattern="^(login|password_reset|email_verification|transaction_confirmation)$", description="OTP purpose")
    
    @validator('email')
    def validate_email_or_phone(cls, v, values):
        if not v and not values.get('phone'):
            raise ValueError('Either email or phone is required')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "otp": "123456",
                "purpose": "email_verification"
            }
        }
    }


class OTPResponse(BaseResponse):
    """OTP operation response"""
    expires_in: Optional[int] = Field(None, description="OTP expiration time in seconds")
    attempts_remaining: Optional[int] = Field(None, description="Verification attempts remaining")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "OTP sent successfully",
                "status": "success",
                "expires_in": 300,
                "attempts_remaining": 3
            }
        }
    } 