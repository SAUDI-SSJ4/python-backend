import logging
import smtplib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.models.student import Student, StudentStatus
from app.models.academy import AcademyUser
from app.models.admin import Admin

logger = logging.getLogger(__name__)


class AuthService:
    """Advanced authentication service"""
    
    def __init__(self):
        self.otp_storage: Dict[str, Dict[str, Any]] = {}
        self.reset_tokens: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, Dict[str, Any]] = {}
        
        # Block settings
        self.max_failed_attempts = 5
        self.block_duration_minutes = 15
        
        # Expiry settings
        self.otp_expiry_minutes = 5
        self.reset_token_expiry_hours = 1
    
    def get_user_by_email(self, db: Session, email: str) -> Tuple[Optional[Union[Student, AcademyUser, Admin]], Optional[str]]:
        """Get user by email from all tables"""
        
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
    
    def get_user_by_phone(self, db: Session, phone: str) -> Tuple[Optional[Union[Student, AcademyUser, Admin]], Optional[str]]:
        """Get user by phone from all tables"""
        
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
    
    def validate_user_status(self, user: Union[Student, AcademyUser, Admin], user_type: str) -> bool:
        """Validate user status"""
        if user_type == "student":
            return user.status == "active"
        elif user_type in ["academy", "admin"]:
            return getattr(user, 'is_active', True)
        return False
    
    def authenticate_user(self, db: Session, email: str, password: str) -> Tuple[Union[Student, AcademyUser, Admin], str]:
        """Authenticate user with email and password"""
        
        user, user_type = self.get_user_by_email(db, email)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not security.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check user status
        if not self.validate_user_status(user, user_type):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )
        
        return user, user_type
    
    def create_tokens(self, user_id: int, user_type: str) -> Dict[str, str]:
        """Create access and refresh tokens"""
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = security.create_access_token(
            subject=str(user_id),
            user_type=user_type,
            expires_delta=access_token_expires
        )
        
        refresh_token = security.create_refresh_token(
            subject=str(user_id),
            user_type=user_type,
            expires_delta=refresh_token_expires
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_type": user_type
        }
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        if ip not in self.failed_attempts:
            return False
        
        attempt_data = self.failed_attempts[ip]
        if attempt_data["count"] >= self.max_failed_attempts:
            block_time = attempt_data["last_attempt"] + timedelta(minutes=self.block_duration_minutes)
            return datetime.utcnow() < block_time
        
        return False
    
    def record_failed_attempt(self, ip: str):
        """Record failed attempt"""
        if ip not in self.failed_attempts:
            self.failed_attempts[ip] = {"count": 0, "last_attempt": datetime.utcnow()}
        
        self.failed_attempts[ip]["count"] += 1
        self.failed_attempts[ip]["last_attempt"] = datetime.utcnow()
    
    def clear_failed_attempts(self, ip: str):
        """Clear failed attempts"""
        if ip in self.failed_attempts:
            del self.failed_attempts[ip]
    
    def store_otp(self, phone: str, user_id: int, user_type: str) -> str:
        """Store OTP"""
        otp_code = self.generate_otp()
        
        self.otp_storage[phone] = {
            "otp": otp_code,
            "user_id": user_id,
            "user_type": user_type,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=self.otp_expiry_minutes)
        }
        
        return otp_code
    
    def verify_otp(self, phone: str, otp: str) -> Dict[str, Any]:
        """Verify OTP"""
        if phone not in self.otp_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No OTP sent to this number"
            )
        
        otp_data = self.otp_storage[phone]
        
        # Check expiry
        if datetime.utcnow() > otp_data["expires_at"]:
            del self.otp_storage[phone]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired"
            )
        
        # Verify OTP
        if otp_data["otp"] != otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP"
            )
        
        # Delete OTP after verification
        user_data = {
            "user_id": otp_data["user_id"],
            "user_type": otp_data["user_type"]
        }
        del self.otp_storage[phone]
        
        return user_data
    
    def store_reset_token(self, email: str, user_id: int, user_type: str) -> str:
        """Store password reset token"""
        reset_token = self.generate_reset_token()
        
        self.reset_tokens[reset_token] = {
            "email": email,
            "user_id": user_id,
            "user_type": user_type,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=self.reset_token_expiry_hours)
        }
        
        return reset_token
    
    def reset_password(self, db: Session, token: str, new_password: str):
        """Reset password using token"""
        if token not in self.reset_tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid reset token"
            )
        
        token_data = self.reset_tokens[token]
        
        # Check expiry
        if datetime.utcnow() > token_data["expires_at"]:
            del self.reset_tokens[token]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        
        # Find user
        user, user_type = self.get_user_by_email(db, token_data["email"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        hashed_password = security.get_password_hash(new_password)
        user.hashed_password = hashed_password
        db.commit()
        
        # Delete token
        del self.reset_tokens[token]
    
    def change_password(self, db: Session, user: Union[Student, AcademyUser, Admin], user_type: str, old_password: str, new_password: str):
        """Change password for current user"""
        
        # Verify old password
        if not security.verify_password(old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        hashed_password = security.get_password_hash(new_password)
        user.hashed_password = hashed_password
        db.commit()
    
    def generate_otp(self) -> str:
        """Generate 6-digit OTP"""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    def generate_reset_token(self) -> str:
        """Generate password reset token"""
        import uuid
        return str(uuid.uuid4()).replace('-', '')
    
    async def send_welcome_email(self, email: str, name: str, user_type: str):
        """Send welcome email"""
        try:
            subject = f"Welcome to SAYAN Platform - {user_type.title()}"
            body = f"""
            Hello {name},
            
            Welcome to SAYAN Educational Platform!
            Your account has been successfully created as {user_type}.
            
            You can now start using all platform features.
            
            Best regards,
            SAYAN Platform Team
            """
            
            await self.send_email(email, subject, body)
            logger.info(f"Welcome email sent to {email}")
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
    
    async def send_sms_otp(self, phone: str, otp: str):
        """Send OTP via SMS"""
        try:
            # Here you can add actual SMS service
            logger.info(f"SMS OTP sent to {phone}: {otp}")
            print(f"📱 SMS OTP to {phone}: {otp}")
            
        except Exception as e:
            logger.error(f"Failed to send SMS OTP: {str(e)}")
    
    async def send_password_reset_email(self, email: str, reset_token: str):
        """Send password reset email"""
        try:
            subject = "Password Reset - SAYAN Platform"
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
            
            body = f"""
            Hello,
            
            A password reset was requested for your account.
            
            To continue, click the following link:
            {reset_url}
            
            If you didn't request a password reset, you can ignore this email.
            
            Best regards,
            SAYAN Platform Team
            """
            
            await self.send_email(email, subject, body)
            logger.info(f"Password reset email sent to {email}")
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
    
    async def send_email(self, to_email: str, subject: str, body: str):
        """Send email"""
        try:
            # In development mode, just print the email
            if settings.DEBUG:
                print(f"📧 Email to {to_email}")
                print(f"Subject: {subject}")
                print(f"Body: {body}")
                return
            
            # Send actual email in production
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_USER
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            text = msg.as_string()
            server.sendmail(settings.SMTP_USER, to_email, text)
            server.quit()
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise
    
    def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        now = datetime.utcnow()
        
        # Clean up expired OTPs
        expired_otps = [phone for phone, data in self.otp_storage.items() if now > data["expires_at"]]
        for phone in expired_otps:
            del self.otp_storage[phone]
        
        # Clean up expired reset tokens
        expired_tokens = [token for token, data in self.reset_tokens.items() if now > data["expires_at"]]
        for token in expired_tokens:
            del self.reset_tokens[token]
        
        # Clean up old failed attempts
        cutoff_time = now - timedelta(hours=24)
        expired_ips = [ip for ip, data in self.failed_attempts.items() if data["last_attempt"] < cutoff_time]
        for ip in expired_ips:
            del self.failed_attempts[ip]
        
        logger.info(f"Cleaned up {len(expired_otps)} expired OTPs, {len(expired_tokens)} expired reset tokens, {len(expired_ips)} old failed attempts")


# Create singleton service instance
auth_service = AuthService() 