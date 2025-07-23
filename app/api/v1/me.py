"""
User Profile Endpoint
=====================
Current user profile management with complete academy details
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.student import Student
from app.models.academy import AcademyUser, Academy
from app.models.admin import Admin
from app.models.template import Template, About, Slider, Faq, Opinion
from app.models.settings import Settings
from app.schemas.base import BaseResponse
from app.core.response_handler import SayanSuccessResponse
from app.crud.academy_content import CRUDAcademyContent

router = APIRouter()

@router.get("/me", response_model=None, summary="Get Current User Profile")
async def get_current_user_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """Returns the current authenticated user's profile with complete academy details"""
    user = current_user
    user_type = user.user_type
    
    user_info = {
        "id": user.id,
        "email": user.email,
        "fname": user.fname,
        "lname": user.lname,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "user_type": user.user_type,
        "account_type": user.account_type,
        "status": user.status,
        "verified": user.verified,
        "avatar": user.avatar,
        "banner": user.banner,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
    
    student_profile = None
    academy_memberships = []

    if user_type == "student":
        student = db.query(Student).filter(Student.user_id == user.id).first()
        if student:
            student_profile = {
                "id": student.id,
                "date_of_birth": getattr(student, "date_of_birth", None),
                "gender": getattr(student, "gender", ""),
                "city": getattr(student, "city", ""),
                "education_level": getattr(student, "education_level", ""),
                "bio": getattr(student, "bio", ""),
                "status": getattr(student, "status", "active"),
            }
        user_info["student_profile"] = student_profile
        
    elif user_type == "academy":
        memberships = db.query(AcademyUser).filter(AcademyUser.user_id == user.id).all()
        academy_content = CRUDAcademyContent()
        
        for membership in memberships:
            academy = db.query(Academy).filter(Academy.id == membership.academy_id).first()
            if academy:
                # Get academy content with error handling
                try:
                    template = academy_content.get_template(db, academy.id)
                except Exception:
                    template = None
                
                try:
                    about = academy_content.get_about(db, academy.id)
                except Exception:
                    about = None
                
                try:
                    sliders = academy_content.get_sliders(db, academy.id)
                except Exception:
                    sliders = []
                
                try:
                    faqs = academy_content.get_faqs(db, academy.id)
                except Exception:
                    faqs = []
                
                try:
                    opinions = academy_content.get_opinions(db, academy.id)
                except Exception:
                    opinions = []
                
                try:
                    settings = academy_content.get_settings(db)
                except Exception:
                    settings = {}
                
                academy_memberships.append({
                    "membership_id": membership.id,
                    "academy_id": academy.id,
                    "academy_name": academy.name,
                    "academy_slug": getattr(academy, "slug", ""),
                    "user_role": membership.user_role,
                    "is_active": membership.is_active,
                    "joined_at": membership.joined_at,
                    "academy_details": {
                        "about": getattr(academy, "about", ""),
                        "image": getattr(academy, "image", ""),
                        "email": getattr(academy, "email", ""),
                        "phone": getattr(academy, "phone", ""),
                        "address": getattr(academy, "address", ""),
                        "status": getattr(academy, "status", "active"),
                        "created_at": getattr(academy, "created_at", None),
                    },
                    "template": template,
                    "about_content": about,
                    "sliders": sliders,
                    "faqs": faqs,
                    "opinions": opinions,
                    "settings": settings
                })
        
        user_info["academy_memberships"] = academy_memberships
        
    return SayanSuccessResponse(
        data=user_info,
        message="تم جلب بيانات المستخدم بنجاح",
        request=request
    )


@router.get("/academy/{academy_id}/content", response_model=None, summary="Get Academy Public Content")
async def get_academy_public_content(
    academy_id: int,
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    """Get public academy content (template, about, sliders, faqs, opinions, settings)"""
    try:
        # Check if academy exists
        academy = db.query(Academy).filter(Academy.id == academy_id).first()
        if not academy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الأكاديمية غير موجودة"
            )
        
        academy_content = CRUDAcademyContent()
        
        # Get all academy content
        template = academy_content.get_template(db, academy_id)
        about = academy_content.get_about(db, academy_id)
        sliders = academy_content.get_sliders(db, academy_id)
        faqs = academy_content.get_faqs(db, academy_id)
        opinions = academy_content.get_opinions(db, academy_id)
        settings = academy_content.get_settings(db)
        
        content_data = {
            "academy_info": {
                "id": academy.id,
                "name": academy.name,
                "slug": getattr(academy, "slug", ""),
                "image": getattr(academy, "image", ""),
                "email": getattr(academy, "email", ""),
                "phone": getattr(academy, "phone", ""),
                "address": getattr(academy, "address", ""),
                "status": getattr(academy, "status", "active"),
            },
            "template": template,
            "about_content": about,
            "sliders": sliders,
            "faqs": faqs,
            "opinions": opinions,
            "settings": settings
        }
        
        return SayanSuccessResponse(
            data=content_data,
            message="تم جلب محتوى الأكاديمية بنجاح",
            request=request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطأ في جلب محتوى الأكاديمية: {str(e)}"
    ) 