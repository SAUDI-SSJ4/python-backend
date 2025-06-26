from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user, get_current_student
from app.models.lesson import Lesson
from app.models.chapter import Chapter
from app.models.course import Course
from app.models.student import Student
from app.models.lesson_progress import LessonProgress
from app.models.video import Video
from app.models.exam import Exam
from app.models.interactive_tool import InteractiveTool
from app.schemas.lesson import (
    LessonCreate, 
    LessonUpdate, 
    LessonResponse, 
    LessonListResponse,
    LessonProgressUpdate,
    LessonProgressResponse
)
from app.services.file_service import upload_video_file

router = APIRouter()

@router.post("/", response_model=LessonResponse)
async def create_lesson(
    lesson_data: LessonCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    إنشاء درس جديد
    """
    # التحقق من وجود الفصل والصلاحية
    chapter = db.query(Chapter).filter(
        Chapter.id == lesson_data.chapter_id
    ).first()
    
    if not chapter:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error": "الفصل غير موجود"}
        )
    
    # التحقق من أن الأكاديمية تملك الكورس
    course = db.query(Course).filter(
        Course.id == chapter.course_id,
        Course.academy_id == current_user.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "error": "ليس لديك صلاحية لإنشاء درس في هذا الكورس"}
        )
    
    # إنشاء الدرس
    lesson = Lesson(
        chapter_id=lesson_data.chapter_id,
        course_id=chapter.course_id,
        title=lesson_data.title,
        description=lesson_data.description,
        order_number=lesson_data.order_number,
        type=lesson_data.type,
        is_free_preview=lesson_data.is_free_preview
    )
    
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    
    return lesson

@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    الحصول على تفاصيل الدرس
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error": "الدرس غير موجود"}
        )
    
    # التحقق من الصلاحية
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "error": "ليس لديك صلاحية لعرض هذا الدرس"}
        )
    
    return lesson

@router.put("/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: str,
    lesson_data: LessonUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    تحديث الدرس
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error": "الدرس غير موجود"}
        )
    
    # التحقق من الصلاحية
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "error": "ليس لديك صلاحية لتعديل هذا الدرس"}
        )
    
    # تحديث البيانات
    update_data = lesson_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lesson, field, value)
    
    db.commit()
    db.refresh(lesson)
    
    return lesson

@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    حذف الدرس
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error": "الدرس غير موجود"}
        )
    
    # التحقق من الصلاحية
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "error": "ليس لديك صلاحية لحذف هذا الدرس"}
        )
    
    db.delete(lesson)
    db.commit()
    
    return {"status": "success", "message": "تم حذف الدرس بنجاح"}

@router.post("/{lesson_id}/video")
async def upload_lesson_video(
    lesson_id: str,
    video_file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    رفع فيديو للدرس
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error": "الدرس غير موجود"}
        )
    
    # التحقق من الصلاحية
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "error": "ليس لديك صلاحية لرفع فيديو لهذا الدرس"}
        )
    
    # رفع الفيديو
    video_path = await upload_video_file(video_file, current_user.id)
    
    # إنشاء سجل الفيديو
    video = Video(
        lesson_id=lesson_id,
        title=title,
        description=description,
        video_path=video_path,
        file_size=video_file.size or 0,
        format=video_file.content_type or "video/mp4"
    )
    
    db.add(video)
    
    # تحديث الدرس ليصبح نوعه فيديو
    lesson.type = "video"
    lesson.video = video_path
    lesson.size_bytes = video_file.size or 0
    
    db.commit()
    db.refresh(video)
    
    return {
        "status": "success",
        "message": "تم رفع الفيديو بنجاح",
        "video": {
            "id": video.id,
            "title": video.title,
            "description": video.description,
            "video_path": video.video_path,
            "file_size": video.file_size,
            "format": video.format,
            "created_at": video.created_at.isoformat()
        }
    }

@router.post("/{lesson_id}/exam")
async def create_lesson_exam(
    lesson_id: str,
    exam_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    إنشاء امتحان للدرس
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error": "الدرس غير موجود"}
        )
    
    # التحقق من الصلاحية
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "error": "ليس لديك صلاحية لإنشاء امتحان لهذا الدرس"}
        )
    
    # إنشاء الامتحان
    exam = Exam(
        lesson_id=lesson_id,
        title=exam_data.get("title"),
        description=exam_data.get("description"),
        duration_minutes=exam_data.get("duration_minutes", 30),
        pass_score=exam_data.get("pass_score", 70),
        max_attempts=exam_data.get("max_attempts", 3),
        is_active=True
    )
    
    db.add(exam)
    
    # تحديث نوع الدرس ليصبح امتحان
    lesson.type = "exam"
    
    db.commit()
    db.refresh(exam)
    
    return {
        "status": "success",
        "message": "تم إنشاء الامتحان بنجاح",
        "exam": {
            "id": exam.id,
            "title": exam.title,
            "description": exam.description,
            "duration_minutes": exam.duration_minutes,
            "pass_score": exam.pass_score,
            "max_attempts": exam.max_attempts,
            "created_at": exam.created_at.isoformat()
        }
    }

@router.post("/{lesson_id}/tools")
async def add_interactive_tool(
    lesson_id: str,
    tool_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    إضافة أداة تفاعلية للدرس
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error": "الدرس غير موجود"}
        )
    
    # التحقق من الصلاحية
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "error": "ليس لديك صلاحية لإضافة أداة لهذا الدرس"}
        )
    
    # إنشاء الأداة التفاعلية
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
    
    # تحديث نوع الدرس ليصبح أداة تفاعلية
    lesson.type = "tool"
    
    db.commit()
    db.refresh(tool)
    
    return {
        "status": "success",
        "message": "تم إضافة الأداة التفاعلية بنجاح",
        "tool": {
            "id": tool.id,
            "title": tool.title,
            "description": tool.description,
            "tool_type": tool.tool_type,
            "url": tool.url,
            "order_number": tool.order_number,
            "created_at": tool.created_at.isoformat()
        }
    }

# Student Progress Endpoints
@router.get("/{lesson_id}/progress", response_model=LessonProgressResponse)
async def get_lesson_progress(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    الحصول على تقدم الطالب في الدرس
    """
    progress = db.query(LessonProgress).filter(
        LessonProgress.lesson_id == lesson_id,
        LessonProgress.student_id == current_student.id
    ).first()
    
    if not progress:
        # إنشاء تقدم افتراضي إذا لم يوجد
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
            progress_percentage=0,
            completed=False,
            current_position_seconds=0
        )
        
        db.add(progress)
        db.commit()
        db.refresh(progress)
    
    return progress

