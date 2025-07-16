from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Form, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, Any

from app.deps.database import get_db
from app.deps.auth import get_current_student, get_current_academy_user, get_current_user
from app.models.student import Student
from app.models.lesson import Lesson
from app.models.video import Video
from app.models.course import Course
from app.models.user import User
from app.models.student_course import StudentCourse
from app.services.video_streaming import video_streaming_service
from app.services.file_service import file_service
from app.core.response_handler import SayanSuccessResponse, SayanErrorResponse

router = APIRouter()


@router.get("/watch/{video_id}")
async def watch_video(
    video_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Simple unified video streaming endpoint
    Provide video_id and we handle all verification
    """
    try:
        # Block download tools first
        video_streaming_service._block_download_tools(request)
        
        # Get video information
        video = db.query(Video).filter(
            Video.id == video_id,
            Video.status == True,
            Video.deleted_at.is_(None)
        ).first()
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الفيديو غير موجود"
            )

        # Get lesson information
        lesson = db.query(Lesson).filter(
            Lesson.id == video.lesson_id,
            Lesson.status == True
        ).first()
        
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الدرس غير متاح"
            )

        # Get course information
        course = db.query(Course).filter(Course.id == lesson.course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الكورس غير موجود"
            )

        # Check access permissions
        has_access = False
        
        # Academy owner access
        if hasattr(current_user, 'academy') and current_user.user_type == "academy":
            if course.academy_id == current_user.academy.id:
                has_access = True
        
        # Student access - free preview
        elif lesson.is_free_preview:
            has_access = True
            
        # Student access - enrolled
        else:
            enrollment = db.query(StudentCourse).filter(
                StudentCourse.student_id == current_user.id,
                StudentCourse.course_id == course.id,
                StudentCourse.status == "active"
            ).first()
            
            if enrollment:
                has_access = True

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية للوصول لهذا الفيديو"
            )

        # Get video file path
        file_path = video_streaming_service.get_video_file_path(video)
        
        # Log access
        video_streaming_service.log_video_access(db, video_id, current_user.id, request)
        
        # Create streaming response
        range_header = request.headers.get("range")
        return video_streaming_service.create_streaming_response(file_path, range_header)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تشغيل الفيديو"
        )


@router.get("/stream/{video_id}")
async def stream_video(
    video_id: str,
    request: Request,
    token: str = Query(..., description="Video access token"),
    db: Session = Depends(get_db)
):
    """Stream protected video content with maximum security"""
    try:
        # Verify access token and extract user info
        token_data = video_streaming_service.verify_access_token(token, request)
        user_id = token_data.get("user_id")
        token_video_id = token_data.get("video_id")
        
        # Ensure token matches requested video
        if token_video_id != video_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="الرمز لا يتطابق مع الفيديو المطلوب"
            )
        
        # Verify user access to video
        video = video_streaming_service.verify_video_access(db, video_id, user_id)
        
        # Get video file path
        file_path = video_streaming_service.get_video_file_path(video)
        
        # Log access for analytics
        video_streaming_service.log_video_access(db, video_id, user_id, request)
        
        # Create streaming response with range support
        range_header = request.headers.get("range")
        return video_streaming_service.create_streaming_response(file_path, range_header)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تشغيل الفيديو"
        )


@router.post("/access-token/{video_id}")
async def create_video_token(
    video_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """Create secure video access token for authenticated students"""
    try:
        # Verify student access to video
        video = video_streaming_service.verify_video_access(db, video_id, current_student.id)
        
        # Extract client information for token security
        user_agent = request.headers.get('user-agent', '')
        ip_address = request.client.host
        
        # Generate secure access token
        access_token = video_streaming_service.create_access_token(
            video_id=video_id,
            user_id=current_student.id,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        return SayanSuccessResponse(
            data={
                "access_token": access_token,
                "video_id": video_id,
                "stream_url": f"/api/v1/videos/stream/{video_id}?token={access_token}",
                "expires_in": 7200,
                "video_info": {
                    "title": video.title,
                    "description": video.description,
                    "duration": video.duration
                },
                "security": {
                    "protected": True,
                    "download_blocked": True,
                    "session_bound": True
                }
            },
            message="تم إنشاء رمز الوصول للفيديو بنجاح"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return SayanErrorResponse(
            message="فشل في إنشاء رمز الوصول",
            error_type="TOKEN_GENERATION_ERROR",
            status_code=500
        )


@router.get("/academy-stream/{video_id}")
async def academy_stream_video(
    video_id: str,
    request: Request,
    token: str = Query(..., description="Academy access token"),
    db: Session = Depends(get_db)
):
    """Stream video for academy owners with extended permissions"""
    try:
        # Verify academy token
        token_data = video_streaming_service.verify_access_token(token, request)
        user_id = token_data.get("user_id")
        token_video_id = token_data.get("video_id")
        
        # Ensure token matches video
        if token_video_id != video_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="الرمز لا يتطابق مع الفيديو المطلوب"
            )
        
        # Verify user is academy owner
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.user_type != "academy":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="هذا الرابط مخصص للأكاديميات فقط"
            )
        
        # Get video and verify academy ownership
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الفيديو غير موجود"
            )
        
        lesson = db.query(Lesson).filter(Lesson.id == video.lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الدرس المرتبط غير موجود"
            )
        
        course = db.query(Course).filter(Course.id == lesson.course_id).first()
        if not course or course.academy_id != user.academy.id:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية للوصول لهذا الفيديو"
            )
        
        # Get file path and create streaming response
        file_path = video_streaming_service.get_video_file_path(video)
        video_streaming_service.log_video_access(db, video_id, user_id, request)
        
        range_header = request.headers.get("range")
        return video_streaming_service.create_streaming_response(file_path, range_header)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تشغيل الفيديو"
        )


@router.get("/get-video-url/{video_id}")
async def get_video_url(
    video_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get secure video streaming URL for both students and academy users"""
    try:
        # Get video information
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return SayanErrorResponse(
                message="الفيديو غير موجود",
                error_type="VIDEO_NOT_FOUND",
                status_code=404
            )

        # Get lesson and course information
        lesson = db.query(Lesson).filter(Lesson.id == video.lesson_id).first()
        if not lesson:
            return SayanErrorResponse(
                message="الدرس المرتبط غير موجود",
                error_type="LESSON_NOT_FOUND", 
                status_code=404
            )

        course = db.query(Course).filter(Course.id == lesson.course_id).first()
        if not course:
            return SayanErrorResponse(
                message="الكورس المرتبط غير موجود",
                error_type="COURSE_NOT_FOUND",
                status_code=404
            )

        # Determine access type and permissions
        user_agent = request.headers.get('user-agent', '')
        ip_address = request.client.host

        # Check if user is academy owner
        if hasattr(current_user, 'academy') and current_user.user_type == "academy":
            if course.academy_id == current_user.academy.id:
                # Academy owner access
                access_token = video_streaming_service.create_access_token(
                    video_id=video_id,
                    user_id=current_user.id,
                    user_agent=user_agent,
                    ip_address=ip_address
                )
                
                return SayanSuccessResponse(
                    data={
                        "video_id": video_id,
                        "video_url": f"/api/v1/videos/academy-stream/{video_id}?token={access_token}",
                        "access_type": "academy_owner",
                        "user_type": "academy",
                        "access_token": access_token,
                        "expires_in": 7200,
                        "video_info": {
                            "title": video.title,
                            "description": video.description,
                            "duration": video.duration,
                            "file_size": video.file_size
                        }
                    },
                    message="تم إنشاء رابط الفيديو للأكاديمية بنجاح"
                )

        # Student access (check enrollment)
        if hasattr(current_user, 'student_courses'):
            # Free preview access
            if lesson.is_free_preview:
                access_token = video_streaming_service.create_access_token(
                    video_id=video_id,
                    user_id=current_user.id,
                    user_agent=user_agent,
                    ip_address=ip_address
                )
                
                return SayanSuccessResponse(
                    data={
                        "video_id": video_id,
                        "video_url": f"/api/v1/videos/stream/{video_id}?token={access_token}",
                        "access_type": "free_preview",
                        "user_type": "student",
                        "access_token": access_token,
                        "expires_in": 7200,
                        "video_info": {
                            "title": video.title,
                            "description": video.description,
                            "duration": video.duration
                        }
                    },
                    message="تم إنشاء رابط الفيديو المجاني بنجاح"
                )

            # Check course enrollment
            from app.models.student_course import StudentCourse
            enrollment = db.query(StudentCourse).filter(
                StudentCourse.student_id == current_user.id,
                StudentCourse.course_id == course.id,
                StudentCourse.status == "active"
            ).first()

            if enrollment:
                access_token = video_streaming_service.create_access_token(
                    video_id=video_id,
                    user_id=current_user.id,
                    user_agent=user_agent,
                    ip_address=ip_address
                )
                
                return SayanSuccessResponse(
                    data={
                        "video_id": video_id,
                        "video_url": f"/api/v1/videos/stream/{video_id}?token={access_token}",
                        "access_type": "enrolled_student",
                        "user_type": "student",
                        "access_token": access_token,
                        "expires_in": 7200,
                        "video_info": {
                            "title": video.title,
                            "description": video.description,
                            "duration": video.duration
                        }
                    },
                    message="تم إنشاء رابط الفيديو المحمي بنجاح"
                )

        # Access denied
        return SayanErrorResponse(
            message="ليس لديك صلاحية للوصول لهذا الفيديو",
            error_type="ACCESS_DENIED",
            status_code=403
        )
        
    except Exception as e:
        return SayanErrorResponse(
            message="حدث خطأ أثناء الحصول على رابط الفيديو",
            error_type="INTERNAL_ERROR",
            status_code=500
        )


@router.post("/upload")
async def upload_video(
    title: str = Form(..., description="Video title"),
    description: Optional[str] = Form(None, description="Video description"),
    lesson_id: Optional[str] = Form(None, description="Lesson ID"),
    video_file: UploadFile = File(..., description="Video file"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Upload video file for lessons"""
    try:
        # Validate file type
        if not video_file.content_type or not video_file.content_type.startswith('video/'):
            return SayanErrorResponse(
                message="يجب أن يكون الملف فيديو",
                error_type="INVALID_FILE_TYPE",
                status_code=400
            )
        
        # Check file size (500MB limit)
        max_size = 500 * 1024 * 1024  # 500MB
        if video_file.size and video_file.size > max_size:
            return SayanErrorResponse(
                message="حجم الفيديو كبير جداً. الحد الأقصى 500 ميجابايت",
                error_type="FILE_TOO_LARGE",
                status_code=400
            )
        
        # Save video file
        video_path = await file_service.save_video_file(video_file, "lessons")
        
        # Create video record
        video = Video(
            lesson_id=lesson_id,
            title=title,
            description=description,
            video=video_path,
            file_size=video_file.size or 0,
            format=video_file.content_type,
            status=True
        )
        
        db.add(video)
        
        # Update lesson if provided
        if lesson_id:
            lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
            if lesson:
                lesson.type = "video"
                lesson.video = video_path
                lesson.size_bytes = video_file.size or 0
        
        db.commit()
        db.refresh(video)
        
        return SayanSuccessResponse(
            data={
                "video": {
                    "id": video.id,
                    "title": video.title,
                    "description": video.description,
                    "video_path": video.video,
                    "file_size": video.file_size,
                    "format": video.format,
                    "lesson_id": video.lesson_id,
                    "status": video.status,
                    "created_at": video.created_at.isoformat() if video.created_at else None
                }
            },
            message="تم رفع الفيديو بنجاح"
        )
        
    except Exception as e:
        db.rollback()
        return SayanErrorResponse(
            message="حدث خطأ أثناء رفع الفيديو",
            error_type="UPLOAD_ERROR",
            status_code=500
        ) 


@router.get("/info/{video_id}")
async def get_video_info(
    video_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get video information and metadata"""
    try:
        video = db.query(Video).filter(
            Video.id == video_id,
            Video.status == True,
            Video.deleted_at.is_(None)
        ).first()
        
        if not video:
            return SayanErrorResponse(
                message="الفيديو غير موجود",
                error_type="VIDEO_NOT_FOUND",
                status_code=404
            )
            
            return SayanSuccessResponse(
                data={
                "video": {
                    "id": video.id,
                        "title": video.title,
                        "description": video.description,
                        "duration": video.duration,
                    "file_size": video.file_size,
                    "format": video.format,
                    "views_count": video.views_count or 0,
                    "lesson_id": video.lesson_id,
                    "created_at": video.created_at.isoformat() if video.created_at else None,
                    "updated_at": video.updated_at.isoformat() if video.updated_at else None
                }
            },
            message="تم استرجاع معلومات الفيديو بنجاح"
            )

    except Exception as e:
        return SayanErrorResponse(
            message="حدث خطأ أثناء استرجاع معلومات الفيديو",
            error_type="INTERNAL_ERROR",
            status_code=500
        ) 


 