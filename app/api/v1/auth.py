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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
security_scheme = HTTPBearer()

# OTP storage (في الإنتاج يجب استخدام Redis أو قاعدة بيانات منفصلة)
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
        return user.status == StudentStatus.ACTIVE
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

@router.post("/student/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_student(
    *,
    db: Session = Depends(get_db),
    request: Request,
    background_tasks: BackgroundTasks,
    # Student registration data
    name: str = Form(..., description="الاسم الكامل"),
    email: str = Form(..., description="البريد الإلكتروني"),
    phone: str = Form(..., description="رقم الهاتف"),
    password: str = Form(..., description="كلمة المرور"),
    password_confirm: str = Form(..., description="تأكيد كلمة المرور"),
    date_of_birth: Optional[str] = Form(None, description="تاريخ الميلاد"),
    gender: Optional[str] = Form(None, description="الجنس"),
    country: Optional[str] = Form(None, description="الدولة"),
    city: Optional[str] = Form(None, description="المدينة"),
    # Optional profile image
    profile_image: Optional[UploadFile] = File(None, description="الصورة الشخصية (اختياري)")
) -> Any:
    """
    Register a new student account with optional profile image (Form Data)
    
    This endpoint accepts multipart/form-data to handle file uploads.
    
    **Required Fields:**
    - **name**: Student's full name (2-255 characters)
    - **email**: Valid email address (unique)
    - **phone**: Phone number (10-15 digits, unique)
    - **password**: Password (minimum 6 characters)
    - **password_confirm**: Password confirmation (must match password)
    
    **Optional Fields:**
    - **date_of_birth**: Optional birth date
    - **gender**: Optional gender (male/female/other)
    - **country**: Optional country
    - **city**: Optional city
    
    **Optional File Upload:**
    - **profile_image**: Profile image (PNG, JPG, WEBP - Max 5MB)
    
    **Returns:** Authentication tokens
    """
    
    client_ip = request.client.host
    
    # Check if IP is blocked (skip in debug mode for testing)
    if not settings.DEBUG and auth_service.is_ip_blocked(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please try again later."
        )
    
    # Validate password confirmation
    if password != password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    # Check if email already exists
    existing_user, _ = auth_service.get_user_by_email(db, email)
    if existing_user:
        auth_service.record_failed_attempt(client_ip)
        log_auth_attempt(request, "student_register", False, {"email": email, "error": "email_exists"})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists"
        )
    
    # Check if phone already exists
    existing_user, _ = auth_service.get_user_by_phone(db, phone)
    if existing_user:
        auth_service.record_failed_attempt(client_ip)
        log_auth_attempt(request, "student_register", False, {"phone": phone, "error": "phone_exists"})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number already exists"
        )
    
    try:
        # Create student data dict
        student_data = {
            "name": name,
            "email": email,
            "phone": phone,
            "password": password,
            "password_confirm": password_confirm
        }
        
        if date_of_birth:
            student_data["date_of_birth"] = date_of_birth
        if gender:
            student_data["gender"] = gender
        if country:
            student_data["country"] = country
        if city:
            student_data["city"] = city
        
        # Create StudentRegister object with validation
        try:
            user_in = StudentRegister(**student_data)
        except ValidationError as e:
            # Extract validation errors and format them for user
            validation_errors = []
            for error in e.errors():
                field = error['loc'][0] if error['loc'] else 'unknown'
                message = error['msg']
                validation_errors.append(f"{field}: {message}")
            
            error_message = "بيانات غير صحيحة: " + " | ".join(validation_errors)
            
            # In development mode, show detailed errors
            if settings.DEBUG:
                error_message = f"Validation Errors: {'; '.join(validation_errors)}"
            
            auth_service.record_failed_attempt(client_ip)
            log_auth_attempt(request, "student_register", False, {"email": email, "error": "validation_error"})
            
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_message
            )
        
        # Create new student
        user = crud_student.student.create(db, obj_in=user_in)
        
        # Upload profile image if provided
        if profile_image:
            profile_image_path = await file_service.upload_profile_image(profile_image, user.id, "student")
            user.profile_image = profile_image_path
            db.commit()
        
        # Generate tokens
        tokens = auth_service.create_tokens(user.id, "student")
        
        # Clear failed attempts for this IP
        auth_service.clear_failed_attempts(client_ip)
        
        # Log successful registration
        log_auth_attempt(request, "student_register", True, {"user_id": user.id, "email": email})
        
        # Send welcome email in background
        background_tasks.add_task(auth_service.send_welcome_email, user.email, user.name, "student")
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        error_detail = str(e)
        logger.error(f"Student registration failed: {error_detail}")
        auth_service.record_failed_attempt(client_ip)
        log_auth_attempt(request, "student_register", False, {"email": email, "error": error_detail})
        
        # In development mode, show actual error
        if settings.DEBUG:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registration failed: {error_detail}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed. Please try again."
            )


