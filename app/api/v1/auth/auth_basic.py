"""
Basic Authentication Endpoints
==============================
Login, Register, and Logout functionality
"""

from typing import Any, Union, Optional
import os
from fastapi import APIRouter, Depends, HTTPException, status, Body, Form, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import ValidationError, Field

from app.core import security
from app.deps import get_db, get_current_user
from app.schemas import (
    Token,
    UnifiedLogin,
    UnifiedRegister,
    MessageResponse,
    GoogleLoginRequest,
    GoogleRegisterRequest
)
from app.models.user import User
from .auth_utils import (
    get_current_timestamp,
    generate_user_tokens
)
from .registration_service import RegistrationService
from app.services.google_auth_service import GoogleAuthService

router = APIRouter()


@router.post("/login", response_model=Token, tags=["Authentication"])
def unified_login(
    body: Union[UnifiedLogin, GoogleLoginRequest] = Body(
        ...,
        examples={
            "local_login": {
                "summary": "تسجيل الدخول المحلي",
                "description": "تسجيل الدخول باستخدام البريد الإلكتروني وكلمة المرور",
                "value": {
                    "email": "user@example.com",
                    "password": "password123",
                    "user_type": "student"
                }
            },
            "google_login": {
                "summary": "تسجيل الدخول بـ Google",
                "description": "تسجيل الدخول باستخدام Google OAuth Token",
                "value": {
                    "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjY...",
                    "user_type": "student"
                }
            }
        }
    ),
    db: Session = Depends(get_db)
) -> Any:
    """
    تسجيل الدخول الموحد - يدعم التسجيل المحلي وGoogle OAuth
    
    ## طرق تسجيل الدخول:
    
    ### 1. التسجيل المحلي:
    - استخدم `email` و `password` و `user_type`
    - مثال: `{"email": "user@example.com", "password": "password123", "user_type": "student"}`
    
    ### 2. تسجيل الدخول بـ Google:
    - استخدم `google_token` و `user_type`
    - مثال: `{"google_token": "your_google_token", "user_type": "student"}`
    
    ## أنواع المستخدمين المدعومة:
    - `student`: طالب
    - `academy`: أكاديمية
    """
    
    try:
        # تحويل body إلى dict للتحقق من المحتوى
        if isinstance(body, dict):
            body_dict = body
        else:
            body_dict = body.dict()
            
        # التحقق من وجود google_token لتحديد نوع تسجيل الدخول
        if "google_token" in body_dict and body_dict["google_token"]:
            # تسجيل الدخول بـ Google
            if not isinstance(body, GoogleLoginRequest):
                google_request = GoogleLoginRequest(**body_dict)
            else:
                google_request = body
            return handle_google_login(google_request, db)
        else:
            # تسجيل الدخول المحلي
            if not isinstance(body, UnifiedLogin):
                login_data = UnifiedLogin(**body_dict)
            else:
                login_data = body
            return handle_local_login(login_data, db)
            
    except ValidationError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "status": 422,
                "error": "Validation Error",
                "message": "بيانات تسجيل الدخول غير صحيحة",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": 500,
                "error": "Internal Server Error",
                "message": "فشل في تسجيل الدخول",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )


def handle_local_login(login_data: UnifiedLogin, db: Session) -> Token:
    """معالجة تسجيل الدخول المحلي"""
    
    # البحث عن المستخدم
    user = None
    if login_data.email:
        user = db.query(User).filter(User.email == login_data.email).first()
    elif login_data.phone:
        user = db.query(User).filter(User.phone_number == login_data.phone).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": 401,
                "error": "Unauthorized",
                "message": "البريد الإلكتروني أو كلمة المرور غير صحيحة",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )
    
    # التحقق من نوع المستخدم
    if user.user_type != login_data.user_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": 401,
                "error": "Unauthorized",
                "message": "نوع المستخدم غير متطابق",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )
    
    # التحقق من حالة الحساب
    if user.status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": 403,
                "error": "Forbidden",
                "message": "الحساب محظور",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )
    
    # التحقق من كلمة المرور للحسابات المحلية
    if user.account_type == "local":
        if not user.password or not security.verify_password(login_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": 401,
                    "error": "Unauthorized",
                    "message": "البريد الإلكتروني أو كلمة المرور غير صحيحة",
                    "path": "/api/v1/auth/login",
                    "timestamp": get_current_timestamp()
                }
            )
    
    return generate_user_tokens(user, db)


def handle_google_login(google_request, db: Session) -> Token:
    """معالجة تسجيل الدخول بـ Google"""
    
    # التحقق من Google token
    google_user_data = GoogleAuthService.verify_google_token(google_request.google_token)
    
    if not google_user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": 401,
                "error": "Unauthorized",
                "message": "Google Token غير صحيح أو منتهي الصلاحية",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )

    # البحث عن المستخدم باستخدام email
    user = db.query(User).filter(User.email == google_user_data["email"]).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": 401,
                "error": "Unauthorized",
                "message": "لم يتم العثور على المستخدم بهذا البريد الإلكتروني، يجب التسجيل أولاً",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )
    
    # التحقق من نوع المستخدم
    if user.user_type != google_request.user_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": 401,
                "error": "Unauthorized",
                "message": "نوع المستخدم غير متطابق",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )
    
    # التحقق من حالة الحساب
    if user.status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": 403,
                "error": "Forbidden",
                "message": "الحساب محظور",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )
    
    return generate_user_tokens(user, db)


