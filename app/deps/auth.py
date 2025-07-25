from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.core import security
from app.core.config import settings
from app.deps.database import get_db
from app.models.user import User
from app.models.admin import Admin
from app.models.academy import AcademyUser, Academy
from app.models.student import Student
from sqlalchemy.orm import joinedload

security_scheme = HTTPBearer()
optional_security_scheme = HTTPBearer(auto_error=False)
optional_security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token.
    
    Args:
        credentials: Bearer token from request
        db: Database session
        
    Returns:
        User object or raises HTTPException
    """
    from datetime import datetime
    
    token = credentials.credentials
    
    try:
        # Try different secret keys to get user type first
        from jose import jwt
        
        payload = None
        user_type = None
        
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
                break
            except jwt.JWTError:
                continue
        
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": 401,
                    "error_type": "INVALID_TOKEN",
                    "message": "الـ token غير صالح أو منتهي الصلاحية",
                    "path": "/api/v1/auth/",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        user_id: int = int(payload.get("sub"))
        
        user = db.query(User).options(
            joinedload(User.student_profile),
            joinedload(User.academy_memberships).joinedload(AcademyUser.academy)
        ).filter(User.id == user_id).first()
            
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": 404,
                    "error_type": "USER_NOT_FOUND",
                    "message": "المستخدم غير موجود",
                    "path": "/api/v1/auth/",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
        if user.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": 403,
                    "error_type": "ACCOUNT_BLOCKED",
                    "message": "الحساب محظور",
                    "path": "/api/v1/auth/",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        if user.status == "inactive":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": 403,
                    "error_type": "ACCOUNT_INACTIVE",
                    "message": "الحساب غير مفعل",
                    "path": "/api/v1/auth/",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": 401,
                "error_type": "TOKEN_EXPIRED",
                "message": "الـ token منتهي الصلاحية أو غير صحيح",
                "path": "/api/v1/auth/",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Admin:
    """Get current admin user."""
    return await get_current_user(credentials, db)


async def get_current_academy_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current academy user with academy information."""
    user = await get_current_user(credentials, db)
    
    if user.user_type != "academy":
        from datetime import datetime
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": 403,
                "error_type": "WRONG_USER_TYPE",
                "message": "هذا الحساب ليس حساب أكاديمية",
                "path": "/api/v1/academy/",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    # Load user with academy relationships to avoid lazy loading issues
    user_with_academy = db.query(User).options(
        joinedload(User.academy_memberships).joinedload(AcademyUser.academy)
    ).filter(User.id == user.id).first()
    
    if not user_with_academy or not user_with_academy.academy:
        from datetime import datetime
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "status": 404,
                "error_type": "ACADEMY_NOT_FOUND",
                "message": "لم يتم العثور على معلومات الأكاديمية",
                "path": "/api/v1/academy/",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    return user_with_academy


async def get_current_student(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Student:
    """Get current student user."""
    user = await get_current_user(credentials, db)
    
    if user.user_type != "student":
        from datetime import datetime
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": 403,
                "error_type": "WRONG_USER_TYPE",
                "message": "هذا الحساب ليس حساب طالب",
                "path": "/api/v1/student/",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    if not user.student_profile:
        from datetime import datetime
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "status": 404,
                "error_type": "STUDENT_PROFILE_NOT_FOUND",
                "message": "لم يتم العثور على ملف الطالب",
                "path": "/api/v1/student/",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    return user.student_profile


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if token is provided, otherwise return None.
    Used for endpoints that work for both authenticated and guest users.
    """
    if not credentials:
        return None
        
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_current_academy_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current academy user if token is provided, otherwise return None.
    Only returns academy users, not students or admins.
    Used for endpoints that work for both teachers and students.
    """
    if not credentials:
        return None
        
    try:
        user = await get_current_user(credentials, db)
        # Only return academy users
        if user.user_type in ["academy", "admin"]:
            return user
        return None
    except HTTPException:
        return None


def require_admin(current_user: Admin = Depends(get_current_admin)) -> Admin:
    """Require admin role."""
    from datetime import datetime
    
    if not current_user.is_superadmin and not current_user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": 403,
                "error": "Forbidden",
                "message": "صلاحيات غير كافية",
                "path": "/api/v1/auth/",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    return current_user


def require_academy(current_user: User = Depends(get_current_academy_user)) -> User:
    """Require academy role."""
    return current_user


def require_student(current_user: Student = Depends(get_current_student)) -> Student:
    """Require student role."""
    return current_user 