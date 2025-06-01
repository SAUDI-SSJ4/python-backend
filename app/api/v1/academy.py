from typing import Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import random

from app.deps import get_db, get_current_academy_user, get_current_admin
from app.schemas.auth import AcademyRegister, AcademyLogin, Token

router = APIRouter()


# Mock data generators
def generate_mock_academy(academy_id: int):
    """Generate mock academy data"""
    return {
        "id": academy_id,
        "name": f"Tech Academy {academy_id}",
        "slug": f"tech-academy-{academy_id}",
        "user_name": f"academy{academy_id}",
        "email": f"academy{academy_id}@example.com",
        "phone": f"05{random.randint(10000000, 99999999)}",
        "address": f"123 Education St, Riyadh {academy_id}0000",
        "country": "Saudi Arabia",
        "city": "Riyadh",
        "description": f"Leading technology academy offering cutting-edge courses in programming and digital skills.",
        "logo": f"https://example.com/academy-{academy_id}-logo.jpg",
        "cover": f"https://example.com/academy-{academy_id}-cover.jpg",
        "status": "ACTIVE",
        "verified": True,
        "featured": academy_id <= 3,
        "created_at": datetime.now().isoformat(),
        "stats": {
            "total_courses": random.randint(10, 50),
            "total_students": random.randint(100, 1000),
            "total_revenue": round(random.uniform(10000, 100000), 2),
            "rating": round(random.uniform(4.0, 5.0), 1)
        }
    }


def generate_mock_course(course_id: int, academy_id: int):
    """Generate mock course data"""
    course_titles = [
        "Python Programming Masterclass",
        "Web Development with React",
        "Data Science & Machine Learning",
        "Mobile App Development",
        "Digital Marketing Strategy",
        "UI/UX Design Fundamentals",
        "Cybersecurity Essentials",
        "Cloud Computing with AWS"
    ]
    
    return {
        "id": course_id,
        "academy_id": academy_id,
        "title": course_titles[(course_id - 1) % len(course_titles)],
        "slug": f"course-{course_id}-{course_titles[(course_id - 1) % len(course_titles)].lower().replace(' ', '-')}",
        "description": f"Comprehensive course covering all aspects of {course_titles[(course_id - 1) % len(course_titles)]}",
        "short_description": f"Learn {course_titles[(course_id - 1) % len(course_titles)]} from scratch to advanced level",
        "thumbnail": f"https://example.com/course-{course_id}.jpg",
        "preview_video": f"https://example.com/preview-{course_id}.mp4",
        "price": round(random.uniform(99.99, 499.99), 2),
        "discount_price": round(random.uniform(49.99, 299.99), 2) if course_id % 3 == 0 else None,
        "duration": random.randint(10, 50),  # hours
        "level": random.choice(["BEGINNER", "INTERMEDIATE", "ADVANCED"]),
        "language": "Arabic",
        "status": "PUBLISHED",
        "is_featured": course_id <= 5,
        "is_free": course_id % 10 == 0,
        "certificate_enabled": True,
        "views_count": random.randint(100, 5000),
        "enrollment_count": random.randint(50, 500),
        "rating": round(random.uniform(4.0, 5.0), 1),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "requirements": [
            "Basic computer skills",
            "Internet connection",
            "Willingness to learn"
        ],
        "what_will_learn": [
            "Master the fundamentals",
            "Build real-world projects",
            "Industry best practices",
            "Hands-on experience"
        ]
    }


def generate_mock_chapter(chapter_id: int, course_id: int):
    """Generate mock chapter data"""
    chapter_titles = [
        "Introduction & Setup",
        "Core Concepts",
        "Intermediate Topics",
        "Advanced Techniques",
        "Real-world Projects",
        "Best Practices",
        "Testing & Debugging",
        "Deployment & Production"
    ]
    
    return {
        "id": chapter_id,
        "course_id": course_id,
        "title": chapter_titles[(chapter_id - 1) % len(chapter_titles)],
        "description": f"Chapter covering {chapter_titles[(chapter_id - 1) % len(chapter_titles)].lower()}",
        "order": chapter_id,
        "is_free": chapter_id == 1,  # First chapter is usually free
        "lessons_count": random.randint(3, 8),
        "duration": random.randint(2, 6),  # hours
        "created_at": datetime.now().isoformat()
    }


