"""
OTP Management Endpoints
========================
OTP request and verification functionality
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas import (
    Token,
    OTPRequest,
    OTPVerify,
    MessageResponse
)
from app.models.user import User, UserStatus
from app.models.otp import OTPPurpose
from app.services.otp_service import OTPService
from app.services.email_service import email_service
from .auth_utils import generate_user_tokens, get_current_timestamp

router = APIRouter()


@router.post("/request", response_model=MessageResponse, tags=["OTP"])
def request_otp(
    otp_request: OTPRequest = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """طلب رمز التحقق (OTP)"""
    
    try:
        # البحث عن المستخدم
        user = db.query(User).filter(User.email == otp_request.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "user_not_found",
                    "message": "لم يتم العثور على مستخدم بهذا البريد الإلكتروني",
                    "status_code": 404,
                    "timestamp": get_current_timestamp()
                }
            )
        
        # التحقق من صحة الغرض
        valid_purposes = [purpose.value for purpose in OTPPurpose]
        normalized_purpose = otp_request.purpose.lower()
        
        if normalized_purpose not in valid_purposes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_purpose",
                    "message": f"الغرض يجب أن يكون واحد من {valid_purposes}",
                    "status_code": 400,
                    "timestamp": get_current_timestamp()
                }
            )
        
        # العثور على enum المطابق
        purpose = None
        for p in OTPPurpose:
            if p.value == normalized_purpose:
                purpose = p
                break
        
        if not purpose:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_purpose",
                    "message": "غرض غير صحيح",
                    "status_code": 400,
                    "timestamp": get_current_timestamp()
                }
            )
        
        # إنشاء OTP
        print(f"🔄 Creating OTP for user {user.id} with purpose {purpose}")
        try:
            otp = OTPService.create_otp(db, user.id, purpose, expires_in_minutes=15)
            print(f"✅ OTP created successfully: {otp.code}")
        except Exception as e:
            print(f"❌ Failed to create OTP: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "otp_generation_failed",
                    "message": "فشل في إنشاء رمز التحقق",
                    "status_code": 500,
                    "details": str(e),
                    "timestamp": get_current_timestamp()
                }
            )
        
        # إرسال OTP
        print(f"📧 Attempting to send OTP to {user.email}")
        try:
            user_name = f"{user.fname} {user.lname}".strip() or "مستخدم"
            print(f"👤 User name: {user_name}")
            print(f"🔢 OTP Code: {otp.code}")
            print(f"🎯 Purpose: {normalized_purpose}")
            
            success = email_service.send_otp_email(
                to_email=user.email,
                user_name=user_name,
                otp_code=otp.code,
                purpose=normalized_purpose
            )
            
            print(f"📬 Email send result: {success}")
            
        except Exception as e:
            print(f"❌ Exception during email sending: {str(e)}")
            import traceback
            print(f"📋 Traceback: {traceback.format_exc()}")
            success = False
        
        if not success:
            # إذا فشل إرسال البريد، احذف OTP من قاعدة البيانات
            try:
                db.delete(otp)
                db.commit()
            except:
                pass
                
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "otp_send_failed",
                    "message": "فشل في إرسال رمز التحقق",
                    "status_code": 500,
                    "suggestion": "يرجى التحقق من صحة البريد الإلكتروني والمحاولة مرة أخرى",
                    "timestamp": get_current_timestamp()
                }
            )
        
        print(f"✅ OTP sent successfully to {user.email}")
        return MessageResponse(
            message="تم إرسال رمز التحقق إلى بريدك الإلكتروني بنجاح",
            status="success",
            data={
                "email": user.email,
                "expires_in": 900,  # 15 minutes in seconds
                "timestamp": get_current_timestamp()
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Unexpected error in request_otp: {str(e)}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "حدث خطأ غير متوقع",
                "status_code": 500,
                "details": str(e),
                "timestamp": get_current_timestamp()
            }
        )


@router.post("/verify", response_model=Token, tags=["OTP"])
def verify_otp(
    otp_verify: OTPVerify = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """التحقق من رمز OTP"""
    
    try:
        # البحث عن المستخدم برقم الهاتف أو البريد الإلكتروني
        user = None
        if hasattr(otp_verify, 'phone') and otp_verify.phone:
            user = db.query(User).filter(User.phone_number == otp_verify.phone).first()
        elif hasattr(otp_verify, 'email') and otp_verify.email:
            user = db.query(User).filter(User.email == otp_verify.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "user_not_found",
                    "message": "لم يتم العثور على المستخدم",
                    "status_code": 404,
                    "timestamp": get_current_timestamp()
                }
            )
        
        # التحقق من OTP
        try:
            purpose = OTPPurpose(otp_verify.purpose)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_purpose",
                    "message": "غرض غير صحيح",
                    "status_code": 400,
                    "timestamp": get_current_timestamp()
                }
            )
        
        success, error_message = OTPService.verify_otp(db, user.id, otp_verify.otp, purpose)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "otp_verification_failed",
                    "message": error_message or "فشل في التحقق من رمز OTP",
                    "status_code": 400,
                    "timestamp": get_current_timestamp()
                }
            )

        # تحديث حالة التحقق إذا لزم الأمر
        if purpose == OTPPurpose.EMAIL_VERIFICATION and not user.verified:
            user.verified = True
            user.status = UserStatus.ACTIVE
            db.commit()
        
        return generate_user_tokens(user, db)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Unexpected error in verify_otp: {str(e)}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "حدث خطأ غير متوقع",
                "status_code": 500,
                "details": str(e),
                "timestamp": get_current_timestamp()
            }
        ) 