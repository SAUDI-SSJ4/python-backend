"""
Password Management Schema Models
==================================
Password change, reset, and recovery schemas
"""

from pydantic import BaseModel, EmailStr, Field, validator
from .base import BasePassword


class PasswordChange(BaseModel):
    """Password change schema"""
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, description="New password")
    confirm_password: str = Field(..., min_length=6, description="Confirm password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "old_password": "oldpassword123",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            }
        }
    }


class PasswordResetRequest(BaseModel):
    """Password reset request schema"""
    email: EmailStr = Field(..., description="Email address")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com"
            }
        }
    }


class OTPVerifyForReset(BaseModel):
    """OTP verification schema for password reset"""
    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=8, description="OTP code from email")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "otp": "123456"
            }
        }
    }


class PasswordResetWithToken(BaseModel):
    """Password reset schema using verification token"""
    verification_token: str = Field(..., description="Verification token from OTP verification")
    new_password: str = Field(..., min_length=6, description="New password")
    confirm_password: str = Field(..., min_length=6, description="Confirm password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "verification_token": "ver_1234567890abcdef",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            }
        }
    }


class PasswordReset(BaseModel):
    """Password reset schema using OTP (legacy)"""
    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=8, description="OTP code from email")
    new_password: str = Field(..., min_length=6, description="New password")
    confirm_password: str = Field(..., min_length=6, description="Confirm password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            }
        }
    }


class OTPVerificationResponse(BaseModel):
    """OTP verification response with token"""
    message: str = Field(..., description="Success message")
    status: str = Field(..., description="Status")
    verification_token: str = Field(..., description="Token for password reset")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "تم التحقق من OTP بنجاح",
                "status": "success",
                "verification_token": "ver_1234567890abcdef",
                "expires_in": 300
            }
        }
    } 