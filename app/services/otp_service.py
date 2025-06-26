import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.models.otp import OTP, OTPPurpose
from app.models.user import User
from app.core.config import settings


class OTPService:
    """خدمة شاملة لإدارة رموز التحقق OTP"""
    
    # مدد انتهاء الصلاحية حسب نوع العملية (بالدقائق)
    EXPIRY_MINUTES = {
        OTPPurpose.LOGIN: 5,
        OTPPurpose.PASSWORD_RESET: 30,
        OTPPurpose.EMAIL_VERIFICATION: 15,
        OTPPurpose.PHONE_VERIFICATION: 10,
        OTPPurpose.TRANSACTION_CONFIRMATION: 5,
        OTPPurpose.ACCOUNT_ACTIVATION: 60,
        OTPPurpose.CHANGE_PASSWORD: 15,
        OTPPurpose.EMAIL_UPDATE: 20,
        OTPPurpose.PHONE_UPDATE: 10,
        OTPPurpose.PAYMENT_CONFIRMATION: 3,
        OTPPurpose.ACCOUNT_DELETION: 60,
        # OTPPurpose.ACCOUNT_UNFREEZE: 30,
        OTPPurpose.TWO_FACTOR_AUTH: 5,
        OTPPurpose.SECURITY_VERIFICATION: 10
    }
    
    # عدد المحاولات المسموحة حسب نوع العملية
    MAX_ATTEMPTS = {
        OTPPurpose.LOGIN: 3,
        OTPPurpose.PASSWORD_RESET: 5,
        OTPPurpose.EMAIL_VERIFICATION: 3,
        OTPPurpose.PHONE_VERIFICATION: 3,
        OTPPurpose.TRANSACTION_CONFIRMATION: 3,
        OTPPurpose.ACCOUNT_ACTIVATION: 5,
        OTPPurpose.CHANGE_PASSWORD: 3,
        OTPPurpose.EMAIL_UPDATE: 3,
        OTPPurpose.PHONE_UPDATE: 3,
        OTPPurpose.PAYMENT_CONFIRMATION: 2,
        OTPPurpose.ACCOUNT_DELETION: 5,
        OTPPurpose.TWO_FACTOR_AUTH: 3,
        OTPPurpose.SECURITY_VERIFICATION: 3
    }
    
    # أطوال الرموز حسب نوع العملية
    CODE_LENGTHS = {
        OTPPurpose.LOGIN: 6,
        OTPPurpose.PASSWORD_RESET: 6,
        OTPPurpose.EMAIL_VERIFICATION: 6,
        OTPPurpose.PHONE_VERIFICATION: 6,
        OTPPurpose.TRANSACTION_CONFIRMATION: 6,
        OTPPurpose.ACCOUNT_ACTIVATION: 6,
        OTPPurpose.CHANGE_PASSWORD: 6,
        OTPPurpose.EMAIL_UPDATE: 6,
        OTPPurpose.PHONE_UPDATE: 6,
        OTPPurpose.PAYMENT_CONFIRMATION: 8,  # رمز أطول للمدفوعات
        OTPPurpose.ACCOUNT_DELETION: 8,  # رمز أطول للحذف
        OTPPurpose.TWO_FACTOR_AUTH: 6,
        OTPPurpose.SECURITY_VERIFICATION: 6
    }
    
    @staticmethod
    def generate_otp_code(length: int = 6, use_letters: bool = False) -> str:
        """توليد رمز OTP مع إمكانية استخدام الأحرف"""
        if use_letters:
            chars = string.ascii_uppercase + string.digits
            # تجنب الأحرف المتشابهة
            chars = chars.replace('O', '').replace('I', '').replace('0', '').replace('1', '')
        else:
            chars = string.digits
        
        return ''.join(random.choices(chars, k=length))
    
    @staticmethod
    def create_otp(
        db: Session,
        user_id: int,
        purpose: OTPPurpose,
        expires_in_minutes: Optional[int] = None
    ) -> OTP:
        """إنشاء رمز OTP جديد مع ميزات أمان متقدمة"""
        
        # حذف رموز OTP السابقة غير المستخدمة لنفس الغرض
        db.query(OTP).filter(
            and_(
                OTP.user_id == user_id,
                OTP.purpose == purpose,
                OTP.is_used == False
            )
        ).delete()
        
        # تحديد المعاملات حسب نوع العملية
        code_length = OTPService.CODE_LENGTHS.get(purpose, 6)
        max_attempts = OTPService.MAX_ATTEMPTS.get(purpose, 3)
        default_expiry = OTPService.EXPIRY_MINUTES.get(purpose, 10)
        
        # استخدام المدة المحددة أو المدة الافتراضية
        expiry_minutes = expires_in_minutes or default_expiry
        
        # توليد رمز خاص للعمليات الحساسة
        use_letters = purpose in [
            OTPPurpose.PAYMENT_CONFIRMATION, 
            OTPPurpose.ACCOUNT_DELETION,
            OTPPurpose.SECURITY_VERIFICATION
        ]
        
        code = OTPService.generate_otp_code(code_length, use_letters)
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        # إنشاء سجل OTP
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
        
        # تسجيل إحصائيات الاستخدام
        OTPService._log_otp_creation(db, user_id, purpose)
        
        return otp
    
    @staticmethod
    def verify_otp(
        db: Session,
        user_id: int,
        code: str,
        purpose: OTPPurpose
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        التحقق من رمز OTP مع معلومات مفصلة
        Returns (success, error_message, additional_info)
        """
        
        # البحث عن OTP
        otp = db.query(OTP).filter(
            and_(
                OTP.user_id == user_id,
                OTP.purpose == purpose,
                OTP.is_used == False
            )
        ).order_by(OTP.created_at.desc()).first()
        
        if not otp:
            return False, "لم يتم العثور على رمز التحقق أو تم استخدامه بالفعل", None
        
        # فحص انتهاء الصلاحية
        if otp.is_expired:
            return False, "انتهت صلاحية رمز التحقق", {
                "expired_at": otp.expires_at.isoformat(),
                "purpose": purpose.value
            }
        
        # فحص عدد المحاولات
        max_attempts = OTPService.MAX_ATTEMPTS.get(purpose, 3)
        if otp.attempts >= max_attempts:
            return False, "تم تجاوز العدد المسموح من المحاولات", {
                "max_attempts": max_attempts,
                "attempts_used": otp.attempts
            }
        
        # زيادة عدد المحاولات
        otp.attempts += 1
        
        # التحقق من الرمز
        if otp.code != code:
            db.commit()
            
            # إحصائيات الفشل
            OTPService._log_verification_attempt(db, user_id, purpose, False)
            
            max_attempts = OTPService.MAX_ATTEMPTS.get(purpose, 3)
            attempts_remaining = max_attempts - otp.attempts
            return False, "رمز التحقق غير صحيح", {
                "attempts_remaining": attempts_remaining,
                "purpose": purpose.value
            }
        

        
        # نجح التحقق - تحديث السجل
        otp.is_used = True
        db.commit()
        
        # إحصائيات النجاح
        OTPService._log_verification_attempt(db, user_id, purpose, True)
        
        return True, None, {
            "verified_at": datetime.utcnow().isoformat(),
            "purpose": purpose.value,
            "attempts_used": otp.attempts
        }
    
    @staticmethod
    def get_otp_status(
        db: Session,
        user_id: int,
        purpose: Optional[OTPPurpose] = None
    ) -> Dict[str, Any]:
        """الحصول على حالة OTP للمستخدم"""
        
        query = db.query(OTP).filter(OTP.user_id == user_id)
        
        if purpose:
            query = query.filter(OTP.purpose == purpose)
        
        all_otps = query.all()
        
        active_otps = [otp for otp in all_otps if not otp.is_used and not otp.is_expired]
        expired_otps = [otp for otp in all_otps if otp.is_expired]
        used_otps = [otp for otp in all_otps if otp.is_used]
        
        total_attempts = sum(otp.attempts for otp in all_otps)
        
        last_otp = db.query(OTP).filter(
            OTP.user_id == user_id
        ).order_by(desc(OTP.created_at)).first()
        
        return {
            "active_otps": len(active_otps),
            "expired_otps": len(expired_otps),
            "used_otps": len(used_otps),
            "total_attempts": total_attempts,
            "last_sent": last_otp.created_at.isoformat() if last_otp else None,
            "active_purposes": [otp.purpose.value for otp in active_otps]
        }
    
    @staticmethod
    def send_otp_email(email: str, code: str, purpose: str, user_name: str = "مستخدم") -> bool:
        """إرسال OTP عبر البريد الإلكتروني مع تخصيص حسب النوع"""
        try:
            import smtplib
            import ssl
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # خريطة الأغراض بالعربية
            purpose_map = {
                "login": "تسجيل الدخول",
                "password_reset": "إعادة تعيين كلمة المرور",
                "email_verification": "تحقق من البريد الإلكتروني",
                "phone_verification": "تحقق من رقم الهاتف",
                "transaction_confirmation": "تأكيد المعاملة",
                "account_activation": "تفعيل الحساب",
                "change_password": "تغيير كلمة المرور",
                "email_update": "تحديث البريد الإلكتروني",
                "phone_update": "تحديث رقم الهاتف",
                "payment_confirmation": "تأكيد الدفع",
                "account_deletion": "حذف الحساب",
                "two_factor_auth": "المصادقة الثنائية",
                "security_verification": "التحقق الأمني"
            }
            
            arabic_purpose = purpose_map.get(purpose, purpose)
            
            # تحديد لون ونبرة الرسالة حسب النوع
            if purpose in ["payment_confirmation", "account_deletion", "security_verification"]:
                color = "#dc3545"  # أحمر للعمليات الحساسة
                urgency = "عملية حساسة"
            elif purpose in ["transaction_confirmation", "change_password"]:
                color = "#fd7e14"  # برتقالي للعمليات المهمة
                urgency = "عملية مهمة"
            else:
                color = "#0d6efd"  # أزرق للعمليات العادية
                urgency = "رمز التحقق"
            
            # إنشاء الرسالة
            message = MIMEMultipart("alternative")
            message["Subject"] = f"{urgency} - {arabic_purpose}"
            message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            message["To"] = email
            
            # محتوى HTML مخصص
            html = f"""
            <html>
              <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; direction: rtl; text-align: right; margin: 0; padding: 0; background-color: #f8f9fa;">
                <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                  
                  <!-- Header -->
                  <div style="background: linear-gradient(135deg, {color} 0%, #495057 100%); color: white; padding: 30px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px; font-weight: bold;">{urgency}</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{arabic_purpose}</p>
                  </div>
                  
                  <!-- Content -->
                  <div style="padding: 40px 30px;">
                    <p style="font-size: 18px; color: #495057; margin-bottom: 20px;">
                      مرحباً {user_name}،
                    </p>
                    
                    <p style="font-size: 16px; color: #6c757d; line-height: 1.6; margin-bottom: 30px;">
                      تم طلب رمز التحقق الخاص بـ <strong>{arabic_purpose}</strong>. استخدم الرمز التالي لإتمام العملية:
                    </p>
                    
                    <!-- OTP Code -->
                    <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border: 3px solid {color}; border-radius: 12px; padding: 25px; text-align: center; margin: 30px 0;">
                      <div style="font-size: 32px; font-weight: bold; color: {color}; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                        {code}
                      </div>
                    </div>
                    
                    <!-- Expiry Info -->
                    <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 15px; margin: 20px 0;">
                      <p style="margin: 0; color: #856404; font-size: 14px; text-align: center;">
                        هذا الرمز صالح لمدة محدودة فقط
                      </p>
                    </div>
                    
                    <!-- Security Notice -->
                    {"<div style='background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 15px; margin: 20px 0;'><p style='margin: 0; color: #721c24; font-size: 14px; text-align: center;'>لا تشارك هذا الرمز مع أي شخص آخر</p></div>" if purpose in ["payment_confirmation", "account_deletion", "security_verification"] else ""}
                    
                    <p style="font-size: 14px; color: #6c757d; margin-top: 30px;">
                      إذا لم تطلب هذا الرمز، يرجى تجاهل هذه الرسالة أو التواصل مع الدعم الفني.
                    </p>
                  </div>
                  
                  <!-- Footer -->
                  <div style="background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #dee2e6;">
                    <p style="margin: 0; color: #6c757d; font-size: 12px;">
                      هذه رسالة تلقائية من منصة سَيان التعليمية<br>
                      © {datetime.now().year} جميع الحقوق محفوظة
                    </p>
                  </div>
                  
                </div>
              </body>
            </html>
            """
            
            # إرفاق المحتوى
            part = MIMEText(html, "html", "utf-8")
            message.attach(part)
            
            # إرسال البريد
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAIL_FROM, email, message.as_string())
            
            print(f"تم إرسال OTP بنجاح: {code} إلى {email} للغرض {purpose}")
            return True
                
        except Exception as e:
            print(f" فشل إرسال OTP عبر البريد: {str(e)}")
            return False
    
    @staticmethod
    def send_otp_sms(phone: str, code: str, purpose: str) -> bool:
        """إرسال OTP عبر SMS مع تخصيص حسب النوع"""
        try:
            # خريطة الأغراض بالعربية
            purpose_map = {
                "login": "تسجيل الدخول",
                "password_reset": "إعادة تعيين كلمة المرور",
                "phone_verification": "تحقق من رقم الهاتف",
                "two_factor_auth": "المصادقة الثنائية",
                "payment_confirmation": "تأكيد الدفع"
            }
            
            arabic_purpose = purpose_map.get(purpose, "التحقق")
            
            # رسالة SMS مخصصة
            if purpose in ["payment_confirmation", "account_deletion"]:
                message = f"رمز {arabic_purpose}: {code}\nلا تشاركه مع أحد. صالح لدقائق قليلة.\n- منصة سَيان"
            else:
                message = f"رمز {arabic_purpose}: {code}\nصالح لدقائق قليلة.\n- منصة سَيان"
            
            # TODO: تكامل مع خدمة SMS حقيقية
            print(f"SMS OTP: {message} إلى {phone}")
            
            return True
        except Exception as e:
            print(f" فشل إرسال SMS: {str(e)}")
            return False
    
    @staticmethod
    def cleanup_expired_otps(db: Session) -> int:
        """تنظيف رموز OTP المنتهية الصلاحية"""
        
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
        """الحصول على OTP نشط للمستخدم والغرض المحدد"""
        
        return db.query(OTP).filter(
            and_(
                OTP.user_id == user_id,
                OTP.purpose == purpose,
                OTP.is_used == False,
                OTP.expires_at > datetime.utcnow()
            )
        ).order_by(OTP.created_at.desc()).first()
    
    @staticmethod
    def _log_otp_creation(db: Session, user_id: int, purpose: OTPPurpose):
        """تسجيل إحصائيات إنشاء OTP"""
        # TODO: إضافة جدول إحصائيات منفصل
        pass
    
    @staticmethod
    def _log_verification_attempt(
        db: Session, 
        user_id: int, 
        purpose: OTPPurpose, 
        success: bool
    ):
        """تسجيل محاولات التحقق"""
        # TODO: إضافة جدول سجل الأمان
        pass
    
    @staticmethod
    def get_purpose_description(purpose: OTPPurpose) -> str:
        """الحصول على وصف الغرض بالعربية"""
        descriptions = {
            OTPPurpose.LOGIN: "تسجيل الدخول",
            OTPPurpose.PASSWORD_RESET: "إعادة تعيين كلمة المرور",
            OTPPurpose.EMAIL_VERIFICATION: "تحقق من البريد الإلكتروني",
            OTPPurpose.PHONE_VERIFICATION: "تحقق من رقم الهاتف",
            OTPPurpose.TRANSACTION_CONFIRMATION: "تأكيد المعاملة",
            OTPPurpose.ACCOUNT_ACTIVATION: "تفعيل الحساب",
            OTPPurpose.CHANGE_PASSWORD: "تغيير كلمة المرور",
            OTPPurpose.EMAIL_UPDATE: "تحديث البريد الإلكتروني",
            OTPPurpose.PHONE_UPDATE: "تحديث رقم الهاتف",
            OTPPurpose.PAYMENT_CONFIRMATION: "تأكيد الدفع",
            OTPPurpose.ACCOUNT_DELETION: "حذف الحساب",
            OTPPurpose.TWO_FACTOR_AUTH: "المصادقة الثنائية",
            OTPPurpose.SECURITY_VERIFICATION: "التحقق الأمني"
        }
        return descriptions.get(purpose, purpose.value) 