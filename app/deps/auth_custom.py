from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime

from app.core import security
from app.core.config import settings
from app.deps.database import get_db
from app.models.user import User
from app.models.admin import Admin
from app.models.academy import AcademyUser, Academy
from app.models.student import Student
from sqlalchemy.orm import joinedload

# Custom HTTPBearer that doesn't auto-raise exceptions
custom_security_scheme = HTTPBearer(auto_error=False)


def create_auth_error_response(
    status_code: int,
    error_type: str,
    message: str,
    details: Optional[str] = None,
    path: str = "/api/v1/auth/"
) -> dict:
    """Create standardized authentication error response"""
    error_response = {
        "status": "error",
        "status_code": status_code,
        "error_type": error_type,
        "message": message,
        "data": None,
        "path": path,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        error_response["details"] = details
    
    return error_response


async def get_current_user_custom(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(custom_security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token with custom error handling.
    
    Args:
        request: FastAPI request object for path info
        credentials: Bearer token from request (optional)
        db: Database session
        
    Returns:
        User object or raises HTTPException with clear error message
    """
    path = request.url.path if request else "/api/v1/auth/"
    
    # Check if token is provided
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_auth_error_response(
                status_code=401,
                error_type="MISSING_TOKEN",
                message="الـ token مطلوب للوصول لهذا الرابط",
                details="يرجى إضافة Authorization header مع Bearer token",
                path=path
            )
        )
    
    token = credentials.credentials
    
    # Check if token is empty
    if not token or token.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_auth_error_response(
                status_code=401,
                error_type="EMPTY_TOKEN",
                message="الـ token فارغ",
                details="يرجى التأكد من إرسال token صحيح",
                path=path
            )
        )
    
    try:
        # Try different secret keys to get user type first
        payload = None
        user_type = None
        used_secret = None
        
        # Try different secret keys to decode and get user type
        secret_keys_by_type = {
            "student": settings.STUDENT_SECRET_KEY,
            "academy": settings.ACADEMY_SECRET_KEY, 
            "admin": settings.ADMIN_SECRET_KEY,
            "default": settings.SECRET_KEY
        }
        
        for test_user_type, secret_key in secret_keys_by_type.items():
            try:
                test_payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
                user_type = test_payload.get("type", test_user_type)
                payload = test_payload
                used_secret = test_user_type
                break
            except jwt.JWTError:
                continue
        
        if payload is None:
            # Token is completely invalid
            error_detail = "الـ token غير صالح أو منتهي الصلاحية"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_auth_error_response(
                    status_code=401,
                    error_type="INVALID_TOKEN",
                    message="الـ token غير صالح أو منتهي الصلاحية",
                    details=error_detail,
                    path=path
                )
            )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp:
            current_time = datetime.utcnow().timestamp()
            if current_time > exp:
                error_detail = f"الـ token منتهي الصلاحية في {datetime.fromtimestamp(exp)}"
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=create_auth_error_response(
                        status_code=401,
                        error_type="TOKEN_EXPIRED",
                        message="الـ token منتهي الصلاحية",
                        details=error_detail,
                        path=path
                    )
                )
        
        user_id: int = int(payload.get("sub"))
        
        user = db.query(User).options(
            joinedload(User.student_profile),
            joinedload(User.academy_memberships).joinedload(AcademyUser.academy)
        ).filter(User.id == user_id).first()
            
        if user is None:
            error_detail = f"المستخدم مع ID {user_id} غير موجود في قاعدة البيانات"
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_auth_error_response(
                    status_code=404,
                    error_type="USER_NOT_FOUND",
                    message="المستخدم غير موجود",
                    details=error_detail,
                    path=path
                )
            )
            
        if user.status == "blocked":
            error_detail = "الحساب محظور من قبل الإدارة"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=create_auth_error_response(
                    status_code=403,
                    error_type="ACCOUNT_BLOCKED",
                    message="الحساب محظور",
                    details=error_detail,
                    path=path
                )
            )
        
        if user.status == "inactive":
            error_detail = "الحساب غير مفعل"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=create_auth_error_response(
                    status_code=403,
                    error_type="ACCOUNT_INACTIVE",
                    message="الحساب غير مفعل",
                    details=error_detail,
                    path=path
                )
            )
        
        return user
        
    except HTTPException:
        # Re-raise HTTP exceptions as they are already formatted
        raise
    except Exception as e:
        # Handle unexpected errors
        error_detail = f"خطأ غير متوقع في معالجة الـ token: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_auth_error_response(
                status_code=500,
                error_type="AUTHENTICATION_ERROR",
                message="خطأ في عملية المصادقة",
                details=error_detail,
                path=path
            )
        )


async def get_current_academy_user_custom(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(custom_security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current academy user with custom error handling."""
    path = request.url.path if request else "/api/v1/academy/"
    
    try:
        user = await get_current_user_custom(request, credentials, db)
        
        if user.user_type != "academy":
            error_detail = f"نوع المستخدم الحالي: {user.user_type}، المطلوب: academy"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=create_auth_error_response(
                    status_code=403,
                    error_type="WRONG_USER_TYPE",
                    message="هذا الحساب ليس حساب أكاديمية",
                    details=error_detail,
                    path=path
                )
            )
        
        # Load user with academy relationships to avoid lazy loading issues
        user_with_academy = db.query(User).options(
            joinedload(User.academy_memberships).joinedload(AcademyUser.academy)
        ).filter(User.id == user.id).first()
        
        if not user_with_academy or not user_with_academy.academy:
            error_detail = "المستخدم لا ينتمي لأي أكاديمية أو الأكاديمية غير موجودة"
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_auth_error_response(
                    status_code=404,
                    error_type="ACADEMY_NOT_FOUND",
                    message="لم يتم العثور على معلومات الأكاديمية",
                    details=error_detail,
                    path=path
                )
            )
        
        return user_with_academy
        
    except HTTPException:
        # Re-raise HTTP exceptions as they are already formatted
        raise
    except Exception as e:
        # Handle unexpected errors
        error_detail = f"خطأ غير متوقع في معالجة حساب الأكاديمية: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_auth_error_response(
                status_code=500,
                error_type="ACADEMY_AUTHENTICATION_ERROR",
                message="خطأ في عملية مصادقة الأكاديمية",
                details=error_detail,
                path=path
            )
        )