def generate_mock_lesson(lesson_id: int, chapter_id: int):
    """Generate mock lesson data"""
    lesson_types = [
        "Introduction to",
        "Understanding",
        "Working with",
        "Advanced",
        "Practical",
        "Building",
        "Implementing",
        "Mastering"
    ]
    
    topics = [
        "Variables and Data Types",
        "Functions and Methods",
        "Object-Oriented Programming",
        "Database Integration",
        "API Development",
        "Error Handling",
        "Performance Optimization",
        "Security Implementation"
    ]
    
    lesson_type = lesson_types[(lesson_id - 1) % len(lesson_types)]
    topic = topics[(lesson_id - 1) % len(topics)]
    
    return {
        "id": lesson_id,
        "chapter_id": chapter_id,
        "title": f"{lesson_type} {topic}",
        "description": f"Learn about {topic.lower()} in detail",
        "order": (lesson_id - 1) % 8 + 1,
        "duration": random.randint(15, 45),  # minutes
        "is_free": lesson_id % 10 == 1,
        "is_published": True,
        "content_type": "video",
        "has_video": True,
        "has_exam": lesson_id % 3 == 0,
        "has_interactive_tools": lesson_id % 4 == 0,
        "created_at": datetime.now().isoformat()
    }


def generate_mock_video(video_id: int, lesson_id: int):
    """Generate mock video data"""
    return {
        "id": video_id,
        "lesson_id": lesson_id,
        "url": f"https://example.com/videos/lesson-{lesson_id}.mp4",
        "duration": random.randint(900, 2700),  # 15-45 minutes in seconds
        "size": random.randint(100000000, 500000000),  # bytes
        "format": "mp4",
        "resolution": "1080p",
        "provider": "self_hosted",
        "thumbnail": f"https://example.com/thumbnails/lesson-{lesson_id}.jpg",
        "subtitles_url": f"https://example.com/subtitles/lesson-{lesson_id}.vtt",
        "is_downloadable": True,
        "created_at": datetime.now().isoformat()
    }


def generate_mock_exam(exam_id: int, lesson_id: int):
    """Generate mock exam data"""
    return {
        "id": exam_id,
        "lesson_id": lesson_id,
        "title": f"Lesson {lesson_id} Assessment",
        "description": "Test your understanding of the lesson concepts",
        "pass_score": 70,
        "max_attempts": 3,
        "time_limit": 30,  # minutes
        "is_active": True,
        "questions_count": random.randint(5, 15),
        "created_at": datetime.now().isoformat()
    }


def generate_mock_question(question_id: int, exam_id: int):
    """Generate mock question data"""
    question_types = ["multiple_choice", "true_false", "fill_blank"]
    
    return {
        "id": question_id,
        "exam_id": exam_id,
        "text": f"What is the correct approach for question {question_id}?",
        "type": random.choice(question_types),
        "order": question_id,
        "points": random.randint(1, 5),
        "explanation": f"Explanation for question {question_id}",
        "options": [
            {"id": i, "text": f"Option {i}", "is_correct": i == 1}
            for i in range(1, 5)
        ] if random.choice(question_types) == "multiple_choice" else [],
        "created_at": datetime.now().isoformat()
    }


def generate_mock_interactive_tool(tool_id: int, lesson_id: int):
    """Generate mock interactive tool data"""
    tool_types = ["code_editor", "quiz", "simulator", "worksheet", "sandbox"]
    tool_names = [
        "Code Practice",
        "Interactive Quiz",
        "Live Simulator",
        "Practice Worksheet",
        "Development Sandbox"
    ]
    
    return {
        "id": tool_id,
        "lesson_id": lesson_id,
        "type": random.choice(tool_types),
        "title": random.choice(tool_names),
        "url": f"https://interactive.example.com/tool-{tool_id}",
        "order": tool_id,
        "created_at": datetime.now().isoformat()
    }


