from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import random

from app.deps import get_db, get_current_student, get_optional_current_user

router = APIRouter()


def generate_mock_course_public(course_id: int):
    """Generate mock course data for public viewing"""
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
        "academy": {
            "id": (course_id % 3) + 1,
            "name": f"Tech Academy {(course_id % 3) + 1}",
            "slug": f"tech-academy-{(course_id % 3) + 1}",
            "logo": f"https://example.com/academy-{(course_id % 3) + 1}-logo.jpg",
            "verified": True,
            "rating": round(random.uniform(4.0, 5.0), 1)
        },
        "title": course_titles[(course_id - 1) % len(course_titles)],
        "slug": f"course-{course_id}-{course_titles[(course_id - 1) % len(course_titles)].lower().replace(' ', '-')}",
        "description": f"Comprehensive course covering all aspects of {course_titles[(course_id - 1) % len(course_titles)]}",
        "short_description": f"Learn {course_titles[(course_id - 1) % len(course_titles)]} from scratch to advanced level",
        "thumbnail": f"https://example.com/course-{course_id}.jpg",
        "preview_video": f"https://example.com/preview-{course_id}.mp4",
        "price": round(random.uniform(99.99, 499.99), 2),
        "discount_price": round(random.uniform(49.99, 299.99), 2) if course_id % 3 == 0 else None,
        "final_price": round(random.uniform(49.99, 299.99), 2) if course_id % 3 == 0 else round(random.uniform(99.99, 499.99), 2),
        "duration": random.randint(10, 50),  # hours
        "lessons_count": random.randint(20, 100),
        "level": random.choice(["BEGINNER", "INTERMEDIATE", "ADVANCED"]),
        "language": "Arabic",
        "certificate_enabled": True,
        "is_featured": course_id <= 5,
        "is_free": course_id % 10 == 0,
        "views_count": random.randint(100, 5000),
        "enrollment_count": random.randint(50, 500),
        "rating": round(random.uniform(4.0, 5.0), 1),
        "reviews_count": random.randint(10, 200),
        "created_at": datetime.now().isoformat(),
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
        ],
        "tags": ["programming", "technology", "online", "certification"]
    }


def generate_course_curriculum(course_id: int):
    """Generate course curriculum structure"""
    chapters = []
    
    for chapter_num in range(1, 6):  # 5 chapters
        chapter = {
            "id": chapter_num,
            "title": f"Chapter {chapter_num}: Core Concepts",
            "description": f"Essential concepts for chapter {chapter_num}",
            "order": chapter_num,
            "duration": random.randint(2, 6),  # hours
            "lessons_count": random.randint(4, 8),
            "is_free": chapter_num == 1,  # First chapter free
            "lessons": []
        }
        
        # Add lessons to chapter
        for lesson_num in range(1, chapter["lessons_count"] + 1):
            lesson = {
                "id": (chapter_num - 1) * 10 + lesson_num,
                "title": f"Lesson {lesson_num}: Important Topic",
                "description": f"Learn about important topic {lesson_num}",
                "duration": random.randint(15, 45),  # minutes
                "order": lesson_num,
                "is_free": chapter_num == 1 and lesson_num <= 2,  # First 2 lessons of first chapter free
                "content_type": "video",
                "has_video": True,
                "has_resources": random.choice([True, False]),
                "has_quiz": lesson_num % 3 == 0,
                "completed": False  # Will be updated based on user progress
            }
            chapter["lessons"].append(lesson)
        
        chapters.append(chapter)
    
    return chapters


def generate_course_reviews(course_id: int, limit: int = 5):
    """Generate course reviews"""
    reviews = []
    
    for i in range(1, limit + 1):
        review = {
            "id": i,
            "student": {
                "name": f"Student {i}",
                "avatar": f"https://example.com/avatar-{i}.jpg"
            },
            "rating": random.randint(4, 5),
            "comment": f"Great course! Really helped me understand the concepts. Review number {i}.",
            "helpful_count": random.randint(5, 50),
            "created_at": datetime.now().isoformat()
        }
        reviews.append(review)
    
    return reviews


