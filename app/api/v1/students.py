from typing import Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import random

from app.deps import get_db, get_current_student, get_current_admin

router = APIRouter()


def generate_mock_enrollment(enrollment_id: int, student_id: int):
    """Generate mock enrollment data"""
    course_titles = [
        "Python Programming Masterclass",
        "Web Development with React", 
        "Data Science & Machine Learning",
        "Mobile App Development",
        "Digital Marketing Strategy"
    ]
    
    return {
        "id": enrollment_id,
        "student_id": student_id,
        "course": {
            "id": (enrollment_id % 5) + 1,
            "title": course_titles[(enrollment_id - 1) % len(course_titles)],
            "thumbnail": f"https://example.com/course-{(enrollment_id % 5) + 1}.jpg",
            "academy": {
                "id": (enrollment_id % 3) + 1,
                "name": f"Tech Academy {(enrollment_id % 3) + 1}",
                "logo": f"https://example.com/academy-{(enrollment_id % 3) + 1}-logo.jpg"
            }
        },
        "enrolled_at": (datetime.now() - timedelta(days=enrollment_id * 5)).isoformat(),
        "progress_percentage": random.randint(10, 100),
        "completed_lessons": random.randint(5, 25),
        "total_lessons": random.randint(25, 50),
        "last_accessed": (datetime.now() - timedelta(days=random.randint(0, 7))).isoformat(),
        "status": random.choice(["ACTIVE", "COMPLETED", "PAUSED"]),
        "certificate_earned": random.choice([True, False]),
        "rating_given": random.randint(4, 5) if random.choice([True, False]) else None,
        "time_spent": random.randint(300, 1800)  # minutes
    }


def generate_mock_progress(student_id: int, course_id: int):
    """Generate mock learning progress"""
    chapters = []
    
    for chapter_num in range(1, 6):  # 5 chapters
        lessons = []
        
        for lesson_num in range(1, 6):  # 5 lessons per chapter
            lesson_id = (chapter_num - 1) * 5 + lesson_num
            
            # Simulate realistic progress
            is_completed = lesson_id <= (student_id + course_id) * 2
            
            lesson = {
                "id": lesson_id,
                "title": f"Lesson {lesson_num}: Important Topic",
                "duration": random.randint(15, 45),
                "completed": is_completed,
                "completed_at": datetime.now().isoformat() if is_completed else None,
                "time_spent": random.randint(10, 45) if is_completed else 0,
                "progress_percentage": 100 if is_completed else random.randint(0, 80),
                "quiz_score": random.randint(70, 100) if is_completed else None,
                "notes_count": random.randint(0, 5)
            }
            lessons.append(lesson)
        
        chapter = {
            "id": chapter_num,
            "title": f"Chapter {chapter_num}: Core Concepts",
            "lessons": lessons,
            "completed_lessons": len([l for l in lessons if l["completed"]]),
            "total_lessons": len(lessons),
            "progress_percentage": round(
                (len([l for l in lessons if l["completed"]]) / len(lessons)) * 100, 1
            )
        }
        chapters.append(chapter)
    
    return {
        "course_id": course_id,
        "student_id": student_id,
        "chapters": chapters,
        "overall_progress": round(
            sum(c["progress_percentage"] for c in chapters) / len(chapters), 1
        ),
        "total_completed_lessons": sum(c["completed_lessons"] for c in chapters),
        "total_lessons": sum(c["total_lessons"] for c in chapters),
        "last_updated": datetime.now().isoformat()
    }