# Academy Authentication
@router.post("/register", response_model=Token)
def register_academy(academy_data: AcademyRegister) -> Any:
    """Register new academy with mock response"""
    return {
        "access_token": "mock_academy_access_token_" + academy_data.user_name,
        "refresh_token": "mock_academy_refresh_token_" + academy_data.user_name,
        "token_type": "bearer"
    }


@router.post("/login", response_model=Token)
def login_academy(login_data: AcademyLogin) -> Any:
    """Academy login with mock response"""
    return {
        "access_token": "mock_academy_access_token",
        "refresh_token": "mock_academy_refresh_token",
        "token_type": "bearer"
    }


# Academy Management Routes
@router.get("/")
def get_academies(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    featured: Optional[bool] = None
) -> Any:
    """Get list of academies"""
    academies = [generate_mock_academy(i) for i in range(1, 21)]
    
    # Apply filters
    if search:
        academies = [a for a in academies if search.lower() in a["name"].lower()]
    if status:
        academies = [a for a in academies if a["status"] == status.upper()]
    if featured is not None:
        academies = [a for a in academies if a["featured"] == featured]
    
    return {
        "data": academies[skip:skip + limit],
        "total": len(academies),
        "skip": skip,
        "limit": limit
    }


@router.get("/{academy_id}")
def get_academy(academy_id: int) -> Any:
    """Get academy details"""
    academy = generate_mock_academy(academy_id)
    
    # Add detailed statistics
    academy["detailed_stats"] = {
        "courses_by_category": {
            "Programming": random.randint(5, 15),
            "Design": random.randint(3, 10),
            "Marketing": random.randint(2, 8),
            "Business": random.randint(1, 5)
        },
        "monthly_revenue": [
            {
                "month": f"2024-{i:02d}",
                "revenue": round(random.uniform(5000, 20000), 2)
            }
            for i in range(1, 13)
        ],
        "student_enrollments": [
            {
                "month": f"2024-{i:02d}",
                "enrollments": random.randint(20, 100)
            }
            for i in range(1, 13)
        ]
    }
    
    return academy


