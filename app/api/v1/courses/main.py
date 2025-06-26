from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user, get_current_student, get_current_user
from app.models.course import Course, CourseStatus, CourseType, CourseLevel
from app.models.academy import Academy
from app.models.user import User
from app.schemas.course import (
    CourseCreate, CourseUpdate, CourseResponse, CourseDetailResponse,
    CourseListResponse, CourseFilters, CourseStatusUpdate
)
from app.services.file_service import file_service
from app.core.config import settings

router = APIRouter()


# Academy endpoints (Course management)
@router.get("/academy/courses", response_model=CourseListResponse)
async def get_academy_courses(
    filters: CourseFilters = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Get all courses for the current academy with filtering and pagination.
    
    Academy owners can view and manage all their courses with comprehensive filtering options.
    """
    try:
        # Build base query for academy's courses
        query = db.query(Course).filter(Course.academy_id == current_user.academy.id)
        
        # Apply filters
        if filters.category_id:
            query = query.filter(Course.category_id == filters.category_id)
        
        if filters.trainer_id:
            query = query.filter(Course.trainer_id == filters.trainer_id)
        
        if filters.status:
            query = query.filter(Course.status == filters.status)
        
        if filters.type:
            query = query.filter(Course.type == filters.type)
        
        if filters.level:
            query = query.filter(Course.level == filters.level)
        
        if filters.price_from is not None:
            query = query.filter(Course.price >= filters.price_from)
        
        if filters.price_to is not None:
            query = query.filter(Course.price <= filters.price_to)
        
        if filters.featured is not None:
            query = query.filter(Course.featured == filters.featured)
        
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(Course.title.ilike(search_term))
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        offset = (filters.page - 1) * filters.per_page
        courses = query.offset(offset).limit(filters.per_page).all()
        
        # Calculate pagination info
        total_pages = (total + filters.per_page - 1) // filters.per_page
        
        return CourseListResponse(
            courses=courses,
            total=total,
            page=filters.page,
            per_page=filters.per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء جلب الدورات: {str(e)}"
        )


@router.post("/academy/courses", response_model=CourseResponse)
async def create_course(
    course_data: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Create a new course for the academy.
    
    Creates a comprehensive course with all necessary details including
    pricing, content, and media files.
    """
    try:
        # Verify trainer belongs to the academy
        trainer = db.query(User).filter(
            User.id == course_data.trainer_id,
            User.user_type == "academy"  # Trainers are academy users
        ).first()
        
        if not trainer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المدرب غير موجود"
            )
        
        # Calculate platform fee
        platform_fee = course_data.price * (settings.PLATFORM_FEE_PERCENTAGE / 100)
        
        # Create course object
        course = Course(
            id=str(uuid.uuid4()),
            academy_id=current_user.academy.id,
            category_id=course_data.category_id,
            trainer_id=course_data.trainer_id,
            title=course_data.title,
            slug=f"{course_data.title.lower().replace(' ', '-')}-{str(uuid.uuid4())[:8]}",
            image=course_data.image,
            content=course_data.content,
            short_content=course_data.short_content,
            preparations=course_data.preparations,
            requirements=course_data.requirements,
            learning_outcomes=course_data.learning_outcomes,
            gallery=course_data.gallery,
            preview_video=course_data.preview_video,
            type=course_data.type,
            level=course_data.level,
            price=course_data.price,
            discount_price=course_data.discount_price,
            discount_ends_at=course_data.discount_ends_at,
            url=course_data.url,
            featured=course_data.featured,
            platform_fee_percentage=platform_fee
        )
        
        db.add(course)
        db.commit()
        db.refresh(course)
        
        return CourseResponse.from_orm(course)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء إنشاء الدورة: {str(e)}"
        )