@router.put("/{lesson_id}/progress", response_model=LessonProgressResponse)
async def update_lesson_progress(
    lesson_id: str,
    progress_data: LessonProgressUpdate,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    تحديث تقدم الطالب في الدرس
    """
    progress = db.query(LessonProgress).filter(
        LessonProgress.lesson_id == lesson_id,
        LessonProgress.student_id == current_student.id
    ).first()
    
    if not progress:
        # إنشاء سجل تقدم جديد
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

@router.get("/{lesson_id}/videos")
async def get_lesson_videos(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    الحصول على فيديوهات الدرس
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error": "الدرس غير موجود"}
        )
    
    videos = db.query(Video).filter(Video.lesson_id == lesson_id).all()
    
    return {
        "status": "success",
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
        ]
    }

@router.get("/{lesson_id}/exams")
async def get_lesson_exams(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    الحصول على امتحانات الدرس
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error": "الدرس غير موجود"}
        )
    
    exams = db.query(Exam).filter(Exam.lesson_id == lesson_id).all()
    
    return {
        "status": "success",
        "exams": [
            {
                "id": exam.id,
                "title": exam.title,
                "description": exam.description,
                "duration_minutes": exam.duration_minutes,
                "pass_score": exam.pass_score,
                "max_attempts": exam.max_attempts,
                "is_active": exam.is_active,
                "created_at": exam.created_at.isoformat()
            }
            for exam in exams
        ]
    }

@router.get("/{lesson_id}/tools")
async def get_lesson_tools(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    الحصول على الأدوات التفاعلية للدرس
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "error": "الدرس غير موجود"}
        )
    
    tools = db.query(InteractiveTool).filter(
        InteractiveTool.lesson_id == lesson_id
    ).order_by(InteractiveTool.order_number).all()
    
    return {
        "status": "success",
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
    }