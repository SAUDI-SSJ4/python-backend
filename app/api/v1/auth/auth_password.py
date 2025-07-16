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
    PasswordResetWithToken,
    PasswordForgotRequest,
)
from app.schemas.base import BaseResponse
from app.models.user import User
from .auth_utils import (
    create_unified_error_response,
    create_validation_error_response,
    generate_verification_token,
    verify_verification_token,
    invalidate_verification_token,
    create_unified_success_response
)
from app.services.auth_service import auth_service
from app.services.email_service import email_service
from app.services.otp_service import OTPService
from app.models.otp import OTPPurpose

router = APIRouter()


def get_current_user_local(credentials: HTTPAuthorizationCredentials = Depends(security.oauth2_scheme), db: Session = Depends(get_db)):
    """       password operations"""
    
    try:
        token = credentials.credentials if credentials else None
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_unified_error_response(
                    status_code=401,
                    error_code="missing_token",
                    required_fields={
                        "authentication": {
                        }
                    },
                    examples={
                        "valid_request": {
                            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                        }
                    }
                )
            )
        
        unverified_payload = jwt.decode(token, key="dummy", options={"verify_signature": False})
        user_type = unverified_payload.get("type", "student")
        
        secret_key = security.get_secret_key_by_type(user_type)
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_unified_error_response(
                    status_code=401,
                    error_code="invalid_token",
                    required_fields={
                        "token_validation": {
                        }
                    }
                )
            )
            
        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_unified_error_response(
                    status_code=401,
                    error_code="user_not_found",
                    required_fields={
                        "user_existence": {
                        }
                    }
                )
            )
        
        if user.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=create_unified_error_response(
                    status_code=403,
                    error_code="account_blocked",
                    required_fields={
                        "account_status": {
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
                    required_fields={
                        "account_status": {
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
                validation_errors=create_validation_error_response(
                ),
                required_fields={
                    "authentication": {
                    }
                }
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_unified_error_response(
                status_code=500,
                error_code="server_error",
                validation_errors=create_validation_error_response(
                )
            )
        )


@router.post("/change", response_model=BaseResponse, response_model_exclude_none=True, tags=["Password"])
def change_password(
    change_data: PasswordChange = Body(...),
    current_user = Depends(get_current_user_local),
    db: Session = Depends(get_db)
) -> Any:
    """تغيير كلمة المرور"""
    
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
    
    hashed_new_password = security.get_password_hash(change_data.new_password)
    current_user.password = hashed_new_password
    db.commit()
    
    return create_unified_success_response(
        message="تم تغيير كلمة المرور بنجاح",
        status_code=200,
        path="/api/v1/auth/password/change"
    )


@router.post("/reset-with-token", response_model=BaseResponse, response_model_exclude_none=True, tags=["Password"])
def reset_password_with_token(
    reset_data: PasswordResetWithToken = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """     verification token"""
    
    try:
        is_valid, token_data, error_message = verify_verification_token(reset_data.verification_token)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=create_unified_error_response(
                    status_code=422,
                    error_code="invalid_verification_token",
                    validation_errors=create_validation_error_response(
                        invalid_fields=[{"field": "verification_token", "error": error_message, "input": "***"}]
                    ),
                    required_fields={
                        "token_verification": {
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
        
        user = db.query(User).filter(User.id == token_data["user_id"]).first()
        
        if not user:
            invalidate_verification_token(reset_data.verification_token)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_unified_error_response(
                    status_code=404,
                    error_code="user_not_found",
                    validation_errors=create_validation_error_response(
                    )
                )
            )
        
        if user.account_type != "local":
            invalidate_verification_token(reset_data.verification_token)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_unified_error_response(
                    status_code=400,
                    error_code="invalid_account_type",
                    validation_errors=create_validation_error_response(
                    )
                )
            )
        
        hashed_new_password = security.get_password_hash(reset_data.new_password)
        user.password = hashed_new_password
        db.commit()
        
        # إبطال التوكن المستعمل
        invalidate_verification_token(reset_data.verification_token)
        
        # إنشاء توكنات تسجيل الدخول مباشرة
        tokens = auth_service.create_tokens(user.id, user.user_type)
        
        return create_unified_success_response(
            data=tokens,
            message="تم إعادة تعيين كلمة المرور بنجاح",
            status_code=200,
            path="/api/v1/auth/password/reset-with-token"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_unified_error_response(
                status_code=500,
                error_code="password_reset_with_token_failed",
                validation_errors=create_validation_error_response(
                ),
                required_fields={
                    "server_status": {
                    }
                },
                examples={
                    "contact_support": {
                    }
                }
            )
        )

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


@router.post("/reset", include_in_schema=False)
def deprecated_reset_password():
    """مسار قديم لإعادة تعيين كلمة المرور، تم تعطيله لصالح /password/reset-with-token"""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=create_unified_error_response(
            status_code=410,
            error_type="Gone",
            message="تم إيقاف هذا المسار. استخدم /password/reset-with-token بدلاً من ذلك."
        )
    ) 

@router.post("/forgot", response_model=BaseResponse, response_model_exclude_none=True, tags=["Password"])
def forgot_password(
    request_data: PasswordForgotRequest,
    db: Session = Depends(get_db)
) -> Any:
    """إرسال رابط إعادة تعيين كلمة المرور إلى البريد الإلكتروني"""

    try:
        email = request_data.email.lower().strip()
        redirect_url = request_data.redirect_url.strip()

        # محاولة العثور على المستخدم، لكن لا نفصح عن وجوده لأسباب أمنية
        user, user_type = auth_service.get_user_by_email(db, email)

        if user:
            # إنشاء verification_token للغرض password_reset (يُستخدم مباشرة بدون خطوة OTP Verify)
            verification_token = generate_verification_token(
                user_id=user.id,
                email=email,
                purpose="password_reset",
                expires_in_minutes=15
            )

            # بناء الرابط النهائي مع التوكن
            separator = '&' if '?' in redirect_url else '?'
            reset_link = f"{redirect_url}{separator}verification_token={verification_token}"

            # إرسال الرابط عبر البريد
            send_ok = email_service.send_password_reset_link(email, reset_link)

            if not send_ok:
                # في حال فشل الإرسال أبطل التوكن
                invalidate_verification_token(verification_token)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=create_unified_error_response(
                        status_code=500,
                        error_code="email_send_failed",
                        message="فشل في إرسال رابط إعادة تعيين كلمة المرور",
                        path="/api/v1/auth/password/forgot"
                    )
                )

        # في كل الأحوال نرجع استجابة ناجحة دون كشف وجود المستخدم
        resp_data = {"email": email}
        if settings.DEBUG and user:
            resp_data.update({"verification_token": verification_token, "reset_link": reset_link})

        return create_unified_success_response(
            data=resp_data,
            message="إذا كان البريد الإلكتروني مسجلاً لدينا سيتم إرسال رابط إعادة تعيين كلمة المرور",
            status_code=200,
            path="/api/v1/auth/password/forgot"
        )

    except Exception as e:
        import traceback
        print("Traceback:", traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_unified_error_response(
                status_code=500,
                error_code="forgot_password_failed",
                validation_errors=create_validation_error_response(),
            )
        ) 
