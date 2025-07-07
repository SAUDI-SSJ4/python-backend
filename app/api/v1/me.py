"""
User Profile Endpoint
=====================
 الملف الشخصي للمستخدم الحالي
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime

from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.student import Student
from app.models.academy import AcademyUser, Academy
from app.models.admin import Admin
from app.schemas.base import BaseResponse

router = APIRouter()

@router.get("/me", response_model=None, summary="Get Current User Profile")
async def get_current_user_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Returns the current authenticated user's profile in a unified response format.
    """
    user = current_user
    user_type = user.user_type
    
    # Base user information - المعلومات الأساسية للمستخدم
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
    
    # Add type-specific information - إضافة معلومات خاصة بنوع المستخدم
    student_profile = None
    academy_memberships = []

    if user_type == "student":
        # Get student profile if exists - الحصول على ملف الطالب إن وُجد
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
        # Get academy memberships - الحصول على عضويات الأكاديمية
        memberships = db.query(AcademyUser).filter(AcademyUser.user_id == user.id).all()
        
        for membership in memberships:
            academy = db.query(Academy).filter(Academy.id == membership.academy_id).first()
            if academy:
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
                    }
                })
        
        user_info["academy_memberships"] = academy_memberships
        
    # يمكن إضافة منطق المدير لاحقًا إذا لزم الأمر
    
    # Build unified response
    response = {
        "status": "success",  # always 'success' for this endpoint
        "status_code": 200,
        "error_type": None,
        "message": "تم جلب بيانات المستخدم بنجاح",
        "data": user_info if user_info else None,
        "path": str(request.url.path),
        "timestamp": datetime.utcnow().isoformat()
    }
    return response 