@router.post("/academy/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_academy(
    *,
    db: Session = Depends(get_db),
    request: Request,
    background_tasks: BackgroundTasks,
    # Academy registration data
    academy_name: str = Form(..., description="اسم الأكاديمية"),
    name: str = Form(..., description="اسم المدير"),
    email: str = Form(..., description="البريد الإلكتروني"),
    phone: str = Form(..., description="رقم الهاتف"),
    password: str = Form(..., description="كلمة المرور"),
    password_confirm: str = Form(..., description="تأكيد كلمة المرور"),
    address: Optional[str] = Form(None, description="العنوان"),
    country: Optional[str] = Form(None, description="الدولة"),
    city: Optional[str] = Form(None, description="المدينة"),
    description: Optional[str] = Form(None, description="وصف الأكاديمية"),
    # Optional image uploads
    logo: Optional[UploadFile] = File(None, description="شعار الأكاديمية (اختياري)"),
    cover: Optional[UploadFile] = File(None, description="غلاف الأكاديمية (اختياري)"),
    profile_image: Optional[UploadFile] = File(None, description="الصورة الشخصية (اختياري)")
) -> Any:
    """
    Register a new academy account with optional image uploads (Form Data)
    
    This endpoint accepts multipart/form-data to handle file uploads.
    
    **Required Fields:**
    - **academy_name**: Academy name (2-255 characters)
    - **name**: Admin's full name
    - **email**: Valid email address (unique)
    - **phone**: Phone number (10-15 digits, unique)
    - **password**: Password (minimum 6 characters)
    - **password_confirm**: Password confirmation
    
    **Optional Fields:**
    - **address**: Optional address
    - **country**: Optional country
    - **city**: Optional city
    - **description**: Optional academy description
    
    **Optional File Uploads:**
    - **logo**: Academy logo image (PNG, JPG, WEBP - Max 5MB)
    - **cover**: Academy cover image (PNG, JPG, WEBP - Max 5MB)
    - **profile_image**: Profile image (PNG, JPG, WEBP - Max 5MB)
    
    **Auto-Generated:**
    - **slug**: Automatically generated from academy name
    - **user_name**: Automatically generated from email
    
    **Returns:** Authentication tokens with academy info
    """
    
    client_ip = request.client.host
    
    # Check if IP is blocked (skip in debug mode for testing)
    if not settings.DEBUG and auth_service.is_ip_blocked(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please try again later."
        )
    
    # Validate password confirmation
    if password != password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    # Check if email already exists
    existing_user, _ = auth_service.get_user_by_email(db, email)
    if existing_user:
        auth_service.record_failed_attempt(client_ip)
        log_auth_attempt(request, "academy_register", False, {"email": email, "error": "email_exists"})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists"
        )
    
    # Check if phone already exists
    existing_user, _ = auth_service.get_user_by_phone(db, phone)
    if existing_user:
        auth_service.record_failed_attempt(client_ip)
        log_auth_attempt(request, "academy_register", False, {"phone": phone, "error": "phone_exists"})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number already exists"
        )
    
    try:
        import re
        import unicodedata
        from datetime import datetime
        
        # Auto-generate slug from academy name
        def generate_slug(name: str) -> str:
            # Convert to lowercase and normalize unicode
            slug = unicodedata.normalize('NFKD', name.lower())
            # Remove special characters and replace spaces with hyphens
            slug = re.sub(r'[^\w\s-]', '', slug)
            slug = re.sub(r'[-\s]+', '-', slug)
            # Remove leading/trailing hyphens
            slug = slug.strip('-')
            # Add timestamp to ensure uniqueness
            timestamp = datetime.now().strftime("%m%d")
            return f"{slug}-{timestamp}"
        
        # Auto-generate username from email
        def generate_username(email_addr: str) -> str:
            username_base = email_addr.split('@')[0]
            # Clean username
            username = re.sub(r'[^\w]', '', username_base)
            # Add random suffix to ensure uniqueness
            import random
            suffix = random.randint(100, 999)
            return f"{username}_{suffix}"
        
        # Generate slug and username
        slug = generate_slug(academy_name)
        user_name = generate_username(email)
        
        # Check if slug already exists and make it unique
        counter = 1
        original_slug = slug
        while db.query(Academy).filter(Academy.slug == slug).first():
            slug = f"{original_slug}-{counter}"
            counter += 1
        
        # Check if username already exists and make it unique
        counter = 1
        original_username = user_name
        while db.query(Academy).filter(Academy.user_name == user_name).first():
            user_name = f"{original_username}{counter}"
            counter += 1
        
        # Hash password
        hashed_password = security.get_password_hash(password)
        
        # Create new academy entry first
        new_academy = Academy(
            name=academy_name,
            slug=slug,
            user_name=user_name,
            address=address,
            country=country,
            city=city,
            description=description,
            is_active=True
        )
        
        db.add(new_academy)
        db.flush()  # Get the academy ID without committing
        
        # Upload images if provided
        logo_path = None
        cover_path = None
        profile_image_path = None
        
        if logo:
            logo_path = await file_service.upload_academy_logo(logo, new_academy.id)
            new_academy.logo = logo_path
            
        if cover:
            cover_path = await file_service.upload_academy_cover(cover, new_academy.id)
            new_academy.cover = cover_path
        
        # Create new academy user
        new_user = AcademyUser(
            name=name,
            email=email,
            phone=phone,
            hashed_password=hashed_password,
            academy_id=new_academy.id,
            is_active=True,
            is_owner=True
        )
        
        # Upload profile image if provided
        if profile_image:
            db.add(new_user)
            db.flush()  # Get user ID
            profile_image_path = await file_service.upload_profile_image(profile_image, new_user.id, "academy")
            new_user.profile_image = profile_image_path
        else:
            db.add(new_user)
        
        db.commit()
        db.refresh(new_user)
        db.refresh(new_academy)
        
        # Generate tokens
        tokens = auth_service.create_tokens(new_user.id, "academy")
        
        # Clear failed attempts for this IP
        auth_service.clear_failed_attempts(client_ip)
        
        # Log successful registration
        log_auth_attempt(request, "academy_register", True, {
            "user_id": new_user.id, 
            "email": email,
            "academy_slug": slug,
            "username": user_name
        })
        
        # Send welcome email in background
        background_tasks.add_task(auth_service.send_welcome_email, new_user.email, new_user.name, "academy")
        
        # Return tokens with additional info
        return {
            **tokens,
            "academy_slug": slug,
            "username": user_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_detail = str(e)
        logger.error(f"Academy registration failed: {error_detail}")
        auth_service.record_failed_attempt(client_ip)
        log_auth_attempt(request, "academy_register", False, {"email": email, "error": error_detail})
        
        # In development mode, show actual error
        if settings.DEBUG:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Academy registration failed: {error_detail}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed. Please try again."
            )


