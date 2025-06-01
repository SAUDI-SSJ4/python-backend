from typing import Generator, Union, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core import security
from app.db.session import SessionLocal
from app.models.student import Student, StudentStatus
from app.models.academy import AcademyUser
from app.models.admin import Admin

security_scheme = HTTPBearer()


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def validate_user_status(user: Union[Student, AcademyUser, Admin], user_type: str) -> bool:
    """Validate if user account is active"""
    if user_type == "student":
        return user.status == StudentStatus.ACTIVE
    elif user_type in ["academy", "admin"]:
        return getattr(user, 'is_active', True)
    return False


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> tuple[Union[Student, AcademyUser, Admin], str]:
    """Get current authenticated user from JWT token"""
    
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Try to decode token for each user type
        for user_type in ["student", "academy", "admin"]:
            payload = security.decode_token(token, user_type)
            if payload:
                user_id = int(payload.get("sub"))
                
                if user_type == "student":
                    user = db.query(Student).filter(Student.id == user_id).first()
                elif user_type == "academy":
                    user = db.query(AcademyUser).filter(AcademyUser.id == user_id).first()
                elif user_type == "admin":
                    user = db.query(Admin).filter(Admin.id == user_id).first()
                
                if user and validate_user_status(user, user_type):
                    return user, user_type
        
        raise credentials_exception
        
    except Exception:
        raise credentials_exception


async def get_current_student(
    current_user_data: tuple = Depends(get_current_user)
) -> Student:
    """Get current authenticated student"""
    user, user_type = current_user_data
    if user_type != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Student access required."
        )
    return user


async def get_current_academy(
    current_user_data: tuple = Depends(get_current_user)
) -> AcademyUser:
    """Get current authenticated academy user"""
    user, user_type = current_user_data
    if user_type != "academy":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Academy access required."
        )
    return user


async def get_current_admin(
    current_user_data: tuple = Depends(get_current_user)
) -> Admin:
    """Get current authenticated admin"""
    user, user_type = current_user_data
    if user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin access required."
        )
    return user


async def get_current_academy_owner(
    current_user: AcademyUser = Depends(get_current_academy)
) -> AcademyUser:
    """Get current authenticated academy owner"""
    if not getattr(current_user, 'is_owner', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Academy owner access required."
        )
    return current_user 