from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.deps.database import get_db
from app.deps.auth_improved import get_current_academy_user_improved, verify_course_ownership_improved
from app.deps.auth import get_current_student
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


# Academy endpoints (Chapter management) - Simplified URLs
@router.get("/academy/courses/{course_id}/chapters")
async def get_course_chapters(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user_improved)
):
    """
    Get all chapters for a specific course with lessons data included.
    
    Returns ordered list of chapters with lesson details, counts and duration information.
    """
    # Verify course ownership with improved error handling
    verify_course_ownership_improved(course_id, current_user, db, request)
    
    # Get the course after verification
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
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
        
        # Prepare lessons data
        lessons_data = []
        for lesson in lessons:
            lesson_info = {
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "type": lesson.type,
                "order_number": lesson.order_number,
                "status": lesson.status,
                "is_free_preview": lesson.is_free_preview,
                "created_at": lesson.created_at.isoformat() if lesson.created_at else None,
                "updated_at": lesson.updated_at.isoformat() if lesson.updated_at else None
            }
            
            # Add type-specific information
            if lesson.type == "video":
                # Get videos count separately
                videos_count = db.query(Video).filter(
                    Video.lesson_id == lesson.id,
                    Video.status == True,
                    Video.deleted_at.is_(None)
                ).count()
                
                # Get first video for direct URL
                first_video = db.query(Video).filter(
                    Video.lesson_id == lesson.id,
                    Video.status == True,
                    Video.deleted_at.is_(None)
                ).first()
                
                lesson_info.update({
                    "video_duration": lesson.video_duration or 0,
                    "size_bytes": lesson.size_bytes or 0,
                    "duration_formatted": f"{lesson.video_duration}m" if lesson.video_duration else "0m",
                    "file_size_formatted": f"{round((lesson.size_bytes or 0) / (1024*1024), 2)} MB",
                    "views_count": lesson.views_count or 0,
                    "has_video": bool(lesson.video),
                    "video_count": videos_count,
                    "video_id": first_video.id if first_video else None
                })
            elif lesson.type == "exam":
                # Get exams and questions count separately
                exams = db.query(Exam).filter(
                    Exam.lesson_id == lesson.id,
                    Exam.status == True
                ).all()
                
                questions_count = sum(
                    db.query(Question).filter(
                        Question.exam_id == exam.id
                    ).count() for exam in exams
                )
                
                lesson_info.update({
                    "exam_count": len(exams),
                    "questions_count": questions_count,
                    "duration_minutes": sum(exam.duration // 60 for exam in exams) if exams else 0
                })
            elif lesson.type == "tool":
                # Get tools count separately
                tools_count = db.query(InteractiveTool).filter(
                    InteractiveTool.lesson_id == lesson.id
                ).count()
                
                lesson_info.update({
                    "tools_count": tools_count
                })
            
            lessons_data.append(lesson_info)
        
        # Sort lessons by order_number
        lessons_data.sort(key=lambda x: x["order_number"])
        
        # Create chapter response with lessons
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
            },
            
            # Lessons data
            "lessons": lessons_data
        }
        
        chapters_data.append(chapter_data)
    
    return success_json_response(
        data=create_list_response(
            items=chapters_data,
            total=len(chapters),
            message="تم استرجاع الفصول مع الدروس بنجاح",
            path=str(request.url.path)
        )["data"],
        message="تم استرجاع الفصول مع الدروس بنجاح",
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
    current_user: User = Depends(get_current_academy_user_improved)
):
    """
    Create a new chapter for the course.
    
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
    current_user: User = Depends(get_current_academy_user_improved)
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
    
    # Prepare lessons data
    lessons_data = []
    for lesson in lessons:
        lesson_info = {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "type": lesson.type,
            "order_number": lesson.order_number,
            "status": lesson.status,
            "is_free_preview": lesson.is_free_preview,
            "created_at": lesson.created_at.isoformat() if lesson.created_at else None,
            "updated_at": lesson.updated_at.isoformat() if lesson.updated_at else None
        }
        
        # Add type-specific information
        if lesson.type == "video":
            # Get videos count separately
            videos_count = db.query(Video).filter(
                Video.lesson_id == lesson.id,
                Video.status == True,
                Video.deleted_at.is_(None)
            ).count()
            
            # Get first video for direct URL
            first_video = db.query(Video).filter(
                Video.lesson_id == lesson.id,
                Video.status == True,
                Video.deleted_at.is_(None)
            ).first()
            
            lesson_info.update({
                "video_duration": lesson.video_duration or 0,
                "size_bytes": lesson.size_bytes or 0,
                "duration_formatted": f"{lesson.video_duration}m" if lesson.video_duration else "0m",
                "file_size_formatted": f"{round((lesson.size_bytes or 0) / (1024*1024), 2)} MB",
                "views_count": lesson.views_count or 0,
                "has_video": bool(lesson.video),
                "video_count": videos_count,
                "video_id": first_video.id if first_video else None
            })
        elif lesson.type == "exam":
            # Get exams and questions count separately
            exams = db.query(Exam).filter(
                Exam.lesson_id == lesson.id,
                Exam.status == True
            ).all()
            
            questions_count = sum(
                db.query(Question).filter(
                    Question.exam_id == exam.id
                ).count() for exam in exams
            )
            
            lesson_info.update({
                "exam_count": len(exams),
                "questions_count": questions_count,
                "duration_minutes": sum(exam.duration // 60 for exam in exams) if exams else 0
            })
        elif lesson.type == "tool":
            # Get tools count separately
            tools_count = db.query(InteractiveTool).filter(
                InteractiveTool.lesson_id == lesson.id
            ).count()
            
            lesson_info.update({
                "tools_count": tools_count
            })
        
        lessons_data.append(lesson_info)
    
    # Sort lessons by order_number
    lessons_data.sort(key=lambda x: x["order_number"])
    
    # Create chapter response with lessons
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
        },
        
        # Lessons data
        "lessons": lessons_data
    }
    
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
    current_user: User = Depends(get_current_academy_user_improved)
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
    current_user: User = Depends(get_current_academy_user_improved)
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
    current_user: User = Depends(get_current_academy_user_improved)
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
@router.get("/public/chapters/{chapter_id}")
async def get_public_chapter_details(
    chapter_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get detailed chapter information for public access.
    
    Returns published chapter with lessons if chapter is published and course is published.
    No authentication required for published content.
    """
    try:
        # Get published chapter
        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.is_published == True
        ).first()
    
        if not chapter:
            return error_json_response(
                message="الفصل غير موجود أو غير متاح",
                status_code=404,
                error_type="Not Found",
                request=request
            )
    
        # Verify course is published
        course = db.query(Course).filter(
            Course.id == chapter.course_id,
            Course.status == "published"
        ).first()
    
        if not course:
            return error_json_response(
                message="الدورة غير موجودة أو غير متاحة",
                status_code=404,
                error_type="Not Found",
                request=request
            )
        
        # Convert to response format
        chapter_response = ChapterDetailResponse.from_orm(chapter)
        
        return success_json_response(
            data=chapter_response,
            message="تم جلب تفاصيل الفصل بنجاح",
            request=request
        )
        
    except Exception as e:
        return error_json_response(
            message=f"حدث خطأ أثناء جلب تفاصيل الفصل: {str(e)}",
            status_code=500,
            error_type="Internal Server Error",
            request=request
        )


# Keep course-specific listing for organizational purposes
@router.get("/public/courses/{course_id}/chapters")
async def get_public_course_chapters(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get published chapters for a course (public view).
    
    Returns only published chapters that are publicly accessible.
    No authentication required for published content.
    """
    try:
        # Verify course is published
        course = db.query(Course).filter(
            Course.id == course_id,
            Course.status == "published"
        ).first()
    
        if not course:
            return error_json_response(
                message="الدورة غير موجودة أو غير متاحة",
                status_code=404,
                error_type="Not Found",
                request=request
            )
    
        # Get published chapters
        chapters = db.query(Chapter).filter(
            Chapter.course_id == course_id,
            Chapter.is_published == True
        ).order_by(Chapter.order_number).all()
    
        # Convert to response format
        chapters_response = ChapterListResponse(
            chapters=chapters,
            total=len(chapters)
        )
        
        return success_json_response(
            data=chapters_response,
            message="تم جلب فصول الدورة بنجاح",
            request=request
        )
        
    except Exception as e:
        return error_json_response(
            message=f"حدث خطأ أثناء جلب فصول الدورة: {str(e)}",
            status_code=500,
            error_type="Internal Server Error",
            request=request
    ) 