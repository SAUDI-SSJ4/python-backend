"""
OTP Schema Models
=================
OTP request and verification schemas with comprehensive purpose support
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any

from .base import BaseResponse


class OTPRequest(BaseModel):
    """OTP request schema with comprehensive purpose support"""
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, pattern="^[0-9]{10,15}$", description="Phone number")
    purpose: str = Field(
        ..., 
        pattern="^(login|password_reset|email_verification|phone_verification|transaction_confirmation|account_activation|change_password|email_update|phone_update|payment_confirmation|account_deletion|two_factor_auth|security_verification)$", 
        description="OTP purpose"
    )
    
    expires_in_minutes: Optional[int] = Field(10, ge=1, le=60, description="OTP expiration time in minutes")
    
    @validator('email')
    def validate_email_or_phone(cls, v, values):
        if not v and not values.get('phone'):
            raise ValueError('Either email or phone is required')
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "purpose": "email_verification",
                    "expires_in_minutes": 15
                },
                {
                    "phone": "1234567890",
                    "purpose": "phone_verification",
                    "expires_in_minutes": 10
                },
                {
                    "email": "user@example.com",
                    "purpose": "password_reset",
                    "expires_in_minutes": 30
                }
            ]
        }
    }


class OTPVerify(BaseModel):
    """OTP verification schema - NO PURPOSE REQUIRED"""
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, pattern="^[0-9]{10,15}$", description="Phone number")
    otp: str = Field(..., min_length=4, max_length=8, description="OTP code")
    
    @validator('email')
    def validate_email_or_phone(cls, v, values):
        if not v and not values.get('phone'):
            raise ValueError('Either email or phone is required')
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "otp": "123456"
                },
                {
                    "phone": "1234567890",
                    "otp": "123456"
                }
            ]
        }
    }


class OTPResponse(BaseResponse):
    """OTP operation response with detailed information"""
    expires_in: Optional[int] = Field(None, description="OTP expiration time in seconds")
    attempts_remaining: Optional[int] = Field(None, description="Verification attempts remaining")
    purpose: Optional[str] = Field(None, description="OTP purpose")
    sent_to: Optional[str] = Field(None, description="Where OTP was sent (masked)")
    expires_at: Optional[str] = Field(None, description="Exact expiration timestamp")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "تم إرسال رمز التحقق بنجاح",
                    "status": "success",
                    "expires_in": 600,
                    "attempts_remaining": 3,
                    "purpose": "email_verification",
                    "sent_to": "user***@example.com",
                    "expires_at": "2024-01-15T10:40:00.000Z"
                },
                {
                    "message": "تم التحقق من الرمز بنجاح",
                    "status": "success",
                    "purpose": "email_verification",
                    "verified": True
                }
            ]
        }
    }


class OTPStatusResponse(BaseResponse):
    """OTP status and management response"""
    active_otps: Optional[int] = Field(None, description="Number of active OTPs")
    expired_otps: Optional[int] = Field(None, description="Number of expired OTPs")
    total_attempts: Optional[int] = Field(None, description="Total verification attempts")
    last_sent: Optional[str] = Field(None, description="Last OTP sent timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "حالة OTP",
                "status": "success", 
                "active_otps": 2,
                "expired_otps": 1,
                "total_attempts": 5,
                "last_sent": "2024-01-15T10:30:00.000Z"
            }
        }
    } 