def generate_mock_certificate(cert_id: int, student_id: int):
    """Generate mock certificate data"""
    course_titles = [
        "Python Programming Masterclass",
        "Web Development with React",
        "Data Science & Machine Learning"
    ]
    
    return {
        "id": cert_id,
        "student_id": student_id,
        "course": {
            "id": (cert_id % 3) + 1,
            "title": course_titles[(cert_id - 1) % len(course_titles)],
            "academy": {
                "name": f"Tech Academy {(cert_id % 3) + 1}",
                "logo": f"https://example.com/academy-{(cert_id % 3) + 1}-logo.jpg"
            }
        },
        "certificate_number": f"CERT-{student_id}-{cert_id}-{datetime.now().strftime('%Y%m')}",
        "issued_at": (datetime.now() - timedelta(days=cert_id * 10)).isoformat(),
        "completion_date": (datetime.now() - timedelta(days=cert_id * 12)).isoformat(),
        "final_score": random.randint(85, 100),
        "grade": "A" if random.randint(85, 100) >= 90 else "B",
        "certificate_url": f"https://certificates.example.com/cert-{cert_id}.pdf",
        "verification_url": f"https://verify.example.com/cert-{cert_id}",
        "skills_earned": [
            "Programming Fundamentals",
            "Problem Solving",
            "Project Development"
        ]
    }


# Student Profile & Dashboard
@router.get("/profile")
def get_student_profile(
    current_user = Depends(get_current_student)
) -> Any:
    """Get student profile and dashboard data"""
    
    # Generate enrollments
    enrollments = [generate_mock_enrollment(i, current_user.id) for i in range(1, 6)]
    
    # Calculate statistics
    completed_courses = len([e for e in enrollments if e["status"] == "COMPLETED"])
    active_courses = len([e for e in enrollments if e["status"] == "ACTIVE"])
    certificates_earned = len([e for e in enrollments if e["certificate_earned"]])
    
    profile = {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": getattr(current_user, 'phone', None),
        "avatar": f"https://example.com/avatar-{current_user.id}.jpg",
        "date_of_birth": "1995-01-01",
        "country": "Saudi Arabia",
        "city": "Riyadh",
        "joined_at": "2024-01-01T00:00:00Z",
        "last_active": datetime.now().isoformat(),
        "statistics": {
            "total_enrollments": len(enrollments),
            "completed_courses": completed_courses,
            "active_courses": active_courses,
            "certificates_earned": certificates_earned,
            "total_study_hours": sum(e["time_spent"] for e in enrollments) // 60,
            "average_progress": round(
                sum(e["progress_percentage"] for e in enrollments) / len(enrollments), 1
            ) if enrollments else 0
        },
        "recent_activity": [
            {
                "type": "lesson_completed",
                "description": "Completed 'Variables and Data Types'",
                "course_title": "Python Programming",
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat()
            },
            {
                "type": "quiz_passed",
                "description": "Passed Chapter 3 Quiz with 95%",
                "course_title": "Web Development",
                "timestamp": (datetime.now() - timedelta(days=1)).isoformat()
            }
        ]
    }
    
    return profile


@router.put("/profile")
def update_student_profile(
    profile_data: dict,
    current_user = Depends(get_current_student)
) -> Any:
    """Update student profile"""
    
    updated_profile = {
        "id": current_user.id,
        "name": profile_data.get("name", current_user.name),
        "phone": profile_data.get("phone"),
        "date_of_birth": profile_data.get("date_of_birth"),
        "country": profile_data.get("country"),
        "city": profile_data.get("city"),
        "bio": profile_data.get("bio"),
        "updated_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Profile updated successfully",
        "profile": updated_profile
    }


# Student Enrollments
@router.get("/enrollments")
def get_student_enrollments(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    status: Optional[str] = None,
    current_user = Depends(get_current_student)
) -> Any:
    """Get student enrollments"""
    enrollments = [generate_mock_enrollment(i, current_user.id) for i in range(1, 16)]
    
    # Filter by status
    if status:
        enrollments = [e for e in enrollments if e["status"] == status.upper()]
    
    return {
        "data": enrollments[skip:skip + limit],
        "total": len(enrollments),
        "skip": skip,
        "limit": limit,
        "filters": {
            "statuses": ["ACTIVE", "COMPLETED", "PAUSED"]
        }
    }


@router.get("/enrollments/{course_id}/progress")
def get_course_progress(
    course_id: int,
    current_user = Depends(get_current_student)
) -> Any:
    """Get detailed progress for a specific course"""
    
    # Check if enrolled
    if course_id % 7 != 0:  # Mock check
        raise HTTPException(
            status_code=404,
            detail="You are not enrolled in this course"
        )
    
    progress = generate_mock_progress(current_user.id, course_id)
    
    return progress


