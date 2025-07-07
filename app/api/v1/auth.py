import logging
import random
import string
from datetime import timedelta, datetime
from typing import Any, Optional, Dict, Union
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import ValidationError

from app.core import security
from app.core.config import settings
from app.crud import student as crud_student
from app.deps import get_db
from app.services.auth_service import auth_service
from app.services.file_service import file_service
from app.schemas.auth import (
    StudentLogin,
    StudentRegister,
    AcademyRegister,
    Token,
    TokenRefresh,
    TokenData,
    OTPRequest,
    OTPVerify,
    PasswordResetRequest,
    PasswordReset,
    PasswordChange,
    MessageResponse,
    OTPResponse,
    OTPVerifyResponse,
    PasswordResetResponse,
    UserInfoResponse
)
from app.models.academy import AcademyUser, Academy
from app.models.admin import Admin
from app.models.student import Student, StudentStatus
from app.api.v1.auth.auth_utils import (
    create_unified_error_response,
    create_validation_error_response,
    generate_verification_token,
    verify_verification_token,
    invalidate_verification_token,
    create_unified_success_response
)
from app.schemas.base import BaseResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
security_scheme = HTTPBearer()

otp_storage: Dict[str, Dict[str, Any]] = {}

# Password reset tokens storage
reset_tokens: Dict[str, Dict[str, Any]] = {}


# ==================== Helper Functions ====================

def generate_otp() -> str:
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


