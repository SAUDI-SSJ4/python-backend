"""
Authentication Module
====================
Unified authentication system for SAYAN platform
"""

from fastapi import APIRouter

from .auth_basic import router as basic_router
from .auth_otp import router as otp_router
from .auth_password import router as password_router
from .auth_profile import router as profile_router
from .auth_test import router as test_router

# إنشاء router رئيسي للمصادقة
auth_router = APIRouter()

# تجميع جميع الـ routers
auth_router.include_router(basic_router, tags=["Authentication"])
auth_router.include_router(otp_router, prefix="/otp", tags=["OTP"])
auth_router.include_router(password_router, prefix="/password", tags=["Password"])
auth_router.include_router(profile_router, tags=["Profile"])
auth_router.include_router(test_router, prefix="/test", tags=["Testing"])

# تصدير الـ router الرئيسي
router = auth_router 