# ==================== Authentication Endpoints ====================

@router.post("/login", response_model=Token)
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
        
        return tokens
        
    except HTTPException as e:
        auth_service.record_failed_attempt(client_ip)
        log_auth_attempt(request, "login", False, {"email": user_in.email, "error": str(e.detail)})
        raise
    except Exception as e:
        error_detail = str(e)
        logger.error(f"Login failed: {error_detail}")
        auth_service.record_failed_attempt(client_ip)
        log_auth_attempt(request, "login", False, {"email": user_in.email, "error": error_detail})
        
        # In development mode, show actual error
        if settings.DEBUG:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Login failed: {error_detail}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed. Please try again."
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

@router.post("/send-otp", response_model=OTPResponse)
async def send_otp(
    *,
    db: Session = Depends(get_db),
    otp_request: OTPRequest,
    request: Request,
    background_tasks: BackgroundTasks
) -> Any:
    """
    Send OTP to phone number
    
    - **phone**: Phone number (10-15 digits)
    
    Sends a 6-digit OTP code to the provided phone number.
    """
    
    phone = otp_request.phone.strip()
    
    # Check if phone exists in database
    user, user_type = auth_service.get_user_by_phone(db, phone)
    if not user:
        log_auth_attempt(request, "send_otp", False, {"phone": phone, "error": "phone_not_found"})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not registered"
        )
    
    try:
        # Store OTP
        otp_code = auth_service.store_otp(phone, user.id, user_type)
        
        # Send OTP via SMS in background
        background_tasks.add_task(auth_service.send_sms_otp, phone, otp_code)
        
        # Log successful OTP send
        log_auth_attempt(request, "send_otp", True, {"phone": phone, "user_type": user_type})
        
        # Prepare response
        response_data = {
            "message": "OTP sent to your phone number",
            "phone": phone
        }
        
        # Include OTP in development mode
        if settings.DEBUG:
            response_data["otp"] = otp_code
            
        return response_data
        
    except Exception as e:
        logger.error(f"OTP send failed: {str(e)}")
        log_auth_attempt(request, "send_otp", False, {"phone": phone, "error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP. Please try again."
        )


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
        
        return {
            "message": "OTP verified successfully",
            "phone": phone,
            "verified": True
        }
        
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
        return {
            "message": "If this email is registered, you will receive a password reset link",
            "email": email
        }
    
    try:
        # Store reset token
        reset_token = auth_service.store_reset_token(email, user.id, user_type)
        
        # Send reset email in background
        background_tasks.add_task(auth_service.send_password_reset_email, email, reset_token)
        
        # Log successful request
        log_auth_attempt(request, "forgot_password", True, {"email": email, "user_type": user_type})
        
        # Prepare response
        response_data = {
            "message": "Password reset link sent to your email",
            "email": email
        }
        
        # Include reset token in development mode
        if settings.DEBUG:
            response_data["reset_token"] = reset_token
            
        return response_data
        
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
        
        return {
            "message": "Password reset successfully"
        }
        
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
        
        return {
            "message": "Password changed successfully"
        }
        
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
    رفع شعار الأكاديمية
    
    - **logo**: ملف صورة الشعار (PNG, JPG, WEBP)
    
    يتطلب صلاحيات الأكاديمية. الحد الأقصى لحجم الملف: 5MB
    أبعاد الصورة المقترحة: 400x400 بكسل
    """
    
    user, user_type = current_user_data
    
    # التحقق من أن المستخدم من نوع أكاديمية
    if user_type != "academy":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه الميزة متاحة للأكاديميات فقط"
        )
    
    try:
        # الحصول على الأكاديمية المرتبطة بالمستخدم
        academy = db.query(Academy).filter(Academy.id == user.academy_id).first()
        if not academy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الأكاديمية غير موجودة"
            )
        
        # رفع الشعار
        logo_path = await file_service.upload_academy_logo(logo, academy.id)
        
        # تحديث قاعدة البيانات في جدول Academy
        academy.logo = logo_path
        db.commit()
        
        # تسجيل العملية بنجاح
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
    رفع غلاف الأكاديمية
    
    - **cover**: ملف صورة الغلاف (PNG, JPG, WEBP)
    
    يتطلب صلاحيات الأكاديمية. الحد الأقصى لحجم الملف: 5MB
    أبعاد الصورة المقترحة: 1200x300 بكسل
    """
    
    user, user_type = current_user_data
    
    # التحقق من أن المستخدم من نوع أكاديمية
    if user_type != "academy":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه الميزة متاحة للأكاديميات فقط"
        )
    
    try:
        # الحصول على الأكاديمية المرتبطة بالمستخدم
        academy = db.query(Academy).filter(Academy.id == user.academy_id).first()
        if not academy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الأكاديمية غير موجودة"
            )
        
        # رفع الغلاف
        cover_path = await file_service.upload_academy_cover(cover, academy.id)
        
        # تحديث قاعدة البيانات في جدول Academy
        academy.cover = cover_path
        db.commit()
        
        # تسجيل العملية بنجاح
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
    رفع الصورة الشخصية للمستخدم
    
    - **image**: ملف الصورة الشخصية (PNG, JPG, WEBP)
    
    متاح لجميع أنواع المستخدمين. الحد الأقصى لحجم الملف: 5MB
    أبعاد الصورة المقترحة: 200x200 بكسل
    """
    
    user, user_type = current_user_data
    
    try:
        # رفع الصورة الشخصية
        image_path = await file_service.upload_profile_image(image, user.id, user_type)
        
        # تحديث قاعدة البيانات حسب نوع المستخدم
        if user_type == "student":
            user.profile_image = image_path
        elif user_type == "academy":
            user.profile_image = image_path
        elif user_type == "admin":
            user.profile_image = image_path
        
        db.commit()
        
        # تسجيل العملية بنجاح
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