"""
Schema Models Module
====================
Unified imports for all schema models
"""

# Base schemas
from .base import (
    BaseUserData,
    BasePassword,
    BaseLogin,
    BaseResponse,
    MessageResponse,
    TimestampedBase
)

# Authentication schemas
from .authentication import (
    UnifiedLogin,
    UnifiedRegister,
    Token,
    TokenRefresh,
    TokenData
)

# Google OAuth schemas
from .google import (
    GoogleLoginRequest,
    GoogleRegisterRequest,
    GoogleAuthRequest,
    GoogleUserData,
    GoogleTokenVerificationResponse
)

# OTP schemas
from .otp import (
    OTPRequest,
    OTPVerify,
    OTPResponse
)

# Password management schemas
from .password import (
    PasswordChange,
    PasswordResetRequest,
    PasswordReset
)

# User profile schemas
from .user import (
    UserInfoResponse,
    UserProfileUpdate
)

# Legacy imports for backward compatibility
from .auth import *

__all__ = [
    # Base
    "BaseUserData",
    "BasePassword", 
    "BaseLogin",
    "BaseResponse",
    "MessageResponse",
    "TimestampedBase",
    
    # Authentication
    "UnifiedLogin",
    "UnifiedRegister", 
    "Token",
    "TokenRefresh",
    "TokenData",
    
    # Google OAuth
    "GoogleLoginRequest",
    "GoogleRegisterRequest",
    "GoogleAuthRequest",
    "GoogleUserData",
    "GoogleTokenVerificationResponse",
    
    # OTP
    "OTPRequest",
    "OTPVerify",
    "OTPResponse",
    
    # Password
    "PasswordChange",
    "PasswordResetRequest",
    "PasswordReset",
    
    # User
    "UserInfoResponse",
    "UserProfileUpdate"
] 