@router.get("/academy/courses/{course_id}", response_model=CourseDetailResponse)
async def get_course_details(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Get detailed information for a specific course.
    
    Returns comprehensive course data including chapters, lessons, and analytics.
    """
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة"
        )
    
    return CourseDetailResponse.from_orm(course)


@router.put("/academy/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    course_data: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Update an existing course.
    
    Allows updating all course fields with proper validation and
    automatic recalculation of computed fields.
    """
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة"
        )
    
    try:
        # Update fields
        update_data = course_data.dict(exclude_unset=True)
        
        # Recalculate platform fee if price changed
        if 'price' in update_data:
            update_data['platform_fee_percentage'] = update_data['price'] * (settings.PLATFORM_FEE_PERCENTAGE / 100)
        
        # Update slug if title changed
        if 'title' in update_data:
            update_data['slug'] = f"{update_data['title'].lower().replace(' ', '-')}-{str(uuid.uuid4())[:8]}"
        
        for field, value in update_data.items():
            setattr(course, field, value)
        
        db.commit()
        db.refresh(course)
        
        return CourseResponse.from_orm(course)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء تحديث الدورة: {str(e)}"
        )


@router.patch("/academy/courses/{course_id}/status", response_model=CourseResponse)
async def update_course_status(
    course_id: str,
    status_data: CourseStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Update course status (publish/unpublish/archive).
    
    Allows quick status changes for course management.
    """
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة"
        )
    
    try:
        course.status = status_data.status
        db.commit()
        db.refresh(course)
        
        return CourseResponse.from_orm(course)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء تحديث حالة الدورة: {str(e)}"
        )


@router.delete("/academy/courses/{course_id}")
async def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Delete a course.
    
    Permanently removes the course and all associated data.
    This action cannot be undone.
    """
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة"
        )
    
    try:
        # Delete associated files
        if course.image:
            file_service.delete_file(course.image)
        
        if course.preview_video:
            file_service.delete_file(course.preview_video)
        
        if course.gallery:
            for image in course.gallery:
                file_service.delete_file(image)
        
        db.delete(course)
        db.commit()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": True,
                "message": "تم حذف الدورة بنجاح"
            }
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء حذف الدورة: {str(e)}"
        )


# Public endpoints (Course browsing)
@router.get("/public/courses", response_model=CourseListResponse)
async def get_public_courses(
    filters: CourseFilters = Depends(),
    db: Session = Depends(get_db)
):
    """
    Get published courses for public browsing.
    
    Returns only published courses with comprehensive filtering
    for students and visitors to browse available courses.
    """
    try:
        # Build base query for published courses only
        query = db.query(Course).filter(Course.status == CourseStatus.PUBLISHED)
        
        # Apply filters (same as academy endpoint but only for published courses)
        if filters.category_id:
            query = query.filter(Course.category_id == filters.category_id)
        
        if filters.level:
            query = query.filter(Course.level == filters.level)
        
        if filters.price_from is not None:
            query = query.filter(Course.price >= filters.price_from)
        
        if filters.price_to is not None:
            query = query.filter(Course.price <= filters.price_to)
        
        if filters.featured is not None:
            query = query.filter(Course.featured == filters.featured)
        
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(Course.title.ilike(search_term))
        
        # Order by featured first, then by creation date
        query = query.order_by(Course.featured.desc(), Course.created_at.desc())
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        offset = (filters.page - 1) * filters.per_page
        courses = query.offset(offset).limit(filters.per_page).all()
        
        # Calculate pagination info
        total_pages = (total + filters.per_page - 1) // filters.per_page
        
        return CourseListResponse(
            courses=courses,
            total=total,
            page=filters.page,
            per_page=filters.per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء جلب الدورات: {str(e)}"
        )


@router.get("/public/courses/{course_id}", response_model=CourseDetailResponse)
async def get_public_course_details(
    course_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific published course.
    
    Returns course details available to the public including
    course outline, preview content, and enrollment information.
    """
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.status == CourseStatus.PUBLISHED
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة أو غير متاحة"
        )
    
    return CourseDetailResponse.from_orm(course) 