# Academy Courses Management
@router.get("/{academy_id}/courses")
def get_academy_courses(
    academy_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    category: Optional[str] = None,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Get courses for specific academy"""
    courses = [generate_mock_course(i, academy_id) for i in range(1, 21)]
    
    # Apply filters
    if status:
        courses = [c for c in courses if c["status"] == status.upper()]
    
    return {
        "data": courses[skip:skip + limit],
        "total": len(courses),
        "academy_id": academy_id,
        "skip": skip,
        "limit": limit
    }


@router.post("/{academy_id}/courses")
def create_course(
    academy_id: int,
    course_data: dict,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Create new course for academy"""
    course = {
        "id": random.randint(100, 999),
        "academy_id": academy_id,
        "title": course_data.get("title"),
        "slug": course_data.get("title", "").lower().replace(" ", "-"),
        "description": course_data.get("description"),
        "price": course_data.get("price", 0),
        "level": course_data.get("level", "BEGINNER"),
        "status": "DRAFT",
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Course created successfully",
        "course": course
    }


@router.get("/{academy_id}/courses/{course_id}")
def get_course_details(
    academy_id: int,
    course_id: int,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Get detailed course information with chapters and lessons"""
    course = generate_mock_course(course_id, academy_id)
    
    # Add chapters with lessons
    chapters = []
    for chapter_num in range(1, 6):  # 5 chapters per course
        chapter = generate_mock_chapter(chapter_num, course_id)
        
        # Add lessons to chapter
        lessons = []
        for lesson_num in range(1, 6):  # 5 lessons per chapter
            lesson_id = (chapter_num - 1) * 5 + lesson_num
            lesson = generate_mock_lesson(lesson_id, chapter_num)
            
            # Add video if lesson has video
            if lesson["has_video"]:
                lesson["video"] = generate_mock_video(lesson_id, lesson_id)
            
            # Add exam if lesson has exam
            if lesson["has_exam"]:
                exam = generate_mock_exam(lesson_id, lesson_id)
                # Add questions to exam
                exam["questions"] = [
                    generate_mock_question(q_id, lesson_id)
                    for q_id in range(1, 6)
                ]
                lesson["exam"] = exam
            
            # Add interactive tools if lesson has them
            if lesson["has_interactive_tools"]:
                lesson["interactive_tools"] = [
                    generate_mock_interactive_tool(t_id, lesson_id)
                    for t_id in range(1, 3)
                ]
            
            lessons.append(lesson)
        
        chapter["lessons"] = lessons
        chapters.append(chapter)
    
    course["chapters"] = chapters
    
    # Add course statistics
    course["statistics"] = {
        "total_chapters": len(chapters),
        "total_lessons": sum(len(c["lessons"]) for c in chapters),
        "total_videos": sum(
            len([l for l in c["lessons"] if l["has_video"]])
            for c in chapters
        ),
        "total_exams": sum(
            len([l for l in c["lessons"] if l["has_exam"]])
            for c in chapters
        ),
        "total_interactive_tools": sum(
            len([l for l in c["lessons"] if l["has_interactive_tools"]])
            for c in chapters
        ),
        "total_duration": sum(c["duration"] for c in chapters)
    }
    
    return course


@router.put("/{academy_id}/courses/{course_id}")
def update_course(
    academy_id: int,
    course_id: int,
    course_data: dict,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Update course information"""
    updated_course = generate_mock_course(course_id, academy_id)
    updated_course.update(course_data)
    updated_course["updated_at"] = datetime.now().isoformat()
    
    return {
        "message": "Course updated successfully",
        "course": updated_course
    }


@router.delete("/{academy_id}/courses/{course_id}")
def delete_course(
    academy_id: int,
    course_id: int,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Delete course"""
    return {"message": "Course deleted successfully"}


@router.post("/{academy_id}/courses/{course_id}/publish")
def publish_course(
    academy_id: int,
    course_id: int,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Publish course"""
    return {
        "message": "Course published successfully",
        "published_at": datetime.now().isoformat()
    }


# Chapter Management
@router.post("/{academy_id}/courses/{course_id}/chapters")
def create_chapter(
    academy_id: int,
    course_id: int,
    chapter_data: dict,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Create new chapter for course"""
    chapter = {
        "id": random.randint(100, 999),
        "course_id": course_id,
        "title": chapter_data.get("title"),
        "description": chapter_data.get("description"),
        "order": chapter_data.get("order", 1),
        "is_free": chapter_data.get("is_free", False),
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Chapter created successfully",
        "chapter": chapter
    }


@router.get("/{academy_id}/courses/{course_id}/chapters/{chapter_id}")
def get_chapter_details(
    academy_id: int,
    course_id: int,
    chapter_id: int,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Get chapter details with lessons"""
    chapter = generate_mock_chapter(chapter_id, course_id)
    
    # Add lessons with full details
    lessons = []
    for lesson_num in range(1, 6):
        lesson = generate_mock_lesson(lesson_num, chapter_id)
        
        if lesson["has_video"]:
            lesson["video"] = generate_mock_video(lesson_num, lesson_num)
        if lesson["has_exam"]:
            exam = generate_mock_exam(lesson_num, lesson_num)
            exam["questions"] = [
                generate_mock_question(q_id, lesson_num)
                for q_id in range(1, 6)
            ]
            lesson["exam"] = exam
        if lesson["has_interactive_tools"]:
            lesson["interactive_tools"] = [
                generate_mock_interactive_tool(t_id, lesson_num)
                for t_id in range(1, 3)
            ]
        
        lessons.append(lesson)
    
    chapter["lessons"] = lessons
    return chapter


# Lesson Management
@router.post("/{academy_id}/courses/{course_id}/chapters/{chapter_id}/lessons")
def create_lesson(
    academy_id: int,
    course_id: int,
    chapter_id: int,
    lesson_data: dict,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Create new lesson for chapter"""
    lesson = {
        "id": random.randint(100, 999),
        "chapter_id": chapter_id,
        "title": lesson_data.get("title"),
        "description": lesson_data.get("description"),
        "order": lesson_data.get("order", 1),
        "duration": lesson_data.get("duration", 30),
        "is_free": lesson_data.get("is_free", False),
        "content_type": lesson_data.get("content_type", "video"),
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Lesson created successfully",
        "lesson": lesson
    }


@router.get("/{academy_id}/courses/{course_id}/chapters/{chapter_id}/lessons/{lesson_id}")
def get_lesson_details(
    academy_id: int,
    course_id: int,
    chapter_id: int,
    lesson_id: int,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Get complete lesson details"""
    lesson = generate_mock_lesson(lesson_id, chapter_id)
    
    # Add all related content
    if lesson["has_video"]:
        lesson["video"] = generate_mock_video(lesson_id, lesson_id)
    
    if lesson["has_exam"]:
        exam = generate_mock_exam(lesson_id, lesson_id)
        exam["questions"] = [
            generate_mock_question(q_id, lesson_id)
            for q_id in range(1, random.randint(5, 10))
        ]
        lesson["exam"] = exam
    
    if lesson["has_interactive_tools"]:
        lesson["interactive_tools"] = [
            generate_mock_interactive_tool(t_id, lesson_id)
            for t_id in range(1, random.randint(2, 4))
        ]
    
    return lesson


# Video Management
@router.post("/{academy_id}/courses/{course_id}/chapters/{chapter_id}/lessons/{lesson_id}/video")
def add_lesson_video(
    academy_id: int,
    course_id: int,
    chapter_id: int,
    lesson_id: int,
    video_data: dict,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Add video to lesson"""
    video = {
        "id": random.randint(100, 999),
        "lesson_id": lesson_id,
        "url": video_data.get("url"),
        "duration": video_data.get("duration"),
        "format": video_data.get("format", "mp4"),
        "resolution": video_data.get("resolution", "1080p"),
        "is_downloadable": video_data.get("is_downloadable", True),
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Video added successfully",
        "video": video
    }


# Exam Management
@router.post("/{academy_id}/courses/{course_id}/chapters/{chapter_id}/lessons/{lesson_id}/exam")
def create_lesson_exam(
    academy_id: int,
    course_id: int,
    chapter_id: int,
    lesson_id: int,
    exam_data: dict,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Create exam for lesson"""
    exam = {
        "id": random.randint(100, 999),
        "lesson_id": lesson_id,
        "title": exam_data.get("title"),
        "description": exam_data.get("description"),
        "pass_score": exam_data.get("pass_score", 70),
        "max_attempts": exam_data.get("max_attempts", 3),
        "time_limit": exam_data.get("time_limit", 30),
        "is_active": True,
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Exam created successfully",
        "exam": exam
    }


# Interactive Tools Management
@router.post("/{academy_id}/courses/{course_id}/chapters/{chapter_id}/lessons/{lesson_id}/tools")
def add_interactive_tool(
    academy_id: int,
    course_id: int,
    chapter_id: int,
    lesson_id: int,
    tool_data: dict,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Add interactive tool to lesson"""
    tool = {
        "id": random.randint(100, 999),
        "lesson_id": lesson_id,
        "type": tool_data.get("type"),
        "title": tool_data.get("title"),
        "url": tool_data.get("url"),
        "order": tool_data.get("order", 1),
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Interactive tool added successfully",
        "tool": tool
    } 