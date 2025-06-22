"""
User Profile Management Endpoints
=================================
User profile information and management functionality
"""

from typing import Any
from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.schemas import UserInfoResponse
from app.models.user import UserType

router = APIRouter()


@router.get("/me", response_model=UserInfoResponse, tags=["Profile"])
def get_current_user_info(
    current_user = Depends(get_current_user)
) -> Any:
    """الحصول على معلومات المستخدم الحالي"""
    
    user_data = {
        "id": current_user.id,
        "fname": current_user.fname,
        "mname": current_user.mname,
        "lname": current_user.lname,
        "email": current_user.email,
        "phone_number": current_user.phone_number,
        "user_type": current_user.user_type.value,
        "account_type": current_user.account_type.value,
        "status": current_user.status.value,
        "verified": current_user.verified,
        "avatar": current_user.avatar,
        "banner": current_user.banner,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }
    
    # إضافة بيانات خاصة بنوع المستخدم
    if current_user.user_type == UserType.STUDENT and current_user.student_profile:
        user_data.update({
            "birth_date": current_user.student_profile.birth_date,
            "gender": current_user.student_profile.gender.value if current_user.student_profile.gender else None,
            "bio": current_user.student_profile.bio,
            "location": current_user.student_profile.location,
            "education_level": current_user.student_profile.education_level,
            "interests": current_user.student_profile.interests
        })
    elif current_user.user_type == UserType.ACADEMY and current_user.academy_profile:
        user_data.update({
            "academy_name": current_user.academy_profile.name,
            "academy_id": current_user.academy_profile.academy_id,
            "about": current_user.academy_profile.about,
            "website": current_user.academy_profile.website,
            "location": current_user.academy_profile.location,
            "established_year": current_user.academy_profile.established_year,
            "accreditation": current_user.academy_profile.accreditation,
            "courses_offered": current_user.academy_profile.courses_offered
        })
    
    return UserInfoResponse(**user_data) 