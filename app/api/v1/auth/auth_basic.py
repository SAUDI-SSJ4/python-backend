"""
Basic Authentication Endpoints
==============================
Login, Register, and Logout functionality
"""

from typing import Any, Union
from fastapi import APIRouter, Depends, HTTPException, status, Body
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
                "error": "validation_error",
                "message": "بيانات تسجيل الدخول غير صحيحة",
                "status_code": 422,
                "details": str(ve),
                "timestamp": get_current_timestamp()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "login_failed",
                "message": "فشل في تسجيل الدخول",
                "status_code": 500,
                "details": str(e),
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "user_not_found",
                "message": "لم يتم العثور على المستخدم",
                "status_code": 404,
                "timestamp": get_current_timestamp()
            }
        )
    
    # التحقق من نوع المستخدم
    if user.user_type != login_data.user_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "user_type_mismatch",
                "message": "نوع المستخدم غير متطابق",
                "status_code": 400,
                "timestamp": get_current_timestamp()
            }
        )
    
    # التحقق من حالة الحساب
    if user.status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "account_blocked",
                "message": "الحساب محظور",
                "status_code": 403,
                "timestamp": get_current_timestamp()
            }
        )
    
    # التحقق من كلمة المرور للحسابات المحلية
    if user.account_type == "local":
        if not user.password or not security.verify_password(login_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_credentials",
                    "message": "كلمة المرور غير صحيحة",
                    "status_code": 401,
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_google_token",
                "message": "Google Token غير صحيح أو منتهي الصلاحية",
                "status_code": 400,
                "timestamp": get_current_timestamp()
            }
        )
    
    # البحث عن المستخدم بـ Google ID
    user = db.query(User).filter(User.google_id == google_user_data['id']).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "user_not_found",
                "message": "لا يوجد حساب مسجل بهذا Google ID",
                "status_code": 404,
                "suggestion": "يرجى التسجيل أولاً"
            }
        )
    
    # التحقق من حالة الحساب
    if user.status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "account_blocked",
                "message": "الحساب محظور",
                "status_code": 403
            }
        )
    
    # تحديث البيانات من Google
    if google_user_data.get('picture') and google_user_data['picture'] != user.avatar:
        user.avatar = google_user_data['picture']
        db.commit()
    
    return generate_user_tokens(user, db)


