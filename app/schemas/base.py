"""
Base Schema Models
==================
Common and reusable schema components
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


class BaseUserData(BaseModel):
    """Base user data schema"""
    fname: str = Field(..., min_length=2, max_length=255, description="First name")
    mname: Optional[str] = Field(None, max_length=255, description="Middle name")
    lname: str = Field(..., min_length=2, max_length=255, description="Last name")
    email: EmailStr = Field(..., description="Email address")
    phone_number: str = Field(..., pattern="^[0-9]{10,15}$", description="Phone number")


class BasePassword(BaseModel):
    """Base password validation schema"""
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    password_confirm: str = Field(..., min_length=6, description="Password confirmation")
    
    @validator('password_confirm')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class BaseLogin(BaseModel):
    """Base login schema"""
    email: Optional[EmailStr] = Field(None, description="User email address")
    phone: Optional[str] = Field(None, pattern="^[0-9]{10,15}$", description="Phone number")
    password: str = Field(..., min_length=6, description="Password")
    
    @validator('email')
    def validate_email_or_phone(cls, v, values):
        if not v and not values.get('phone'):
            raise ValueError('Either email or phone is required')
        return v


class BaseResponse(BaseModel):
    """Unified API response schema (success or error)"""
    status: str = Field(..., description="Request result: success | error")
    status_code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Human-readable message")
    error_type: Optional[str] = Field(None, description="Error category when status=error")
    data: Optional[Dict[str, Any]] = Field(None, description="Payload for success responses")
    path: Optional[str] = Field(None, description="Request path")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Timestamp ISO 8601")


class MessageResponse(BaseResponse):
    """Generic message response (inherits unified fields)"""
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "status_code": 200,
                "message": "Operation completed successfully",
                "data": {},
                "timestamp": "2025-06-29T13:20:00.123456"
            }
        }
    }


class TimestampedBase(BaseModel):
    """Base schema with timestamps"""
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp") 