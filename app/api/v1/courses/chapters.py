from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user, get_current_student
from app.models.chapter import Chapter
from app.models.course import Course
from app.models.user import User
from app.models.student import Student
from app.schemas.chapter import (
    ChapterCreate, ChapterUpdate, ChapterResponse, ChapterDetailResponse,
    ChapterListResponse, ChapterOrderUpdate, ChaptersBulkOrderUpdate
)
from app.core.response_utils import (
    create_success_response, create_error_response, create_list_response,
    success_json_response, error_json_response
)

router = APIRouter()


# Academy endpoints (Chapter management) - Simplified URLs
@router.get("/academy/courses/{course_id}/chapters")
async def get_course_chapters(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Get all chapters for a specific course.
    
    Returns ordered list of chapters with lesson counts and duration information.
    """
    # Verify course ownership
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        return error_json_response(
            message="الدورة غير موجودة",
            status_code=404,
            error_type="Not Found",
            request=request
        )
    
    # Get chapters ordered by order_number
    chapters = db.query(Chapter).filter(
        Chapter.course_id == course_id
    ).order_by(Chapter.order_number).all()
    
    # Convert chapters to response format
    chapters_data = [ChapterResponse.from_orm(chapter) for chapter in chapters]
    
    return success_json_response(
        data=create_list_response(
            items=chapters_data,
            total=len(chapters),
            message="تم استرجاع الفصول بنجاح",
            path=str(request.url.path)
        )["data"],
        message="تم استرجاع الفصول بنجاح",
        request=request
    )


@router.post("/academy/courses/{course_id}/chapters")
async def create_chapter(
    course_id: str,
    request: Request,
    title: str = Form(..., min_length=3, max_length=200, description="عنوان الفصل"),
    description: Optional[str] = Form(None, description="وصف الفصل"),
    order_number: int = Form(0, ge=0, description="ترتيب الفصل داخل الكورس"),
    is_published: bool = Form(True, description="هل الفصل منشور"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Create a new chapter for the course.
    
    Automatically assigns order number if not provided.
    Accepts form-data instead of JSON.
    """
    # Verify course ownership
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        return error_json_response(
            message="الدورة غير موجودة",
            status_code=404,
            error_type="Not Found",
            request=request
        )
    
    try:
        # Auto-assign order number if not provided
        if order_number == 0:
            last_chapter = db.query(Chapter).filter(
                Chapter.course_id == course_id
            ).order_by(Chapter.order_number.desc()).first()
            
            order_number = (last_chapter.order_number + 1) if last_chapter else 1
        
        # Create chapter
        chapter = Chapter(
            course_id=course_id,
            title=title,
            description=description,
            order_number=order_number,
            is_published=is_published
        )
        
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
        
        # Convert to response format
        chapter_data = ChapterResponse.from_orm(chapter)
        
        return success_json_response(
            data=chapter_data,
            message="تم إنشاء الفصل بنجاح",
            status_code=201,
            request=request
        )
        
    except Exception as e:
        db.rollback()
        return error_json_response(
            message=f"حدث خطأ أثناء إنشاء الفصل: {str(e)}",
            status_code=500,
            error_type="Internal Server Error",
            request=request
        )


# Simplified chapter endpoints - Using only chapter_id
@router.get("/chapters/{chapter_id}")
async def get_chapter_details(
    chapter_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Get detailed information for a specific chapter.
    
    Returns chapter data with associated lessons.
    """
    # Get chapter
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id
    ).first()
    
    if not chapter:
        return error_json_response(
            message="الفصل غير موجود",
            status_code=404,
            error_type="Not Found",
            request=request
        )
    
    # Verify course ownership through chapter
    course = db.query(Course).filter(
        Course.id == chapter.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        return error_json_response(
            message="الدورة غير موجودة أو ليس لديك صلاحية",
            status_code=404,
            error_type="Not Found",
            request=request
        )
    
    # Convert to response format
    chapter_data = ChapterDetailResponse.from_orm(chapter)
    
    return success_json_response(
        data=chapter_data,
        message="تم استرجاع بيانات الفصل بنجاح",
        request=request
    )


@router.put("/chapters/{chapter_id}")
async def update_chapter(
    chapter_id: int,
    chapter_data: ChapterUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Update an existing chapter.
    
    Allows updating all chapter fields with proper validation.
    """
    # Get chapter
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id
    ).first()
    
    if not chapter:
        return error_json_response(
            message="الفصل غير موجود",
            status_code=404,
            error_type="Not Found",
            request=request
        )
    
    # Verify course ownership through chapter
    course = db.query(Course).filter(
        Course.id == chapter.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        return error_json_response(
            message="الدورة غير موجودة أو ليس لديك صلاحية",
            status_code=404,
            error_type="Not Found",
            request=request
        )
    
    try:
        # Update fields
        update_data = chapter_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(chapter, field, value)
        
        db.commit()
        db.refresh(chapter)
        
        # Convert to response format
        chapter_response = ChapterResponse.from_orm(chapter)
        
        return success_json_response(
            data=chapter_response,
            message="تم تحديث الفصل بنجاح",
            request=request
        )
        
    except Exception as e:
        db.rollback()
        return error_json_response(
            message=f"حدث خطأ أثناء تحديث الفصل: {str(e)}",
            status_code=500,
            error_type="Internal Server Error",
            request=request
        )


@router.delete("/chapters/{chapter_id}")
async def delete_chapter(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Delete a chapter and all its lessons.
    
    This action cannot be undone and will remove all associated content.
    """
    # Get chapter
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id
    ).first()
    
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الفصل غير موجود"
        )
    
    # Verify course ownership through chapter
    course = db.query(Course).filter(
        Course.id == chapter.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة أو ليس لديك صلاحية"
        )
    
    try:
        db.delete(chapter)
        db.commit()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": True,
                "message": "تم حذف الفصل بنجاح"
            }
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء حذف الفصل: {str(e)}"
        )


# Bulk operations for chapters within a course
@router.patch("/academy/courses/{course_id}/chapters/reorder")
async def reorder_chapters(
    course_id: str,
    reorder_data: ChaptersBulkOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Reorder chapters within a course.
    
    Updates the order_number for multiple chapters in a single transaction.
    """
    # Verify course ownership
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
        # Update chapter orders
        for chapter_order in reorder_data.chapters:
            chapter = db.query(Chapter).filter(
                Chapter.id == chapter_order.chapter_id,
                Chapter.course_id == course_id
            ).first()
            
            if chapter:
                chapter.order_number = chapter_order.new_order
        
        db.commit()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": True,
                "message": "تم إعادة ترتيب الفصول بنجاح"
            }
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء إعادة الترتيب: {str(e)}"
        )


# Public endpoints (Chapter browsing for students) - Simplified
@router.get("/public/chapters/{chapter_id}", response_model=ChapterDetailResponse)
async def get_public_chapter_details(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """
    Get detailed chapter information for students.
    
    Returns chapter with lessons, considering enrollment status for access control.
    """
    # Get published chapter
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.is_published == True
    ).first()
    
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الفصل غير موجود أو غير متاح"
        )
    
    # Verify course is published
    course = db.query(Course).filter(
        Course.id == chapter.course_id,
        Course.status == "published"
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة أو غير متاحة"
        )
    
    return ChapterDetailResponse.from_orm(chapter)


# Keep course-specific listing for organizational purposes
@router.get("/public/courses/{course_id}/chapters", response_model=ChapterListResponse)
async def get_public_course_chapters(
    course_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """
    Get published chapters for a course (student view).
    
    Returns only published chapters that students can access.
    """
    # Verify course is published
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.status == "published"
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة أو غير متاحة"
        )
    
    # Get published chapters
    chapters = db.query(Chapter).filter(
        Chapter.course_id == course_id,
        Chapter.is_published == True
    ).order_by(Chapter.order_number).all()
    
    return ChapterListResponse(
        chapters=chapters,
        total=len(chapters)
    ) 