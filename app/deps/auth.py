from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.core import security
from app.core.config import settings
from app.deps.database import get_db
from app.models.user import User
from app.models.admin import Admin
from app.models.academy import AcademyUser
from app.models.student import Student

security_scheme = HTTPBearer()


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
        payload = security.decode_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": 401,
                    "error": "Unauthorized",
                    "message": "غير مخول للوصول",
                    "path": "/api/v1/auth/",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        user_id: int = int(payload.get("sub"))
        
        # البحث في User table أولاً
        user = db.query(User).filter(User.id == user_id).first()
            
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": 404,
                    "error": "Not Found",
                    "message": "المستخدم غير موجود",
                    "path": "/api/v1/auth/",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
        # التحقق من حالة المستخدم
        if user.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": 403,
                    "error": "Forbidden",
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
                    "error": "Forbidden",
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
                "error": "Unauthorized",
                "message": "رمز المصادقة غير صحيح",
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
) -> AcademyUser:
    """Get current academy user."""
    return await get_current_user(credentials, db)


async def get_current_student(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Student:
    """Get current student user."""
    return await get_current_user(credentials, db)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Optional[dict]:
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


def require_academy(current_user: AcademyUser = Depends(get_current_academy_user)) -> AcademyUser:
    """Require academy role."""
    return current_user


def require_student(current_user: Student = Depends(get_current_student)) -> Student:
    """Require student role."""
    return current_user 