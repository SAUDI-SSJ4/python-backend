from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from .base import BaseResponse  # استيراد المخطط الموحد


# Base schemas
class LoginBase(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=6, description="User's password (minimum 6 characters)")


class PhoneLoginBase(BaseModel):
    phone: str = Field(..., pattern="^[0-9]{10,15}$", description="Phone number (10-15 digits)")
    password: str = Field(..., min_length=6, description="User's password (minimum 6 characters)")


class RegisterBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Full name (2-255 characters)")
    email: EmailStr = Field(..., description="Valid email address")
    phone: str = Field(..., pattern="^[0-9]{10,15}$", description="Phone number (10-15 digits)")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    password_confirm: str = Field(..., min_length=6, description="Password confirmation")
    
    @validator('password_confirm')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "1234567890",
                "password": "password123",
                "password_confirm": "password123"
            }
        }
    }


# Admin schemas
class AdminLogin(LoginBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "admin@example.com",
                "password": "admin123"
            }
        }
    }


class AdminRegister(RegisterBase):
    role_id: Optional[int] = Field(None, description="Optional role ID")


# Academy schemas  
class AcademyLogin(LoginBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "academy@example.com",
                "password": "academy123"
            }
        }
    }


class AcademyRegister(BaseModel):
    # Academy details
    academy_name: str = Field(..., min_length=2, max_length=255, description="Academy name")
    slug: str = Field(..., min_length=2, max_length=255, description="Academy URL slug")
    user_name: str = Field(..., min_length=2, max_length=255, description="Academy username")
    
    # User details
    name: str = Field(..., min_length=2, max_length=255, description="Admin's full name")
    email: EmailStr = Field(..., description="Admin's email address")
    phone: str = Field(..., pattern="^[0-9]{10,15}$", description="Admin's phone number")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    password_confirm: str = Field(..., min_length=6, description="Password confirmation")
    
    # Optional details
    address: Optional[str] = Field(None, description="Academy address")
    country: Optional[str] = Field(None, description="Country")
    city: Optional[str] = Field(None, description="City")
    description: Optional[str] = Field(None, description="Academy description")
    
    @validator('password_confirm')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "academy_name": "Tech Academy",
                "slug": "tech-academy",
                "user_name": "tech_admin",
                "name": "Jane Smith",
                "email": "admin@techacademy.com",
                "phone": "1234567890",
                "password": "academy123",
                "password_confirm": "academy123",
                "address": "123 Main St",
                "country": "Saudi Arabia",
                "city": "Riyadh",
                "description": "A leading technology academy"
            }
        }
    }


# Student schemas
class StudentLogin(LoginBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "student@example.com",
                "password": "student123"
            }
        }
    }


class StudentPhoneLogin(PhoneLoginBase):
    model_config = {
        "json_schema_extra": {
            "example": {
                "phone": "1234567890",
                "password": "student123"
            }
        }
    }


class StudentRegister(RegisterBase):
    date_of_birth: Optional[datetime] = Field(None, description="Date of birth")
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$", description="Gender")
    country: Optional[str] = Field(None, description="Country")
    city: Optional[str] = Field(None, description="City")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Ahmed Ali",
                "email": "ahmed@example.com",
                "phone": "1234567890",
                "password": "student123",
                "password_confirm": "student123",
                "date_of_birth": "1995-01-01T00:00:00Z",
                "gender": "male",
                "country": "Saudi Arabia",
                "city": "Riyadh"
            }
        }
    }


# Unified authentication schemas
class UnifiedLogin(BaseModel):
    """Unified login schema for both students and academies"""
    email: Optional[EmailStr] = Field(None, description="User email address")
    phone: Optional[str] = Field(None, pattern="^[0-9]{10,15}$", description="Phone number")
    password: str = Field(..., min_length=6, description="Password")
    
    @validator('email')
    def validate_email_or_phone(cls, v, values):
        if not v and not values.get('phone'):
            raise ValueError('Either email or phone is required')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "password123"
            }
        }
    }

class UnifiedRegister(BaseModel):
    """Unified registration schema for both students and academies"""
    fname: str = Field(..., min_length=2, max_length=255, description="First name")
    mname: Optional[str] = Field(None, max_length=255, description="Middle name")
    lname: str = Field(..., min_length=2, max_length=255, description="Last name")
    email: EmailStr = Field(..., description="Email address")
    phone_number: str = Field(..., pattern="^[0-9]{10,15}$", description="Phone number")
    password: str = Field(..., min_length=6, description="Password")
    password_confirm: str = Field(..., min_length=6, description="Confirm password")
    user_type: str = Field(..., pattern="^(student|academy)$", description="User type")
    
    # Student specific fields
    birth_date: Optional[datetime] = Field(None, description="Birth date (students only)")
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$", description="Gender (students only)")
    
    # Academy specific fields
    academy_name: Optional[str] = Field(None, min_length=2, max_length=200, description="Academy name (academies only)")
    academy_about: Optional[str] = Field(None, description="Academy description")
    
    # Optional fields
    refere_id: Optional[int] = Field(None, description="Referrer user ID")
    picture: Optional[str] = Field(None, description="Profile picture URL (for Google auth)")
    
    @validator('password_confirm')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('academy_name')
    def validate_academy_fields(cls, v, values):
        if values.get('user_type') == 'academy' and not v:
            raise ValueError('Academy name is required for academy registration')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "fname": "أحمد",
                "lname": "علي",
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


