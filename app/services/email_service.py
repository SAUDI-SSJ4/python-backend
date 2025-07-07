#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """خدمة إرسال البريد الإلكتروني"""
    
    def __init__(self):
        # Use new MAIL_* settings as primary, fallback to legacy SMTP_* settings
        self.smtp_server = settings.MAIL_HOST or settings.SMTP_HOST or 'smtp.hostinger.com'
        self.smtp_port = settings.MAIL_PORT or settings.SMTP_PORT or 465
        self.email_user = settings.MAIL_USERNAME or settings.SMTP_USERNAME or settings.EMAIL_FROM or 'support@sayan.pro'
        self.email_password = settings.MAIL_PASSWORD or settings.SMTP_PASSWORD or ''
        self.email_from = settings.MAIL_FROM_ADDRESS or settings.EMAIL_FROM or 'support@sayan.pro'
        self.email_from_name = settings.MAIL_FROM_NAME or settings.EMAIL_FROM_NAME or 'SAYAN Platform'
        self.mail_encryption = settings.MAIL_ENCRYPTION or ('ssl' if self.smtp_port == 465 else 'tls')
        
        # Debug print للتأكد من الإعدادات
        if settings.DEBUG:
            print(f"Email Service Configuration:")
            print(f"- SMTP Server: {self.smtp_server}")
            print(f"- SMTP Port: {self.smtp_port}")
            print(f"- Email User: {self.email_user}")
            print(f"- Email From: {self.email_from}")
            print(f"- Encryption: {self.mail_encryption}")
            print(f"- Password exists: {'Yes' if self.email_password else 'No'}")
    
    def send_otp_email(self, to_email: str, user_name: str, otp_code: str, purpose: str = "registration") -> bool:
        """
        إرسال رمز التحقق OTP
        
        Args:
            to_email: البريد الإلكتروني للمستقبل
            user_name: اسم المستخدم
            otp_code: رمز التحقق
            purpose: الغرض من الرمز (registration, login, password_reset, etc.)
            
        Returns:
            bool: True إذا تم الإرسال بنجاح
        """
        
        # تحديد نوع العملية - تطابق قيم الـ enum OTPPurpose
        purpose_text = {
            "login": "تسجيل الدخول",
            "password_reset": "إعادة تعيين كلمة المرور",
            "email_verification": "تأكيد البريد الإلكتروني",
            "transaction_confirmation": "تأكيد المعاملة",
            "registration": "تأكيد التسجيل",
            # القيم الكبيرة للتوافق العكسي
            "LOGIN": "تسجيل الدخول",
            "PASSWORD_RESET": "إعادة تعيين كلمة المرور",
            "EMAIL_VERIFICATION": "تأكيد البريد الإلكتروني",
            "TRANSACTION_CONFIRMATION": "تأكيد المعاملة"
        }
        
        operation = purpose_text.get(purpose, "العملية المطلوبة")
        print(f" إرسال OTP: {purpose} إلى {to_email}")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{self.email_from_name} <{self.email_from}>"
        msg['To'] = to_email
        msg['Subject'] = f"Verification Code - {operation}"
        
        # وقت انتهاء الصلاحية (15 دقيقة من الآن)
        expiry_time = datetime.now() + timedelta(minutes=15)
        expiry_formatted = expiry_time.strftime("%I:%M %p")
        
        # محتوى HTML مع الخط العربي وتحسينات التصميم
        html_body = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>رمز التحقق - سَيان</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Cairo:wght@300;400;600;700&display=swap');
                
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Amiri', 'Cairo', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    color: #333;
                    direction: rtl;
                    text-align: right;
                    direction: rtl;
                    text-align: right;
                    line-height: 1.8;
                }}
                
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background: #ffffff;
                    border-radius: 20px;
                    box-shadow: 0 15px 35px rgba(27, 77, 184, 0.15);
                    overflow: hidden;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #1B4DB8 0%, #00D4C7 100%);
                    padding: 50px 30px;
                    text-align: center;
                    color: white;
                }}
                
                .logo {{
                    font-family: 'Amiri', serif;
                    font-size: 48px;
                    font-weight: 700;
                    margin-bottom: 15px;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
                }}
                
                .subtitle {{
                    font-size: 18px;
                    opacity: 0.95;
                    font-weight: 300;
                }}
                
                .content {{
                    padding: 50px 40px;
                    text-align: center;
                }}
                
                .greeting {{
                    font-family: 'Amiri', serif;
                    font-size: 28px;
                    font-weight: 700;
                    color: #1B4DB8;
                    margin-bottom: 30px;
                }}
                
                .message {{
                    font-size: 18px;
                    color: #555;
                    margin-bottom: 40px;
                    line-height: 2;
                }}
                
                .otp-container {{
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    border: 4px solid #00D4C7;
                    border-radius: 20px;
                    padding: 40px;
                    margin: 40px 0;
                    text-align: center;
                    box-shadow: 0 8px 25px rgba(0, 212, 199, 0.2);
                }}
                
                .otp-code {{
                    font-size: 38px;
                    font-weight: 700;
                    color: #1B4DB8;
                    letter-spacing: 12px;
                    margin: 20px 0;
                    font-family: 'Courier New', monospace;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
                }}
                
                .otp-expiry {{
                    font-size: 14px;
                    color: #dc3545;
                    margin-top: 15px;
                    font-weight: 600;
                }}
                
                .footer {{
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    padding: 40px;
                    text-align: center;
                    color: #666;
                    font-size: 16px;
                }}
                
                .footer-title {{
                    font-family: 'Amiri', serif;
                    font-size: 20px;
                    color: #1B4DB8;
                    margin-bottom: 10px;
                    font-weight: 700;
                }}
                
                .footer-copyright {{
                    margin-top: 15px;
                    font-size: 14px;
                    color: #888;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">سَيان</div>
                    <div class="subtitle">منصة التعليم الإلكتروني الرائدة</div>
                </div>
                
                <div class="content">
                    <div class="greeting">أهلاً وسهلاً {user_name}</div>
                    
                    <div class="message">
                        تم طلب رمز التحقق الخاص بك لـ <strong>{operation}</strong><br>
                        يرجى استخدام الرمز التالي لإتمام العملية
                    </div>
                    
                    <div class="otp-container">
                        <div class="otp-code">{otp_code}</div>
                        <div class="otp-expiry">صالح حتى {expiry_formatted}</div>
                    </div>
                </div>
                
                <div class="footer">
                    <div class="footer-title">فريق منصة سَيان</div>
                    <div class="footer-copyright">© {datetime.now().year} منصة سَيان التعليمية</div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # إرفاق HTML
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        try:            
            print("Attempting to send email to:", to_email)
            print("SMTP server:", self.smtp_server)
            print("SMTP port:", self.smtp_port)
            print("SMTP user:", self.email_user)
            print("SMTP password exists:", "Yes" if self.email_password else "No")
            
            # Check SMTP settings completeness
            if not self.smtp_server or not self.smtp_port or not self.email_user or not self.email_password:
                print("Error: Incomplete email settings")
                print("Check .env file and ensure all SMTP variables exist")
                return False
            
            # Connect to SMTP server based on encryption settings
            print("Connecting to SMTP server...")
            print("Mail encryption:", self.mail_encryption)
            
            # Use encryption setting to determine connection type
            if self.mail_encryption.lower() == 'ssl' or self.smtp_port == 465:
                # SSL connection
                print("Using SSL connection")
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                # TLS connection (port 587 or others)
                print("Using TLS connection")
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            
            print("Connected successfully")
            
            print("Logging into SMTP server...")
            server.login(self.email_user, self.email_password)
            print("Login successful")
            
            text = msg.as_string()
            print("Sending email...")
            server.sendmail(self.email_user, to_email, text)
            print("Email sent")
            
            print("Closing connection...")
            server.quit()
            print("Connection closed")
            
            print("Email sent successfully to:", to_email)
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            print("خطأ في مصادقة SMTP:", str(e))
            print("تحقق من بيانات اعتماد SMTP (SMTP_USERNAME و SMTP_PASSWORD)")
            print("تأكد من أن كلمة المرور صحيحة ومن تفعيل وصول التطبيقات الأقل أمانًا إذا كنت تستخدم Gmail")
            logger.error(f"SMTP Authentication Error: {e}")
            return False
        except smtplib.SMTPConnectError as e:
            print("خطأ في الاتصال بخادم SMTP:", str(e))
            print("تحقق من SMTP_HOST و SMTP_PORT")
            print("تأكد من أن الخادم متاح وأن المنفذ غير محجوب بواسطة جدار الحماية")
            logger.error(f"SMTP Connection Error: {e}")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            print("تم رفض البريد الإلكتروني المستقبل:", str(e))
            print("تحقق من صحة البريد الإلكتروني")
            logger.error(f"SMTP Recipients Refused: {e}")
            return False
        except smtplib.SMTPException as e:
            print("خطأ عام في SMTP:", str(e))
            print("نوع الخطأ:", type(e).__name__)
            logger.error(f"SMTP Exception: {e}")
            return False
        except ConnectionRefusedError as e:
            print("تم رفض الاتصال بخادم SMTP:", str(e))
            print("تأكد من أن خادم SMTP يعمل وأن المنفذ مفتوح")
            logger.error(f"Connection Refused: {e}")
            return False
        except ConnectionResetError as e:
            print("تم قطع الاتصال بخادم SMTP:", str(e))
            print("هذا قد يحدث بسبب:")
            print("1. خادم SMTP يرفض الاتصال")
            print("2. المنفذ محجوب بواسطة جدار الحماية")
            print("3. إعدادات SSL/TLS غير صحيحة")
            print("4. كلمة المرور أو اسم المستخدم غير صحيح")
            print("5. الخادم مشغول أو غير متاح")
            print("محاولة استخدام TLS بدلاً من SSL...")
            logger.error(f"Connection Reset Error: {e}")
            
            # محاولة بديلة باستخدام TLS
            try:
                if self.smtp_port == 465:
                    print("محاولة الاتصال بالمنفذ 587 مع TLS...")
                    server = smtplib.SMTP(self.smtp_server, 587)
                    server.starttls()
                    server.login(self.email_user, self.email_password)
                    server.sendmail(self.email_user, to_email, msg.as_string())
                    server.quit()
                    print("تم الإرسال بنجاح باستخدام TLS!")
                    return True
            except Exception as fallback_e:
                print("فشلت المحاولة البديلة أيضاً:", str(fallback_e))
                logger.error(f"Fallback attempt failed: {fallback_e}")
            
            return False
        except TimeoutError as e:
            print("انتهت مهلة الاتصال بخادم SMTP:", str(e))
            print("تحقق من اتصال الإنترنت وتوفر خادم SMTP")
            logger.error(f"Timeout Error: {e}")
            return False
        except Exception as e:
            print("خطأ غير متوقع في إرسال البريد الإلكتروني:", str(e))
            print("نوع الخطأ:", type(e).__name__)
            import traceback
            print("تفاصيل الخطأ:", traceback.format_exc())
            logger.error(f"Unexpected error in email service: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    # --------------------------------------------------------------------
    # Password reset link email
    # --------------------------------------------------------------------

    def send_password_reset_link(self, to_email: str, reset_link: str) -> bool:
        """Send password reset email containing a button that links to the provided reset URL"""

        from datetime import datetime

        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{self.email_from_name} <{self.email_from}>"
        msg['To'] = to_email
        msg['Subject'] = "إعادة تعيين كلمة المرور - منصة سَيان"

        # Arabic friendly HTML body with button
        html_body = f"""
        <!DOCTYPE html>
        <html dir='rtl' lang='ar'>
        <head>
            <meta charset='UTF-8'>
            <meta name='viewport' content='width=device-width, initial-scale=1.0'>
            <title>إعادة تعيين كلمة المرور</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');
                body {{
                    font-family: 'Cairo', sans-serif;
                    background: #f5f7fa;
                    color: #333;
                    direction: rtl;
                    text-align: right;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background: #ffffff;
                    border-radius: 20px;
                    box-shadow: 0 15px 35px rgba(27, 77, 184, 0.15);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #1B4DB8 0%, #00D4C7 100%);
                    padding: 40px 30px;
                    text-align: center;
                    color: white;
                }}
                .content {{
                    padding: 40px 30px;
                    text-align: center;
                }}
                .button {{
                    display: inline-block;
                    padding: 15px 25px;
                    margin-top: 30px;
                    background-color: #1B4DB8;
                    color: #fff !important;
                    text-decoration: none;
                    font-weight: bold;
                    border-radius: 8px;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    font-size: 14px;
                    color: #888;
                }}
            </style>
        </head>
        <body>
            <div class='container'>
                <div class='header'>
                    <h2>منصة سَيان التعليمية</h2>
                </div>
                <div class='content'>
                    <p>تم طلب إعادة تعيين كلمة المرور لحسابك.</p>
                    <p>اضغط على الزر أدناه لإعادة تعيين كلمة المرور:</p>
                    <a href='{reset_link}' class='button'>إعادة تعيين كلمة المرور</a>
                    <p style='margin-top:25px;'>إذا لم يعمل الزر، يمكنك نسخ الرابط التالي ولصقه في المتصفح:</p>
                    <p>{reset_link}</p>
                </div>
                <div class='footer'>
                    © {datetime.now().year} منصة سَيان التعليمية
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        try:
            # في وضع DEBUG، نطبع المعلومات لكن نستمر في محاولة الإرسال لضمان اختبار كامل
            if settings.DEBUG:
                print("[DEBUG] Attempting to send password reset link email to:", to_email)
                print("[DEBUG] Reset link:", reset_link)

            # Ensure SMTP creds
            if not self.smtp_server or not self.smtp_port or not self.email_user or not self.email_password:
                logger.error("SMTP settings incomplete; cannot send password reset email")
                return False

            # Connect to SMTP
            if self.mail_encryption.lower() == 'ssl' or self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()

            server.login(self.email_user, self.email_password)
            server.sendmail(self.email_user, to_email, msg.as_string())
            server.quit()

            logger.info(f"Password reset email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {e}")
            return False

# إنشاء instance عام للاستخدام
email_service = EmailService() 