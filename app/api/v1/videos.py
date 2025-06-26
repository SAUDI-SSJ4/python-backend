from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.deps.database import get_db
from app.deps.auth import get_current_student
from app.models.student import Student
from app.models.lesson_progress import LessonProgress
from app.services.video_streaming import video_streaming_service
from app.schemas.lesson import LessonProgressUpdate, LessonProgressResponse

router = APIRouter()


@router.get("/stream/{video_id}")
async def stream_video(
    video_id: str,
    request: Request,
    token: str = Query(..., description="Video access token"),
    db: Session = Depends(get_db)
):
    """
    Stream video content with security and access control.
    
    This endpoint provides secure video streaming with:
    - JWT token-based access control
    - Range request support for efficient streaming
    - Student enrollment verification
    - Access logging for analytics
    """
    try:
        # Verify access token
        payload = video_streaming_service.verify_video_token(token)
        video_id_from_token = payload.get("video_id")
        student_id = payload.get("student_id")
        
        # Ensure token is for the correct video
        if video_id_from_token != video_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="رمز الوصول غير صالح لهذا الفيديو"
            )
        
        # Verify student access to video
        video, is_enrolled = video_streaming_service.verify_student_access(
            db, video_id, student_id
        )
        
        # Get video file path
        file_path = video_streaming_service.get_video_file_path(video)
        
        # Log video access
        video_streaming_service.log_video_access(db, video_id, student_id, request)
        
        # Get range header for partial content support
        range_header = request.headers.get("range")
        
        # Create streaming response
        return video_streaming_service.create_range_response(file_path, range_header)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء تشغيل الفيديو: {str(e)}"
        )


@router.post("/access-token/{video_id}")
async def get_video_access_token(
    video_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """
    Generate a secure access token for video streaming.
    
    This endpoint verifies student enrollment and generates a JWT token
    that can be used to access the video streaming endpoint.
    """
    try:
        # Verify student access to video
        video, is_enrolled = video_streaming_service.verify_student_access(
            db, video_id, current_student.id
        )
        
        # Generate access token
        token = video_streaming_service.generate_video_token(
            video_id, current_student.id
        )
        
        return {
            "status": True,
            "message": "تم إنشاء رمز الوصول بنجاح",
            "data": {
                "access_token": token,
                "video_id": video_id,
                "stream_url": f"/api/v1/videos/stream/{video_id}?token={token}",
                "expires_in": 7200  # 2 hours in seconds
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء إنشاء رمز الوصول: {str(e)}"
        )


@router.post("/progress/{lesson_id}")
async def update_lesson_progress(
    lesson_id: str,
    progress_data: LessonProgressUpdate,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """
    Update student progress for a specific lesson.
    
    This endpoint tracks video watch progress and completion status
    for analytics and course progress tracking.
    """
    try:
        # Get or create lesson progress record
        progress = db.query(LessonProgress).filter(
            LessonProgress.lesson_id == lesson_id,
            LessonProgress.student_id == current_student.id
        ).first()
        
        if not progress:
            # Create new progress record
            progress = LessonProgress(
                lesson_id=lesson_id,
                student_id=current_student.id,
                course_id=progress_data.get("course_id"),  # Should be provided
                progress_percentage=progress_data.progress_percentage,
                current_position_seconds=progress_data.current_position_seconds or 0,
                completed=progress_data.completed or False
            )
            db.add(progress)
        else:
            # Update existing progress
            progress.update_progress(
                progress_data.progress_percentage,
                progress_data.current_position_seconds
            )
            
            if progress_data.completed is not None:
                progress.completed = progress_data.completed
        
        db.commit()
        db.refresh(progress)
        
        return LessonProgressResponse.from_orm(progress)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء تحديث التقدم: {str(e)}"
        )


@router.get("/progress/{lesson_id}", response_model=LessonProgressResponse)
async def get_lesson_progress(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """
    Get student progress for a specific lesson.
    
    Returns the current progress information including watch time,
    completion status, and last accessed timestamp.
    """
    progress = db.query(LessonProgress).filter(
        LessonProgress.lesson_id == lesson_id,
        LessonProgress.student_id == current_student.id
    ).first()
    
    if not progress:
        # Return default progress if none exists
        return LessonProgressResponse(
            id="",
            student_id=current_student.id,
            lesson_id=lesson_id,
            course_id="",  # This should be fetched from lesson
            progress_percentage=0,
            completed=False,
            current_position_seconds=0,
            last_watched_at=None,
            created_at=None,
            updated_at=None,
            is_completed=False,
            is_started=False,
            completion_status="Not Started"
        )
    
    return LessonProgressResponse.from_orm(progress)


@router.get("/info/{video_id}")
async def get_video_info(
    video_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """
    Get video information and metadata.
    
    Returns video details including duration, quality options,
    and access permissions for the authenticated student.
    """
    try:
        # Verify student access to video
        video, is_enrolled = video_streaming_service.verify_student_access(
            db, video_id, current_student.id
        )
        
        # Get video file information
        file_path = video_streaming_service.get_video_file_path(video)
        video_info = video_streaming_service.get_video_info(file_path)
        
        return {
            "status": True,
            "data": {
                "video_id": video_id,
                "title": video.title,
                "description": video.description,
                "duration": video.duration,
                "duration_formatted": video.duration_formatted,
                "file_size": video_info["size"],
                "mime_type": video_info["mime_type"],
                "is_enrolled": is_enrolled,
                "can_access": True,
                "lesson_id": video.lesson_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء جلب معلومات الفيديو: {str(e)}"
        ) 