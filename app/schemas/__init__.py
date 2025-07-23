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

# Auth refresh schemas
from .auth import RefreshTokenRequest

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
    OTPResponse,
    OTPStatusResponse
)

# Password management schemas
from .password import (
    PasswordChange,
    PasswordResetRequest,
    PasswordReset,
    OTPVerifyForReset,
    PasswordResetWithToken,
    PasswordForgotRequest,
    OTPVerificationResponse
)

# User profile schemas
from .user import (
    UserInfoResponse,
    UserProfileUpdate
)

# Legacy imports for backward compatibility
from .auth import *

# Product schemas
from .product import *

# Template schemas
from .template import Template, TemplateCreate, TemplateUpdate
from .faq import Faq, FaqCreate, FaqUpdate
from .opinion import Opinion, OpinionCreate, OpinionUpdate
from .about import About, AboutCreate, AboutUpdate
from .slider import Slider, SliderCreate, SliderUpdate
from .settings import Settings, SettingsCreate, SettingsUpdate

# Academy profile schemas
from .academy_profile import (
    AcademyBasicInfo, TemplateInfo, AboutInfo, SocialLinks, SettingsInfo,
    MembershipInfo, ContentStatistics, SliderInfo, FaqInfo, OpinionInfo,
    AcademyProfileResponse, AcademyProfileSummaryResponse, PublicAcademyProfileResponse
)

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
    "OTPStatusResponse",
    
    # Password
    "PasswordChange",
    "PasswordResetRequest",
    "PasswordReset",
    "OTPVerifyForReset",
    "PasswordResetWithToken",
    "PasswordForgotRequest",
    "OTPVerificationResponse",
    
    # User
    "UserInfoResponse",
    "UserProfileUpdate",
    
    # Template
    "Template",
    "TemplateCreate", 
    "TemplateUpdate",
    "Faq",
    "FaqCreate",
    "FaqUpdate",
    "Opinion",
    "OpinionCreate",
    "OpinionUpdate",
    "About",
    "AboutCreate",
    "AboutUpdate",
    "Slider",
    "SliderCreate",
    "SliderUpdate",
    "Settings",
    "SettingsCreate",
    "SettingsUpdate",
    
    # Academy Profile
    "AcademyBasicInfo",
    "TemplateInfo",
    "AboutInfo",
    "SocialLinks",
    "SettingsInfo",
    "MembershipInfo",
    "ContentStatistics",
    "SliderInfo",
    "FaqInfo",
    "OpinionInfo",
    "AcademyProfileResponse",
    "AcademyProfileSummaryResponse",
    "PublicAcademyProfileResponse"
] 