@router.post("/enrollments/{course_id}/progress")
def update_lesson_progress(
    course_id: int,
    progress_data: dict,
    current_user = Depends(get_current_student)
) -> Any:
    """Update progress for a specific lesson"""
    
    lesson_id = progress_data.get("lesson_id")
    progress_percentage = progress_data.get("progress_percentage", 0)
    completed = progress_data.get("completed", False)
    time_spent = progress_data.get("time_spent", 0)
    
    updated_progress = {
        "lesson_id": lesson_id,
        "course_id": course_id,
        "student_id": current_user.id,
        "progress_percentage": progress_percentage,
        "completed": completed,
        "time_spent": time_spent,
        "updated_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Progress updated successfully",
        "progress": updated_progress
    }


# Student Certificates
@router.get("/certificates")
def get_student_certificates(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    current_user = Depends(get_current_student)
) -> Any:
    """Get student certificates"""
    certificates = [
        generate_mock_certificate(i, current_user.id) 
        for i in range(1, 6)
    ]
    
    return {
        "data": certificates[skip:skip + limit],
        "total": len(certificates),
        "skip": skip,
        "limit": limit
    }


@router.get("/certificates/{certificate_id}")
def get_certificate_details(
    certificate_id: int,
    current_user = Depends(get_current_student)
) -> Any:
    """Get certificate details"""
    certificate = generate_mock_certificate(certificate_id, current_user.id)
    
    # Add verification details
    certificate["verification"] = {
        "is_valid": True,
        "verified_at": datetime.now().isoformat(),
        "verification_code": f"VER-{certificate_id}-{current_user.id}",
        "blockchain_hash": f"0x{certificate_id:064x}"
    }
    
    return certificate


