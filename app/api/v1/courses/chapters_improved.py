from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.deps.database import get_db
from app.deps.auth_improved import get_current_academy_user_improved, verify_course_ownership_improved
from app.models.chapter import Chapter
from app.models.course import Course
from app.models.user import User
from app.models.student import Student
from app.models.lesson import Lesson
from app.models.video import Video
from app.models.exam import Exam, Question
from app.models.interactive_tool import InteractiveTool
from app.schemas.chapter import (
    ChapterCreate, ChapterUpdate, ChapterResponse, ChapterDetailResponse,
    ChapterListResponse, ChapterOrderUpdate, ChaptersBulkOrderUpdate
)
from app.core.response_utils import (
    create_success_response, create_error_response, create_list_response,
    success_json_response, error_json_response
)

router = APIRouter()


@router.post("/academy/courses/{course_id}/chapters")
async def create_chapter_improved(
    course_id: str,
    request: Request,
    title: str = Form(..., min_length=3, max_length=200, description="عنوان الفصل"),
    description: Optional[str] = Form(None, description="وصف الفصل"),
    order_number: int = Form(0, ge=0, description="ترتيب الفصل داخل الكورس"),
    is_published: bool = Form(True, description="هل الفصل منشور"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user_improved)
):
    """
    Create a new chapter for the course with improved error handling.
    
    Automatically assigns order number if not provided.
    Accepts form-data instead of JSON.
    """
    try:
        # Verify course ownership with improved error handling
        verify_course_ownership_improved(course_id, current_user, db, request)
        
        # Get the course after verification
        course = db.query(Course).filter(
            Course.id == course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
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
        
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        db.rollback()
        
        # Create detailed error response
        error_detail = f"حدث خطأ أثناء إنشاء الفصل: {str(e)}"
        return error_json_response(
            message="حدث خطأ أثناء إنشاء الفصل",
            status_code=500,
            error_type="CHAPTER_CREATION_ERROR",
            details=error_detail,
            request=request
        )


@router.get("/academy/courses/{course_id}/chapters")
async def get_course_chapters_improved(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user_improved)
):
    """
    Get all chapters for a specific course with improved error handling.
    
    Returns ordered list of chapters with lesson details, counts and duration information.
    """
    try:
        # Verify course ownership with improved error handling
        verify_course_ownership_improved(course_id, current_user, db, request)
        
        # Get chapters first to avoid collation issues
        chapters = db.query(Chapter).filter(
            Chapter.course_id == course_id
        ).order_by(Chapter.order_number).all()
        
        # Convert chapters to response format with lessons data
        chapters_data = []
        for chapter in chapters:
            # Get lessons for this chapter separately to avoid collation issues
            lessons = db.query(Lesson).filter(
                Lesson.chapter_id == chapter.id
            ).order_by(Lesson.order_number).all()
            
            # Calculate chapter statistics
            total_lessons = len(lessons)
            video_lessons = [l for l in lessons if l.type == "video"]
            exam_lessons = [l for l in lessons if l.type == "exam"]
            tool_lessons = [l for l in lessons if l.type == "tool"]
            
            total_duration = sum(l.video_duration or 0 for l in video_lessons)
            total_size = sum(l.size_bytes or 0 for l in video_lessons)
            
            chapter_data = {
                "id": chapter.id,
                "title": chapter.title,
                "description": chapter.description,
                "order_number": chapter.order_number,
                "is_published": chapter.is_published,
                "created_at": chapter.created_at.isoformat() if chapter.created_at else None,
                "updated_at": chapter.updated_at.isoformat() if chapter.updated_at else None,
                
                # Chapter statistics
                "statistics": {
                    "total_lessons": total_lessons,
                    "video_lessons": len(video_lessons),
                    "exam_lessons": len(exam_lessons),
                    "tool_lessons": len(tool_lessons),
                    "total_duration_minutes": total_duration // 60 if total_duration else 0,
                    "total_duration_hours": round((total_duration // 60) / 60, 1) if total_duration else 0,
                    "total_size_mb": round(total_size / (1024*1024), 2) if total_size else 0,
                    "free_preview_lessons": len([l for l in lessons if l.is_free_preview])
                }
            }
            
            chapters_data.append(chapter_data)
        
        return success_json_response(
            data=chapters_data,
            message="تم استرجاع فصول الكورس بنجاح",
            request=request
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        # Create detailed error response
        error_detail = f"حدث خطأ أثناء استرجاع فصول الكورس: {str(e)}"
        return error_json_response(
            message="حدث خطأ أثناء استرجاع فصول الكورس",
            status_code=500,
            error_type="CHAPTERS_RETRIEVAL_ERROR",
            details=error_detail,
            request=request
        )


# Add more improved endpoints as needed... 