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
        # Use new mail settings first, fallback to legacy SMTP settings
        self.smtp_server = getattr(settings, 'MAIL_HOST', None) or getattr(settings, 'SMTP_HOST', 'smtp.hostinger.com')
        self.smtp_port = getattr(settings, 'MAIL_PORT', None) or getattr(settings, 'SMTP_PORT', 465)
        self.email_user = getattr(settings, 'MAIL_USERNAME', None) or getattr(settings, 'SMTP_USERNAME', '') or getattr(settings, 'EMAIL_FROM', 'support@sayan.pro')
        self.email_password = getattr(settings, 'MAIL_PASSWORD', None) or getattr(settings, 'SMTP_PASSWORD', '') or getattr(settings, 'EMAIL_PASSWORD', '')
        self.email_from = getattr(settings, 'MAIL_FROM_ADDRESS', None) or getattr(settings, 'EMAIL_FROM', 'support@sayan.pro')
        self.email_from_name = getattr(settings, 'MAIL_FROM_NAME', None) or getattr(settings, 'EMAIL_FROM_NAME', 'SAYAN Platform')
        self.mail_encryption = getattr(settings, 'MAIL_ENCRYPTION', 'tls')
    
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
        print(f"📧 إرسال OTP: {purpose} إلى {to_email}")
        
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
            
            # Connect to SMTP server based on port and encryption
            print("Connecting to SMTP server...")
            
            # Port 465 uses SSL, Port 587 uses TLS
            if self.smtp_port == 465:
                # SSL connection
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                # TLS connection (port 587)
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

# إنشاء instance عام للاستخدام
email_service = EmailService() 