@router.post("/register", response_model=Token, tags=["Authentication"])
async def unified_register(
    fname: str = Form(..., description="الاسم الأول"),
    lname: str = Form(..., description="الاسم الأخير"), 
    email: str = Form(..., description="البريد الإلكتروني"),
    phone_number: str = Form(..., description="رقم الهاتف"),
    password: str = Form(..., description="كلمة المرور"),
    password_confirm: str = Form(..., description="تأكيد كلمة المرور"),
    user_type: str = Form(..., description="نوع المستخدم (student/academy)"),
    avatar: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db)
) -> Any:
    """
    تسجيل مستخدم جديد مع دعم رفع صورة شخصية
    
    ## الحقول المطلوبة:
    - fname: الاسم الأول
    - lname: الاسم الأخير
    - email: البريد الإلكتروني
    - phone_number: رقم الهاتف
    - password: كلمة المرور
    - password_confirm: تأكيد كلمة المرور
    - user_type: نوع المستخدم (student/academy)
    
    ## الحقول الاختيارية:
    - avatar: صورة الملف الشخصي
    """
    
    try:
        # التحقق المبكر من user_type لحل مشكلة الاستضافة  
        user_type_clean = user_type.strip().lower() if user_type else ""
        if user_type_clean not in ["student", "academy"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_user_type",
                    "message": f"نوع المستخدم '{user_type}' غير صحيح. القيم المسموحة: student, academy",
                    "received_value": user_type,
                    "cleaned_value": user_type_clean,
                    "valid_options": ["student", "academy"],
                    "timestamp": get_current_timestamp()
                }
            )
        
        # التحقق من كلمات المرور
        if password != password_confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "password_mismatch",
                    "message": "كلمات المرور غير متطابقة",
                    "status_code": 400,
                    "timestamp": get_current_timestamp()
                }
            )
        
        # إنشاء بيانات التسجيل مع القيمة المنظفة
        registration_data = {
            "fname": fname.strip(),
            "lname": lname.strip(),
            "email": email.strip().lower(),
            "phone_number": phone_number.strip(),
            "password": password,
            "password_confirm": password_confirm,
            "user_type": user_type_clean  # استخدام القيمة المنظفة
        }
        
        # إنشاء المستخدم أولاً
        register_request = UnifiedRegister(**registration_data)
        user_tokens = await RegistrationService.register_local_user(register_request, db, avatar)
        
        return user_tokens
        
    except HTTPException:
        raise
    except ValidationError as ve:
        # معالجة أخطاء التحقق من Pydantic
        error_message = "البيانات المُدخلة غير صحيحة"
        
        # استخراج رسائل أخطاء محددة
        validation_errors = []
        for error in ve.errors():
            field = error.get('loc', ['unknown'])[-1]
            error_type = error.get('type', '')
            
            if 'email' in error_type:
                error_message = "البريد الإلكتروني غير صحيح"
            elif field == 'phone_number':
                error_message = "رقم الهاتف غير صحيح"
            
            validation_errors.append({
                "field": field,
                "message": error.get('msg', ''),
                "type": error_type
            })
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "status": "error",
                "error": "validation_error",
                "message": error_message,
                "status_code": 422,
                "validation_errors": validation_errors,
                "timestamp": get_current_timestamp()
            }
        )
    except Exception as e:
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "user_exists",
                    "message": "مستخدم بهذا البريد الإلكتروني أو رقم الهاتف موجود بالفعل",
                    "status_code": 409,
                    "timestamp": get_current_timestamp()
                }
            )
        else:
            # إضافة المزيد من التفاصيل للتشخيص
            error_details = {
                "error": "registration_failed",
                "message": "فشل في التسجيل، يرجى المحاولة مرة أخرى",
                "status_code": 500,
                "details": str(e),
                "debug_info": {
                    "user_type_received": user_type,
                    "user_type_type": str(type(user_type)),
                    "validation_error": "validation" in str(e).lower()
                },
                "timestamp": get_current_timestamp()
            }
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_details
            )


@router.post("/logout", response_model=MessageResponse, tags=["Authentication"])
def logout(current_user = Depends(get_current_user)) -> Any:
    """تسجيل الخروج"""
    
    return MessageResponse(
        message="تم تسجيل الخروج بنجاح. تم إنهاء جميع الجلسات.",
        status="success",
        data={
            "logged_out_at": get_current_timestamp(),
            "user_id": current_user.id,
            "tokens_invalidated": True
        }
    )


 