async def get_current_student_custom(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(custom_security_scheme),
    db: Session = Depends(get_db)
) -> Student:
    """Get current student user with custom error handling."""
    path = request.url.path if request else "/api/v1/student/"
    
    try:
        user = await get_current_user_custom(request, credentials, db)
        
        if user.user_type != "student":
            error_detail = f"نوع المستخدم الحالي: {user.user_type}، المطلوب: student"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=create_auth_error_response(
                    status_code=403,
                    error_type="WRONG_USER_TYPE",
                    message="هذا الحساب ليس حساب طالب",
                    details=error_detail,
                    path=path
                )
            )
        
        if not user.student_profile:
            error_detail = "لم يتم العثور على ملف الطالب"
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_auth_error_response(
                    status_code=404,
                    error_type="STUDENT_PROFILE_NOT_FOUND",
                    message="لم يتم العثور على ملف الطالب",
                    details=error_detail,
                    path=path
                )
            )
        
        return user.student_profile
        
    except HTTPException:
        # Re-raise HTTP exceptions as they are already formatted
        raise
    except Exception as e:
        # Handle unexpected errors
        error_detail = f"خطأ غير متوقع في معالجة حساب الطالب: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_auth_error_response(
                status_code=500,
                error_type="STUDENT_AUTHENTICATION_ERROR",
                message="خطأ في عملية مصادقة الطالب",
                details=error_detail,
                path=path
            )
        ) 