def generate_reset_token() -> str:
    """Generate password reset token"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


def log_auth_attempt(request: Request, action: str, success: bool, user_data: dict = None):
    """Log authentication attempts for security monitoring"""
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")
    
    log_data = {
        "action": action,
        "success": success,
        "ip": client_ip,
        "user_agent": user_agent,
        "timestamp": datetime.utcnow(),
        "user_data": user_data or {}
    }
    
    if success:
        logger.info(f"AUTH_SUCCESS: {log_data}")
    else:
        logger.warning(f"AUTH_FAILED: {log_data}")


def get_user_by_email(db: Session, email: str) -> tuple[Optional[Union[Student, AcademyUser, Admin]], Optional[str]]:
    """Get user from any table by email"""
    
    # Check students
    student = db.query(Student).filter(Student.email == email).first()
    if student:
        return student, "student"
    
    # Check academies
    academy = db.query(AcademyUser).filter(AcademyUser.email == email).first()
    if academy:
        return academy, "academy"
    
    # Check admins
    admin = db.query(Admin).filter(Admin.email == email).first()
    if admin:
        return admin, "admin"
    
    return None, None


def get_user_by_phone(db: Session, phone: str) -> tuple[Optional[Union[Student, AcademyUser, Admin]], Optional[str]]:
    """Get user from any table by phone"""
    
    # Check students
    student = db.query(Student).filter(Student.phone == phone).first()
    if student:
        return student, "student"
    
    # Check academies  
    academy = db.query(AcademyUser).filter(AcademyUser.phone == phone).first()
    if academy:
        return academy, "academy"
    
    # Check admins
    admin = db.query(Admin).filter(Admin.phone == phone).first()
    if admin:
        return admin, "admin"
    
    return None, None


def validate_user_status(user: Union[Student, AcademyUser, Admin], user_type: str) -> bool:
    """Validate if user account is active"""
    if user_type == "student":
        return user.status == "active"
    elif user_type in ["academy", "admin"]:
        return getattr(user, 'is_active', True)
    return False


async def get_current_user_from_token(
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
                
                if user and auth_service.validate_user_status(user, user_type):
                    return user, user_type
        
        raise credentials_exception
        
    except Exception:
        raise credentials_exception


# ==================== Registration Endpoints ====================

# ==================== Authentication Endpoints ====================

@router.post("/login", response_model=BaseResponse, response_model_exclude_none=True)
async def login(
    *,
    db: Session = Depends(get_db),
    user_in: StudentLogin,
    request: Request
) -> Any:
    """
    Universal login for all user types (students, academies, admins)
    
    - **email**: User's email address
    - **password**: User's password
    
    The system automatically detects the user type and returns appropriate tokens.
    """
    
    client_ip = request.client.host
    
    # Check if IP is blocked (skip in debug mode for testing)
    if not settings.DEBUG and auth_service.is_ip_blocked(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please try again later."
        )
    
    try:
        # Authenticate user
        user, user_type = auth_service.authenticate_user(db, user_in.email, user_in.password)
        
        # Generate tokens
        tokens = auth_service.create_tokens(user.id, user_type)
        
        # Update last login (for students)
        if user_type == "student":
            user.last_login_at = datetime.utcnow()
            db.commit()
        
        # Clear failed attempts for this IP
        auth_service.clear_failed_attempts(client_ip)
        
        # Log successful login
        log_auth_attempt(request, "login", True, {"user_id": user.id, "email": user_in.email, "user_type": user_type})
        
        return create_unified_success_response(
            data=tokens,
            status_code=200,
            path="/api/v1/auth/login"
        )
        
    except HTTPException as e:
        auth_service.record_failed_attempt(client_ip)
        log_auth_attempt(request, "login", False, {"email": user_in.email, "error": str(e.detail)})
        raise
    except Exception as e:
        error_detail = str(e)
        logger.error(f"Login failed: {error_detail}")
        auth_service.record_failed_attempt(client_ip)
        log_auth_attempt(request, "login", False, {"email": user_in.email, "error": error_detail})
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


def _get_user_by_token(db: Session, token: str) -> tuple[Union[Student, AcademyUser, Admin], str]:
    """Helper function to get user from refresh token"""
    
    # Try to decode as each user type
    for user_type in ["student", "academy", "admin"]:
        payload = security.decode_token(token, user_type)
        if payload and payload.get("refresh"):
            user_id = payload.get("sub")
            
            if user_type == "student":
                user = crud_student.student.get(db, id=user_id)
            elif user_type == "academy":
                user = db.query(AcademyUser).filter(AcademyUser.id == user_id).first()
            elif user_type == "admin":
                user = db.query(Admin).filter(Admin.id == user_id).first()
            
            if user and auth_service.validate_user_status(user, user_type):
                return user, user_type
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    *,
    db: Session = Depends(get_db),
    token_data: TokenRefresh,
    request: Request
) -> Any:
    """
    Refresh access token using refresh token
    
    - **refresh_token**: Valid refresh token
    
    Returns new access and refresh tokens.
    """
    
    try:
        user, user_type = _get_user_by_token(db, token_data.refresh_token)
        
        # Generate new tokens
        tokens = auth_service.create_tokens(user.id, user_type)
        
        # Log successful refresh
        log_auth_attempt(request, "refresh_token", True, {"user_id": user.id, "user_type": user_type})
        
        return tokens
        
    except HTTPException:
        log_auth_attempt(request, "refresh_token", False, {"error": "invalid_refresh_token"})
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        log_auth_attempt(request, "refresh_token", False, {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


# ==================== OTP Endpoints ====================

@router.post("/verify-otp", response_model=OTPVerifyResponse)
async def verify_otp(
    *,
    db: Session = Depends(get_db),
    otp_verify: OTPVerify,
    request: Request
) -> Any:
    """
    Verify OTP code
    
    - **phone**: Phone number
    - **otp**: 6-digit OTP code
    
    Verifies the OTP code sent to the phone number.
    """
    
    phone = otp_verify.phone.strip()
    
    try:
        # Verify OTP
        user_data = auth_service.verify_otp(phone, otp_verify.otp)
        
        # Update phone verification status
        if user_data["user_type"] == "student":
            user = db.query(Student).filter(Student.id == user_data["user_id"]).first()
            if user:
                user.phone_verified_at = datetime.utcnow()
                db.commit()
        
        # Log successful verification
        log_auth_attempt(request, "verify_otp", True, {"phone": phone, "user_type": user_data["user_type"]})
        
        return create_unified_success_response(
            data={
                "phone": phone,
                "verified": True
            },
            message="OTP verified successfully",
            status_code=200
        )
        
    except HTTPException:
        log_auth_attempt(request, "verify_otp", False, {"phone": phone, "error": "verification_failed"})
        raise
    except Exception as e:
        logger.error(f"OTP verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OTP verification failed"
        )


# ==================== Password Reset Endpoints ====================

@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    *,
    db: Session = Depends(get_db),
    request_data: PasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks
) -> Any:
    """
    Request password reset
    
    - **email**: User's email address
    
    Sends a password reset link to the user's email.
    """
    
    email = request_data.email.lower().strip()
    
    # Check if email exists
    user, user_type = auth_service.get_user_by_email(db, email)
    if not user:
        # Return success even if email doesn't exist (security best practice)
        log_auth_attempt(request, "forgot_password", False, {"email": email, "error": "email_not_found"})
        return create_unified_success_response(
            data={"email": email},
            message="إذا كان البريد الإلكتروني موجود، سيتم إرسال رمز إعادة التعيين",
            status_code=200,
            path=request.url.path
        )
    
    try:
        # Store reset token
        reset_token = auth_service.store_reset_token(email, user.id, user_type)
        
        # Send reset email in background
        background_tasks.add_task(auth_service.send_password_reset_email, email, reset_token)
        
        # Log successful request
        log_auth_attempt(request, "forgot_password", True, {"email": email, "user_type": user_type})
        
        resp_data = {"email": email}
        if settings.DEBUG:
            resp_data["reset_token"] = reset_token
        return create_unified_success_response(
            data=resp_data,
            message="تم إرسال رابط إعادة التعيين إلى بريدك الإلكتروني",
            status_code=200,
            path=request.url.path
        )
        
    except Exception as e:
        logger.error(f"Password reset request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request"
        )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    *,
    db: Session = Depends(get_db),
    reset_data: PasswordReset,
    request: Request
) -> Any:
    """
    Reset password using token
    
    - **token**: Password reset token received via email
    - **new_password**: New password (minimum 6 characters)
    - **confirm_password**: Confirm new password
    
    Resets the user's password using the provided token.
    """
    
    try:
        # Reset password using service
        auth_service.reset_password(db, reset_data.token, reset_data.new_password)
        
        # Log successful reset
        log_auth_attempt(request, "reset_password", True, {"token": reset_data.token[:8] + "..."})
        
        return create_unified_success_response(
            message="تم إعادة تعيين كلمة المرور بنجاح",
            status_code=200,
            path=request.url.path
        )
        
    except HTTPException:
        log_auth_attempt(request, "reset_password", False, {"error": "reset_failed"})
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


# ==================== Change Password Endpoint ====================

@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    *,
    db: Session = Depends(get_db),
    password_data: PasswordChange,
    request: Request,
    current_user_data: tuple = Depends(get_current_user_from_token)
) -> Any:
    """
    Change password for authenticated user
    
    - **old_password**: Current password
    - **new_password**: New password (minimum 6 characters)
    - **confirm_password**: Confirm new password
    
    Requires valid authentication token.
    """
    
    user, user_type = current_user_data
    
    try:
        # Change password using service
        auth_service.change_password(
            db, user, user_type, 
            password_data.old_password, 
            password_data.new_password
        )
        
        # Log successful change
        log_auth_attempt(request, "change_password", True, {"user_id": user.id, "user_type": user_type})
        
        return create_unified_success_response(
            message="تم تغيير كلمة المرور بنجاح",
            status_code=200,
            path=request.url.path
        )
        
    except HTTPException:
        log_auth_attempt(request, "change_password", False, {"user_id": user.id, "error": "change_failed"})
        raise
    except Exception as e:
        logger.error(f"Password change failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


# ==================== User Info Endpoint ====================

@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    *,
    db: Session = Depends(get_db),
    current_user_data: tuple = Depends(get_current_user_from_token)
) -> Any:
    """
    Get current authenticated user information
    
    Returns user profile information based on authentication token.
    """
    
    user, user_type = current_user_data
    
    try:
        # Build user info response based on user type
        user_info = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": getattr(user, 'phone', None),
            "user_type": user_type,
            "is_active": auth_service.validate_user_status(user, user_type),
            "profile_image_url": file_service.get_file_url(getattr(user, 'profile_image', '')) if getattr(user, 'profile_image', None) else None
        }
        
        # Add type-specific fields
        if user_type == "student":
            user_info.update({
                "date_of_birth": user.date_of_birth,
                "gender": user.gender,
                "country": user.country,
                "city": user.city,
                "status": user.status.value if user.status else None,
                "email_verified": bool(user.email_verified_at),
                "phone_verified": bool(user.phone_verified_at),
                "last_login": user.last_login_at
            })
        elif user_type == "academy":
            # Get academy info from Academy table
            academy = db.query(Academy).filter(Academy.id == user.academy_id).first()
            academy_logo_url = None
            academy_cover_url = None
            
            if academy:
                academy_logo_url = file_service.get_file_url(academy.logo) if academy.logo else None
                academy_cover_url = file_service.get_file_url(academy.cover) if academy.cover else None
            
            user_info.update({
                "academy_name": getattr(academy, 'name', None) if academy else None,
                "user_name": getattr(academy, 'user_name', None) if academy else None,
                "is_owner": getattr(user, 'is_owner', False),
                "country": getattr(academy, 'country', None) if academy else None,
                "city": getattr(academy, 'city', None) if academy else None,
                "logo_url": academy_logo_url,
                "cover_url": academy_cover_url
            })
        elif user_type == "admin":
            user_info.update({
                "role_id": getattr(user, 'role_id', None)
            })
        
        return {
            "message": "User information retrieved successfully",
            "user": user_info
        }
        
    except Exception as e:
        logger.error(f"Get user info failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )


# ==================== Logout Endpoint ====================

@router.post("/logout", response_model=MessageResponse)
async def logout(
    *,
    request: Request,
    current_user_data: tuple = Depends(get_current_user_from_token)
) -> Any:
    """
    Logout current user
    
    Logs out the current authenticated user. 
    Token invalidation is handled on the client side by removing stored tokens.
    """
    
    user, user_type = current_user_data
    
    # Log successful logout
    log_auth_attempt(request, "logout", True, {"user_id": user.id, "user_type": user_type})
    
    return {
        "message": "Logged out successfully"
    }


# ==================== Cleanup Task ====================

@router.post("/admin/cleanup-tokens", response_model=MessageResponse)
async def cleanup_expired_tokens(
    *,
    current_user: Admin = Depends(get_current_user_from_token)
) -> Any:
    """
    Admin endpoint to manually cleanup expired tokens
    """
    user, user_type = current_user
    if user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    auth_service.cleanup_expired_tokens()
    
    return {
        "message": "Expired tokens cleaned up successfully"
    }


# ==================== File Upload Endpoints ====================

@router.post("/academy/upload-logo", response_model=MessageResponse)
async def upload_academy_logo(
    *,
    db: Session = Depends(get_db),
    current_user_data: tuple = Depends(get_current_user_from_token),
    logo: UploadFile = File(..., description="شعار الأكاديمية (صورة)")
) -> Any:
    """
    
    
    """
    
    user, user_type = current_user_data
    
    if user_type != "academy":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه الميزة متاحة للأكاديميات فقط"
        )
    
    try:
        academy = db.query(Academy).filter(Academy.id == user.academy_id).first()
        if not academy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الأكاديمية غير موجودة"
            )
        
        logo_path = await file_service.upload_academy_logo(logo, academy.id)
        
        academy.logo = logo_path
        db.commit()
        
        logger.info(f"Academy logo uploaded successfully: Academy ID {academy.id}")
        
        return {
            "message": "تم رفع شعار الأكاديمية بنجاح",
            "logo_url": file_service.get_file_url(logo_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Academy logo upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="فشل في رفع شعار الأكاديمية"
        )


@router.post("/academy/upload-cover", response_model=MessageResponse)
async def upload_academy_cover(
    *,
    db: Session = Depends(get_db),
    current_user_data: tuple = Depends(get_current_user_from_token),
    cover: UploadFile = File(..., description="غلاف الأكاديمية (صورة)")
) -> Any:
    """
    
    
    """
    
    user, user_type = current_user_data
    
    if user_type != "academy":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه الميزة متاحة للأكاديميات فقط"
        )
    
    try:
        academy = db.query(Academy).filter(Academy.id == user.academy_id).first()
        if not academy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الأكاديمية غير موجودة"
            )
        
        cover_path = await file_service.upload_academy_cover(cover, academy.id)
        
        academy.cover = cover_path
        db.commit()
        
        logger.info(f"Academy cover uploaded successfully: Academy ID {academy.id}")
        
        return {
            "message": "تم رفع غلاف الأكاديمية بنجاح",
            "cover_url": file_service.get_file_url(cover_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Academy cover upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="فشل في رفع غلاف الأكاديمية"
        )


@router.post("/upload-profile-image", response_model=MessageResponse)
async def upload_profile_image(
    *,
    db: Session = Depends(get_db),
    current_user_data: tuple = Depends(get_current_user_from_token),
    image: UploadFile = File(..., description="الصورة الشخصية")
) -> Any:
    """
    
    
    """
    
    user, user_type = current_user_data
    
    try:
        image_path = await file_service.upload_profile_image(image, user.id, user_type)
        
        if user_type == "student":
            user.profile_image = image_path
        elif user_type == "academy":
            user.profile_image = image_path
        elif user_type == "admin":
            user.profile_image = image_path
        
        db.commit()
        
        logger.info(f"Profile image uploaded successfully: {user_type} {user.id}")
        
        return {
            "message": "تم رفع الصورة الشخصية بنجاح",
            "image_url": file_service.get_file_url(image_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile image upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="فشل في رفع الصورة الشخصية"
        ) 