# Public Courses Routes
@router.get("/")
def get_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(12, ge=1, le=50),
    search: Optional[str] = None,
    category: Optional[str] = None,
    level: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    is_free: Optional[bool] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|price|rating|popularity|title)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Get list of all courses (public endpoint)"""
    courses = [generate_mock_course_public(i) for i in range(1, 51)]
    
    # Apply filters
    if search:
        courses = [c for c in courses if search.lower() in c["title"].lower() or search.lower() in c["description"].lower()]
    
    if category:
        # Mock category filtering
        courses = [c for c in courses if category.lower() in " ".join(c["tags"]).lower()]
    
    if level:
        courses = [c for c in courses if c["level"] == level.upper()]
    
    if price_min is not None:
        courses = [c for c in courses if c["final_price"] >= price_min]
    
    if price_max is not None:
        courses = [c for c in courses if c["final_price"] <= price_max]
    
    if is_free is not None:
        courses = [c for c in courses if c["is_free"] == is_free]
    
    # Sort courses
    reverse = order == "desc"
    if sort_by == "popularity":
        courses.sort(key=lambda x: x["enrollment_count"], reverse=reverse)
    elif sort_by == "rating":
        courses.sort(key=lambda x: x["rating"], reverse=reverse)
    elif sort_by == "price":
        courses.sort(key=lambda x: x["final_price"], reverse=reverse)
    else:
        courses.sort(key=lambda x: x[sort_by], reverse=reverse)
    
    # Add enrollment status for authenticated users
    if current_user:
        for course in courses:
            course["is_enrolled"] = course["id"] % 7 == 0  # Mock enrollment check
            course["progress"] = random.randint(0, 100) if course["is_enrolled"] else 0
    
    return {
        "data": courses[skip:skip + limit],
        "total": len(courses),
        "skip": skip,
        "limit": limit,
        "filters": {
            "categories": ["Programming", "Design", "Marketing", "Business", "Technology"],
            "levels": ["BEGINNER", "INTERMEDIATE", "ADVANCED"],
            "price_range": {"min": 0, "max": 500}
        }
    }


@router.get("/featured")
def get_featured_courses(
    limit: int = Query(8, ge=1, le=20),
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Get featured courses"""
    courses = [generate_mock_course_public(i) for i in range(1, 21) if i <= 8]
    
    # Add enrollment status for authenticated users
    if current_user:
        for course in courses:
            course["is_enrolled"] = course["id"] % 7 == 0
            course["progress"] = random.randint(0, 100) if course["is_enrolled"] else 0
    
    return {
        "data": courses[:limit],
        "total": len(courses)
    }


@router.get("/free")
def get_free_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(12, ge=1, le=50),
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Get free courses"""
    courses = [generate_mock_course_public(i) for i in range(1, 51) if i % 10 == 0]
    
    if current_user:
        for course in courses:
            course["is_enrolled"] = course["id"] % 7 == 0
            course["progress"] = random.randint(0, 100) if course["is_enrolled"] else 0
    
    return {
        "data": courses[skip:skip + limit],
        "total": len(courses),
        "skip": skip,
        "limit": limit
    }


@router.get("/{course_id}")
def get_course_details(
    course_id: int,
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Get detailed course information"""
    course = generate_mock_course_public(course_id)
    
    # Add curriculum
    course["curriculum"] = generate_course_curriculum(course_id)
    
    # Add instructor info
    course["instructor"] = {
        "id": 1,
        "name": "Ahmed Mohammed",
        "title": "Senior Software Engineer",
        "bio": "Experienced developer with 10+ years in the industry",
        "avatar": "https://example.com/instructor-1.jpg",
        "rating": 4.8,
        "students_count": 15000,
        "courses_count": 12,
        "social_links": {
            "linkedin": "https://linkedin.com/in/ahmed",
            "twitter": "https://twitter.com/ahmed"
        }
    }
    
    # Add recent reviews
    course["recent_reviews"] = generate_course_reviews(course_id, 5)
    
    # Add related courses
    related_ids = [i for i in range(course_id + 1, course_id + 5) if i <= 50]
    course["related_courses"] = [generate_mock_course_public(i) for i in related_ids[:4]]
    
    # Add FAQ
    course["faq"] = [
        {
            "question": "How long do I have access to the course?",
            "answer": "You have lifetime access to the course materials."
        },
        {
            "question": "Is there a certificate of completion?",
            "answer": "Yes, you will receive a certificate upon course completion."
        },
        {
            "question": "What if I'm not satisfied with the course?",
            "answer": "We offer a 30-day money-back guarantee."
        }
    ]
    
    # Add user-specific data if authenticated
    if current_user:
        course["is_enrolled"] = course_id % 7 == 0
        course["progress"] = random.randint(0, 100) if course["is_enrolled"] else 0
        course["is_favorite"] = course_id % 5 == 0
        course["last_lesson"] = {
            "chapter_id": 1,
            "lesson_id": 3,
            "title": "Variables and Data Types"
        } if course["is_enrolled"] else None
    
    return course


