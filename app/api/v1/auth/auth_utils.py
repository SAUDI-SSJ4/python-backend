"""
Authentication Utility Functions
===============================
Helper functions for authentication operations
"""

from datetime import timedelta, datetime
from typing import Any, Dict, Optional, List, Tuple
from sqlalchemy.orm import Session
import random
import string
import secrets

from app.core import security
from app.schemas.auth import Token
from app.models.user import User
from app.models.student import Student
from app.models.academy import Academy, AcademyUser, AcademyStatus, TrialStatus
from app.models.otp import OTP, OTPPurpose
from app.services.email_service import email_service

_verification_tokens: Dict[str, Dict] = {}

def get_current_timestamp():
    """Helper function to get current timestamp"""
    return datetime.utcnow().isoformat()


def create_unified_error_response(
    status_code: int = 400,
    error_type: str = "خطأ",
    message: str = "فشل الطلب",
    path: str = "/api/v1/auth/",
    validation_errors: Optional[Dict] = None,
    required_fields: Optional[Dict] = None,
    examples: Optional[Dict] = None,
    error_code: Optional[str] = None,
    extra_data: Optional[Dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    إنشاء استجابة خطأ موحدة بنفس تنسيق ملف error
    """
    
    response = {
        "status": "error",
        "status_code": status_code,
        "error_type": error_code or error_type,
        "message": message,
        "data": extra_data,
        "path": path,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return response


def create_unified_success_response(
    data: Any = None,
    message: str = "تم الطلب بنجاح",
    status_code: int = 200,
    path: str | None = None
) -> Dict:
    """إنشاء استجابة نجاح موحدة"""
    if isinstance(data, Token):
        return data

    return {
        "status": "success",
        "status_code": status_code,
        "error_type": None,
        "message": message,
        "data": data,
        "path": path,
        "timestamp": get_current_timestamp()
    }


def create_validation_error_response(missing_fields: List[str] = None, invalid_fields: List[Dict] = None) -> Dict:
    """   validation """
    return {
        "missing_fields": missing_fields or [],
        "invalid_fields": invalid_fields or []
    }


def generate_academy_id(name: str) -> str:
    """إنشاء معرف أكاديمية فريد"""
    clean_name = "".join(c.lower() for c in name if c.isalnum() or c.isspace()).replace(" ", "_")
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{clean_name}_{suffix}"


def generate_academy_slug(academy_name: str) -> str:
    """ slug """
    import re
    
    slug = academy_name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{slug}-{suffix}"


def generate_academy_username(academy_name: str) -> str:
    """إنشاء اسم مستخدم للأكاديمية"""
    import re
    
    username = academy_name.lower()
    username = re.sub(r'[^a-z0-9\s_]', '', username)
    username = re.sub(r'\s+', '_', username)
    username = re.sub(r'_+', '_', username)
    username = username.strip('_')
    
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{username}_{suffix}"


def create_student_profile(user: User, register_data: Any, db: Session):
    """  """
    gender = register_data.gender if register_data.gender else None
    
    student_profile = Student(
        user_id=user.id,
        birth_date=register_data.birth_date.date() if register_data.birth_date else None,
        gender=gender
    )
    
    db.add(student_profile)
    db.commit()


def create_academy_profile(user: User, register_data: Any, db: Session):
    """إنشاء ملف الأكاديمية"""
    academy_name = getattr(register_data, 'academy_name', None) or f"{user.fname} {user.lname} Academy"
    academy_about = getattr(register_data, 'academy_about', None)
    
    academy_profile = Academy(
        name=academy_name,
        about=academy_about,
        email=user.email,
        phone=user.phone_number,
        slug=generate_academy_slug(academy_name),
        status=AcademyStatus.ACTIVE.value,
        trial_status=TrialStatus.AVAILABLE.value
    )
    
    db.add(academy_profile)
    db.commit()
    db.refresh(academy_profile)
    
    # إنشاء علاقة المستخدم مع الأكاديمية كمالك
    academy_user = AcademyUser(
        academy_id=academy_profile.id,
        user_id=user.id,
        user_role="owner",
        is_active=True
    )
    
    db.add(academy_user)
    db.commit()


def send_verification_otp(user: User, db: Session):
    """     """
    try:
        db.query(OTP).filter(
            OTP.user_id == user.id,
            OTP.purpose == OTPPurpose.EMAIL_VERIFICATION,
            OTP.is_used == False
        ).delete()
        
        otp_code = ''.join(random.choices(string.digits, k=6))
        expires_at = datetime.utcnow() + timedelta(minutes=15)
        
        otp_record = OTP(
            user_id=user.id,
            code=otp_code,
            purpose=OTPPurpose.EMAIL_VERIFICATION,
            expires_at=expires_at,
            attempts=0,
            is_used=False
        )
        
        db.add(otp_record)
        db.commit()
        
        user_name = f"{user.fname} {user.lname}"
        success = email_service.send_otp_email(
            to_email=user.email,
            user_name=user_name,
            otp_code=otp_code,
            purpose=OTPPurpose.EMAIL_VERIFICATION.value
        )
        
        return success
        
    except Exception as e:
        return False


def generate_user_tokens(user: User, db: Session) -> Token:
    """إنشاء JWT tokens للمستخدم"""
    token_data = {
        "user_id": user.id,
        "user_type": user.user_type,
        "email": user.email
    }
    
    access_token = security.create_access_token(
        subject=token_data["user_id"],
        user_type=token_data["user_type"],
        additional_claims={"email": token_data["email"]}
    )
    refresh_token = security.create_refresh_token(
        subject=token_data["user_id"],
        user_type=token_data["user_type"]
    )
    
    user_data = {
        "id": user.id,
        "email": user.email,
        "fname": user.fname,
        "lname": user.lname,
        "user_type": user.user_type,
        "account_type": user.account_type,
        "verified": user.verified,
        "status": user.status,
        "avatar": user.avatar
    }
    
    if user.user_type == "student":
        user_data["profile_type"] = "student"
    elif user.user_type == "academy":
        user_data["profile_type"] = "academy"
    
    return create_unified_success_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_type": user.user_type,
            "user_data": user_data
        },
        message="أهلاً بك" if not user.is_verified else "تم تسجيل الدخول بنجاح",
        status_code=201,
        path="/api/v1/auth/login"
    )


def generate_verification_token(user_id: int, email: str, purpose: str = "password_reset", expires_in_minutes: int = 5) -> str:
    """إنشاء توكن مؤقت للتحقق من العمليات الحساسة (مثل إعادة تعيين كلمة المرور)"""
    from datetime import datetime, timedelta
    import secrets
    
    token = f"ver_{secrets.token_hex(16)}"
    
    expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
    
    _verification_tokens[token] = {
        "user_id": user_id,
        "email": email,
        "purpose": purpose,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at
    }
    
    return token


def verify_verification_token(token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """التحقق من verification token"""
    
    if token not in _verification_tokens:
        return False, None, "التوكن غير صحيح"
    
    token_data = _verification_tokens[token]
    
    if datetime.utcnow() > token_data["expires_at"]:
        del _verification_tokens[token]
        return False, None, "انتهت صلاحية التوكن"
    
    return True, token_data, None


def invalidate_verification_token(token: str) -> bool:
    """ verification token  """
    if token in _verification_tokens:
        del _verification_tokens[token]
        return True
    return False


def cleanup_expired_verification_tokens():
    """تنظيف التوكنات المنتهية الصلاحية"""
    current_time = datetime.utcnow()
    expired_tokens = [
        token for token, data in _verification_tokens.items() 
        if current_time > data["expires_at"]
    ]
    
    for token in expired_tokens:
        del _verification_tokens[token]
    
    return len(expired_tokens) 
