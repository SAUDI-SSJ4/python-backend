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
    OTPVerifyForReset
)
from app.schemas.base import BaseResponse
from app.models.user import User
from app.models.otp import OTPPurpose
from app.services.otp_service import OTPService
from app.services.email_service import email_service
from .auth_utils import (
    create_unified_error_response,
    create_validation_error_response,
    generate_verification_token,
    verify_verification_token,
    invalidate_verification_token,
    create_unified_success_response
)

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


@router.post("/forgot", response_model=BaseResponse, response_model_exclude_none=True, tags=["Password"])
def forgot_password(
    request_data: PasswordResetRequest = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """    """
    
    try:
        user = db.query(User).filter(User.email == request_data.email).first()
        
        if not user:
            return create_unified_success_response(
                status_code=200,
                path="/api/v1/auth/password/forgot"
            )
        
        if user.account_type != "local":
            return create_unified_success_response(
                status_code=200,
                path="/api/v1/auth/password/forgot"
            )
        
        otp = OTPService.create_otp(
            db=db,
            user_id=user.id,
            purpose=OTPPurpose.PASSWORD_RESET,
        )
        
        
        try:
            success = email_service.send_otp_email(
                to_email=user.email,
                user_name=user_name,
                otp_code=otp.code,
                purpose=OTPPurpose.PASSWORD_RESET.value
            )
            
            if not success:
                db.delete(otp)
                db.commit()
        except Exception as e:
            db.delete(otp)
            db.commit()
        
        return create_unified_success_response(
            status_code=200,
            path="/api/v1/auth/password/forgot"
        )
        
    except Exception as e:
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=create_unified_error_response(
                status_code=422,
                error_code="password_reset_request_failed",
                validation_errors=create_validation_error_response(
                ),
                required_fields={
                    "password_reset_request": {
                    }
                },
                examples={
                    "password_reset_request": {
                        "email": "alitaha27191@gmail.com"
                    }
                }
            )
        )

                        
                
                   
                
        

@router.post("/verify-otp", response_model=BaseResponse, response_model_exclude_none=True, tags=["Password"])
def verify_otp_for_reset(
    verify_data: OTPVerifyForReset = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """التحقق من OTP لإعادة تعيين كلمة المرور وإرجاع verification token"""
    
    try:
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
        
        otp_record.is_used = True
        otp_record.attempts += 1
        db.commit()
        
        verification_token = generate_verification_token(
            user_id=user.id,
            email=user.email,
            purpose="password_reset"
        )
        
        return create_unified_success_response(
            data={
                "verification_token": verification_token,
                "expires_in": 300
            },
            message="تم التحقق من OTP بنجاح. استخدم التوكن لإعادة تعيين كلمة المرور",
            status_code=200,
            path="/api/v1/auth/password/verify-otp"
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
        
        invalidate_verification_token(reset_data.verification_token)
        
        return create_unified_success_response(
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
