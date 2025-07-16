from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Path, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import logging
import os

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user, get_current_student
from app.models.lesson import Lesson
from app.models.chapter import Chapter
from app.models.course import Course
from app.models.student import Student
from app.models.lesson_progress import LessonProgress
from app.models.video import Video
from app.models.exam import Exam, Question, QuestionOption, QuestionType
from app.models.interactive_tool import InteractiveTool
from app.models.ai_assistant import VideoTranscription, ProcessingStatus
from app.schemas.lesson import (
    LessonCreate, 
    LessonUpdate, 
    LessonResponse, 
    LessonListResponse,
    LessonProgressUpdate,
    LessonProgressResponse
)
from app.services.file_service import FileService
from app.services.video_streaming import VideoStreamingService
from app.core.response_handler import SayanSuccessResponse, SayanErrorResponse
from app.services.lesson_access_service import LessonAccessService
from app.services.video_processing import VideoProcessingService
from app.core.ai_config import AIServiceFactory, ai_config

router = APIRouter()
file_service = FileService()
video_processing_service = VideoProcessingService()
logger = logging.getLogger(__name__)


async def process_video_transcription_task(
    video_id: str,
    lesson_id: str,
    video_file_path: str,
    academy_id: int,
    db: Session
):
    """
    Background task for processing video transcription after upload
    Uses improved video processing service without MoviePy dependency
    """
    transcription_id = str(uuid.uuid4())
    
    try:
        # Create initial transcription record
        transcription = VideoTranscription(
            id=transcription_id,
            lesson_id=lesson_id,
            video_id=video_id,
            academy_id=academy_id,
            transcription_text="",
            language="ar",
            processing_status=ProcessingStatus.PROCESSING
        )
        db.add(transcription)
        db.commit()
        
        logger.info(f"Starting video transcription for video {video_id}")
        
        # Check if AI transcription service is available
        if not ai_config.is_service_available("transcription"):
            logger.error("AI transcription service is not available")
            transcription.processing_status = ProcessingStatus.FAILED
            db.commit()
            return
        
        # Get full video path
        full_video_path = f"static/uploads/{video_file_path}"
        
        if not os.path.exists(full_video_path):
            raise Exception(f"Video file not found: {full_video_path}")
        
        # Validate video file integrity
        validation_result = video_processing_service.validate_video_file(full_video_path)
        
        if not validation_result.get("valid", False):
            raise Exception(f"Video file validation error: {validation_result.get('error', 'Invalid file')}")
        
        # Transcribe video to text using Whisper
        logger.info(f"Transcribing video to text using Whisper: {full_video_path}")
        
        result = await video_processing_service.transcribe_video_with_whisper(
            video_path=full_video_path,
            language="ar",
            academy_id=academy_id
        )
        
        if result.get("status") == "error":
            raise Exception(f"Transcription failed: {result.get('error', 'Unknown error')}")
        
        # Update transcription record with results
        transcription.transcription_text = result.get("text", "")
        transcription.confidence_score = result.get("confidence", 0.0)
        transcription.segments = result.get("segments", [])
        transcription.processing_status = ProcessingStatus.COMPLETED
        transcription.duration_seconds = int(result.get("duration", 0))
        
        # Create SRT subtitles from segments
        if result.get("segments"):
            srt_content = video_processing_service.create_srt_subtitles(result["segments"])
            transcription.subtitles_srt = srt_content
        
        db.commit()
        logger.info(f"Video transcription completed successfully for video {video_id}")
        
    except Exception as e:
        logger.error(f"Video transcription failed for video {video_id}: {str(e)}")
        
        # Update transcription status to failed
        transcription = db.query(VideoTranscription).filter(
            VideoTranscription.id == transcription_id
        ).first()
        if transcription:
            transcription.processing_status = ProcessingStatus.FAILED
            db.commit()


def create_srt_subtitles(segments):
    """Create SRT subtitle content from segments"""
    return video_processing_service.create_srt_subtitles(segments)


