"""
Authentication Module
====================
Unified authentication system for SAYAN platform
"""

from fastapi import APIRouter

from .auth_basic import router as basic_router
from .auth_otp import router as otp_router
from .auth_password import router as password_router

# إنشاء router رئيسي للمصادقة
auth_router = APIRouter()

# تجميع الـ routers الأساسية فقط في Swagger، بينما نخفي OTP و Password لمنع التكرار
auth_router.include_router(basic_router)

# مسارات OTP القديمة (لا تظهر في Swagger)
auth_router.include_router(
    otp_router,
    prefix="/otp",
    include_in_schema=False  # إخفاء من التوثيق لتجنب الازدواجية
)

# مسارات Password القديمة (لا تظهر في Swagger)
auth_router.include_router(
    password_router,
    prefix="/password",
    include_in_schema=False  # إخفاء من التوثيق لتجنب الازدواجية
)

# تصدير الـ router الرئيسي
router = auth_router 