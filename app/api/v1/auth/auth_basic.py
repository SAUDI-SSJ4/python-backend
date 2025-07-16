"""
Basic Authentication Endpoints
==============================
Login, Register, and Logout functionality with automatic cart merging
"""

from typing import Any, Union, Optional, Dict
import os
from fastapi import APIRouter, Depends, HTTPException, status, Body, Form, UploadFile, File, Request, Header
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import ValidationError, Field
import logging

from app.core import security
from app.deps import get_db, get_current_user
from app.deps.auth import security_scheme
from app.schemas import (
    Token,
    UnifiedLogin,
    UnifiedRegister,
    MessageResponse,
    GoogleLoginRequest,
    GoogleRegisterRequest,
    RefreshTokenRequest
)
from app.models.user import User
from app.services.cart_service import CartService
from .auth_utils import (
    get_current_timestamp,
    generate_user_tokens,
    create_unified_error_response
)
from .registration_service import RegistrationService
from app.services.google_auth_service import GoogleAuthService

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=Token, response_model_exclude_none=True, tags=["Authentication"])
async def unified_login(
    request: Request,
    db: Session = Depends(get_db),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    """
    Unified login with automatic cart merging - supports Form Data and JSON
    
    Can use Form Data for ease:
    - email: Email address
    - password: Password
    - user_type: User type (optional - will be auto-detected)
    
    Or JSON in body for backward compatibility
    
    Automatically merges guest cart items to student cart upon login
    """
    
    try:
        # Check content type
        content_type = request.headers.get("content-type", "").lower()
        
        # Parse request body based on content type
        if "application/json" in content_type:
            # JSON request
            body = await request.json()
            merged_data = {
                "email": body.get("email"),
                "password": body.get("password"),
                "user_type": body.get("user_type"),
                "phone": body.get("phone"),
                "google_token": body.get("google_token")
            }
        else:
            # Form data request
            form = await request.form()
            merged_data = {
                "email": form.get("email"),
                "password": form.get("password"),
                "user_type": form.get("user_type"),
                "phone": form.get("phone"),
                "google_token": form.get("google_token")
            }
            
        # Remove None values
        merged_data = {k: v for k, v in merged_data.items() if v is not None}
        
        # Ensure required data exists
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
        
        # Distinguish between regular login and Google OAuth
        if "google_token" in merged_data and merged_data["google_token"]:
            # Google OAuth login
            google_request = GoogleLoginRequest(**merged_data)
            return await handle_google_login(google_request, db, the_cookie)
        else:
            # Local login - add user_type if not present
            if "user_type" not in merged_data:
                # Auto-detect user and determine type
                return await handle_auto_detect_login(merged_data, db, the_cookie)
            else:
                # Regular login with specified type
                login_data = UnifiedLogin(**merged_data)
                return await handle_local_login(login_data, db, the_cookie)
            
    except ValidationError as ve:
        # Improve error message for clarity
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


async def handle_auto_detect_login(body: dict, db: Session, cookie_id: Optional[str] = None) -> Token:
    """Login with automatic user type detection and cart merging"""
    
    # Check for required fields
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
    
    # Search for user
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
    
    # Verify password
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
    
    # Check account status
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
    
    # Generate tokens without cart merge
    return generate_user_tokens(user, db)


async def handle_local_login(login_data: UnifiedLogin, db: Session, cookie_id: Optional[str] = None) -> Token:
    """Handle local login with cart merging"""
    
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
        
        # Generate tokens without cart merge
        return generate_user_tokens(user, db)
        
    except Exception as e:
        logger.error(f"خطأ في تسجيل الدخول: {str(e)}")
        raise


async def handle_google_login(google_request, db: Session, cookie_id: Optional[str] = None) -> Token:
    """Handle Google login with cart merging"""
    
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
    
    # Generate tokens without cart merge
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
def logout(
    request: Request, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> dict:
    
    try:
        # Extract token from credentials
        token = credentials.credentials
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Decode token to get JTI and expiration
        from app.core import security
        from jose import jwt
        
        # Try to decode token to get JTI
        token_jti = None
        token_exp = None
        
        # Try different user types to decode the token
        for user_type in ["student", "academy", "admin"]:
            try:
                payload = security.decode_token(token, user_type, db)
                if payload:
                    token_jti = payload.get("jti")
                    token_exp = payload.get("exp")
                    break
            except Exception:
                continue
        
        # If we have JTI, add token to blacklist
        if token_jti and token_exp:
            from datetime import datetime
            expires_at = datetime.utcfromtimestamp(token_exp)
            
            # Add token to blacklist
            security.blacklist_token(
                db=db,
                token_jti=token_jti,
                user_id=current_user.id,
                user_type=current_user.user_type,
                expires_at=expires_at,
                token_type="access",
                reason="logout",
                ip_address=client_ip,
                user_agent=user_agent
            )
            
            tokens_invalidated = True
        else:
            tokens_invalidated = False

        response = {
            "status": "success",
            "status_code": 200,
            "error_type": None,
            "message": "تم تسجيل الخروج بنجاح وإبطال التوكن",
            "data": {
                "logged_out_at": get_current_timestamp(),
                "user_id": current_user.id,
                "tokens_invalidated": tokens_invalidated,
                "logout_method": "server_side_blacklist"
            },
            "path": str(request.url.path),
            "timestamp": get_current_timestamp()
        }
        return response
        
    except Exception as e:
        # Fallback to basic logout if blacklist fails
        response = {
            "status": "success",
            "status_code": 200,
            "error_type": None,
            "message": "تم تسجيل الخروج بنجاح (وضع الطوارئ)",
            "data": {
                "logged_out_at": get_current_timestamp(),
                "user_id": current_user.id,
                "tokens_invalidated": False,
                "logout_method": "fallback",
                "error": str(e)
            },
            "path": str(request.url.path),
            "timestamp": get_current_timestamp()
        }
        return response


@router.post("/refresh", response_model=Token, response_model_exclude_none=True, tags=["Authentication"])
async def refresh(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """تحديث الرمز المميز باستخدام refresh_token - يدعم JSON و Form Data"""
    
    try:
        # استخراج refresh_token من Request (JSON أو Form Data)
        content_type = request.headers.get("content-type", "").lower()
        refresh_token = None
        
        if "application/json" in content_type:
            # JSON request
            body = await request.json()
            refresh_token = body.get("refresh_token")
        else:
            # Form data request
            form = await request.form()
            refresh_token = form.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "status_code": 400,
                    "error_type": "Missing Data",
                    "message": "refresh_token مطلوب إما عبر JSON أو Form Data",
                    "path": "/api/v1/auth/refresh",
                    "timestamp": get_current_timestamp()
                }
            )
        
        # فك تشفير refresh_token وتحديد نوع المستخدم
        refresh_payload = None
        user_type = None
        
        # تجربة فك التشفير مع جميع أنواع المستخدمين
        for utype in ["student", "academy", "admin"]:
            try:
                payload = security.decode_token(refresh_token, utype, db)
                if payload and payload.get("refresh"):
                    refresh_payload = payload
                    user_type = utype
                    break
            except Exception:
                continue
        
        if not refresh_payload or not user_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "status_code": 401,
                    "error_type": "Invalid Token",
                    "message": "refresh_token غير صالح أو منتهي الصلاحية",
                    "path": "/api/v1/auth/refresh",
                    "timestamp": get_current_timestamp()
                }
            )
        
        # استخراج معلومات المستخدم من التوكن
        user_id = refresh_payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "status_code": 401,
                    "error_type": "Invalid Token",
                    "message": "معلومات المستخدم غير موجودة في التوكن",
                    "path": "/api/v1/auth/refresh",
                    "timestamp": get_current_timestamp()
                }
            )
        
        # البحث عن المستخدم في قاعدة البيانات
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "status_code": 401,
                    "error_type": "User Not Found",
                    "message": "المستخدم غير موجود",
                    "path": "/api/v1/auth/refresh",
                    "timestamp": get_current_timestamp()
                }
            )
        
        # التحقق من حالة المستخدم
        if user.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "error",
                    "status_code": 403,
                    "error_type": "Account Blocked",
                    "message": "الحساب محظور",
                    "path": "/api/v1/auth/refresh",
                    "timestamp": get_current_timestamp()
                }
            )
        
        if user.status == "inactive":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "error",
                    "status_code": 403,
                    "error_type": "Account Inactive",
                    "message": "الحساب غير نشط",
                    "path": "/api/v1/auth/refresh",
                    "timestamp": get_current_timestamp()
                }
            )
        
        # التحقق من تطابق نوع المستخدم
        if user.user_type != user_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "status_code": 401,
                    "error_type": "User Type Mismatch",
                    "message": "نوع المستخدم غير متطابق",
                    "path": "/api/v1/auth/refresh",
                    "timestamp": get_current_timestamp()
                }
            )
        
        # توليد tokens جديدة
        return generate_user_tokens(user, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطأ في تحديث التوكن: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "status_code": 500,
                "error_type": "Server Error",
                "message": "خطأ داخلي في الخادم",
                "path": "/api/v1/auth/refresh",
                "timestamp": get_current_timestamp()
            }
        )


 