# Student Notes & Bookmarks
@router.get("/notes")
def get_student_notes(
    course_id: Optional[int] = None,
    lesson_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    current_user = Depends(get_current_student)
) -> Any:
    """Get student notes"""
    notes = []
    
    for i in range(1, 21):
        note = {
            "id": i,
            "student_id": current_user.id,
            "course_id": (i % 5) + 1,
            "lesson_id": (i % 10) + 1,
            "content": f"Important note {i}: This is a key concept to remember.",
            "timestamp": random.randint(100, 3600),  # Video timestamp in seconds
            "created_at": (datetime.now() - timedelta(days=i)).isoformat(),
            "updated_at": (datetime.now() - timedelta(days=i//2)).isoformat()
        }
        notes.append(note)
    
    # Apply filters
    if course_id:
        notes = [n for n in notes if n["course_id"] == course_id]
    if lesson_id:
        notes = [n for n in notes if n["lesson_id"] == lesson_id]
    
    return {
        "data": notes[skip:skip + limit],
        "total": len(notes),
        "skip": skip,
        "limit": limit
    }


@router.post("/notes")
def create_note(
    note_data: dict,
    current_user = Depends(get_current_student)
) -> Any:
    """Create a new note"""
    note = {
        "id": random.randint(100, 999),
        "student_id": current_user.id,
        "course_id": note_data.get("course_id"),
        "lesson_id": note_data.get("lesson_id"),
        "content": note_data.get("content"),
        "timestamp": note_data.get("timestamp", 0),
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Note created successfully",
        "note": note
    }


@router.put("/notes/{note_id}")
def update_note(
    note_id: int,
    note_data: dict,
    current_user = Depends(get_current_student)
) -> Any:
    """Update a note"""
    return {
        "message": "Note updated successfully",
        "note": {
            "id": note_id,
            "content": note_data.get("content"),
            "updated_at": datetime.now().isoformat()
        }
    }


@router.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    current_user = Depends(get_current_student)
) -> Any:
    """Delete a note"""
    return {"message": "Note deleted successfully"}


# Student Analytics & Statistics
@router.get("/analytics")
def get_student_analytics(
    period: str = Query("month", pattern="^(week|month|year)$"),
    current_user = Depends(get_current_student)
) -> Any:
    """Get student learning analytics"""
    
    analytics = {
        "period": period,
        "study_time": {
            "total_minutes": random.randint(1000, 5000),
            "daily_average": random.randint(30, 120),
            "weekly_data": [
                {
                    "day": f"Day {i}",
                    "minutes": random.randint(0, 180)
                }
                for i in range(1, 8)
            ]
        },
        "progress": {
            "lessons_completed": random.randint(20, 100),
            "quizzes_passed": random.randint(10, 50),
            "certificates_earned": random.randint(1, 5),
            "average_quiz_score": random.randint(75, 95)
        },
        "engagement": {
            "login_days": random.randint(15, 30),
            "video_completion_rate": random.randint(80, 95),
            "quiz_participation_rate": random.randint(70, 90),
            "note_taking_frequency": random.randint(5, 20)
        },
        "achievements": [
            {
                "id": 1,
                "title": "Fast Learner",
                "description": "Completed 10 lessons in a week",
                "icon": "⚡",
                "earned_at": datetime.now().isoformat()
            },
            {
                "id": 2,
                "title": "Quiz Master",
                "description": "Scored 90%+ on 5 consecutive quizzes",
                "icon": "🏆",
                "earned_at": datetime.now().isoformat()
            }
        ]
    }
    
    return analytics


# Admin endpoints for student management
@router.get("/admin/students")
def get_all_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    current_user = Depends(get_current_admin)
) -> Any:
    """Get all students (admin only)"""
    students = []
    
    for i in range(1, 51):
        student = {
            "id": i,
            "name": f"Student {i}",
            "email": f"student{i}@example.com",
            "phone": f"05{random.randint(10000000, 99999999)}",
            "status": random.choice(["ACTIVE", "INACTIVE", "SUSPENDED"]),
            "enrollments_count": random.randint(1, 10),
            "certificates_count": random.randint(0, 5),
            "total_study_hours": random.randint(10, 500),
            "joined_at": (datetime.now() - timedelta(days=i * 10)).isoformat(),
            "last_active": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
        }
        students.append(student)
    
    # Apply filters
    if search:
        students = [s for s in students if search.lower() in s["name"].lower() or search.lower() in s["email"].lower()]
    if status:
        students = [s for s in students if s["status"] == status.upper()]
    
    return {
        "data": students[skip:skip + limit],
        "total": len(students),
        "skip": skip,
        "limit": limit,
        "statistics": {
            "total_students": len(students),
            "active_students": len([s for s in students if s["status"] == "ACTIVE"]),
            "new_this_month": random.randint(10, 50),
            "total_study_hours": sum(s["total_study_hours"] for s in students)
        }
    }


@router.get("/admin/students/{student_id}")
def get_student_admin_details(
    student_id: int,
    current_user = Depends(get_current_admin)
) -> Any:
    """Get detailed student information (admin only)"""
    
    # Generate comprehensive student data
    student = {
        "id": student_id,
        "name": f"Student {student_id}",
        "email": f"student{student_id}@example.com",
        "phone": f"05{random.randint(10000000, 99999999)}",
        "status": "ACTIVE",
        "joined_at": "2024-01-01T00:00:00Z",
        "last_active": datetime.now().isoformat(),
        "profile": {
            "date_of_birth": "1995-01-01",
            "country": "Saudi Arabia",
            "city": "Riyadh",
            "education_level": "Bachelor's Degree"
        },
        "enrollments": [generate_mock_enrollment(i, student_id) for i in range(1, 6)],
        "certificates": [generate_mock_certificate(i, student_id) for i in range(1, 3)],
        "activity_log": [
            {
                "action": "login",
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "ip_address": "192.168.1.100"
            },
            {
                "action": "lesson_completed",
                "details": "Python Basics - Variables",
                "timestamp": (datetime.now() - timedelta(hours=3)).isoformat()
            }
        ]
    }
    
    return student 