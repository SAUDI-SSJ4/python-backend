import random
import string
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.otp import OTP, OTPPurpose
from app.models.user import User
from app.core.config import settings


class OTPService:
    """Service for handling OTP operations"""
    
    @staticmethod
    def generate_otp_code(length: int = 6) -> str:
        """Generate a random OTP code"""
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def create_otp(
        db: Session,
        user_id: int,
        purpose: OTPPurpose,
        expires_in_minutes: int = 10
    ) -> OTP:
        """Create a new OTP for the user"""
        
        # Delete any existing unused OTPs for this user and purpose
        db.query(OTP).filter(
            and_(
                OTP.user_id == user_id,
                OTP.purpose == purpose,
                OTP.is_used == False
            )
        ).delete()
        
        # Generate new OTP
        code = OTPService.generate_otp_code()
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        
        # Create OTP record
        otp = OTP(
            user_id=user_id,
            code=code,
            purpose=purpose,
            expires_at=expires_at,
            attempts=0,
            is_used=False
        )
        
        db.add(otp)
        db.commit()
        # إزالة db.refresh لتجنب مشكلة enum
        # db.refresh(otp)
        return otp
    
    @staticmethod
    def verify_otp(
        db: Session,
        user_id: int,
        code: str,
        purpose: OTPPurpose,
        max_attempts: int = 3
    ) -> tuple[bool, Optional[str]]:
        """
        Verify OTP code
        Returns (success, error_message)
        """
        
        # Find the OTP
        otp = db.query(OTP).filter(
            and_(
                OTP.user_id == user_id,
                OTP.purpose == purpose,
                OTP.is_used == False
            )
        ).order_by(OTP.created_at.desc()).first()
        
        if not otp:
            return False, "OTP not found or already used"
        
        # Check if OTP is expired
        if datetime.utcnow() > otp.expires_at:
            return False, "OTP has expired"
        
        # Check attempts limit
        if otp.attempts >= max_attempts:
            return False, "Maximum attempts exceeded"
        
        # Increment attempts
        otp.attempts += 1
        
        # Check if code matches
        if otp.code != code:
            db.commit()
            return False, "Invalid OTP code"
        
        # Mark OTP as used
        otp.is_used = True
        db.commit()
        
        return True, None
    
    @staticmethod
    def send_otp_sms(phone: str, code: str, purpose: str) -> bool:
        """
        Send OTP via SMS
        This is a placeholder implementation
        Replace with your actual SMS service
        """
        try:
            # TODO: Implement actual SMS sending logic
            # For now, just print to console (development mode)
            print(f"📱 SMS OTP: {code} sent to {phone} for {purpose}")
            
            # In production, integrate with SMS service like:
            # - Twilio
            # - AWS SNS
            # - Local SMS gateway
            
            return True
        except Exception as e:
            print(f"❌ Failed to send SMS: {str(e)}")
            return False
    
    @staticmethod
    def send_otp_email(email: str, code: str, purpose: str) -> bool:
        """
        Send OTP via Email using real SMTP service
        """
        try:
            # Import here to avoid circular imports
            import smtplib
            import ssl
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Map purpose to Arabic text
            purpose_map = {
                "login": "تسجيل الدخول",
                "password_reset": "إعادة تعيين كلمة المرور", 
                "email_verification": "تحقق من البريد الإلكتروني",
                "transaction_confirmation": "تأكيد المعاملة",
                # القيم الكبيرة للتوافق العكسي
                "LOGIN": "تسجيل الدخول",
                "PASSWORD_RESET": "إعادة تعيين كلمة المرور", 
                "EMAIL_VERIFICATION": "تحقق من البريد الإلكتروني",
                "TRANSACTION_CONFIRMATION": "تأكيد المعاملة"
            }
            
            arabic_purpose = purpose_map.get(purpose, purpose)
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = f"رمز التحقق - {arabic_purpose}"
            message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            message["To"] = email
            
            # Create HTML content
            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; direction: rtl; text-align: right;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #2196F3;">رمز التحقق - {arabic_purpose}</h2>
                  <p>مرحباً،</p>
                  <p>رمز التحقق الخاص بك هو:</p>
                  <div style="background-color: #f5f5f5; padding: 20px; text-align: center; font-size: 24px; font-weight: bold; color: #2196F3; margin: 20px 0;">
                    {code}
                  </div>
                  <p>هذا الرمز صالح لمدة 10 دقائق فقط.</p>
                  <p>إذا لم تطلب هذا الرمز، يرجى تجاهل هذه الرسالة.</p>
                  <hr style="margin: 30px 0;">
                  <p style="color: #666; font-size: 12px;">
                    هذه رسالة تلقائية من منصة سيان التعليمية<br>
                    {settings.EMAIL_FROM}
                  </p>
                </div>
              </body>
            </html>
            """
            
            # Convert to MIMEText
            part = MIMEText(html, "html", "utf-8")
            message.attach(part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAIL_FROM, email, message.as_string())
            
            print(f"📧 ✅ Email OTP: {code} sent successfully to {email} for {purpose}")
            return True
                
        except Exception as e:
            print(f"❌ Failed to send email OTP: {str(e)}")
            return False
    
    @staticmethod
    def cleanup_expired_otps(db: Session) -> int:
        """Clean up expired OTPs from database"""
        
        deleted_count = db.query(OTP).filter(
            OTP.expires_at < datetime.utcnow()
        ).delete()
        
        db.commit()
        return deleted_count
    
    @staticmethod
    def get_otp_by_user_and_purpose(
        db: Session,
        user_id: int,
        purpose: OTPPurpose
    ) -> Optional[OTP]:
        """Get active OTP for user and purpose"""
        
        return db.query(OTP).filter(
            and_(
                OTP.user_id == user_id,
                OTP.purpose == purpose,
                OTP.is_used == False,
                OTP.expires_at > datetime.utcnow()
            )
        ).order_by(OTP.created_at.desc()).first() 