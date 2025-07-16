from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.deps.database import get_db
from app.deps.auth import get_current_user
from app.models.student import Student
from app.services.lesson_access_service import LessonAccessService
from app.core.response_handler import SayanSuccessResponse, SayanErrorResponse

router = APIRouter(prefix="/progression", tags=["Course Progression"])


@router.get("/course/{course_id}")
def get_course_progression(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive course progression information for the current student
    
    Args:
        course_id: ID of the course
        db: Database session
        current_user: Current authenticated student
        
    Returns:
        Course progression information with chapter and lesson details
    """
    try:
        access_service = LessonAccessService(db)
        progression = access_service.get_course_progression(current_user.id, course_id)
        
        if not progression.get("is_enrolled"):
            return SayanErrorResponse(
                error_type="NOT_ENROLLED",
                message="You are not enrolled in this course",
                details={"course_id": course_id}
            )
        
        return SayanSuccessResponse(
            data=progression,
            message="Course progression retrieved successfully"
        )
        
    except Exception as e:
        return SayanErrorResponse(
            error_type="SYSTEM_ERROR",
            message=f"Error retrieving course progression: {str(e)}",
            details={"course_id": course_id}
        )


@router.get("/lesson/{lesson_id}/access")
def check_lesson_access(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check if the current student can access a specific lesson
    
    Args:
        lesson_id: ID of the lesson to check
        db: Database session
        current_user: Current authenticated student
        
    Returns:
        Access information for the lesson
    """
    try:
        access_service = LessonAccessService(db)
        access_result = access_service.can_access_lesson(current_user.id, lesson_id)
        
        return SayanSuccessResponse(
            data=access_result,
            message="Lesson access checked successfully"
        )
        
    except Exception as e:
        return SayanErrorResponse(
            error_type="SYSTEM_ERROR",
            message=f"Error checking lesson access: {str(e)}",
            details={"lesson_id": lesson_id}
        )


@router.get("/chapter/{chapter_id}/completion")
def get_chapter_completion(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get completion information for a specific chapter
    
    Args:
        chapter_id: ID of the chapter
        db: Database session
        current_user: Current authenticated student
        
    Returns:
        Chapter completion information
    """
    try:
        access_service = LessonAccessService(db)
        completion = access_service.get_chapter_completion(current_user.id, chapter_id)
        
        return SayanSuccessResponse(
            data=completion,
            message="Chapter completion retrieved successfully"
        )
        
    except Exception as e:
        return SayanErrorResponse(
            error_type="SYSTEM_ERROR",
            message=f"Error retrieving chapter completion: {str(e)}",
            details={"chapter_id": chapter_id}
        )


@router.get("/course/{course_id}/next-lesson")
def get_next_lesson(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the next accessible lesson for the student in a course
    
    Args:
        course_id: ID of the course
        db: Database session
        current_user: Current authenticated student
        
    Returns:
        Next accessible lesson information
    """
    try:
        access_service = LessonAccessService(db)
        next_lesson = access_service.get_next_accessible_lesson(current_user.id, course_id)
        
        if not next_lesson:
            return SayanSuccessResponse(
                data={"message": "No more lessons available or course completed"},
                message="No next lesson found"
            )
        
        return SayanSuccessResponse(
            data=next_lesson,
            message="Next lesson retrieved successfully"
        )
        
    except Exception as e:
        return SayanErrorResponse(
            error_type="SYSTEM_ERROR",
            message=f"Error retrieving next lesson: {str(e)}",
            details={"course_id": course_id}
        ) 