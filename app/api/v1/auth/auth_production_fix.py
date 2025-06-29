"""
Production-Ready Registration Endpoint
=====================================
مُحسّن للعمل على الاستضافة مع معالجة أفضل للأخطاء
"""

from typing import Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime

from app.deps.database import get_db
from app.schemas.authentication import Token
from app.api.v1.auth.registration_service import RegistrationService
from app.api.v1.auth.auth_utils import get_current_timestamp

router = APIRouter()


class ProductionRegisterSchema(BaseModel):
    """Schema مُحسّن للإنتاج"""
    fname: str = Field(..., min_length=2, max_length=255)
    lname: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone_number: str = Field(..., pattern="^[0-9]{10,15}$")
    password: str = Field(..., min_length=6)
    password_confirm: str = Field(..., min_length=6)
    user_type: str = Field(..., pattern="^(student|academy)$")
    
    @validator('password_confirm')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('كلمات المرور غير متطابقة')
        return v
    
    @validator('user_type')
    def validate_user_type(cls, v):
        if v not in ['student', 'academy']:
            raise ValueError('نوع المستخدم يجب أن يكون student أو academy')
        return v


@router.post("/register-production", response_model=Token, tags=["Production"])
async def production_register(
    fname: str = Form(..., description="الاسم الأول"),
    lname: str = Form(..., description="الاسم الأخير"), 
    email: str = Form(..., description="البريد الإلكتروني"),
    phone_number: str = Form(..., description="رقم الهاتف"),
    password: str = Form(..., description="كلمة المرور"),
    user_type: str = Form(..., description="نوع المستخدم (student/academy)"),
    avatar: Optional[UploadFile] = File(None, description="صورة الملف الشخصي"),
    db: Session = Depends(get_db)
) -> Any:
    """
    نقطة تسجيل محسّنة للإنتاج
    ========================
    
    معالجة محسّنة للأخطاء والتحقق من البيانات
    """
    
    try:
        # تنظيف البيانات المرسلة
        cleaned_data = {
            "fname": fname.strip() if fname else "",
            "lname": lname.strip() if lname else "",
            "email": email.strip().lower() if email else "",
            "phone_number": phone_number.strip() if phone_number else "",
            "password": password,
            "password_confirm": password_confirm,
            "user_type": user_type.strip().lower() if user_type else ""
        }
        
        # التحقق من الحقول المطلوبة
        required_fields = ["fname", "lname", "email", "phone_number", "password", "password_confirm", "user_type"]
        missing_fields = []
        
        for field in required_fields:
            if not cleaned_data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "missing_fields",
                    "message": f"الحقول المطلوبة مفقودة: {', '.join(missing_fields)}",
                    "missing_fields": missing_fields,
                    "timestamp": get_current_timestamp()
                }
            )
        
        # التحقق من user_type بشكل صريح
        valid_user_types = ["student", "academy"]
        if cleaned_data["user_type"] not in valid_user_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_user_type",
                    "message": f"نوع المستخدم يجب أن يكون أحد القيم التالية: {', '.join(valid_user_types)}",
                    "received_value": cleaned_data["user_type"],
                    "valid_values": valid_user_types,
                    "timestamp": get_current_timestamp()
                }
            )
        
        # التحقق من كلمات المرور
        if cleaned_data["password"] != cleaned_data["password_confirm"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "password_mismatch",
                    "message": "كلمات المرور غير متطابقة",
                    "timestamp": get_current_timestamp()
                }
            )
        
        # التحقق من طول كلمة المرور
        if len(cleaned_data["password"]) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "password_too_short",
                    "message": "كلمة المرور يجب أن تكون 6 أحرف على الأقل",
                    "timestamp": get_current_timestamp()
                }
            )
        
        # إنشاء schema object بعد التحقق
        register_schema = ProductionRegisterSchema(**cleaned_data)
        
        # تسجيل المستخدم
        user_tokens = RegistrationService.register_local_user(register_schema, db, avatar)
        
        return user_tokens
        
    except HTTPException:
        raise
    except ValueError as ve:
        # أخطاء التحقق من Pydantic
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": f"خطأ في التحقق من البيانات: {str(ve)}",
                "details": str(ve),
                "timestamp": get_current_timestamp()
            }
        )
    except Exception as e:
        # أخطاء أخرى
        error_message = str(e)
        
        if "already exists" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "user_exists",
                    "message": "مستخدم بهذا البريد الإلكتروني أو رقم الهاتف موجود بالفعل",
                    "timestamp": get_current_timestamp()
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "registration_failed",
                    "message": "فشل في التسجيل، يرجى المحاولة مرة أخرى",
                    "debug_details": {
                        "error_type": type(e).__name__,
                        "error_message": error_message,
                        "received_user_type": cleaned_data.get("user_type", "N/A")
                    },
                    "timestamp": get_current_timestamp()
                }
            )


@router.post("/register-simple", response_model=Token, tags=["Production"])
async def simple_register(
    request: ProductionRegisterSchema,
    db: Session = Depends(get_db)
) -> Any:
    """
    تسجيل بسيط باستخدام JSON body
    =============================
    
    للاختبار مع requests مباشرة
    """
    
    try:
        user_tokens = RegistrationService.register_local_user(request, db)
        return user_tokens
        
    except Exception as e:
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "user_exists", 
                    "message": "مستخدم موجود بالفعل",
                    "timestamp": get_current_timestamp()
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "registration_failed",
                    "message": "فشل في التسجيل",
                    "details": str(e),
                    "timestamp": get_current_timestamp()
                }
            ) 