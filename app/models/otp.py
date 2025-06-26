from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.db.base import Base


class OTPPurpose(str, Enum):
    """
    أغراض رموز التحقق المختلفة
    """
    # تسجيل الدخول
    LOGIN = "login"
    
    # إعادة تعيين كلمة المرور
    PASSWORD_RESET = "password_reset"
    
    # تحقق من البريد الإلكتروني
    EMAIL_VERIFICATION = "email_verification"
    
    # تحقق من رقم الهاتف
    PHONE_VERIFICATION = "phone_verification"
    
    # تأكيد المعاملات المالية
    TRANSACTION_CONFIRMATION = "transaction_confirmation"
    
    # تفعيل الحساب بعد التسجيل
    ACCOUNT_ACTIVATION = "account_activation"
    
    # تغيير كلمة المرور (للحسابات النشطة)
    CHANGE_PASSWORD = "change_password"
    
    # تحديث البريد الإلكتروني
    EMAIL_UPDATE = "email_update"
    
    # تحديث رقم الهاتف
    PHONE_UPDATE = "phone_update"
    
    # تأكيد الدفع
    PAYMENT_CONFIRMATION = "payment_confirmation"
    
    # حذف الحساب
    ACCOUNT_DELETION = "account_deletion"

    
    # تسجيل دخول ثنائي العامل
    TWO_FACTOR_AUTH = "two_factor_auth"
    
    # تحقق إضافي لعمليات حساسة
    SECURITY_VERIFICATION = "security_verification"


class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    purpose = Column(SQLEnum(OTPPurpose, values_callable=lambda obj: [e.value for e in obj]), nullable=False, index=True)
    is_used = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0)
    
    # إضافة حقول جديدة للأمان والوظائف المتقدمة
    ip_address = Column(String(45), nullable=True)  # لتسجيل IP العنوان
    user_agent = Column(String(500), nullable=True)  # لتسجيل متصفح المستخدم
    device_id = Column(String(255), nullable=True)  # لتتبع الأجهزة
    expires_in_minutes = Column(Integer, default=10)  # مدة الصلاحية بالدقائق
    max_attempts = Column(Integer, default=3)  # عدد المحاولات المسموحة

    # Relationships
    user = relationship("User", back_populates="otps")
    
    def __repr__(self):
        return f"<OTP(id={self.id}, user_id={self.user_id}, purpose='{self.purpose}', is_used={self.is_used})>"
    
    @property
    def is_expired(self):
        """Check if OTP is expired"""
        from datetime import datetime
        return datetime.utcnow() > self.expires_at
    
    @property
    def attempts_remaining(self):
        """Get remaining attempts"""
        return max(0, self.max_attempts - self.attempts)
    
    @property
    def can_retry(self):
        """Check if user can still retry"""
        return self.attempts < self.max_attempts and not self.is_expired and not self.is_used 