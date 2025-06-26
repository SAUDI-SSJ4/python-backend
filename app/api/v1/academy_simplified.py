"""
Academy API with Simplified Endpoints
===================================
Using direct IDs instead of nested parameters for cleaner API design
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import random

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user
from app.models.academy import Academy
from app.models.course import Course
from app.models.chapter import Chapter
from app.models.lesson import Lesson
from app.models.user import User

router = APIRouter()

# =====================================
# SIMPLIFIED COURSE ENDPOINTS
# =====================================

@router.get("/courses/{course_id}")
def get_course_details(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Get detailed course information"""
    
    # Verify course ownership
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة أو ليس لديك صلاحية"
        )
    
    return course


@router.put("/courses/{course_id}")
def update_course(
    course_id: str,
    course_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Update course details"""
    
    # Verify course ownership
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة أو ليس لديك صلاحية"
        )
    
    # Update course fields
    for field, value in course_data.items():
        if hasattr(course, field):
            setattr(course, field, value)
    
    db.commit()
    db.refresh(course)
    
    return {
        "status": "success",
        "message": "تم تحديث الدورة بنجاح",
        "course": course
    }


@router.delete("/courses/{course_id}")
def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Delete course"""
    
    # Verify course ownership
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة أو ليس لديك صلاحية"
        )
    
    db.delete(course)
    db.commit()
    
    return {
        "status": "success",
        "message": "تم حذف الدورة بنجاح"
    }


# =====================================
# SIMPLIFIED CHAPTER ENDPOINTS
# =====================================

@router.get("/chapters/{chapter_id}")
def get_chapter_details(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Get chapter details with lessons"""
    
    # Get chapter
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الفصل غير موجود"
        )
    
    # Verify ownership through course
    course = db.query(Course).filter(
        Course.id == chapter.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ليس لديك صلاحية لعرض هذا الفصل"
        )
    
    return chapter


@router.put("/chapters/{chapter_id}")
def update_chapter(
    chapter_id: int,
    chapter_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Update chapter"""
    
    # Get chapter
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الفصل غير موجود"
        )
    
    # Verify ownership through course
    course = db.query(Course).filter(
        Course.id == chapter.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ليس لديك صلاحية لتعديل هذا الفصل"
        )
    
    # Update chapter fields
    for field, value in chapter_data.items():
        if hasattr(chapter, field):
            setattr(chapter, field, value)
    
    db.commit()
    db.refresh(chapter)
    
    return {
        "status": "success",
        "message": "تم تحديث الفصل بنجاح",
        "chapter": chapter
    }


@router.delete("/chapters/{chapter_id}")
def delete_chapter(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Delete chapter"""
    
    # Get chapter
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الفصل غير موجود"
        )
    
    # Verify ownership through course
    course = db.query(Course).filter(
        Course.id == chapter.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ليس لديك صلاحية لحذف هذا الفصل"
        )
    
    db.delete(chapter)
    db.commit()
    
    return {
        "status": "success",
        "message": "تم حذف الفصل بنجاح"
    }


# =====================================
# SIMPLIFIED LESSON ENDPOINTS
# =====================================

@router.get("/lessons/{lesson_id}")
def get_lesson_details(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Get lesson details"""
    
    # Get lesson
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدرس غير موجود"
        )
    
    # Verify ownership through course
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ليس لديك صلاحية لعرض هذا الدرس"
        )
    
    return lesson


@router.put("/lessons/{lesson_id}")
def update_lesson(
    lesson_id: str,
    lesson_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Update lesson"""
    
    # Get lesson
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدرس غير موجود"
        )
    
    # Verify ownership through course
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ليس لديك صلاحية لتعديل هذا الدرس"
        )
    
    # Update lesson fields
    for field, value in lesson_data.items():
        if hasattr(lesson, field):
            setattr(lesson, field, value)
    
    db.commit()
    db.refresh(lesson)
    
    return {
        "status": "success",
        "message": "تم تحديث الدرس بنجاح",
        "lesson": lesson
    }


@router.delete("/lessons/{lesson_id}")
def delete_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Delete lesson"""
    
    # Get lesson
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدرس غير موجود"
        )
    
    # Verify ownership through course
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ليس لديك صلاحية لحذف هذا الدرس"
        )
    
    db.delete(lesson)
    db.commit()
    
    return {
        "status": "success",
        "message": "تم حذف الدرس بنجاح"
    }


# =====================================
# ACADEMY SUMMARY ENDPOINTS
# =====================================

@router.get("/academy/dashboard")
def get_academy_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Get academy dashboard data"""
    
    academy = current_user.academy
    
    # Get academy statistics
    total_courses = db.query(Course).filter(
        Course.academy_id == academy.id
    ).count()
    
    published_courses = db.query(Course).filter(
        Course.academy_id == academy.id,
        Course.status == "published"
    ).count()
    
    total_chapters = db.query(Chapter).join(Course).filter(
        Course.academy_id == academy.id
    ).count()
    
    total_lessons = db.query(Lesson).join(Course).filter(
        Course.academy_id == academy.id
    ).count()
    
    return {
        "academy": academy,
        "statistics": {
            "total_courses": total_courses,
            "published_courses": published_courses,
            "total_chapters": total_chapters,
            "total_lessons": total_lessons
        }
    } 