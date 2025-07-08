"""
Basic Authentication Endpoints
==============================
Login, Register, and Logout functionality
"""

from typing import Any, Union, Optional
import os
from fastapi import APIRouter, Depends, HTTPException, status, Body, Form, UploadFile, File, Request
from sqlalchemy.orm import Session
from pydantic import ValidationError, Field
import logging

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
    generate_user_tokens,
    create_unified_error_response
)
from .registration_service import RegistrationService
from app.services.google_auth_service import GoogleAuthService

# إعداد Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=Token, response_model_exclude_none=True, tags=["Authentication"])
async def unified_login(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    تسجيل الدخول الموحد - يدعم Form Data و JSON
    
    يمكن استخدام Form Data للسهولة:
    - email: البريد الإلكتروني
    - password: كلمة المرور  
    - user_type: نوع المستخدم (اختياري - سيتم التحديد تلقائياً)
    
    أو JSON في body للتوافق مع الإصدارات السابقة
    """
    
    try:
        # Check content type - التحقق من نوع المحتوى
        content_type = request.headers.get("content-type", "").lower()
        
        # Parse request body based on content type - تحليل محتوى الطلب حسب نوعه
        if "application/json" in content_type:
            # JSON request - طلب JSON
            body = await request.json()
            merged_data = {
                "email": body.get("email"),
                "password": body.get("password"),
                "user_type": body.get("user_type"),
                "phone": body.get("phone"),
                "google_token": body.get("google_token")
            }
        else:
            # Form data request - طلب Form Data
            form = await request.form()
            merged_data = {
                "email": form.get("email"),
                "password": form.get("password"),
                "user_type": form.get("user_type"),
                "phone": form.get("phone"),
                "google_token": form.get("google_token")
            }
            
        # Remove None values - إزالة القيم الفارغة
        merged_data = {k: v for k, v in merged_data.items() if v is not None}
        
        # التأكد من وجود البيانات المطلوبة
        if not merged_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_type": "Missing Data",
                    "message": "يجب تقديم بيانات تسجيل الدخول إما عبر Form Data أو JSON",
                    "path": "/api/v1/auth/login",
                    "timestamp": get_current_timestamp()
                }
            )
        
        # التمييز بين تسجيل الدخول العادي و Google OAuth
        if "google_token" in merged_data and merged_data["google_token"]:
            # Google OAuth login
            google_request = GoogleLoginRequest(**merged_data)
            return handle_google_login(google_request, db)
        else:
            # Local login - إضافة user_type إذا لم يكن موجوداً
            if "user_type" not in merged_data:
                # البحث عن المستخدم تلقائياً وتحديد نوعه
                return handle_auto_detect_login(merged_data, db)
            else:
                # تسجيل دخول عادي مع نوع محدد
                login_data = UnifiedLogin(**merged_data)
                return handle_local_login(login_data, db)
            
    except ValidationError as ve:
        # تحسين رسالة الخطأ للتوضيح
        error_msg = "بيانات تسجيل الدخول غير صحيحة"
        missing_fields = []
        
        for error in ve.errors():
            if error['type'] == 'missing':
                field_name = error['loc'][-1]
                if field_name == 'user_type':
                    error_msg = "نوع المستخدم مطلوب (student/academy/admin)"
                    missing_fields.append("user_type")
                elif field_name == 'email':
                    missing_fields.append("email")
                elif field_name == 'password':
                    missing_fields.append("password")
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "status": "error",
                "status_code": 422,
                "error_type": "Validation Error",
                "message": error_msg,
                "missing_fields": missing_fields,
                "suggestion": "أضف حقل user_type أو دع النظام يحدده تلقائياً",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )
    except Exception as e:
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


def handle_auto_detect_login(body: dict, db: Session) -> Token:
    """تسجيل الدخول مع التحديد التلقائي لنوع المستخدم"""
    
    # التحقق من وجود الحقول المطلوبة
    if "email" not in body and "phone" not in body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "error_type": "Missing Required Field",
                "message": "البريد الإلكتروني أو رقم الهاتف مطلوب",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )
    
    if "password" not in body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error", 
                "error_type": "Missing Required Field",
                "message": "كلمة المرور مطلوبة",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )
    
    # البحث عن المستخدم
    user = None
    if body.get("email"):
        user = db.query(User).filter(User.email == body["email"]).first()
    elif body.get("phone"):
        user = db.query(User).filter(User.phone_number == body["phone"]).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "error_type": "User Not Found",
                "message": "المستخدم غير موجود",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )
    
    # التحقق من كلمة المرور
    if user.account_type == "local":
        if not user.password or not security.verify_password(body["password"], user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "error_type": "Invalid Credentials",
                    "message": "كلمة المرور غير صحيحة",
                    "path": "/api/v1/auth/login",
                    "timestamp": get_current_timestamp()
                }
            )
    
    # التحقق من حالة الحساب
    if user.status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "error_type": "Account Blocked",
                "message": "الحساب محظور",
                "path": "/api/v1/auth/login",
                "timestamp": get_current_timestamp()
            }
        )
    
    return generate_user_tokens(user, db)


def handle_local_login(login_data: UnifiedLogin, db: Session) -> Token:
    """   """
    
    try:
        logger.info(f"محاولة تسجيل دخول لـ: {login_data.email}")
        
        user = None
        if login_data.email:
            user = db.query(User).filter(User.email == login_data.email).first()
            logger.info(f"تم العثور على المستخدم: {user is not None}")
        elif login_data.phone:
            user = db.query(User).filter(User.phone_number == login_data.phone).first()
            logger.info(f"تم العثور على المستخدم: {user is not None}")
        
        if not user:
            logger.warning(f"لم يتم العثور على المستخدم: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": 401,
                    "error": "Unauthorized",
                    "message": "المستخدم غير موجود",
                    "path": "/api/v1/auth/login",
                    "timestamp": get_current_timestamp()
                }
            )
        
        logger.info(f"نوع المستخدم المطلوب: {login_data.user_type}, نوع المستخدم الفعلي: {user.user_type}")
        if user.user_type != login_data.user_type:
            logger.warning(f"نوع المستخدم غير متطابق: {login_data.user_type} != {user.user_type}")
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
        
        if user.status == "blocked":
            logger.warning(f"المستخدم محظور: {user.email}")
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
        
        if user.account_type == "local":
            logger.info("التحقق من كلمة المرور")
            if not user.password or not security.verify_password(login_data.password, user.password):
                logger.warning("كلمة المرور غير صحيحة")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "status": 401,
                        "error": "Unauthorized",
                        "message": "كلمة المرور غير صحيحة",
                        "path": "/api/v1/auth/login",
                        "timestamp": get_current_timestamp()
                    }
                )
        
        logger.info("توليد التوكن للمستخدم")
        return generate_user_tokens(user, db)
        
    except Exception as e:
        logger.error(f"خطأ في تسجيل الدخول: {str(e)}")
        raise


def handle_google_login(google_request, db: Session) -> Token:
    """معالجة تسجيل الدخول بـ Google"""
    
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


@router.post("/register", response_model=Token, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def unified_register(
    fname: str = Form(..., description="الاسم الأول"),
    lname: str = Form(..., description="الاسم الأخير"), 
    email: str = Form(..., description="البريد الإلكتروني"),
    phone_number: str = Form(..., description="رقم الهاتف"),
    password: str = Form(..., description="كلمة المرور"),
    user_type: str = Form(..., description="نوع المستخدم (student/academy)"),
    avatar: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db)
) -> Any:
    """
    
    
    """
    
    try:
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
        
        
        registration_data = {
            "fname": fname.strip(),
            "lname": lname.strip(),
            "email": email.strip().lower(),
            "phone_number": phone_number.strip(),
            "password": password,
            "password_confirm": password,
            "user_type": user_type_clean  # استخدام القيمة المنظفة
        }
        
        register_request = UnifiedRegister(**registration_data)
        user_tokens = await RegistrationService.register_local_user(register_request, db, avatar)
        
        return user_tokens
        
    except HTTPException:
        raise
    except ValidationError as ve:
        error_message = "البيانات المُدخلة غير صحيحة"
        
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
            detail=create_unified_error_response(
                status_code=422,
                error_code="validation_error",
                message=error_message,
                path="/api/v1/auth/register",
                extra_data={"errors": validation_errors}
            )
        )
    except Exception as e:
        import traceback
        error_details = {
            "error": "registration_failed",
            "message": "فشل في التسجيل، يرجى المحاولة مرة أخرى",
            "status_code": 500,
            "details": str(e),
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc(),
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


@router.post("/logout", response_model=None, tags=["Authentication"])
def logout(request: Request, current_user = Depends(get_current_user)) -> dict:
    """تسجيل الخروج وإبطال التوكن (على المستوى الأمامي فقط)"""

    response = {
        "status": "success",
        "status_code": 200,
        "error_type": None,
        "message": "تم تسجيل الخروج بنجاح",
        "data": {
            "logged_out_at": get_current_timestamp(),
            "user_id": current_user.id,
            "tokens_invalidated": True
        },
        "path": str(request.url.path),
        "timestamp": get_current_timestamp()
    }
    return response


@router.post("/refresh", response_model=Token, response_model_exclude_none=True, tags=["Authentication"])
def refresh(current_user = Depends(get_current_user)) -> Any:
    """تحديث الرمز المميز"""
    
    return generate_user_tokens(current_user, None)


 
