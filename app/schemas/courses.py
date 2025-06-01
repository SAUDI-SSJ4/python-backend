from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Review schemas
class ReviewCreate(BaseModel):
    course_id: int
    rating: int = Field(..., ge=1, le=5)
    title: str = Field(..., min_length=5, max_length=100)
    comment: str = Field(..., min_length=10, max_length=1000)


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, min_length=5, max_length=100)
    comment: Optional[str] = Field(None, min_length=10, max_length=1000)


class ReviewResponse(BaseModel):
    id: int
    comment: str
    created_at: str
    updated_at: Optional[str] = None


class CourseReview(BaseModel):
    id: int
    course_id: int
    student: dict
    rating: int
    title: str
    comment: str
    created_at: str
    updated_at: Optional[str] = None
    helpful_count: int = 0
    is_verified_purchase: bool = False
    instructor_response: Optional[ReviewResponse] = None


class ReviewStatistics(BaseModel):
    course_id: int
    total_reviews: int
    average_rating: float
    rating_breakdown: dict
    rating_percentages: dict
    verified_purchase_reviews: int
    reviews_with_comments: int
    instructor_responses: int
    recent_rating_trend: str 