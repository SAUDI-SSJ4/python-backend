from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


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

    class Config:
        schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "1234567890",
                "password": "password123",
                "password_confirm": "password123"
            }
        }


# Admin schemas
class AdminLogin(LoginBase):
    class Config:
        schema_extra = {
            "example": {
                "email": "admin@example.com",
                "password": "admin123"
            }
        }


class AdminRegister(RegisterBase):
    role_id: Optional[int] = Field(None, description="Optional role ID")


# Academy schemas  
class AcademyLogin(LoginBase):
    class Config:
        schema_extra = {
            "example": {
                "email": "academy@example.com",
                "password": "academy123"
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

    class Config:
        schema_extra = {
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


# Student schemas
class StudentLogin(LoginBase):
    class Config:
        schema_extra = {
            "example": {
                "email": "student@example.com",
                "password": "student123"
            }
        }


class StudentPhoneLogin(PhoneLoginBase):
    class Config:
        schema_extra = {
            "example": {
                "phone": "1234567890",
                "password": "student123"
            }
        }


class StudentRegister(RegisterBase):
    date_of_birth: Optional[datetime] = Field(None, description="Date of birth")
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$", description="Gender")
    country: Optional[str] = Field(None, description="Country")
    city: Optional[str] = Field(None, description="City")

    class Config:
        schema_extra = {
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


# OTP schemas
class OTPRequest(BaseModel):
    phone: str = Field(..., pattern="^[0-9]{10,15}$", description="Phone number to send OTP to")

    class Config:
        schema_extra = {
            "example": {
                "phone": "1234567890"
            }
        }


class OTPVerify(BaseModel):
    phone: str = Field(..., pattern="^[0-9]{10,15}$", description="Phone number")
    otp: str = Field(..., min_length=4, max_length=6, description="6-digit OTP code")

    class Config:
        schema_extra = {
            "example": {
                "phone": "1234567890",
                "otp": "123456"
            }
        }


# Token schemas
class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    user_type: Optional[str] = Field(None, description="User type (student/academy/admin)")

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_type": "student"
            }
        }


class TokenRefresh(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token")

    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class TokenData(BaseModel):
    user_id: Optional[int] = None
    user_type: Optional[str] = None


# Password reset schemas
class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address to send reset link to")

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class PasswordReset(BaseModel):
    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(..., min_length=6, description="New password (minimum 6 characters)")
    confirm_password: str = Field(..., min_length=6, description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

    class Config:
        schema_extra = {
            "example": {
                "token": "abc123def456ghi789",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            }
        }


class PasswordChange(BaseModel):
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, description="New password (minimum 6 characters)")
    confirm_password: str = Field(..., min_length=6, description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

    class Config:
        schema_extra = {
            "example": {
                "old_password": "oldpassword123",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            }
        }


# Response schemas
class MessageResponse(BaseModel):
    message: str = Field(..., description="Response message")

    class Config:
        schema_extra = {
            "example": {
                "message": "Operation completed successfully"
            }
        }


class OTPResponse(BaseModel):
    message: str = Field(..., description="Response message")
    phone: str = Field(..., description="Phone number")
    otp: Optional[str] = Field(None, description="OTP code (development only)")

    class Config:
        schema_extra = {
            "example": {
                "message": "OTP sent to your phone number",
                "phone": "1234567890",
                "otp": "123456"
            }
        }


class OTPVerifyResponse(BaseModel):
    message: str = Field(..., description="Response message")
    phone: str = Field(..., description="Phone number")
    verified: bool = Field(..., description="Verification status")

    class Config:
        schema_extra = {
            "example": {
                "message": "OTP verified successfully",
                "phone": "1234567890",
                "verified": True
            }
        }


class PasswordResetResponse(BaseModel):
    message: str = Field(..., description="Response message")
    email: str = Field(..., description="Email address")
    reset_token: Optional[str] = Field(None, description="Reset token (development only)")

    class Config:
        schema_extra = {
            "example": {
                "message": "Password reset link sent to your email",
                "email": "user@example.com",
                "reset_token": "abc123def456ghi789"
            }
        }


class UserInfo(BaseModel):
    id: int = Field(..., description="User ID")
    name: str = Field(..., description="User's full name")
    email: str = Field(..., description="User's email")
    phone: Optional[str] = Field(None, description="User's phone number")
    user_type: str = Field(..., description="User type")
    is_active: bool = Field(..., description="Account status")
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")
    
    # Student specific fields
    date_of_birth: Optional[datetime] = Field(None, description="Date of birth (students only)")
    gender: Optional[str] = Field(None, description="Gender (students only)")
    country: Optional[str] = Field(None, description="Country")
    city: Optional[str] = Field(None, description="City")
    status: Optional[str] = Field(None, description="Account status (students only)")
    email_verified: Optional[bool] = Field(None, description="Email verification status")
    phone_verified: Optional[bool] = Field(None, description="Phone verification status")
    last_login: Optional[datetime] = Field(None, description="Last login time")
    
    # Academy specific fields
    academy_name: Optional[str] = Field(None, description="Academy name")
    user_name: Optional[str] = Field(None, description="Username")
    is_owner: Optional[bool] = Field(None, description="Owner status")
    logo_url: Optional[str] = Field(None, description="Academy logo URL")
    cover_url: Optional[str] = Field(None, description="Academy cover URL")
    
    # Admin specific fields
    role_id: Optional[int] = Field(None, description="Role ID")

    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "name": "أحمد علي",
                "email": "ahmed@example.com",
                "phone": "1234567890",
                "user_type": "student",
                "is_active": True,
                "profile_image_url": "/static/uploads/profiles/profile.png",
                "date_of_birth": "1995-01-01T00:00:00Z",
                "gender": "male",
                "country": "السعودية",
                "city": "الرياض",
                "status": "active",
                "email_verified": True,
                "phone_verified": True,
                "last_login": "2023-12-01T10:30:00Z"
            }
        }


class UserInfoResponse(BaseModel):
    message: str = Field(..., description="Response message")
    user: UserInfo = Field(..., description="User information")

    class Config:
        schema_extra = {
            "example": {
                "message": "User information retrieved successfully",
                "user": {
                    "id": 1,
                    "name": "Ahmed Ali",
                    "email": "ahmed@example.com",
                    "user_type": "student",
                    "is_active": True
                }
            }
        } 