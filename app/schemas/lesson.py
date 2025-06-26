from pydantic import BaseModel, Field, validator, model_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


# Enums for validation
class LessonTypeEnum(str, Enum):
    VIDEO = "video"
    EXAM = "exam"
    TOOL = "tool"
    TEXT = "text"


class VideoTypeEnum(str, Enum):
    UPLOAD = "upload"
    EMBED = "embed"
    YOUTUBE = "youtube"
    VIMEO = "vimeo"


class LessonBase(BaseModel):
    """Base lesson schema with common fields"""
    title: str = Field(..., min_length=3, max_length=255, description="Lesson title")
    description: Optional[str] = Field(None, description="Lesson description")
    type: LessonTypeEnum = Field(LessonTypeEnum.VIDEO, description="Lesson content type")
    order_number: int = Field(0, ge=0, description="Lesson order within chapter")
    status: bool = Field(True, description="Whether lesson is active")
    is_free_preview: bool = Field(False, description="Whether lesson is free preview")


class LessonCreate(LessonBase):
    """Schema for creating a new lesson"""
    chapter_id: int = Field(..., gt=0, description="Chapter ID that this lesson belongs to")
    course_id: str = Field(..., description="Course ID that this lesson belongs to")
    
    # Video-specific fields (optional for non-video lessons)
    video: Optional[str] = Field(None, description="Video file path or URL")
    video_type: Optional[VideoTypeEnum] = Field(VideoTypeEnum.UPLOAD, description="Video source type")
    video_provider: Optional[str] = Field(None, max_length=20, description="Video provider name")
    video_duration: Optional[int] = Field(None, ge=0, description="Video duration in seconds")
    size_bytes: Optional[int] = Field(None, ge=0, description="File size in bytes")

    @model_validator(mode='after')
    def validate_video_lesson_fields(self):
        """Validate required fields for video lessons"""
        if self.type == LessonTypeEnum.VIDEO and not self.video:
            raise ValueError('ملف الفيديو مطلوب للدروس المرئية')
        
        return self

    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "chapter_id": 1,
                "course_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "مقدمة في HTML",
                "description": "تعلم أساسيات لغة HTML",
                "type": "video",
                "order_number": 1,
                "status": True,
                "is_free_preview": False,
                "video": "lessons/video.mp4",
                "video_type": "upload",
                "video_duration": 1800
            }
        }


class LessonUpdate(BaseModel):
    """Schema for updating an existing lesson"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    type: Optional[LessonTypeEnum] = None
    order_number: Optional[int] = Field(None, ge=0)
    status: Optional[bool] = None
    is_free_preview: Optional[bool] = None
    video: Optional[str] = None
    video_type: Optional[VideoTypeEnum] = None
    video_provider: Optional[str] = Field(None, max_length=20)
    video_duration: Optional[int] = Field(None, ge=0)
    size_bytes: Optional[int] = Field(None, ge=0)


class LessonResponse(LessonBase):
    """Schema for lesson response"""
    id: str
    chapter_id: int
    course_id: str
    video: Optional[str] = None
    video_type: Optional[VideoTypeEnum] = None
    video_provider: Optional[str] = None
    video_duration: Optional[int] = None
    size_bytes: Optional[int] = None
    views_count: int
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    is_video_lesson: bool
    is_exam_lesson: bool
    is_tool_lesson: bool
    is_accessible: bool
    duration_formatted: str
    file_size_formatted: str

    class Config:
        """Pydantic configuration for ORM compatibility"""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LessonDetailResponse(LessonResponse):
    """Schema for detailed lesson response with related content"""
    videos: Optional[List[Dict[str, Any]]] = None
    exams: Optional[List[Dict[str, Any]]] = None
    interactive_tools: Optional[List[Dict[str, Any]]] = None
    progress: Optional[Dict[str, Any]] = None  # Student progress if available

    class Config:
        from_attributes = True


class LessonListResponse(BaseModel):
    """Schema for lesson list response"""
    lessons: List[LessonResponse]
    total: int

    class Config:
        from_attributes = True


class LessonProgressUpdate(BaseModel):
    """Schema for updating lesson progress"""
    progress_percentage: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    current_position_seconds: Optional[int] = Field(None, ge=0, description="Current video position in seconds")
    completed: Optional[bool] = Field(None, description="Whether lesson is completed")

    class Config:
        schema_extra = {
            "example": {
                "progress_percentage": 75,
                "current_position_seconds": 1350,
                "completed": False
            }
        }


class LessonProgressResponse(BaseModel):
    """Schema for lesson progress response"""
    id: str
    student_id: int
    lesson_id: str
    course_id: str
    progress_percentage: int
    completed: bool
    current_position_seconds: int
    last_watched_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    is_completed: bool
    is_started: bool
    completion_status: str

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class LessonOrderUpdate(BaseModel):
    """Schema for updating lesson order"""
    lesson_id: str = Field(..., description="Lesson ID")
    new_order: int = Field(..., ge=0, description="New order number")

    class Config:
        schema_extra = {
            "example": {
                "lesson_id": "123e4567-e89b-12d3-a456-426614174000",
                "new_order": 3
            }
        }


class LessonsBulkOrderUpdate(BaseModel):
    """Schema for bulk updating lesson orders"""
    lessons: List[LessonOrderUpdate] = Field(..., description="List of lessons with new orders")

    @validator('lessons')
    def validate_unique_orders(cls, v):
        """Validate that order numbers are unique"""
        orders = [lesson.new_order for lesson in v]
        if len(orders) != len(set(orders)):
            raise ValueError('أرقام الترتيب يجب أن تكون فريدة')
        return v

    class Config:
        schema_extra = {
            "example": {
                "lessons": [
                    {"lesson_id": "123e4567-e89b-12d3-a456-426614174001", "new_order": 1},
                    {"lesson_id": "123e4567-e89b-12d3-a456-426614174002", "new_order": 2},
                    {"lesson_id": "123e4567-e89b-12d3-a456-426614174003", "new_order": 3}
                ]
            }
        }


class LessonFilters(BaseModel):
    """Schema for lesson filtering"""
    chapter_id: Optional[int] = Field(None, description="Filter by chapter")
    type: Optional[LessonTypeEnum] = Field(None, description="Filter by lesson type")
    status: Optional[bool] = Field(None, description="Filter by status")
    is_free_preview: Optional[bool] = Field(None, description="Filter free preview lessons")
    search: Optional[str] = Field(None, min_length=2, max_length=100, description="Search query")

    class Config:
        schema_extra = {
            "example": {
                "chapter_id": 1,
                "type": "video",
                "status": True,
                "search": "HTML"
            }
        } 