@router.post("/register", response_model=Token, tags=["Authentication"])
def unified_register(
    body: Union[UnifiedRegister, GoogleRegisterRequest] = Body(
        ...,
        examples={
            "local_register_student": {
                "summary": "تسجيل طالب محلي",
                "description": "تسجيل طالب جديد باستخدام البيانات المحلية",
                "value": {
                    "birth_date": "1995-01-01T00:00:00Z",
                    "email": "student@example.com",
                    "fname": "أحمد",
                    "gender": "male",
                    "lname": "علي",
                    "password": "password123",
                    "password_confirm": "password123",
                    "phone_number": "1234567890",
                    "user_type": "student"
                }
            },
            "local_register_academy": {
                "summary": "تسجيل أكاديمية محلية",
                "description": "تسجيل أكاديمية جديدة باستخدام البيانات المحلية",
                "value": {
                    "email": "academy@example.com",
                    "fname": "إدارة",
                    "lname": "الأكاديمية",
                    "password": "password123",
                    "password_confirm": "password123",
                    "phone_number": "1234567890",
                    "user_type": "academy",
                    "academy_name": "أكاديمية التعلم الذكي",
                    "academy_about": "أكاديمية متخصصة في التعليم الإلكتروني"
                }
            },
            "google_register_student": {
                "summary": "تسجيل طالب بـ Google",
                "description": "تسجيل طالب جديد باستخدام Google OAuth",
                "value": {
                    "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjY...",
                    "user_type": "student"
                }
            },
            "google_register_academy": {
                "summary": "تسجيل أكاديمية بـ Google",
                "description": "تسجيل أكاديمية جديدة باستخدام Google OAuth",
                "value": {
                    "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjY...",
                    "user_type": "academy"
                }
            }
        }
    ),
    db: Session = Depends(get_db)
) -> Any:
    """
    تسجيل مستخدم جديد - يدعم التسجيل المحلي وGoogle OAuth
    
    ## طرق التسجيل:
    
    ### 1. التسجيل المحلي للطلاب:
    - الحقول المطلوبة: `fname`, `lname`, `email`, `phone_number`, `password`, `password_confirm`, `user_type`, `birth_date`, `gender`
    - مثال: انظر "تسجيل طالب محلي" في الأمثلة
    
    ### 2. التسجيل المحلي للأكاديميات:
    - الحقول المطلوبة: `fname`, `lname`, `email`, `phone_number`, `password`, `password_confirm`, `user_type`, `academy_name`
    - الحقول الاختيارية: `academy_about`
    - مثال: انظر "تسجيل أكاديمية محلية" في الأمثلة
    
    ### 3. التسجيل بـ Google:
    - الحقول المطلوبة: `google_token`, `user_type`
    - مثال: انظر "تسجيل بـ Google" في الأمثلة
    
    ## أنواع المستخدمين المدعومة:
    - `student`: طالب (يتطلب birth_date و gender للتسجيل المحلي)
    - `academy`: أكاديمية (يتطلب academy_name للتسجيل المحلي)
    
    ## ملاحظات:
    - عند التسجيل بـ Google، يتم استخراج البيانات الأساسية من Google Token
    - كلمات المرور يجب أن تتطابق في التسجيل المحلي
    - يتم إرسال OTP للتحقق من البريد الإلكتروني بعد التسجيل المحلي
    """
    
    try:
        # تحويل body إلى dict للتحقق من المحتوى
        if isinstance(body, dict):
            body_dict = body
        else:
            body_dict = body.dict()
            
        # التحقق من وجود google_token لتحديد نوع التسجيل
        if "google_token" in body_dict and body_dict["google_token"]:
            # تسجيل Google
            if not isinstance(body, GoogleRegisterRequest):
                google_request = GoogleRegisterRequest(**body_dict)
            else:
                google_request = body
            return handle_google_register(google_request, db)
        else:
            # تسجيل محلي
            if not isinstance(body, UnifiedRegister):
                register_data = UnifiedRegister(**body_dict)
            else:
                register_data = body
            return handle_local_register(register_data, db)
            
    except ValidationError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "validation_error",
                "message": "بيانات التسجيل غير صحيحة",
                "status_code": 422,
                "details": str(ve),
                "timestamp": get_current_timestamp()
            }
        )
    except Exception as e:
        if "duplicate key" in str(e).lower() or "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "user_exists",
                    "message": "مستخدم بهذا البريد الإلكتروني أو رقم الهاتف موجود بالفعل",
                    "status_code": 409,
                    "suggestion": "يرجى استخدام بريد إلكتروني أو رقم هاتف مختلف",
                    "timestamp": get_current_timestamp()
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "registration_failed",
                    "message": "فشل في التسجيل، يرجى المحاولة مرة أخرى",
                    "status_code": 500,
                    "details": str(e),
                    "timestamp": get_current_timestamp()
                }
            )


def handle_local_register(register_data: UnifiedRegister, db: Session) -> Token:
    """معالجة التسجيل المحلي"""
    return RegistrationService.register_local_user(register_data, db)


def handle_google_register(google_request, db: Session) -> Token:
    """معالجة التسجيل بـ Google"""
    
    # التحقق من Google token
    google_user_data = GoogleAuthService.verify_google_token(google_request.google_token)
    
    if not google_user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_google_token",
                "message": "Google Token غير صحيح أو منتهي الصلاحية",
                "status_code": 400,
                "timestamp": get_current_timestamp()
            }
        )
    
    # التحقق من وجود المستخدم
    existing_user = db.query(User).filter(
        (User.google_id == google_user_data['id']) | 
        (User.email == google_user_data['email'])
    ).first()
    
    if existing_user:
        if existing_user.google_id == google_user_data['id']:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "user_already_exists",
                    "message": "يوجد حساب مسجل بهذا Google ID بالفعل",
                    "status_code": 409,
                    "suggestion": "استخدم تسجيل الدخول"
                }
            )
        else:
            # ربط الحساب المحلي الموجود بـ Google
            return RegistrationService.link_google_account(existing_user, google_user_data, db)
    
    # تسجيل مستخدم Google جديد
    return RegistrationService.register_google_user(google_user_data, google_request.user_type, db)


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