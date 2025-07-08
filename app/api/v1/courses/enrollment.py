from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Any, List, Optional
import random
from datetime import datetime, timedelta

from app.deps.database import get_db
from app.deps.auth import get_current_student
from app.models.student import Student
from app.core.response_handler import SayanSuccessResponse

router = APIRouter()


def generate_enrolled_course(course_id: int):
    """Generate mock enrolled course data"""
    course_titles = [
        "Python Programming Masterclass",
        "Web Development with React", 
        "Data Science & Machine Learning",
        "Mobile App Development",
        "Digital Marketing Strategy"
    ]
    
    return {
        "id": course_id,
        "title": course_titles[(course_id - 1) % len(course_titles)],
        "slug": f"course-{course_id}",
        "description": f"Comprehensive course covering {course_titles[(course_id - 1) % len(course_titles)]}",
        "thumbnail": f"https://example.com/course-{course_id}.jpg",
        "academy": {
            "id": (course_id % 3) + 1,
            "name": f"Tech Academy {(course_id % 3) + 1}",
            "logo": f"https://example.com/academy-{(course_id % 3) + 1}-logo.jpg"
        },
        "progress": random.randint(0, 100),
        "completed_lessons": random.randint(5, 25),
        "total_lessons": random.randint(30, 50),
        "duration": random.randint(10, 40),  # hours
        "level": random.choice(["BEGINNER", "INTERMEDIATE", "ADVANCED"]),
        "certificate_enabled": True,
        "certificate_earned": random.choice([True, False]),
        "enrolled_at": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
        "last_accessed": (datetime.now() - timedelta(days=random.randint(0, 7))).isoformat(),
        "expires_at": (datetime.now() + timedelta(days=365)).isoformat(),
        "is_active": True,
        "rating_given": random.randint(4, 5) if random.choice([True, False]) else None
    }


@router.get("/student/enrolled")
def get_student_enrolled_courses(
    request: Request,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Get courses enrolled by current student"""
    try:
        # Generate mock enrolled courses for the student
        enrolled_courses = [generate_enrolled_course(i) for i in range(1, 6)]
        
        # Add some statistics
        stats = {
            "total_enrolled": len(enrolled_courses),
            "completed": len([c for c in enrolled_courses if c["progress"] == 100]),
            "in_progress": len([c for c in enrolled_courses if 0 < c["progress"] < 100]),
            "not_started": len([c for c in enrolled_courses if c["progress"] == 0]),
            "certificates_earned": len([c for c in enrolled_courses if c["certificate_earned"]])
        }
        
        return SayanSuccessResponse(
            data={
                "courses": enrolled_courses,
                "stats": stats
            },
            message="الكورسات المسجل بها",
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في جلب الكورسات: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.get("/student/progress/{course_id}")
def get_course_progress(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Get detailed progress for a specific course"""
    try:
        # Generate mock progress data
        progress_data = {
            "course_id": course_id,
            "overall_progress": random.randint(20, 95),
            "completed_lessons": random.randint(5, 20),
            "total_lessons": random.randint(25, 40),
            "time_spent": random.randint(5, 30),  # hours
            "last_lesson_completed": {
                "id": random.randint(1, 20),
                "title": "Important Lesson",
                "completed_at": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat()
            },
            "next_lesson": {
                "id": random.randint(21, 40),
                "title": "Next Lesson to Complete",
                "chapter": "Chapter 3"
            },
            "chapters_progress": [
                {
                    "id": i,
                    "title": f"Chapter {i}",
                    "progress": random.randint(0, 100),
                    "lessons_completed": random.randint(0, 8),
                    "total_lessons": random.randint(5, 8)
                }
                for i in range(1, 6)
            ],
            "quiz_scores": [
                {
                    "quiz_id": i,
                    "title": f"Quiz {i}",
                    "score": random.randint(70, 100),
                    "attempts": random.randint(1, 3),
                    "completed_at": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
                }
                for i in range(1, 4)
            ]
        }
        
        return SayanSuccessResponse(
            data=progress_data,
            message="تقدم الكورس",
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في جلب التقدم: {str(e)}", "error_type": "Internal Server Error"}
        )