def format_time(seconds):
    """Format seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

@router.post("/{chapter_id}", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    chapter_id: str = Path(..., description="Chapter ID"),
    title: str = Form(..., min_length=3, max_length=255, description="Lesson title"),
    description: Optional[str] = Form(None, description="Lesson description"),
    type: str = Form("video", description="Lesson type"),
    order_number: int = Form(0, description="Lesson order"),
    status: bool = Form(True, description="Lesson status"),
    is_free_preview: bool = Form(False, description="Is free preview"),
    video_duration: Optional[int] = Form(None, description="Video duration in seconds"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    Create a new lesson without video
    Video can be uploaded separately after lesson creation
    """
    print(f"DEBUG: create_lesson function hit for chapter_id: {chapter_id}")
    try:
        # Find chapter
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        
        if not chapter:
            return SayanErrorResponse(
            message="الفصل غير موجود",
                error_type="CHAPTER_NOT_FOUND",
                status_code=404
            )
        
        # Get course_id from chapter
        course_id = chapter.course_id
        
        # Verify course ownership
        course = db.query(Course).filter(
            Course.id == course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
            message="ليس لديك صلاحية لإنشاء درس في هذا الكورس",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        # Create lesson without video
        lesson = Lesson(
            chapter_id=chapter_id,
            course_id=course_id,
            title=title,
            description=description,
            order_number=order_number,
            type=type,
            status=status,
            is_free_preview=is_free_preview,
            video_duration=video_duration or 0,
            size_bytes=0  # Will be updated when video is uploaded
        )
        
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        
        # Prepare response based on lesson type
        if lesson.type == "video":
            message = "تم إنشاء درس الفيديو بنجاح. يمكنك الآن رفع الفيديو للدرس"
            response_data = {
                "lesson": {
                    "id": lesson.id,
                    "chapter_id": lesson.chapter_id,
                    "course_id": lesson.course_id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "type": lesson.type,
                    "order_number": lesson.order_number,
                    "status": lesson.status,
                    "is_free_preview": lesson.is_free_preview,
                    "video_duration": lesson.video_duration,
                    "size_bytes": lesson.size_bytes,
                    "has_video": lesson.video is not None,
                    "created_at": lesson.created_at.isoformat() if lesson.created_at else None
                },
                "next_actions": {
                    "upload_video": f"/api/v1/lessons/{lesson.id}/video",
                    "message": "استخدم الرابط أعلاه لرفع الفيديو للدرس"
                }
            }
        elif lesson.type == "exam":
            message = "تم إنشاء درس الاختبار بنجاح. يمكنك الآن إنشاء الامتحان وإضافة الأسئلة"
            response_data = {
                "lesson": {
                    "id": lesson.id,
                    "chapter_id": lesson.chapter_id,
                    "course_id": lesson.course_id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "type": lesson.type,
                    "order_number": lesson.order_number,
                    "status": lesson.status,
                    "is_free_preview": lesson.is_free_preview,
                    "video_duration": 0,  # لا يوجد فيديو للاختبار
                    "size_bytes": 0,      # لا يوجد فيديو للاختبار
                    "has_video": False,   # لا يوجد فيديو للاختبار
                    "created_at": lesson.created_at.isoformat() if lesson.created_at else None
                },
                "exam_info": {
                    "exam_type": "interactive",
                    "questions_count": 0,
                    "duration_minutes": 0,
                    "pass_score": 0,
                    "max_attempts": 0,
                    "is_active": False
                },
                "next_actions": {
                    "create_exam": f"/api/v1/lessons/{lesson.id}/exam",
                    "message": "استخدم الرابط أعلاه لإضافة أسئلة الاختبار"
                }
            }
        elif lesson.type == "tool":
            message = "تم إنشاء درس الأداة التفاعلية بنجاح. يمكنك الآن إضافة الأداة التفاعلية"
            response_data = {
                "lesson": {
                    "id": lesson.id,
                    "chapter_id": lesson.chapter_id,
                    "course_id": lesson.course_id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "type": lesson.type,
                    "order_number": lesson.order_number,
                    "status": lesson.status,
                    "is_free_preview": lesson.is_free_preview,
                    "video_duration": 0,  # لا يوجد فيديو للأداة
                    "size_bytes": 0,      # لا يوجد فيديو للأداة
                    "has_video": False,   # لا يوجد فيديو للأداة
                    "created_at": lesson.created_at.isoformat() if lesson.created_at else None
                },
                "tool_info": {
                    "tool_type": "interactive",
                    "tools_count": 0,
                    "is_active": False
                },
                "next_actions": {
                    "add_tool": f"/api/v1/lessons/{lesson.id}/tools",
                    "message": "استخدم الرابط أعلاه لإضافة الأداة التفاعلية"
                }
            }
        else:
            message = "تم إنشاء الدرس بنجاح"
            response_data = {
                "lesson": {
                    "id": lesson.id,
                    "chapter_id": lesson.chapter_id,
                    "course_id": lesson.course_id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "type": lesson.type,
                    "order_number": lesson.order_number,
                    "status": lesson.status,
                    "is_free_preview": lesson.is_free_preview,
                    "video_duration": lesson.video_duration,
                    "size_bytes": lesson.size_bytes,
                    "has_video": lesson.video is not None,
                    "created_at": lesson.created_at.isoformat() if lesson.created_at else None
                }
            }

        return SayanSuccessResponse(
            data=response_data,
            message=message
        )
        
    except HTTPException as http_exc:
        db.rollback()
        return SayanErrorResponse(
            message=http_exc.detail,
            error_type="HTTP_ERROR",
            status_code=http_exc.status_code
        )
    except Exception as e:
        db.rollback()
        return SayanErrorResponse(
            message=f"حدث خطأ أثناء إنشاء الدرس: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )

@router.get("/{lesson_id}")
async def get_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    Get lesson details with unified response format
    Academy owners get direct video access without tokens
    """
    try:
        from sqlalchemy.orm import joinedload
        
        lesson = db.query(Lesson).options(
            joinedload(Lesson.chapter)
        ).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            return SayanErrorResponse(
                message="الدرس غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        # Check permissions and load product relationship
        course = db.query(Course).options(
            joinedload(Course.product)
        ).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
                message="ليس لديك صلاحية لعرض هذا الدرس",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        # Get lesson videos
        videos = db.query(Video).filter(
            Video.lesson_id == lesson_id,
            Video.deleted_at.is_(None)
        ).all()
        
        # Prepare video information with direct access for academy
        video_info = None
        if lesson.video:
            direct_video_url = f"/static/uploads/{lesson.video}"
            video_info = {
                "has_video": True,
                "video_path": lesson.video,
                "direct_video_url": direct_video_url,  # Direct access for academy
                "video_size": lesson.size_bytes,
                "video_duration": lesson.video_duration,
                "file_size_formatted": f"{round(lesson.size_bytes / (1024*1024), 2)} MB" if lesson.size_bytes else "0 MB",
                "duration_formatted": f"{lesson.video_duration}m" if lesson.video_duration else "0m",
                "videos_count": len(videos),
                "academy_access": True,  # Academy has direct access
                "download_available": True  # Academy can download video
            }
        else:
            video_info = {
                "has_video": False,
                "video_path": None,
                "direct_video_url": None,
                "video_size": 0,
                "video_duration": 0,
                "file_size_formatted": "0 MB",
                "duration_formatted": "0m",
                "videos_count": len(videos),
                "academy_access": True,
                "download_available": False
            }
        
        # Prepare base lesson data
        lesson_data = {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "type": lesson.type,
            "order_number": lesson.order_number,
            "status": lesson.status,
            "is_free_preview": lesson.is_free_preview,
            "chapter_id": lesson.chapter_id,
            "course_id": lesson.course_id,
            "created_at": lesson.created_at.isoformat() if lesson.created_at else None,
            "updated_at": lesson.updated_at.isoformat() if lesson.updated_at else None,
            
            # Course information
            "course_info": {
                "course_id": lesson.course_id,
                "course_title": course.product.title if course.product else "غير محدد",
                "chapter_id": lesson.chapter_id,
                "chapter_title": lesson.chapter.title if lesson.chapter else None
            },
            
            # Access permissions for academy
            "permissions": {
                "can_edit": True,
                "can_delete": True,
                "direct_access": True
            }
        }
        
        # Add type-specific information
        if lesson.type == "video":
            lesson_data.update({
                "video": lesson.video,
                "video_type": lesson.video_type,
                "video_provider": lesson.video_provider,
                "video_duration": lesson.video_duration,
                "size_bytes": lesson.size_bytes,
                "views_count": lesson.views_count,
                "duration_formatted": f"{lesson.video_duration}m" if lesson.video_duration else "0m",
                "file_size_formatted": f"{round(lesson.size_bytes / (1024*1024), 2)} MB" if lesson.size_bytes else "0 MB",
                "video_info": video_info,
            "permissions": {
                "can_edit": True,
                "can_delete": True,
                "can_upload_video": True,
                "can_download_video": True,
                "direct_access": True
            }
            })
        elif lesson.type == "exam":
            # Get exam information
            exam = db.query(Exam).filter(Exam.lesson_id == lesson_id).first()
            exam_info = {
                "has_exam": exam is not None,
                "exam_id": exam.id if exam else None,
                "questions_count": 0,  # Will be updated when exam questions are implemented
                "duration_minutes": exam.duration_minutes if exam else 0,
                "pass_score": exam.pass_score if exam else 0,
                "max_attempts": exam.max_attempts if exam else 0,
                "is_active": exam.is_active if exam else False
            }
            
            lesson_data.update({
                "video_duration": 0,  # لا يوجد فيديو للاختبار
                "size_bytes": 0,      # لا يوجد فيديو للاختبار
                "views_count": 0,     # لا يوجد فيديو للاختبار
                "duration_formatted": "0m",
                "file_size_formatted": "0 MB",
                "exam_info": exam_info,
                "permissions": {
                    "can_edit": True,
                    "can_delete": True,
                    "can_create_exam": True,
                    "direct_access": True
                }
            })
        elif lesson.type == "tool":
            # Get tool information
            tools = db.query(InteractiveTool).filter(InteractiveTool.lesson_id == lesson_id).all()
            tool_info = {
                "tools_count": len(tools),
                "tools": [
                    {
                        "id": tool.id,
                        "title": tool.title,
                        "tool_type": tool.tool_type,
                        "is_active": True
                    } for tool in tools
                ]
            }
            
            lesson_data.update({
                "video_duration": 0,  # لا يوجد فيديو للأداة
                "size_bytes": 0,      # لا يوجد فيديو للأداة
                "views_count": 0,     # لا يوجد فيديو للأداة
                "duration_formatted": "0m",
                "file_size_formatted": "0 MB",
                "tool_info": tool_info,
                "permissions": {
                    "can_edit": True,
                    "can_delete": True,
                    "can_add_tools": True,
                    "direct_access": True
                }
            })
        
        # Prepare success message based on lesson type
        if lesson.type == "video":
            message = "تم جلب تفاصيل درس الفيديو بنجاح"
        elif lesson.type == "exam":
            message = "تم جلب تفاصيل درس الاختبار بنجاح"
        elif lesson.type == "tool":
            message = "تم جلب تفاصيل درس الأداة التفاعلية بنجاح"
        else:
            message = "تم جلب تفاصيل الدرس بنجاح"
        
        return SayanSuccessResponse(
            data=lesson_data,
            message=message
        )
        
    except Exception as e:
        logger.error(f"خطأ في جلب الدرس: {str(e)}")
        return SayanErrorResponse(
            message=f"حدث خطأ أثناء جلب الدرس: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )

@router.put("/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: str,
    lesson_data: LessonUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    Update lesson
    """
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            return SayanErrorResponse(
                message="الدرس غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        # Check permissions
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
                message="ليس لديك صلاحية لتعديل هذا الدرس",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        # Update data
        update_data = lesson_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lesson, field, value)
        
        db.commit()
        db.refresh(lesson)
        
        return lesson
    except HTTPException as http_exc:
        db.rollback()
        return SayanErrorResponse(
            message=http_exc.detail,
            error_type="HTTP_ERROR",
            status_code=http_exc.status_code
        )
    except Exception as e:
        db.rollback()
        return SayanErrorResponse(
            message=f"خطأ أثناء تحديث الدرس: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )

@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Delete lesson"""
    
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            return SayanErrorResponse(
                message="الدرس غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
                message="ليس لديك صلاحية لحذف هذا الدرس",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        db.delete(lesson)
        db.commit()
        
        return SayanSuccessResponse(
            message="تم حذف الدرس بنجاح"
        )
    except HTTPException as http_exc:
        db.rollback()
        return SayanErrorResponse(
            message=http_exc.detail,
            error_type="HTTP_ERROR",
            status_code=http_exc.status_code
        )
    except Exception as e:
        db.rollback()
        return SayanErrorResponse(
            message=f"خطأ أثناء حذف الدرس: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )

@router.post("/{lesson_id}/video")
async def upload_lesson_video(
    lesson_id: str,
    background_tasks: BackgroundTasks,
    video_file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    auto_transcribe: bool = Form(True, description="Enable automatic transcription"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    Upload video for previously created lesson
    Video is uploaded independently from lesson creation
    Maximum 500MB video file size
    Note: Videos > 25MB cannot be automatically transcribed
    """
    try:
        # Find lesson
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            return SayanErrorResponse(
                message="الدرس غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        # Check permissions
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
                message="ليس لديك صلاحية لتحميل فيديو لهذا الدرس",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        # Validate lesson type for video upload
        if lesson.type == "exam":
            return SayanErrorResponse(
                message="لا يمكن رفع فيديو لدرس من نوع اختبار. استخدم رابط إنشاء الاختبار بدلاً من ذلك",
                error_type="INVALID_LESSON_TYPE",
                status_code=400
            )
        elif lesson.type == "tool":
            return SayanErrorResponse(
                message="لا يمكن رفع فيديو لدرس من نوع أداة تفاعلية. استخدم رابط إنشاء الأداة التفاعلية بدلاً من ذلك",
                error_type="INVALID_LESSON_TYPE",
                status_code=400
            )
        
        # Validate file type
        if not video_file.content_type or not video_file.content_type.startswith('video/'):
            return SayanErrorResponse(
                message="الملف يجب أن يكون فيديو",
                error_type="INVALID_FILE_TYPE",
                status_code=400
            )
        
        # Check file size for upload (no maximum limit for upload)
        file_size_mb = round(video_file.size / (1024 * 1024), 2) if video_file.size else 0
        logger.info(f"Uploading video with size {file_size_mb}MB")
        
        # Check transcription capability
        can_transcribe = True  # All videos can be transcribed
        
        # Start transcription if enabled
        if auto_transcribe:
            logger.info(f"Video will be transcribed to text (size: {file_size_mb}MB)")
        
        # Save video file
        video_path = await file_service.save_video_file(video_file, "lessons")
        
        # Create new video record
        video = Video(
            lesson_id=lesson_id,
            title=title,
            description=description,
            video=video_path,
            file_size=video_file.size or 0,
            format=video_file.content_type
        )
        
        db.add(video)
        
        # Update lesson with video info
        lesson.type = "video"
        lesson.video = video_path
        lesson.size_bytes = video_file.size or 0
        
        db.commit()
        db.refresh(video)
        
        # Prepare response with transcription info
        transcription_info = {
            "can_transcribe": can_transcribe,
            "file_size_mb": file_size_mb,
            "max_transcription_size": "No limit",
            "transcription_enabled": auto_transcribe,
            "transcription_status": "processing" if auto_transcribe else "disabled"
        }
        
        # Start transcription if enabled
        if auto_transcribe:
            background_tasks.add_task(
                process_video_transcription_task,
                video_id=video.id,
                lesson_id=lesson_id,
                video_file_path=video_path,
                academy_id=current_user.academy.id,
                db=db
            )
        
        # Build response message
        upload_message = "تم رفع الفيديو بنجاح"
        if auto_transcribe:
            upload_message += f" وبدأ تحويله إلى نص (حجم: {file_size_mb}MB)"
        else:
            upload_message += f" (حجم: {file_size_mb}MB)"
        
        return SayanSuccessResponse(
            message=upload_message,
            data={
                "video_id": video.id,
                "lesson_id": lesson_id,
                "video_url": f"/static/uploads/{video_path}",
                "title": title,
                "description": description,
                "file_size": video_file.size or 0,
                "file_size_mb": file_size_mb,
                "format": video_file.content_type,
                "transcription": transcription_info
            }
        )
        
    except Exception as e:
        logger.error(f"خطأ في رفع الفيديو: {e}")
        return SayanErrorResponse(
            message="حدث خطأ أثناء رفع الفيديو",
            error_type="UPLOAD_ERROR",
            status_code=500
        )

@router.get("/{lesson_id}/transcription/status")
async def get_transcription_status(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    Get video transcription status for a lesson
    Check if transcription is processing, completed, or failed
    """
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            return SayanErrorResponse(
                message="الدرس غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        # Check permissions
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
                message="ليس لديك صلاحية للوصول لهذا الدرس",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        # Get transcription status
        transcription = db.query(VideoTranscription).filter(
            VideoTranscription.lesson_id == lesson_id
        ).first()
        
        if not transcription:
            return SayanSuccessResponse(
                data={
                    "transcription_status": "not_started",
                    "message": "لم يتم بدء تحويل الفيديو إلى نص بعد",
                    "has_transcription": False
                },
                message="لا يوجد تحويل للفيديو"
            )
        
        # Prepare response based on transcription status
        response_data = {
            "transcription_id": transcription.id,
            "status": transcription.processing_status,
            "has_transcription": transcription.processing_status == ProcessingStatus.COMPLETED,
            "language": transcription.language,
            "created_at": transcription.created_at.isoformat() if transcription.created_at else None,
            "updated_at": transcription.updated_at.isoformat() if transcription.updated_at else None
        }
        
        if transcription.processing_status == ProcessingStatus.COMPLETED:
            response_data.update({
                "transcription_text": transcription.transcription_text,
                "confidence_score": float(transcription.confidence_score) if transcription.confidence_score else 0.0,
                "duration_seconds": transcription.duration_seconds,
                "segments_count": len(transcription.segments) if transcription.segments else 0,
                "has_subtitles": bool(transcription.subtitles_srt),
                "message": "تم تحويل الفيديو إلى نص بنجاح"
            })
        elif transcription.processing_status == ProcessingStatus.PROCESSING:
            response_data.update({
                "message": "جاري تحويل الفيديو إلى نص...",
                "estimated_completion": "5-10 دقائق"
            })
        elif transcription.processing_status == ProcessingStatus.FAILED:
            response_data.update({
                "message": "فشل في تحويل الفيديو إلى نص",
                "error": "يرجى المحاولة مرة أخرى أو الاتصال بالدعم الفني"
            })
        
        return SayanSuccessResponse(
            data=response_data,
            message="تم جلب حالة التحويل بنجاح"
        )
        
    except Exception as e:
        return SayanErrorResponse(
            message=f"حدث خطأ في جلب حالة التحويل: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )

@router.get("/{lesson_id}/transcription/text")
async def get_transcription_text(
    lesson_id: str,
    format: str = "text",  # text, srt, json
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    Get transcription text in different formats
    Supports: text, srt, json (with segments)
    """
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            return SayanErrorResponse(
                message="الدرس غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        # Check permissions
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
                message="ليس لديك صلاحية للوصول لهذا الدرس",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        # Get completed transcription
        transcription = db.query(VideoTranscription).filter(
            VideoTranscription.lesson_id == lesson_id,
            VideoTranscription.processing_status == ProcessingStatus.COMPLETED
        ).first()
        
        if not transcription:
            return SayanErrorResponse(
                message="لا يوجد تحويل مكتمل للفيديو",
                error_type="TRANSCRIPTION_NOT_FOUND",
                status_code=404
            )
        
        response_data = {
            "transcription_id": transcription.id,
            "lesson_id": lesson_id,
            "language": transcription.language,
            "confidence_score": float(transcription.confidence_score) if transcription.confidence_score else 0.0,
            "duration_seconds": transcription.duration_seconds,
            "format": format
        }
        
        if format == "text":
            response_data["content"] = transcription.transcription_text
        elif format == "srt":
            response_data["content"] = transcription.subtitles_srt
        elif format == "json":
            response_data["content"] = {
                "text": transcription.transcription_text,
                "segments": transcription.segments,
                "subtitles_srt": transcription.subtitles_srt
            }
        else:
            return SayanErrorResponse(
                message="تنسيق غير مدعوم. الأنواع المدعومة: text, srt, json",
                error_type="INVALID_FORMAT",
                status_code=400
            )
        
        return SayanSuccessResponse(
            data=response_data,
            message="تم جلب النص بنجاح"
        )
        
    except Exception as e:
        return SayanErrorResponse(
            message=f"حدث خطأ في جلب النص: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )

@router.get("/{lesson_id}/status")
async def get_lesson_status(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    Get lesson status and video upload status
    Used to check lesson status and whether video has been uploaded
    """
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            return SayanErrorResponse(
                message="الدرس غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        # Check permissions and load product relationship
        from sqlalchemy.orm import joinedload
        course = db.query(Course).options(
            joinedload(Course.product)
        ).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
                message="ليس لديك صلاحية لعرض هذا الدرس",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        # Prepare base response data
        response_data = {
                "lesson": {
                    "id": lesson.id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "type": lesson.type,
                    "status": lesson.status,
                    "order_number": lesson.order_number,
                    "is_free_preview": lesson.is_free_preview,
                    "created_at": lesson.created_at.isoformat() if lesson.created_at else None,
                    "updated_at": lesson.updated_at.isoformat() if lesson.updated_at else None
                },
            "course_info": {
                "course_id": lesson.course_id,
                "course_title": course.product.title if course.product else "غير محدد",
                "chapter_id": lesson.chapter_id,
                "chapter_title": lesson.chapter.title if lesson.chapter else None
            }
        }
        
        # Add type-specific information
        if lesson.type == "video":
            # Find videos related to lesson
            videos = db.query(Video).filter(
                Video.lesson_id == lesson_id,
                Video.deleted_at.is_(None)
            ).all()
            
            has_video = lesson.video is not None
            videos_count = len(videos)
            
            response_data.update({
                "video_status": {
                    "has_video": has_video,
                    "video_path": lesson.video,
                    "video_size": lesson.size_bytes,
                    "video_duration": lesson.video_duration,
                    "videos_count": videos_count,
                    "upload_complete": has_video and videos_count > 0,
                    "upload_url": f"/api/v1/lessons/{lesson_id}/video"
                },
                "next_actions": [
                    "تحميل فيديو للدرس" if not has_video else "تحديث الفيديو",
                    "إضافة درس جديد",
                    "عرض الدرس",
                    "تعديل معلومات الدرس"
                ]
            })
            message = "تم جلب حالة درس الفيديو بنجاح"
            
        elif lesson.type == "exam":
            # Get exam information
            exam = db.query(Exam).filter(Exam.lesson_id == lesson_id).first()
            
            response_data.update({
                "exam_status": {
                    "has_exam": exam is not None,
                    "exam_id": exam.id if exam else None,
                    "questions_count": 0,  # Will be updated when exam questions are implemented
                    "duration_minutes": exam.duration_minutes if exam else 0,
                    "pass_score": exam.pass_score if exam else 0,
                    "max_attempts": exam.max_attempts if exam else 0,
                    "is_active": exam.is_active if exam else False
                },
                "next_actions": [
                    "إضافة أسئلة الاختبار" if not exam else "تعديل الاختبار",
                    "إضافة درس جديد",
                    "عرض الدرس",
                    "تعديل معلومات الدرس"
                ]
            })
            message = "تم جلب حالة درس الاختبار بنجاح"
            
        elif lesson.type == "tool":
            # Get tool information
            tools = db.query(InteractiveTool).filter(InteractiveTool.lesson_id == lesson_id).all()
            
            response_data.update({
                "tool_status": {
                    "tools_count": len(tools),
                    "tools": [
                        {
                            "id": tool.id,
                            "title": tool.title,
                            "tool_type": tool.tool_type,
                            "is_active": True
                        } for tool in tools
                    ]
                },
                "next_actions": [
                    "إضافة أداة تفاعلية" if len(tools) == 0 else "تعديل الأدوات",
                    "إضافة درس جديد",
                    "عرض الدرس",
                    "تعديل معلومات الدرس"
                ]
            })
            message = "تم جلب حالة درس الأداة التفاعلية بنجاح"
            
        else:
            response_data["next_actions"] = [
                "إضافة درس جديد",
                "عرض الدرس",
                "تعديل معلومات الدرس"
            ]
            message = "تم جلب حالة الدرس بنجاح"
        
        return SayanSuccessResponse(
            data=response_data,
            message=message
        )
        
    except Exception as e:
        return SayanErrorResponse(
            message=f"حدث خطأ أثناء جلب حالة الدرس: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )

@router.post("/{lesson_id}/exam")
async def create_lesson_exam(
    lesson_id: str,
    exam_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    Create exam for lesson
    """
    try:
        # Find lesson
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            return SayanErrorResponse(
                message="الدرس غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        # Check permissions
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
                message="ليس لديك صلاحية لإنشاء امتحان لهذا الدرس",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        # Validate lesson type for exam creation
        if lesson.type == "video":
            return SayanErrorResponse(
                message="لا يمكن إنشاء اختبار لدرس من نوع فيديو. استخدم رابط رفع الفيديو بدلاً من ذلك",
                error_type="INVALID_LESSON_TYPE",
                status_code=400
            )
        elif lesson.type == "tool":
            return SayanErrorResponse(
                message="لا يمكن إنشاء اختبار لدرس من نوع أداة تفاعلية. استخدم رابط إنشاء الأداة التفاعلية بدلاً من ذلك",
                error_type="INVALID_LESSON_TYPE",
                status_code=400
            )
        
        # Create exam with correct fields
        exam = Exam(
            lesson_id=lesson_id,
            title=exam_data.get("title", "اختبار الدرس"),
            duration=exam_data.get("duration_minutes", 30) * 60,  # Convert to seconds
            status=True,
            order_number=0
        )
        
        db.add(exam)
        db.flush()  # Get exam ID before adding questions
        
        # Process questions if provided
        questions_data = exam_data.get("questions", [])
        questions_count = 0
        
        if questions_data:
            for question_data in questions_data:
                # Determine question type - match database enum values
                question_type = QuestionType.TEXT  # Default
                if question_data.get("type") == "multiple_choice":
                    question_type = QuestionType.MULTIPLE_CHOICE
                elif question_data.get("type") == "true_false":
                    question_type = QuestionType.TRUE_FALSE
                elif question_data.get("type") == "text":
                    question_type = QuestionType.TEXT
                
                # Create question
                question = Question(
                    exam_id=exam.id,
                    title=question_data.get("question_text", ""),
                    description=question_data.get("explanation", ""),
                    type=question_type,
                    score=question_data.get("points", 10),
                    correct_answer=question_data.get("explanation", "")
                )
                
                db.add(question)
                db.flush()  # Get question ID before adding options
                
                # Add options for choice-based questions
                if question_data.get("type") in ["multiple_choice", "true_false"]:
                    if question_data.get("options"):
                        # Add custom options for choice-based questions
                        for option_data in question_data.get("options", []):
                            option = QuestionOption(
                                question_id=question.id,
                                text=option_data.get("text", ""),
                                is_correct=option_data.get("is_correct", False)
                            )
                            db.add(option)
                
                questions_count += 1
        
        # Update lesson type to exam
        lesson.type = "exam"
        
        db.commit()
        db.refresh(exam)
        
        return SayanSuccessResponse(
            data={
                "exam": {
                    "id": exam.id,
                    "title": exam.title,
                    "duration_minutes": exam.duration // 60,  # Convert back to minutes
                    "duration_seconds": exam.duration,
                    "status": exam.status,
                    "order_number": exam.order_number,
                    "questions_count": questions_count,
                    "created_at": exam.created_at.isoformat()
                },
                "next_actions": {
                    "add_questions": f"/api/v1/exams/{exam.id}/questions",
                    "message": f"تم إضافة {questions_count} سؤال للاختبار" if questions_count > 0 else "استخدم الرابط أعلاه لإضافة أسئلة الاختبار"
                }
            },
            message=f"تم إنشاء الامتحان بنجاح{' مع ' + str(questions_count) + ' سؤال' if questions_count > 0 else ''}"
        )
        
    except Exception as e:
        db.rollback()
        return SayanErrorResponse(
            message=f"حدث خطأ أثناء إنشاء الامتحان: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )

@router.post("/{lesson_id}/tools")
async def add_interactive_tool(
    lesson_id: str,
    tool_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    Add interactive tool to lesson
    """
    try:
        # Find lesson
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            return SayanErrorResponse(
                message="الدرس غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        # Check permissions
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
                message="ليس لديك صلاحية لإضافة أداة لهذا الدرس",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        # Validate lesson type for tool creation
        if lesson.type == "video":
            return SayanErrorResponse(
                message="لا يمكن إضافة أداة تفاعلية لدرس من نوع فيديو. استخدم رابط رفع الفيديو بدلاً من ذلك",
                error_type="INVALID_LESSON_TYPE",
                status_code=400
            )
        elif lesson.type == "exam":
            return SayanErrorResponse(
                message="لا يمكن إضافة أداة تفاعلية لدرس من نوع اختبار. استخدم رابط إنشاء الاختبار بدلاً من ذلك",
                error_type="INVALID_LESSON_TYPE",
                status_code=400
            )
        
        # Create interactive tool
        tool = InteractiveTool(
            lesson_id=lesson_id,
            title=tool_data.get("title"),
            description=tool_data.get("description"),
            tool_type=tool_data.get("tool_type"),
            url=tool_data.get("url"),
            content=tool_data.get("content"),
            settings=tool_data.get("settings"),
            order_number=tool_data.get("order_number", 1)
        )
        
        db.add(tool)
        
        # Update lesson type to tool
        lesson.type = "tool"
        
        db.commit()
        db.refresh(tool)
        
        return SayanSuccessResponse(
            data={
                "tool": {
                    "id": tool.id,
                    "title": tool.title,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "url": tool.url,
                    "order_number": tool.order_number,
                    "created_at": tool.created_at.isoformat()
                }
            },
            message="تم إضافة الأداة التفاعلية بنجاح"
        )
        
    except Exception as e:
        db.rollback()
        return SayanErrorResponse(
            message=f"حدث خطأ أثناء إضافة الأداة التفاعلية: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )

# Student Progress Endpoints
@router.get("/{lesson_id}/progress", response_model=LessonProgressResponse)
async def get_lesson_progress(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    Get student progress for a lesson with access control
    """
    try:
        # Check if student can access this lesson
        access_service = LessonAccessService(db)
        access_result = access_service.can_access_lesson(current_student.id, int(lesson_id))
        
        if not access_result["is_accessible"]:
            return SayanErrorResponse(
                error_type=access_result.get("error", "ACCESS_DENIED"),
                message=access_result["access_reason"],
                details={"lesson_id": lesson_id}
            )
        
        progress = db.query(LessonProgress).filter(
            LessonProgress.lesson_id == lesson_id,
            LessonProgress.student_id == current_student.id
        ).first()
        
        if not progress:
            # Create default progress if none exists
            lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
            if not lesson:
                return SayanErrorResponse(
                    error_type="LESSON_NOT_FOUND",
                    message="Lesson not found",
                    details={"lesson_id": lesson_id}
                )
            
            progress = LessonProgress(
                student_id=current_student.id,
                lesson_id=lesson_id,
                course_id=lesson.course_id,
                progress_percentage=0,
                completed=False,
                current_position_seconds=0
            )
            
            db.add(progress)
            db.commit()
            db.refresh(progress)
        
        return SayanSuccessResponse(
            data={
                "lesson_id": progress.lesson_id,
                "student_id": progress.student_id,
                "progress_percentage": progress.progress_percentage,
                "completed": progress.completed,
                "current_position_seconds": progress.current_position_seconds,
                "access_info": access_result
            },
            message="Lesson progress retrieved successfully"
        )
    except Exception as e:
        db.rollback()
        return SayanErrorResponse(
            error_type="SYSTEM_ERROR",
            message=f"Error retrieving lesson progress: {str(e)}",
            details={"lesson_id": lesson_id}
        )

@router.put("/{lesson_id}/progress", response_model=LessonProgressResponse)
async def update_lesson_progress(
    lesson_id: str,
    progress_data: LessonProgressUpdate,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    Update student progress for a lesson with access control
    """
    try:
        # Check if student can access this lesson
        access_service = LessonAccessService(db)
        access_result = access_service.can_access_lesson(current_student.id, int(lesson_id))
        
        if not access_result["is_accessible"]:
            return SayanErrorResponse(
                error_type=access_result.get("error", "ACCESS_DENIED"),
                message=access_result["access_reason"],
                details={"lesson_id": lesson_id}
            )
        
        progress = db.query(LessonProgress).filter(
            LessonProgress.lesson_id == lesson_id,
            LessonProgress.student_id == current_student.id
        ).first()
        
        if not progress:
            # Create new progress record
            lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
            if not lesson:
                raise HTTPException(
                    status_code=404,
                    detail={"status": "error", "error": "الدرس غير موجود"}
                )
            
            progress = LessonProgress(
                student_id=current_student.id,
                lesson_id=lesson_id,
                course_id=lesson.course_id,
                progress_percentage=progress_data.progress_percentage,
                completed=progress_data.completed or False,
                current_position_seconds=progress_data.current_position_seconds or 0
            )
            
            db.add(progress)
        else:
            # تحديث التقدم الموجود
            progress.progress_percentage = progress_data.progress_percentage
            if progress_data.completed is not None:
                progress.completed = progress_data.completed
            if progress_data.current_position_seconds is not None:
                progress.current_position_seconds = progress_data.current_position_seconds
            progress.last_watched_at = datetime.now()
        
        db.commit()
        db.refresh(progress)
        
        return progress
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "error": f"حدث خطأ أثناء تحديث تقدم الدرس: {str(e)}"}
        )

@router.get("/{lesson_id}/videos")
async def get_lesson_videos(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Get lesson videos with access control"""
    try:
        # Check if student can access this lesson
        access_service = LessonAccessService(db)
        access_result = access_service.can_access_lesson(current_student.id, int(lesson_id))
        
        if not access_result["is_accessible"]:
            return SayanErrorResponse(
                error_type=access_result.get("error", "ACCESS_DENIED"),
                message=access_result["access_reason"],
                details={"lesson_id": lesson_id}
            )
        
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            return SayanErrorResponse(
                error_type="LESSON_NOT_FOUND",
                message="الدرس غير موجود",
                details={"lesson_id": lesson_id}
            )
        
        videos = db.query(Video).filter(Video.lesson_id == lesson_id).all()
        
        return SayanSuccessResponse(
            data={
                "videos": [
                    {
                        "id": video.id,
                        "title": video.title,
                        "description": video.description,
                        "duration": video.duration,
                        "format": video.format,
                        "resolution": video.resolution,
                        "file_size": video.file_size,
                        "created_at": video.created_at.isoformat()
                    }
                    for video in videos
                ],
                "access_info": access_result
            },
            message="تم جلب فيديوهات الدرس بنجاح"
        )
    except Exception as e:
        return SayanErrorResponse(
            error_type="SYSTEM_ERROR",
            message=f"حدث خطأ في جلب فيديوهات الدرس: {str(e)}",
            details={"lesson_id": lesson_id}
        )

@router.get("/{lesson_id}/exams")
async def get_lesson_exams(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Get lesson exams"""
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            return SayanErrorResponse(
                message="الدرس غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        exams = db.query(Exam).filter(Exam.lesson_id == lesson_id).all()
        
        return SayanSuccessResponse(
            data={
                "exams": [
                    {
                        "id": exam.id,
                        "title": exam.title,
                        "duration_minutes": exam.duration // 60 if exam.duration else 0,
                        "duration_seconds": exam.duration,
                        "status": exam.status,
                        "order_number": exam.order_number,
                        "created_at": exam.created_at.isoformat()
                    }
                    for exam in exams
                ]
            },
            message="تم جلب امتحانات الدرس بنجاح"
        )
        
    except Exception as e:
        return SayanErrorResponse(
            message=f"حدث خطأ في جلب امتحانات الدرس: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )

@router.get("/{lesson_id}/tools")
async def get_lesson_tools(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Get lesson interactive tools"""
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        if not lesson:
            return SayanErrorResponse(
                message="الدرس غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        tools = db.query(InteractiveTool).filter(
            InteractiveTool.lesson_id == lesson_id
        ).order_by(InteractiveTool.order_number).all()
        
        return SayanSuccessResponse(
            data={
                "tools": [
                    {
                        "id": tool.id,
                        "title": tool.title,
                        "description": tool.description,
                        "tool_type": tool.tool_type,
                        "url": tool.url,
                        "content": tool.content,
                        "settings": tool.settings,
                        "order_number": tool.order_number,
                        "created_at": tool.created_at.isoformat()
                    }
                    for tool in tools
                ]
            },
            message="تم جلب أدوات الدرس التفاعلية بنجاح"
        )
        
    except Exception as e:
        return SayanErrorResponse(
            message=f"حدث خطأ في جلب أدوات الدرس: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )

@router.post("/check-video-file")
async def check_video_file(
    video_file: UploadFile = File(...),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    Check video file compatibility before upload
    """
    try:
        # Reset file position
        await video_file.seek(0)
        
        # Check file type
        if not video_file.content_type or not video_file.content_type.startswith('video/'):
            return SayanErrorResponse(
                message="الملف ليس فيديو",
                error_type="INVALID_FILE_TYPE",
                status_code=400
            )
        
        # Get file size
        file_size = video_file.size or 0
        file_size_mb = round(file_size / (1024 * 1024), 2)
        
        # Check upload capability
        can_upload = True
        
        # Check transcription capability (جميع الفيديوهات يمكن تحويلها)
        can_transcribe = True
        
        # Get file service for format validation
        file_service = FileService()
        is_supported_format = video_file.content_type in file_service.allowed_video_types
        
        # Estimate transcription time
        estimated_transcription_time = "5-15 دقيقة حسب حجم الفيديو"
        
        # Generate recommendations
        recommendations = []
        recommendations.append("الفيديو جاهز للرفع والتحويل التلقائي")
        
        if not is_supported_format:
            recommendations.append("استخدم صيغة MP4 أو MOV للحصول على أفضل النتائج")
        
        # Build response
        status = "ready" if is_supported_format else "needs_format_adjustment"
        
        return SayanSuccessResponse(
            message=f"فحص الملف مكتمل - {status}",
            data={
                "file_info": {
                    "name": video_file.filename,
                    "size_bytes": file_size,
                    "size_mb": file_size_mb,
                    "content_type": video_file.content_type,
                    "format_supported": is_supported_format
                },
                "upload_capability": {
                    "can_upload": can_upload,
                    "upload_limit_mb": "بدون حد أقصى",
                    "exceeds_upload_limit": False
                },
                "transcription_capability": {
                    "can_transcribe": can_transcribe,
                    "transcription_limit_mb": "بدون حد أقصى",
                    "exceeds_transcription_limit": False, # Always False now
                    "estimated_time": estimated_transcription_time
                },
                "recommendations": recommendations,
                "status": status,
                "next_action": "يمكن رفع الفيديو وتحويله"
            }
        )
        
    except Exception as e:
        logger.error(f"خطأ في فحص الملف: {e}")
        return SayanErrorResponse(
            message="حدث خطأ في فحص الملف",
            error_type="FILE_CHECK_ERROR",
            status_code=500
        )


@router.get("/video-upload-info")
async def get_video_upload_info(
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    Get video upload limitations and transcription capabilities
    """
    try:
        # Get video processing capabilities
        video_service = VideoProcessingService()
        capabilities = video_service.get_whisper_capabilities()
        
        # Get file service limits
        file_service = FileService()
        
        return SayanSuccessResponse(
            message="معلومات رفع الفيديو وإمكانيات التحويل",
            data={
                "upload_limits": {
                    "max_video_size_mb": "بدون حد أقصى",
                    "max_video_size_bytes": "بدون حد أقصى",
                    "allowed_formats": list(file_service.allowed_video_types),
                    "recommended_formats": ["video/mp4", "video/mov", "video/webm"]
                },
                "transcription_limits": {
                    "max_size_mb": "بدون حد أقصى",
                    "max_size_bytes": "بدون حد أقصى",
                    "service": capabilities["service"],
                    "model": capabilities["model"],
                    "rate_limit": capabilities["rate_limit"],
                    "supported_languages": capabilities["supported_languages"],
                    "supported_formats": [f["format"] for f in capabilities["supported_formats"]]
                },
                "recommendations": {
                    "for_transcription": "جميع الفيديوهات يمكن تحويلها إلى نص - بدون حد أقصى",
                    "for_storage": "يمكن رفع فيديوهات بأي حجم",
                    "optimal_duration": "جميع الفيديوهات مدعومة للتحويل التلقائي",
                    "best_format": "استخدم MP4 أو MOV للحصول على أفضل النتائج"
                },
                "examples": [
                    {
                        "duration": "1-2 دقيقة",
                        "estimated_size": "10-20 MB",
                        "can_upload": True,
                        "can_transcribe": True,
                        "note": "مثالي للتحويل السريع"
                    },
                    {
                        "duration": "5-10 دقائق",
                        "estimated_size": "50-100 MB",
                        "can_upload": True,
                        "can_transcribe": True,
                        "note": "يمكن رفعه وتحويله تلقائياً"
                    },
                    {
                        "duration": "20+ دقائق",
                        "estimated_size": "200+ MB",
                        "can_upload": True,
                        "can_transcribe": True,
                        "note": "يمكن رفعه وتحويله - قد يستغرق وقتاً أطول"
                    }
                ]
            }
        )
        
    except Exception as e:
        logger.error(f"خطأ في جلب معلومات الرفع: {e}")
        return SayanErrorResponse(
            message="حدث خطأ في جلب معلومات الرفع",
            error_type="INFO_ERROR",
            status_code=500
        )