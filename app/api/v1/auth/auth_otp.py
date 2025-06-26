"""
OTP Management Endpoints
========================
OTP request and verification functionality with comprehensive support
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas import (
    Token,
    OTPRequest,
    OTPVerify,
    MessageResponse,
    OTPResponse,
    OTPStatusResponse
)
from app.models.user import User, UserStatus
from app.models.otp import OTPPurpose
from app.services.otp_service import OTPService
from app.services.email_service import email_service
from .auth_utils import (
    generate_user_tokens, 
    get_current_timestamp,
    create_unified_error_response,
    create_validation_error_response
)

router = APIRouter()





@router.post("/request", response_model=OTPResponse, tags=["OTP"])
def request_otp(
    otp_request: OTPRequest = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """
    طلب رمز التحقق (OTP) مع دعم شامل لجميع الأغراض
    
    ## الأغراض المدعومة:
    
    ### أغراض التحقق الأساسية:
    - `email_verification`: تحقق من البريد الإلكتروني
    - `phone_verification`: تحقق من رقم الهاتف
    - `account_activation`: تفعيل الحساب
    
    ### أغراض الأمان:
    - `login`: تسجيل الدخول
    - `password_reset`: إعادة تعيين كلمة المرور
    - `change_password`: تغيير كلمة المرور
    - `two_factor_auth`: المصادقة الثنائية
    - `security_verification`: التحقق الأمني
    
    ### أغراض التحديث:
    - `email_update`: تحديث البريد الإلكتروني
    - `phone_update`: تحديث رقم الهاتف
    
    ### أغراض المعاملات:
    - `transaction_confirmation`: تأكيد المعاملة
    - `payment_confirmation`: تأكيد الدفع
    
    ### أغراض الحساب:
    - `account_deletion`: حذف الحساب
    """
    
    try:
        # البحث عن المستخدم
        user = None
        if otp_request.email:
            user = db.query(User).filter(User.email == otp_request.email).first()
        elif otp_request.phone:
            user = db.query(User).filter(User.phone_number == otp_request.phone).first()
        
        if not user:
            contact_method = "البريد الإلكتروني" if otp_request.email else "رقم الهاتف"
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_unified_error_response(
                    status_code=404,
                    error_code="user_not_found",
                    message=f"لم يتم العثور على مستخدم بهذا {contact_method}",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "contact", "error": "المستخدم غير موجود", "input": otp_request.email or otp_request.phone}]
                    ),
                    required_fields={
                        "registration": {
                            "suggestion": "يرجى التسجيل أولاً باستخدام endpoint /register"
                        }
                    },
                    examples={
                        "register_first": {
                            "email": "user@example.com",
                            "suggestion": "قم بالتسجيل أولاً للحصول على حساب"
                        }
                    }
                )
            )
        
        # التحقق من صحة الغرض
        try:
            purpose = OTPPurpose(otp_request.purpose)
        except ValueError:
            valid_purposes = [p.value for p in OTPPurpose]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_unified_error_response(
                    status_code=400,
                    error_code="invalid_purpose",
                    message="الغرض المطلوب غير صحيح",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "purpose", "error": "غرض غير صالح", "input": otp_request.purpose}]
                    ),
                    required_fields={
                        "valid_purposes": {
                            "email_verification": "تحقق من البريد الإلكتروني",
                            "phone_verification": "تحقق من رقم الهاتف",
                            "password_reset": "إعادة تعيين كلمة المرور",
                            "login": "تسجيل الدخول",
                            "two_factor_auth": "المصادقة الثنائية"
                        }
                    },
                    examples={
                        "valid_request": {
                            "email": "user@example.com",
                            "purpose": "email_verification",
                            "expires_in_minutes": 15
                        },
                        "all_valid_purposes": valid_purposes
                    }
                )
            )
        
        # التحقق من حالة المستخدم للعمليات الحساسة
        sensitive_purposes = [
            OTPPurpose.ACCOUNT_DELETION,
            OTPPurpose.PAYMENT_CONFIRMATION,
            OTPPurpose.TRANSACTION_CONFIRMATION
        ]
        
        if purpose in sensitive_purposes and user.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=create_unified_error_response(
                    status_code=403,
                    error_code="account_blocked",
                    message="الحساب محظور، لا يمكن تنفيذ هذه العملية",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "account_status", "error": "الحساب محظور", "input": user.status}]
                    ),
                    required_fields={
                        "account_status": {
                            "status": "يجب أن يكون الحساب نشطاً"
                        }
                    },
                    examples={
                        "contact_support": {
                            "email": "support@example.com",
                            "message": "تواصل مع الدعم الفني لإعادة تفعيل الحساب"
                        }
                    }
                )
            )
        
        # إنشاء OTP
        print(f"إنشاء OTP للمستخدم {user.id} للغرض {purpose.value}")
        try:
            otp = OTPService.create_otp(
                db=db,
                user_id=user.id,
                purpose=purpose,
                expires_in_minutes=otp_request.expires_in_minutes
            )
            print(f" تم إنشاء OTP بنجاح: {otp.code}")
        except Exception as e:
            print(f" خطأ غير متوقع في إنشاء OTP: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_unified_error_response(
                    status_code=500,
                    error_code="otp_generation_failed",
                    message="فشل في إنشاء رمز التحقق",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "server", "error": "خطأ في الخادم", "input": str(e)[:100]}]
                    ),
                    required_fields={
                        "server_status": {
                            "status": "يجب أن يكون الخادم متاحاً"
                        }
                    },
                    examples={
                        "retry": {
                            "suggestion": "يرجى المحاولة مرة أخرى أو التواصل مع الدعم الفني"
                        }
                    }
                )
            )
        
        # إرسال OTP
        print(f" محاولة إرسال OTP إلى {user.email or user.phone_number}")
        try:
            user_name = f"{user.fname} {user.lname}".strip() or "مستخدم"
            
            # تحديد طريقة الإرسال
            if otp_request.email:
                success = OTPService.send_otp_email(
                    email=user.email,
                    code=otp.code,
                    purpose=purpose.value,
                    user_name=user_name
                )
                sent_to = f"{user.email[:3]}***@{user.email.split('@')[1]}" if user.email else None
            else:
                success = OTPService.send_otp_sms(
                    phone=user.phone_number,
                    code=otp.code,
                    purpose=purpose.value
                )
                sent_to = f"***{user.phone_number[-3:]}" if user.phone_number else None
            
            print(f" نتيجة الإرسال: {success}")
            
        except Exception as e:
            print(f" استثناء أثناء الإرسال: {str(e)}")
            success = False
        
        # إعداد الاستجابة
        if success:
            # الحصول على عدد المحاولات المسموحة
            max_attempts = OTPService.MAX_ATTEMPTS.get(purpose, 3)
            expiry_minutes = OTPService.EXPIRY_MINUTES.get(purpose, 10)
            
            return OTPResponse(
                message=f"تم إرسال رمز التحقق بنجاح للغرض: {OTPService.get_purpose_description(purpose)}",
                status="success",
                expires_in=expiry_minutes * 60,  # بالثواني
                attempts_remaining=max_attempts,
                purpose=purpose.value,
                sent_to=sent_to,
                expires_at=otp.expires_at.isoformat(),
                timestamp=get_current_timestamp()
            )
        else:
            # حذف OTP إذا فشل الإرسال
            db.delete(otp)
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_unified_error_response(
                    status_code=500,
                    error_code="otp_send_failed",
                    message="فشل في إرسال رمز التحقق",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "email_service", "error": "فشل الإرسال", "input": user.email or user.phone_number}]
                    ),
                    required_fields={
                        "email_service": {
                            "status": "يجب أن تكون خدمة البريد متاحة"
                        }
                    },
                    examples={
                        "retry": {
                            "suggestion": "يرجى المحاولة مرة أخرى أو استخدام وسيلة اتصال أخرى"
                        }
                    }
                )
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f" خطأ غير متوقع في request_otp: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_unified_error_response(
                status_code=500,
                error_code="internal_server_error",
                message="حدث خطأ غير متوقع",
                validation_errors=create_validation_error_response(
                    invalid_fields=[{"field": "system", "error": "خطأ في النظام", "input": str(e)[:100]}]
                ),
                required_fields={
                    "system_status": {
                        "status": "يجب أن يكون النظام مستقراً"
                    }
                },
                examples={
                    "contact_support": {
                        "suggestion": "يرجى التواصل مع الدعم الفني"
                    }
                }
            )
        )


@router.post("/verify", response_model=Token, tags=["OTP"])
def verify_otp(
    otp_verify: OTPVerify = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """
    التحقق من رمز OTP مع دعم شامل لجميع الأغراض
    
    يدعم التحقق من جميع أنواع OTP مع ميزات أمان متقدمة
    """
    
    try:
        # البحث عن المستخدم
        user = None
        if otp_verify.email:
            user = db.query(User).filter(User.email == otp_verify.email).first()
        elif otp_verify.phone:
            user = db.query(User).filter(User.phone_number == otp_verify.phone).first()
        
        if not user:
            # رسالة مثل ملف الرسالة المرفق
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=create_unified_error_response(
                    status_code=422,
                    error_code="invalid_otp_data",
                    message="بيانات التحقق من OTP ناقصة أو غير صحيحة",
                    required_fields={
                        "otp_verification": {
                            "email": "البريد الإلكتروني يجب أن يكون مسجلاً مسبقاً",
                            "otp": "رمز التحقق مطلوب",
                            "account_status": "الحساب يجب أن يكون نشطاً"
                        }
                    },
                    examples={
                        "otp_verification": {
                            "email": "ali.taha27191@gmail.com",
                            "otp": "123456"
                        }
                    }
                )
            )
        
        # البحث عن أي OTP صالح للمستخدم (بغض النظر عن الغرض)
        from app.models.otp import OTP
        from datetime import datetime
        
        otp_record = db.query(OTP).filter(
            OTP.user_id == user.id,
            OTP.code == otp_verify.otp,
            OTP.is_used == False,
            OTP.expires_at > datetime.utcnow()
        ).first()
        
        if not otp_record:
            # رسالة مثل ملف الرسالة المرفق
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=create_unified_error_response(
                    status_code=422,
                    error_code="invalid_otp_data",
                    message="بيانات التحقق من OTP ناقصة أو غير صحيحة",
                    required_fields={
                        "otp_verification": {
                            "email": "البريد الإلكتروني مطلوب",
                            "otp": "رمز التحقق صحيح وساري المفعول",
                            "verification_status": "يجب أن يكون الرمز غير مستخدم"
                        }
                    },
                    examples={
                        "otp_verification": {
                            "email": "ali.taha27191@gmail.com",
                            "otp": "123456"
                        }
                    }
                )
            )
        
        # تحديث OTP كمستخدم
        otp_record.is_used = True
        otp_record.attempts += 1
        db.commit()
        
        success = True
        purpose = OTPPurpose(otp_record.purpose)

        # تحديث حالة التحقق إذا لزم الأمر
        if purpose == OTPPurpose.EMAIL_VERIFICATION and not user.verified:
            user.verified = True
            if user.status == "pending_verification":
                user.status = "active"
            db.commit()
        elif purpose == OTPPurpose.PHONE_VERIFICATION:
            # TODO: إضافة حقل phone_verified إلى User model
            pass
        elif purpose == OTPPurpose.ACCOUNT_ACTIVATION:
            user.status = "active"
            user.verified = True
            db.commit()
        
        # إنشاء tokens للمستخدم
        return generate_user_tokens(user, db)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f" خطأ غير متوقع في verify_otp: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_unified_error_response(
                status_code=500,
                error_code="internal_server_error",
                message="حدث خطأ غير متوقع أثناء التحقق",
                validation_errors=create_validation_error_response(
                    invalid_fields=[{"field": "system", "error": "خطأ في النظام", "input": str(e)[:100]}]
                ),
                required_fields={
                    "system_status": {
                        "status": "يجب أن يكون النظام مستقراً"
                    }
                },
                examples={
                    "contact_support": {
                        "suggestion": "يرجى التواصل مع الدعم الفني"
                    }
                }
            )
        )
