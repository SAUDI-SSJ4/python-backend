"""
Google Auth Test Endpoints - للاختبار فقط
===========================================
endpoints للاختبار والتطوير بدون الحاجة لـ Google Token حقيقي
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
import random
import string
from typing import Any

from app.core import security
from app.deps import get_db
from app.schemas.auth import GoogleRegisterRequest, Token
from app.models.user import User
from app.models.student import Student
from app.models.academy import Academy, AcademyUser
from app.api.v1.auth.general import (
    generate_user_tokens, 
    generate_academy_id, 
    get_current_timestamp
)

router = APIRouter()


def generate_academy_slug(academy_name: str) -> str:
    """Generate URL-friendly slug for academy"""
    import re
    
    # Convert to lowercase and replace spaces with hyphens
    slug = academy_name.lower()
    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Add random suffix to ensure uniqueness
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{slug}-{suffix}"


def generate_academy_username(academy_name: str) -> str:
    """Generate username for academy"""
    import re
    
    # Convert to lowercase and replace spaces with underscores
    username = academy_name.lower()
    # Remove non-alphanumeric characters except underscores
    username = re.sub(r'[^a-z0-9\s_]', '', username)
    # Replace spaces with underscores
    username = re.sub(r'\s+', '_', username)
    # Remove multiple consecutive underscores
    username = re.sub(r'_+', '_', username)
    # Remove leading/trailing underscores
    username = username.strip('_')
    
    # Add random suffix to ensure uniqueness
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{username}_{suffix}"


@router.post(
    "/google/register-test", 
    response_model=Token, 
    tags=["🧪 Google Test - للاختبار"],
    status_code=status.HTTP_201_CREATED,
    summary="📝 Google Register Test - تسجيل اختبار مبسط",
    description="""
    **تسجيل اختبار مبسط بدون التحقق من Google Token**
    
    للاختبار والتطوير فقط - لا يتطلب Google Token صحيح
    
    **المطلوب:**
    - `google_token`: أي نص (للاختبار فقط)
    - `user_type`: نوع المستخدم (student أو academy)
    
    **مثال:**
    ```json
    {
      "google_token": "test_token_123",
      "user_type": "student"
    }
    ```
    """
)
def google_register_test(
    google_request: GoogleRegisterRequest = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """تسجيل اختبار مبسط بدون التحقق من Google Token"""
    
    # بيانات اختبار ثابتة
    random_id = random.randint(1000, 9999)
    google_user_data = {
        'id': f'test_google_id_{google_request.user_type}_{random_id}',
        'email': f'test_{google_request.user_type}_{random.randint(100, 999)}@gmail.com',
        'name': f'Test {google_request.user_type.title()} {random_id}',
        'picture': 'https://via.placeholder.com/150',
        'given_name': 'Test',
        'family_name': f'{google_request.user_type.title()} {random_id}',
        'email_verified': True
    }
    
    # تحقق من وجود المستخدم بنفس البريد الإلكتروني
    existing_user = db.query(User).filter(
        User.email == google_user_data['email']
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "user_already_exists",
                "message": "يوجد حساب اختبار بهذا البريد الإلكتروني بالفعل",
                "status_code": 409,
                "timestamp": get_current_timestamp()
            }
        )
    
    # إنشاء مستخدم جديد
    new_user = User(
        fname=google_user_data.get('given_name') or 'Test',
        lname=google_user_data.get('family_name') or 'User',
        email=google_user_data['email'],
        phone_number=None,
        password=None,
        user_type=google_request.user_type,
        account_type="google",
        status="active",
        verified=True,
        google_id=google_user_data['id'],
        avatar=google_user_data.get('picture')
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # إنشاء profile حسب النوع
    if google_request.user_type == "student":
        student = Student(
            user_id=new_user.id,
            birth_date=None,
            gender=None
        )
        db.add(student)
        db.commit()
    else:  # academy
        academy_name = f"Test {new_user.fname} Academy"
        academy_id = generate_academy_id(academy_name)
        academy_slug = generate_academy_slug(academy_name)
        user_name = generate_academy_username(academy_name)
        
        academy = Academy(
            user_id=new_user.id,
            name=academy_name,
            academy_id=academy_id,
            slug=academy_slug,
            user_name=user_name,
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


@router.post(
    "/google/debug", 
    tags=["🧪 Google Test - للاختبار"],
    status_code=status.HTTP_200_OK,
    summary="🔍 Google Debug - فحص البيانات",
    description="فحص البيانات المرسلة بدون معالجة"
)
def google_debug(
    google_request: GoogleRegisterRequest = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """فحص البيانات المرسلة"""
    
    return {
        "message": "تم استلام البيانات بنجاح",
        "received_data": {
            "google_token": google_request.google_token[:50] + "..." if len(google_request.google_token) > 50 else google_request.google_token,
            "user_type": google_request.user_type,
            "token_length": len(google_request.google_token)
        },
        "validation": {
            "google_token_provided": bool(google_request.google_token),
            "user_type_valid": google_request.user_type in ["student", "academy"],
            "timestamp": get_current_timestamp()
        }
    } 