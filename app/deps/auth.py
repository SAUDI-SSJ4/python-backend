from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.core import security
from app.core.config import settings
from app.deps.database import get_db
from app.models.admin import Admin
from app.models.academy import AcademyUser
from app.models.student import Student

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
    user_type: str = "student"
) -> Optional[dict]:
    """
    Get current user from JWT token.
    
    Args:
        credentials: Bearer token from request
        db: Database session
        user_type: Expected user type
        
    Returns:
        User object or raises HTTPException
    """
    token = credentials.credentials
    
    try:
        payload = security.decode_token(token, user_type)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id: int = int(payload.get("sub"))
        
        # Get user based on type
        if user_type == "admin":
            user = db.query(Admin).filter(Admin.id == user_id).first()
        elif user_type == "academy":
            user = db.query(AcademyUser).filter(AcademyUser.id == user_id).first()
        elif user_type == "student":
            user = db.query(Student).filter(Student.id == user_id).first()
        else:
            user = None
            
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        if hasattr(user, 'is_active') and not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
            
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Admin:
    """Get current admin user."""
    return await get_current_user(credentials, db, "admin")


async def get_current_academy_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> AcademyUser:
    """Get current academy user."""
    return await get_current_user(credentials, db, "academy")


async def get_current_student(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Student:
    """Get current student user."""
    return await get_current_user(credentials, db, "student")


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
        return await get_current_user(credentials, db, "student")
    except HTTPException:
        return None


def require_admin(current_user: Admin = Depends(get_current_admin)) -> Admin:
    """Require admin role."""
    if not current_user.is_superadmin and not current_user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def require_academy(current_user: AcademyUser = Depends(get_current_academy_user)) -> AcademyUser:
    """Require academy role."""
    return current_user


def require_student(current_user: Student = Depends(get_current_student)) -> Student:
    """Require student role."""
    return current_user 