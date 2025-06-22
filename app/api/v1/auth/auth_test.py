"""
Testing Endpoints
================
Development and testing functionality
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
import random

from app.deps import get_db
from app.schemas.auth import (
    Token,
    GoogleRegisterRequest
)
from app.models.user import User
from app.models.student import Student
from app.models.academy import Academy, AcademyUser
from .auth_utils import (
    get_current_timestamp,
    generate_user_tokens,
    generate_academy_id,
    generate_academy_slug,
    generate_academy_username
)

router = APIRouter()


@router.post("/debug", tags=["Testing"])
def test_debug_data(
    google_request: GoogleRegisterRequest = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """اختبار البيانات المرسلة من Frontend"""
    
    return {
        "message": "تم استلام البيانات بنجاح ✅",
        "received_data": {
            "google_token_length": len(google_request.google_token),
            "google_token_preview": google_request.google_token[:50] + "..." if len(google_request.google_token) > 50 else google_request.google_token,
            "user_type": google_request.user_type,
        },
        "validation_status": {
            "google_token_exists": bool(google_request.google_token),
            "user_type_valid": google_request.user_type in ["student", "academy"],
            "schema_validation": "passed"
        },
        "timestamp": get_current_timestamp()
    }


@router.post("/simple-register", response_model=Token, tags=["Testing"])
def test_simple_register(
    google_request: GoogleRegisterRequest = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """تسجيل تجريبي بدون التحقق من Google Token للاختبار فقط"""
    
    # إنشاء بيانات تجريبية
    random_id = random.randint(1000, 9999)
    test_email = f"test_{google_request.user_type}_{random_id}@test.com"
    
    # تحقق من وجود المستخدم
    existing_user = db.query(User).filter(User.email == test_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "test_user_exists",
                "message": "مستخدم تجريبي بهذا البريد موجود",
                "status_code": 409
            }
        )
    
    # إنشاء مستخدم تجريبي
    new_user = User(
        fname=f"Test",
        lname=f"{google_request.user_type.title()} {random_id}",
        email=test_email,
        user_type=google_request.user_type,
        account_type="google",
        status="active",
        verified=True,
        google_id=f"test_google_id_{random_id}",
        avatar="https://via.placeholder.com/150"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # إنشاء profile
    if google_request.user_type == "student":
        student = Student(
            user_id=new_user.id,
            birth_date=None,
            gender=None
        )
        db.add(student)
        db.commit()
    else:
        academy_name = f"Test Academy {random_id}"
        academy = Academy(
            user_id=new_user.id,
            name=academy_name,
            academy_id=generate_academy_id(academy_name),
            slug=generate_academy_slug(academy_name),
            user_name=generate_academy_username(academy_name),
            status="active"
        )
        db.add(academy)
        db.commit()
        db.refresh(academy)
        
        academy_user = AcademyUser(
            user_id=new_user.id,
            academy_id=academy.id,
            user_role="owner"
        )
        db.add(academy_user)
        db.commit()
    
    return generate_user_tokens(new_user, db) 