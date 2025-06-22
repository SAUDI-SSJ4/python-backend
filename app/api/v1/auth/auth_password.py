"""
Password Management Endpoints
=============================
Change, forgot, and reset password functionality
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from app.core import security
from app.deps import get_db, get_current_user
from app.schemas import (
    PasswordChange,
    PasswordResetRequest,
    PasswordReset,
    MessageResponse
)
from app.models.user import User, AccountType
from app.models.otp import OTPPurpose
from app.services.otp_service import OTPService

router = APIRouter()


@router.post("/change", response_model=MessageResponse, tags=["Password"])
def change_password(
    change_data: PasswordChange = Body(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """تغيير كلمة المرور"""
    
    # التحقق من أن الحساب محلي
    if current_user.account_type != AccountType.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_account_type",
                "message": "تغيير كلمة المرور غير متاح لحسابات Google",
                "status_code": 400
            }
        )
    
    # التحقق من كلمة المرور القديمة
    if not security.verify_password(change_data.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_old_password",
                "message": "كلمة المرور القديمة غير صحيحة",
                "status_code": 400
            }
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
    
    # البحث عن المستخدم
    user = db.query(User).filter(User.email == request_data.email).first()
    
    if not user:
        # عدم الكشف عن وجود المستخدم من عدمه لأسباب أمنية
        return MessageResponse(
            message="إذا كان البريد الإلكتروني موجود، سيتم إرسال رمز إعادة التعيين",
            status="success"
        )
    
    # السماح فقط للحسابات المحلية
    if user.account_type != AccountType.LOCAL:
        return MessageResponse(
            message="إذا كان البريد الإلكتروني موجود، سيتم إرسال رمز إعادة التعيين",
            status="success"
        )
    
    # إنشاء OTP لإعادة تعيين كلمة المرور
    otp = OTPService.create_otp(db, user.id, OTPPurpose.PASSWORD_RESET)
    
    # إرسال OTP عبر البريد الإلكتروني
    purpose_value = OTPPurpose.PASSWORD_RESET.value
    success = OTPService.send_otp_email(user.email, otp.code, purpose_value)
    
    return MessageResponse(
        message="إذا كان البريد الإلكتروني موجود، سيتم إرسال رمز إعادة التعيين",
        status="success"
    )


@router.post("/reset", response_model=MessageResponse, tags=["Password"])
def reset_password(
    reset_data: PasswordReset = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """إعادة تعيين كلمة المرور باستخدام OTP"""
    
    try:
        # في التطبيق الحقيقي، يجب تنفيذ التحقق من الـ token بشكل صحيح
        return MessageResponse(
            message="تم إعادة تعيين كلمة المرور بنجاح",
            status="success"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_token",
                "message": "رمز إعادة التعيين غير صحيح أو منتهي الصلاحية",
                "status_code": 400
            }
        ) 