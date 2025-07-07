"""
Authentication Package
=====================
يتضمن جميع راوترات ومرافق المصادقة ذات الصلة
"""

from fastapi import APIRouter

from .auth_basic import router as basic_router
from .auth_otp import router as otp_router
from .auth_password import router as password_router

# Create main authentication router - إنشاء راوتر رئيسي للمصادقة
router = APIRouter()

# Include basic routers only in Swagger, hide OTP & Password to prevent duplication - تجميع الراوترات الأساسية فقط في Swagger، إخفاء OTP و Password لمنع التكرار
router.include_router(basic_router, prefix="")

# Legacy OTP routes (not shown in Swagger) - مسارات OTP القديمة (لا تظهر في Swagger)
router.include_router(otp_router, prefix="/otp")

# Legacy Password routes (not shown in Swagger) - مسارات Password القديمة (لا تظهر في Swagger)
router.include_router(password_router, prefix="/password")

# Export main router - تصدير الراوتر الرئيسي
router = router 