# Google authentication schemas
class GoogleLoginRequest(BaseModel):
    """Google login request - simplified"""
    google_token: str = Field(..., description="Google ID token من Frontend")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjBkOGE2NzM5OWU3ODgyYWNhZTdkN2Y2OGIyMjgwMjU2YTc5NmE1ODIiLCJ0eXAiOiJKV1QifQ..."
            }
        }
    }


class GoogleRegisterRequest(BaseModel):
    """Google registration request - simplified"""
    google_token: str = Field(..., description="Google ID token من Frontend")
    user_type: str = Field(..., pattern="^(student|academy)$", description="نوع المستخدم")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjBkOGE2NzM5OWU3ODgyYWNhZTdkN2Y2OGIyMjgwMjU2YTc5NmE1ODIiLCJ0eXAiOiJKV1QifQ...",
                "user_type": "student"
            }
        }
    }


# Legacy Google Auth schema - لأغراض التوافق مع الكود الموجود
class GoogleAuthRequest(BaseModel):
    """Google authentication request schema - Legacy"""
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
                "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjBkOGE2NzM5OWU3ODgyYWNhZTdkN2Y2OGIyMjgwMjU2YTc5NmE1ODIiLCJ0eXAiOiJKV1QifQ...",
                "user_type": "student"
            }
        }
    }


# OTP schemas
class OTPRequest(BaseModel):
    """OTP request schema"""
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, pattern="^[0-9]{10,15}$", description="Phone number")
    purpose: str = Field(..., pattern="^(login|password_reset|email_verification|phone_verification|transaction_confirmation|account_activation|change_password|email_update|phone_update|payment_confirmation|account_deletion|two_factor_auth|security_verification)$", description="OTP purpose")
    
    # حقول إضافية للأمان والتتبع
    device_id: Optional[str] = Field(None, description="Device identifier")
    expires_in_minutes: Optional[int] = Field(10, ge=1, le=60, description="OTP expiration time in minutes")
    
    @validator('email')
    def validate_email_or_phone(cls, v, values):
        if not v and not values.get('phone'):
            raise ValueError('Either email or phone is required')
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "purpose": "email_verification",
                "expires_in_minutes": 15
            }
        }
    }


class OTPVerify(BaseModel):
    """OTP verification schema - simplified without purpose"""
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, pattern="^[0-9]{10,15}$", description="Phone number")
    otp: str = Field(..., min_length=4, max_length=6, description="OTP code")
    
    @validator('email')
    def validate_email_or_phone(cls, v, values):
        if not v and not values.get('phone'):
            raise ValueError('Either email or phone is required')
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "otp": "123456"
            }
        }
    }


# Token schemas
class Token(BaseModel):
    """Authentication token response"""
    access_token: Optional[str] = Field(default=None, description="JWT access token")
    refresh_token: Optional[str] = Field(default=None, description="JWT refresh token")
    token_type: Optional[str] = Field(default=None, description="Token type")
    user_type: Optional[str] = Field(default=None, description="User type")
    status: str = Field(default="success", description="Response status")
    status_code: Optional[int] = Field(default=200, description="HTTP status code")
    error_type: Optional[str] = Field(default=None, description="Error category (null فى حالة النجاح)")
    message: Optional[str] = Field(default="تمت العملية بنجاح", description="رسالة بشرية")
    path: Optional[str] = Field(default=None, description="مسار الطلب")
    timestamp: Optional[str] = Field(default=None, description="Response timestamp")
    user_data: Optional[Dict[str, Any]] = Field(default=None, description="User information")

    # استبعاد الحقول None تلقائياً فى المخرجات
    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                "token_type": "bearer",
                "user_type": "student",
                "status": "success",
                "user_data": {
                    "id": 123,
                    "email": "user@example.com",
                    "fname": "أحمد",
                    "lname": "محمد",
                    "user_type": "student",
                    "account_type": "local",
                    "verified": True,
                    "status": "active"
                }
            }
        },
        "extra": "allow",
        "ser_json_exclude_none": True  # حذف الحقول None من الإخراج
    }


class TokenRefresh(BaseModel):
    """Token refresh schema"""
    refresh_token: str = Field(..., description="Valid refresh token")

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    }


class TokenData(BaseModel):
    """Token data schema"""
    user_id: Optional[int] = None
    user_type: Optional[str] = None
    email: Optional[str] = None


# Password reset schemas
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


class PasswordReset(BaseModel):
    """Password reset schema using OTP"""
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


# Response schemas
class MessageResponse(BaseResponse):
    """رد بسيط يعتمد على البنية الموحدة، مع إمكانية إلحاق بيانات اختيارية"""

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "status_code": 200,
                "error_type": None,
                "message": "تمت العملية بنجاح",
                "data": None,
                "path": "/api/v1/...",
                "timestamp": "2025-06-29T13:20:00.123456"
            }
        }
    }


class UserInfoResponse(BaseModel):
    """User information response"""
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
    created_at: datetime = Field(..., description="Registration date")
    
    # Student specific fields
    birth_date: Optional[datetime] = Field(None, description="Birth date")
    gender: Optional[str] = Field(None, description="Gender")
    
    # Academy specific fields
    academy_name: Optional[str] = Field(None, description="Academy name")
    academy_id: Optional[str] = Field(None, description="Academy ID")
    academy_about: Optional[str] = Field(None, description="Academy description")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "fname": "أحمد",
                "lname": "علي",
                "email": "ahmed@example.com",
                "phone_number": "1234567890",
                "user_type": "student",
                "account_type": "local",
                "status": "active",
                "verified": True,
                "created_at": "2023-12-01T10:00:00Z"
            }
        }
    } 