@router.post("/{course_id}/enroll")
def enroll_in_course(
    course_id: int,
    current_user = Depends(get_current_student)
) -> Any:
    """Enroll student in course"""
    course = generate_mock_course_public(course_id)
    
    # Check if already enrolled
    if course_id % 7 == 0:  # Mock check
        raise HTTPException(
            status_code=400,
            detail="You are already enrolled in this course"
        )
    
    # Check if course is free
    if not course["is_free"]:
        raise HTTPException(
            status_code=400,
            detail="This course requires payment. Please use the payment endpoint."
        )
    
    # Create enrollment
    enrollment = {
        "id": f"ENR_{current_user.id}_{course_id}",
        "student_id": current_user.id,
        "course_id": course_id,
        "academy_id": course["academy"]["id"],
        "enrolled_at": datetime.now().isoformat(),
        "progress": 0,
        "is_active": True
    }
    
    return {
        "message": "Successfully enrolled in course",
        "enrollment": enrollment,
        "course": {
            "id": course_id,
            "title": course["title"],
            "thumbnail": course["thumbnail"]
        }
    }


@router.post("/{course_id}/favorite")
def toggle_course_favorite(
    course_id: int,
    current_user = Depends(get_current_student)
) -> Any:
    """Add/remove course from favorites"""
    is_favorite = course_id % 5 == 0  # Mock check
    
    return {
        "course_id": course_id,
        "is_favorite": not is_favorite,
        "message": "Removed from favorites" if is_favorite else "Added to favorites"
    }


@router.get("/{course_id}/reviews")
def get_course_reviews(
    course_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    rating_filter: Optional[int] = Query(None, ge=1, le=5)
) -> Any:
    """Get course reviews with pagination"""
    all_reviews = generate_course_reviews(course_id, 25)
    
    # Filter by rating if provided
    if rating_filter:
        all_reviews = [r for r in all_reviews if r["rating"] == rating_filter]
    
    return {
        "data": all_reviews[skip:skip + limit],
        "total": len(all_reviews),
        "skip": skip,
        "limit": limit,
        "rating_distribution": {
            5: random.randint(10, 50),
            4: random.randint(5, 20),
            3: random.randint(1, 10),
            2: random.randint(0, 5),
            1: random.randint(0, 2)
        }
    }


@router.post("/{course_id}/review")
def add_course_review(
    course_id: int,
    review_data: dict,
    current_user = Depends(get_current_student)
) -> Any:
    """Add review for course (only if enrolled)"""
    # Check if enrolled
    if course_id % 7 != 0:  # Mock check
        raise HTTPException(
            status_code=403,
            detail="You must be enrolled in the course to leave a review"
        )
    
    # Check if already reviewed
    if course_id % 3 == 0:  # Mock check
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this course"
        )
    
    review = {
        "id": random.randint(100, 999),
        "course_id": course_id,
        "student_id": current_user.id,
        "rating": review_data.get("rating"),
        "comment": review_data.get("comment", ""),
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Review added successfully",
        "review": review
    }


@router.get("/search/suggestions")
def get_search_suggestions(
    query: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20)
) -> Any:
    """Get search suggestions for courses"""
    suggestions = [
        "Python Programming",
        "Web Development", 
        "Data Science",
        "Machine Learning",
        "JavaScript",
        "React",
        "Node.js",
        "Database Design",
        "API Development",
        "Mobile Development"
    ]
    
    # Filter suggestions based on query
    filtered = [s for s in suggestions if query.lower() in s.lower()]
    
    return {
        "suggestions": filtered[:limit],
        "query": query
    }