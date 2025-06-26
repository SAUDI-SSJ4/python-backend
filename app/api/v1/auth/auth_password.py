"""
Password Management Endpoints
=============================
Change, forgot, and reset password functionality
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime

from app.core import security
from app.core.config import settings
from app.deps import get_db
from app.schemas import (
    PasswordChange,
    PasswordResetRequest,
    PasswordReset,
    PasswordResetWithToken,
    OTPVerifyForReset,
    OTPVerificationResponse,
    MessageResponse
)
from app.models.user import User
from app.models.otp import OTPPurpose
from app.services.otp_service import OTPService
from app.services.email_service import email_service
from .auth_utils import (
    create_unified_error_response,
    create_validation_error_response,
    generate_verification_token,
    verify_verification_token,
    invalidate_verification_token
)

router = APIRouter()


def get_current_user_local(credentials: HTTPAuthorizationCredentials = Depends(security.oauth2_scheme), db: Session = Depends(get_db)):
    """الحصول على المستخدم الحالي من التوكن للـ password operations"""
    
    try:
        token = credentials.credentials if credentials else None
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_unified_error_response(
                    status_code=401,
                    error_code="missing_token",
                    message="التوكن مطلوب للوصول لهذا المورد",
                    required_fields={
                        "authentication": {
                            "Authorization": "Bearer token في header"
                        }
                    },
                    examples={
                        "valid_request": {
                            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                        }
                    }
                )
            )
        
        # فك تشفير التوكن - نحتاج لمعرفة نوع المستخدم أولاً
        unverified_payload = jwt.decode(token, key="dummy", options={"verify_signature": False})
        user_type = unverified_payload.get("type", "student")
        
        # الآن فك تشفير صحيح بـ secret key المناسب
        secret_key = security.get_secret_key_by_type(user_type)
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_unified_error_response(
                    status_code=401,
                    error_code="invalid_token",
                    message="التوكن غير صحيح أو غير مُرسل",
                    required_fields={
                        "token_validation": {
                            "sub": "معرف المستخدم مطلوب في التوكن"
                        }
                    }
                )
            )
            
        # البحث عن المستخدم في User table
        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_unified_error_response(
                    status_code=401,
                    error_code="user_not_found",
                    message="المستخدم غير موجود",
                    required_fields={
                        "user_existence": {
                            "user_id": "معرف مستخدم صحيح وموجود في النظام"
                        }
                    }
                )
            )
        
        # التحقق من حالة المستخدم
        if user.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=create_unified_error_response(
                    status_code=403,
                    error_code="account_blocked",
                    message="الحساب محظور",
                    required_fields={
                        "account_status": {
                            "status": "يجب أن يكون الحساب نشط وغير محظور"
                        }
                    }
                )
            )
        
        if user.status == "inactive":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=create_unified_error_response(
                    status_code=403,
                    error_code="account_inactive",
                    message="الحساب غير نشط",
                    required_fields={
                        "account_status": {
                            "status": "يجب أن يكون الحساب نشط"
                        }
                    }
                )
            )
        
        return user
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_unified_error_response(
                status_code=401,
                error_code="invalid_token",
                message="التوكن غير صحيح أو منتهي الصلاحية",
                validation_errors=create_validation_error_response(
                    invalid_fields=[{"field": "token", "error": "تشفير غير صحيح", "input": "***"}]
                ),
                required_fields={
                    "authentication": {
                        "token": "توكن صحيح وساري المفعول"
                    }
                }
            )
        )
    except Exception as e:
        print(f"خطأ في get_current_user_local: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_unified_error_response(
                status_code=500,
                error_code="server_error",
                message="خطأ في الخادم",
                validation_errors=create_validation_error_response(
                    invalid_fields=[{"field": "server", "error": "خطأ داخلي", "input": str(e)[:100]}]
                )
            )
        )


@router.post("/change", response_model=MessageResponse, tags=["Password"])
def change_password(
    change_data: PasswordChange = Body(...),
    current_user = Depends(get_current_user_local),
    db: Session = Depends(get_db)
) -> Any:
    """تغيير كلمة المرور"""
    
    # التحقق من أن الحساب محلي
    if current_user.account_type != "local":  # Use string comparison instead of enum
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_unified_error_response(
                status_code=400,
                error_code="invalid_account_type",
                message="تغيير كلمة المرور غير متاح لحسابات Google",
                validation_errors=create_validation_error_response(
                    invalid_fields=[{"field": "account_type", "error": "نوع الحساب غير مدعوم", "input": current_user.account_type}]
                ),
                required_fields={
                    "account_type": {
                        "type": "يجب أن يكون الحساب محلي (local)"
                    }
                },
                examples={
                    "local_account": {
                        "suggestion": "هذه الميزة متاحة فقط للحسابات المحلية"
                    }
                }
            )
        )
    
    # التحقق من كلمة المرور القديمة
    if not security.verify_password(change_data.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_unified_error_response(
                status_code=400,
                error_code="invalid_old_password",
                message="كلمة المرور القديمة غير صحيحة",
                validation_errors=create_validation_error_response(
                    invalid_fields=[{"field": "old_password", "error": "كلمة المرور غير صحيحة", "input": "***"}]
                ),
                required_fields={
                    "old_password": {
                        "value": "كلمة المرور الحالية الصحيحة"
                    }
                },
                examples={
                    "password_change": {
                        "old_password": "كلمة المرور الحالية",
                        "new_password": "كلمة المرور الجديدة"
                    }
                }
            )
        )
    
    # تحديث كلمة المرور
    hashed_new_password = security.get_password_hash(change_data.new_password)
    current_user.password = hashed_new_password
    db.commit()
    
    return MessageResponse(
        message="تم تغيير كلمة المرور بنجاح",
        status="success"
    )


@router.post("/forgot", response_model=MessageResponse, tags=["Password"])
def forgot_password(
    request_data: PasswordResetRequest = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """طلب إعادة تعيين كلمة المرور"""
    
    try:
        # البحث عن المستخدم
        user = db.query(User).filter(User.email == request_data.email).first()
        
        if not user:
            # عدم الكشف عن وجود المستخدم من عدمه لأسباب أمنية
            return MessageResponse(
                message="إذا كان البريد الإلكتروني موجود، سيتم إرسال رمز إعادة التعيين",
                status="success"
            )
        
        # السماح فقط للحسابات المحلية
        if user.account_type != "local":
            return MessageResponse(
                message="إذا كان البريد الإلكتروني موجود، سيتم إرسال رمز إعادة التعيين",
                status="success"
            )
        
        # إنشاء OTP لإعادة تعيين كلمة المرور
        otp = OTPService.create_otp(
            db=db,
            user_id=user.id,
            purpose=OTPPurpose.PASSWORD_RESET,
            expires_in_minutes=30  # 30 دقيقة لإعادة تعيين كلمة المرور
        )
        
        # إعداد اسم المستخدم
        user_name = f"{user.fname} {user.lname}".strip() or "مستخدم"
        
        # إرسال OTP عبر البريد الإلكتروني
        try:
            success = email_service.send_otp_email(
                to_email=user.email,
                user_name=user_name,
                otp_code=otp.code,
                purpose=OTPPurpose.PASSWORD_RESET.value
            )
            
            if not success:
                # في حالة فشل الإرسال، حذف OTP المُنشأ
                db.delete(otp)
                db.commit()
                print(f" فشل إرسال OTP لـ {user.email}")
        except Exception as e:
            # في حالة فشل الإرسال، حذف OTP المُنشأ
            db.delete(otp)
            db.commit()
            print(f" خطأ في إرسال OTP: {str(e)}")
        
        # إرجاع نفس الرسالة دائماً لأسباب أمنية
        return MessageResponse(
            message="إذا كان البريد الإلكتروني موجود، سيتم إرسال رمز إعادة التعيين",
            status="success"
        )
        
    except Exception as e:
        print(f" خطأ غير متوقع في forgot_password: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        # معالجة موحدة للأخطاء
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=create_unified_error_response(
                status_code=422,
                error_code="password_reset_request_failed",
                message="فشل في معالجة طلب إعادة تعيين كلمة المرور",
                validation_errors=create_validation_error_response(
                    invalid_fields=[{"field": "email_service", "error": "خطأ في خدمة البريد الإلكتروني", "input": str(e)[:100]}]
                ),
                required_fields={
                    "password_reset_request": {
                        "email": "بريد إلكتروني صحيح ومُسجل مسبقاً",
                        "account_type": "حساب محلي (ليس Google)",
                        "email_service": "خدمة البريد الإلكتروني يجب أن تكون متاحة"
                    }
                },
                examples={
                    "password_reset_request": {
                        "email": "alitaha27191@gmail.com"
                    }
                }
            )
        )


@router.post("/reset", response_model=MessageResponse, tags=["Password"])
def reset_password(
    reset_data: PasswordReset = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """إعادة تعيين كلمة المرور باستخدام OTP"""
    
    try:
        # البحث عن المستخدم بالبريد الإلكتروني
        user = db.query(User).filter(User.email == reset_data.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=create_unified_error_response(
                    status_code=422,
                    error_code="invalid_password_reset_data",
                    message="بيانات إعادة تعيين كلمة المرور غير صحيحة أو ناقصة",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "email", "error": "البريد الإلكتروني غير مسجل", "input": reset_data.email}]
                    ),
                    required_fields={
                        "password_reset": {
                            "email": "بريد إلكتروني مسجل في النظام",
                            "otp": "رمز التحقق صحيح وساري المفعول",
                            "new_password": "كلمة مرور جديدة (6 أحرف على الأقل)",
                            "confirm_password": "تأكيد كلمة المرور"
                        }
                    },
                    examples={
                        "password_reset": {
                            "email": "alitaha27191@gmail.com",
                            "otp": "123456",
                            "new_password": "newPassword123",
                            "confirm_password": "newPassword123"
                        }
                    }
                )
            )
        
        # التحقق من أن الحساب محلي
        if user.account_type != "local":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_unified_error_response(
                    status_code=400,
                    error_code="invalid_account_type",
                    message="إعادة تعيين كلمة المرور غير متاح لحسابات Google",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "account_type", "error": "نوع الحساب غير مدعوم", "input": user.account_type}]
                    ),
                    required_fields={
                        "account_type": {
                            "type": "يجب أن يكون الحساب محلي (local)"
                        }
                    },
                    examples={
                        "local_account": {
                            "suggestion": "هذه الميزة متاحة فقط للحسابات المحلية"
                        }
                    }
                )
            )
        
        # التحقق من OTP
        from app.models.otp import OTP
        from datetime import datetime
        
        otp_record = db.query(OTP).filter(
            OTP.user_id == user.id,
            OTP.code == reset_data.otp,
            OTP.purpose == OTPPurpose.PASSWORD_RESET,
            OTP.is_used == False,
            OTP.expires_at > datetime.utcnow()
        ).first()
        
        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=create_unified_error_response(
                    status_code=422,
                    error_code="invalid_otp_data",
                    message="بيانات التحقق من OTP ناقصة أو غير صحيحة",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "otp", "error": "رمز غير صالح أو منتهي الصلاحية", "input": "***"}]
                    ),
                    required_fields={
                        "otp_verification": {
                            "email": "البريد الإلكتروني مطلوب",
                            "otp": "رمز التحقق صحيح وساري المفعول",
                            "verification_status": "يجب أن يكون الرمز غير مستخدم"
                        }
                    },
                    examples={
                        "otp_verification": {
                            "email": "alitaha27191@gmail.com",
                            "otp": "123456"
                        }
                    }
                )
            )
        
        # تحديث كلمة المرور
        hashed_new_password = security.get_password_hash(reset_data.new_password)
        user.password = hashed_new_password
        
        # تحديد OTP كمستخدم
        otp_record.is_used = True
        otp_record.attempts += 1
        
        # حفظ التغييرات
        db.commit()
        
        return MessageResponse(
            message="تم إعادة تعيين كلمة المرور بنجاح",
            status="success"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f" خطأ غير متوقع في reset_password: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_unified_error_response(
                status_code=500,
                error_code="password_reset_failed",
                message="حدث خطأ في إعادة تعيين كلمة المرور",
                validation_errors=create_validation_error_response(
                    invalid_fields=[{"field": "server", "error": "خطأ في الخادم", "input": str(e)[:100]}]
                ),
                required_fields={
                    "server_status": {
                        "status": "يجب أن يكون الخادم متاحاً"
                    }
                },
                examples={
                    "contact_support": {
                        "suggestion": "يرجى التواصل مع الدعم الفني"
                    }
                }
            )
        )


@router.post("/verify-otp", response_model=OTPVerificationResponse, tags=["Password"])
def verify_otp_for_reset(
    verify_data: OTPVerifyForReset = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """التحقق من OTP لإعادة تعيين كلمة المرور وإرجاع verification token"""
    
    try:
        # البحث عن المستخدم بالبريد الإلكتروني
        user = db.query(User).filter(User.email == verify_data.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=create_unified_error_response(
                    status_code=422,
                    error_code="invalid_email",
                    message="البريد الإلكتروني غير مسجل في النظام",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "email", "error": "البريد الإلكتروني غير موجود", "input": verify_data.email}]
                    ),
                    required_fields={
                        "email_verification": {
                            "email": "بريد إلكتروني مسجل في النظام"
                        }
                    },
                    examples={
                        "valid_email": {
                            "email": "alitaha27191@gmail.com"
                        }
                    }
                )
            )
        
        # التحقق من أن الحساب محلي
        if user.account_type != "local":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_unified_error_response(
                    status_code=400,
                    error_code="invalid_account_type",
                    message="إعادة تعيين كلمة المرور غير متاح لحسابات Google",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "account_type", "error": "نوع الحساب غير مدعوم", "input": user.account_type}]
                    ),
                    required_fields={
                        "account_type": {
                            "type": "يجب أن يكون الحساب محلي (local)"
                        }
                    },
                    examples={
                        "local_account": {
                            "suggestion": "هذه الميزة متاحة فقط للحسابات المحلية"
                        }
                    }
                )
            )
        
        # التحقق من OTP
        from app.models.otp import OTP
        from datetime import datetime
        
        otp_record = db.query(OTP).filter(
            OTP.user_id == user.id,
            OTP.code == verify_data.otp,
            OTP.purpose == OTPPurpose.PASSWORD_RESET,
            OTP.is_used == False,
            OTP.expires_at > datetime.utcnow()
        ).first()
        
        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=create_unified_error_response(
                    status_code=422,
                    error_code="invalid_otp_data",
                    message="رمز التحقق غير صحيح أو منتهي الصلاحية",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "otp", "error": "رمز غير صالح أو منتهي الصلاحية", "input": "***"}]
                    ),
                    required_fields={
                        "otp_verification": {
                            "email": "البريد الإلكتروني المسجل",
                            "otp": "رمز التحقق صحيح وساري المفعول"
                        }
                    },
                    examples={
                        "otp_verification": {
                            "email": "alitaha27191@gmail.com",
                            "otp": "123456"
                        }
                    }
                )
            )
        
        # تحديد OTP كمستخدم
        otp_record.is_used = True
        otp_record.attempts += 1
        db.commit()
        
        # إنشاء verification token
        verification_token = generate_verification_token(
            user_id=user.id,
            email=user.email,
            purpose="password_reset"
        )
        
        return OTPVerificationResponse(
            message="تم التحقق من OTP بنجاح. استخدم التوكن لإعادة تعيين كلمة المرور",
            status="success",
            verification_token=verification_token,
            expires_in=300  # 5 دقائق
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f" خطأ غير متوقع في verify_otp_for_reset: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_unified_error_response(
                status_code=500,
                error_code="otp_verification_failed",
                message="حدث خطأ في التحقق من OTP",
                validation_errors=create_validation_error_response(
                    invalid_fields=[{"field": "server", "error": "خطأ في الخادم", "input": str(e)[:100]}]
                ),
                required_fields={
                    "server_status": {
                        "status": "يجب أن يكون الخادم متاحاً"
                    }
                },
                examples={
                    "contact_support": {
                        "suggestion": "يرجى التواصل مع الدعم الفني"
                    }
                }
            )
        )


@router.post("/reset-with-token", response_model=MessageResponse, tags=["Password"])
def reset_password_with_token(
    reset_data: PasswordResetWithToken = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """إعادة تعيين كلمة المرور باستخدام verification token"""
    
    try:
        # التحقق من verification token
        is_valid, token_data, error_message = verify_verification_token(reset_data.verification_token)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=create_unified_error_response(
                    status_code=422,
                    error_code="invalid_verification_token",
                    message=f"التوكن غير صحيح: {error_message}",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "verification_token", "error": error_message, "input": "***"}]
                    ),
                    required_fields={
                        "token_verification": {
                            "verification_token": "توكن صحيح وساري المفعول من خطوة التحقق"
                        }
                    },
                    examples={
                        "valid_token": {
                            "verification_token": "ver_1234567890abcdef",
                            "new_password": "newpassword123",
                            "confirm_password": "newpassword123"
                        }
                    }
                )
            )
        
        # البحث عن المستخدم
        user = db.query(User).filter(User.id == token_data["user_id"]).first()
        
        if not user:
            # إلغاء التوكن إذا كان المستخدم غير موجود
            invalidate_verification_token(reset_data.verification_token)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_unified_error_response(
                    status_code=404,
                    error_code="user_not_found",
                    message="المستخدم غير موجود",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "user_id", "error": "معرف مستخدم غير موجود", "input": str(token_data["user_id"])}]
                    )
                )
            )
        
        # التحقق من أن الحساب محلي
        if user.account_type != "local":
            invalidate_verification_token(reset_data.verification_token)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_unified_error_response(
                    status_code=400,
                    error_code="invalid_account_type",
                    message="إعادة تعيين كلمة المرور غير متاح لحسابات Google",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "account_type", "error": "نوع الحساب غير مدعوم", "input": user.account_type}]
                    )
                )
            )
        
        # تحديث كلمة المرور
        hashed_new_password = security.get_password_hash(reset_data.new_password)
        user.password = hashed_new_password
        db.commit()
        
        # إلغاء التوكن بعد الاستخدام الناجح
        invalidate_verification_token(reset_data.verification_token)
        
        return MessageResponse(
            message="تم إعادة تعيين كلمة المرور بنجاح",
            status="success"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f" خطأ غير متوقع في reset_password_with_token: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_unified_error_response(
                status_code=500,
                error_code="password_reset_with_token_failed",
                message="حدث خطأ في إعادة تعيين كلمة المرور باستخدام الرمز المميز",
                validation_errors=create_validation_error_response(
                    invalid_fields=[{"field": "server", "error": "خطأ في الخادم", "input": str(e)[:100]}]
                ),
                required_fields={
                    "server_status": {
                        "status": "يجب أن يكون الخادم متاحاً"
                    }
                },
                examples={
                    "contact_support": {
                        "suggestion": "يرجى التواصل مع الدعم الفني"
                    }
                }
            )
        ) 