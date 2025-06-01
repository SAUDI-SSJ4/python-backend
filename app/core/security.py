from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = settings.ALGORITHM


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: timedelta = None,
    user_type: str = "student",
    additional_claims: dict = None
) -> str:
    """
    Create JWT access token for a user.
    
    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Token expiration time
        user_type: Type of user (admin, academy, student)
        additional_claims: Additional claims to include in token
        
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "exp": expire, 
        "sub": str(subject),
        "type": user_type
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    # Use different secret key based on user type
    secret_key = get_secret_key_by_type(user_type)
    
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    user_type: str = "student",
    expires_delta: timedelta = None
) -> str:
    """
    Create JWT refresh token for a user.
    
    Args:
        subject: The subject of the token (usually user ID)
        user_type: Type of user (admin, academy, student)
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT refresh token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": user_type,
        "refresh": True
    }
    
    # Use different secret key based on user type
    secret_key = get_secret_key_by_type(user_type)
    
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def get_secret_key_by_type(user_type: str) -> str:
    """
    Get the appropriate secret key based on user type.
    
    Args:
        user_type: Type of user (admin, academy, student)
        
    Returns:
        Secret key for the user type
    """
    if user_type == "admin":
        return settings.ADMIN_SECRET_KEY
    elif user_type == "academy":
        return settings.ACADEMY_SECRET_KEY
    elif user_type == "student":
        return settings.STUDENT_SECRET_KEY
    else:
        return settings.SECRET_KEY  # Default fallback


def decode_token(token: str, user_type: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token to decode
        user_type: Expected user type
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        secret_key = get_secret_key_by_type(user_type)
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        
        # Verify the token is for the correct user type
        if payload.get("type") != user_type:
            return None
            
        return payload
    except jwt.JWTError:
        return None 