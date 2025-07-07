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
    بث الفيديو المحمي مع طبقات الحماية المتقدمة
    
    الحمايات المُطبقة:
    - فحص JWT token مع client fingerprint
    - منع User Agents المشبوهة (curl, wget, youtube-dl, etc.)
    - فحص IP و Referer
    - منع أدوات التحميل
    - Headers حماية متقدمة
    """
    try:
        # التحقق من رمز الوصول مع فحص معلومات العميل
        payload = video_streaming_service.verify_video_token(token, request)
        video_id_from_token = payload.get("video_id")
        student_id = payload.get("student_id")
        
        # التأكد من أن التوكن خاص بهذا الفيديو
        if video_id_from_token != video_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="رمز الوصول غير صالح لهذا الفيديو"
            )
        
        # التحقق من وصول الطالب للفيديو
        video, is_enrolled = video_streaming_service.verify_student_access(
            db, video_id, student_id
        )
        
        # الحصول على مسار ملف الفيديو
        file_path = video_streaming_service.get_video_file_path(video)
        
        # تسجيل الوصول للفيديو مع معلومات الحماية
        video_streaming_service.log_video_access(db, video_id, student_id, request)
        
        # الحصول على Range header للبث المتقطع
        range_header = request.headers.get("range")
        
        # إنشاء استجابة بث محمية
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
    request: Request,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """
    إنشاء رمز وصول آمن للفيديو مع بصمة العميل
    
    يتم ربط التوكن بـ:
    - معرف الطالب
    - معرف الفيديو
    - User Agent
    - عنوان IP
    - Referer (إن وجد)
    """
    try:
        # التحقق من وصول الطالب للفيديو
        video, is_enrolled = video_streaming_service.verify_student_access(
            db, video_id, current_student.id
        )
        
        # جمع معلومات العميل للحماية
        client_info = {
            'user_agent': request.headers.get('user-agent', ''),
            'ip': request.client.host,
            'referer': request.headers.get('referer', '')
        }
        
        # إنشاء رمز وصول مع معلومات العميل
        token = video_streaming_service.generate_video_token(
            video_id, current_student.id, client_info=client_info
        )
        
        return {
            "status": True,
            "message": "تم إنشاء رمز الوصول بنجاح",
            "data": {
                "access_token": token,
                "video_id": video_id,
                "stream_url": f"/api/v1/videos/stream/{video_id}?token={token}",
                "expires_in": 7200,  # ساعتين بالثواني
                "security_info": {
                    "protected": True,
                    "download_blocked": True,
                    "device_bound": True
                }
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
    تحديث تقدم الطالب في الدرس
    """
    try:
        # الحصول على أو إنشاء سجل تقدم الدرس
        progress = db.query(LessonProgress).filter(
            LessonProgress.lesson_id == lesson_id,
            LessonProgress.student_id == current_student.id
        ).first()
        
        if not progress:
            # إنشاء سجل تقدم جديد
            progress = LessonProgress(
                lesson_id=lesson_id,
                student_id=current_student.id,
                course_id=progress_data.get("course_id"),
                progress_percentage=progress_data.progress_percentage,
                current_position_seconds=progress_data.current_position_seconds or 0,
                completed=progress_data.completed or False
            )
            db.add(progress)
        else:
            # تحديث التقدم الموجود
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
    الحصول على تقدم الطالب في الدرس
    """
    progress = db.query(LessonProgress).filter(
        LessonProgress.lesson_id == lesson_id,
        LessonProgress.student_id == current_student.id
    ).first()
    
    if not progress:
        # إرجاع تقدم افتراضي إذا لم يوجد
        return LessonProgressResponse(
            id="",
            student_id=current_student.id,
            lesson_id=lesson_id,
            course_id="",
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
    الحصول على معلومات الفيديو مع حالة الحماية
    """
    try:
        # التحقق من وصول الطالب للفيديو
        video, is_enrolled = video_streaming_service.verify_student_access(
            db, video_id, current_student.id
        )
        
        # الحصول على معلومات ملف الفيديو
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
                "lesson_id": video.lesson_id,
                "protection_status": {
                    "download_protected": True,
                    "hotlink_protected": True,
                    "user_agent_filtered": True,
                    "token_secured": True
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء جلب معلومات الفيديو: {str(e)}"
        )


@router.get("/security-check")
async def security_check(request: Request):
    """
    فحص حالة الحماية للعميل الحالي
    """
    try:
        user_agent = request.headers.get('user-agent', '')
        
        # فحص User Agent
        security_status = {
            "client_supported": True,
            "user_agent": user_agent,
            "ip_address": request.client.host,
            "security_level": "high"
        }
        
        # فحص إذا كان العميل محظور
        blocked_agents = video_streaming_service.BLOCKED_USER_AGENTS
        for blocked in blocked_agents:
            if blocked in user_agent.lower():
                security_status["client_supported"] = False
                security_status["security_level"] = "blocked"
                break
        
        # فحص المتصفحات المدعومة
        valid_browsers = ['chrome', 'firefox', 'safari', 'edge', 'opera']
        if not any(browser in user_agent.lower() for browser in valid_browsers):
            security_status["client_supported"] = False
            security_status["security_level"] = "unsupported"
        
        return {
            "status": True,
            "data": security_status
        }
        
    except Exception as e:
        return {
            "status": False,
            "error": str(e)
        } 