from typing import Generator, Union, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core import security
from app.db.session import SessionLocal
from app.models.user import User, UserStatus, UserType

security_scheme = HTTPBearer()


def get_db() -> Generator:
    """Database dependency"""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": "unauthorized",
            "message": "Could not validate credentials",
            "status_code": 401
        },
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode token
        payload = security.decode_token(token)
        if not payload:
            raise credentials_exception
            
        user_id = payload.get("user_id")
        if not user_id:
            raise credentials_exception
            
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise credentials_exception
            
        # Check if user is active
        if user.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "account_blocked",
                    "message": "الحساب محظور",
                    "status_code": 403
                }
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception:
        raise credentials_exception


def get_current_student(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current authenticated student"""
    if current_user.user_type != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "access_denied",
                "message": "مطلوب حساب طالب للوصول لهذه الخدمة",
                "status_code": 403
            }
        )
    return current_user


def get_current_academy(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current authenticated academy user"""
    if current_user.user_type != "academy":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "access_denied",
                "message": "مطلوب حساب أكاديمية للوصول لهذه الخدمة",
                "status_code": 403
            }
        )
    return current_user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (verified and active)"""
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "account_not_active",
                "message": "الحساب غير مفعل، يرجى التحقق من البريد الإلكتروني أو رقم الهاتف",
                "status_code": 403
            }
        )
    
    if not current_user.verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "account_not_verified",
                "message": "الحساب غير محقق، يرجى إكمال عملية التحقق",
                "status_code": 403
            }
        )
    
    return current_user


def get_current_verified_student(
    current_user: User = Depends(get_current_student)
) -> User:
    """Get current verified student"""
    return get_current_active_user(current_user)


def get_current_verified_academy(
    current_user: User = Depends(get_current_academy)
) -> User:
    """Get current verified academy"""
    return get_current_active_user(current_user) 