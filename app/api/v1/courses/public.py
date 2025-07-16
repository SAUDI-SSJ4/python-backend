from typing import Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import random

from app.deps.database import get_db
from app.deps.auth import get_current_student, get_optional_current_user

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
        "is_free": course_id % 10 == 0,
        "currency": "USD",
        "level": ["BEGINNER", "INTERMEDIATE", "ADVANCED"][course_id % 3],
        "language": "Arabic",
        "duration": f"{random.randint(10, 50)} hours",
        "lessons_count": random.randint(20, 100),
        "students_count": random.randint(100, 5000),
        "rating": round(random.uniform(4.0, 5.0), 1),
        "reviews_count": random.randint(50, 1000),
        "created_at": datetime.now() - timedelta(days=random.randint(1, 365)),
        "updated_at": datetime.now() - timedelta(days=random.randint(1, 30)),
        "tags": ["programming", "web", "technology", "education"],
        "instructor": {
            "id": course_id % 5 + 1,
            "name": f"Dr. Ahmed {course_id % 5 + 1}",
            "avatar": f"https://example.com/instructor-{course_id % 5 + 1}.jpg",
            "title": "Senior Developer",
            "experience": f"{random.randint(5, 15)} years"
        },
        "certificate": True,
        "has_preview": True,
        "enrollment_count": random.randint(100, 5000),
        "last_updated": datetime.now() - timedelta(days=random.randint(1, 30))
    }


@router.get("/public/courses")
def get_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, min_length=2),
    category: Optional[str] = Query(None),
    level: Optional[str] = Query(None, regex="^(beginner|intermediate|advanced)$"),
    price_min: Optional[float] = Query(None, ge=0),
    price_max: Optional[float] = Query(None, ge=0),
    is_free: Optional[bool] = Query(None),
    academy_id: Optional[int] = Query(None),
    sort_by: str = Query("created_at", regex="^(created_at|price|rating|popularity|title)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Get list of all courses (public endpoint)"""
    try:
        courses = [generate_mock_course_public(i) for i in range(1, 51)]
        
        # Apply filters
        if academy_id:
            courses = [c for c in courses if c["academy"]["id"] == academy_id]
        
        if search:
            courses = [c for c in courses if search.lower() in c["title"].lower() or search.lower() in c["description"].lower()]
        
        if category:
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
                course["is_enrolled"] = course["id"] % 7 == 0
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
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving courses: {str(e)}",
            "data": [],
            "total": 0
        }


@router.get("/public/courses/featured")
def get_featured_courses(
    limit: int = Query(8, ge=1, le=20),
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Get featured courses"""
    try:
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
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving featured courses: {str(e)}",
            "data": [],
            "total": 0
        }


@router.get("/public/courses/search/suggestions")
def get_search_suggestions(
    query: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20)
) -> Any:
    """Get search suggestions based on query"""
    suggestions = [
        "Python Programming", "Web Development", "Data Science",
        "Machine Learning", "Mobile Development", "UI/UX Design",
        "Digital Marketing", "Business Analysis", "Cybersecurity",
        "Cloud Computing", "Artificial Intelligence", "React Development"
    ]
    
    # Filter suggestions based on query
    filtered_suggestions = [
        s for s in suggestions 
        if query.lower() in s.lower()
    ]
    
    return {
        "data": filtered_suggestions[:limit],
        "total": len(filtered_suggestions)
    } 