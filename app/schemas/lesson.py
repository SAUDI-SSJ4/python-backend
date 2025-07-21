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


# ========================================
# TRANSCRIPTION SCHEMAS
# ========================================

class TranscriptionErrorDetails(BaseModel):
    """Schema for transcription error details"""
    processing_time_seconds: int = Field(0, description="Processing time in seconds")
    file_size_bytes: int = Field(0, description="File size in bytes")
    duration_seconds: int = Field(0, description="Video duration in seconds")
    confidence_score: float = Field(0.0, description="Confidence score")
    has_transcription_text: bool = Field(False, description="Whether transcription text exists")
    transcription_text_length: int = Field(0, description="Length of transcription text")
    has_segments: bool = Field(False, description="Whether segments exist")
    segments_count: int = Field(0, description="Number of segments")
    has_subtitles: bool = Field(False, description="Whether subtitles exist")
    subtitles_length: int = Field(0, description="Length of subtitles")


class TranscriptionSystemInfo(BaseModel):
    """Schema for transcription system information"""
    openai_api_key_configured: bool = Field(False, description="Whether OpenAI API key is configured")
    openai_api_key_length: int = Field(0, description="Length of OpenAI API key")
    ai_transcription_enabled: bool = Field(True, description="Whether AI transcription is enabled")
    video_processing_service_available: bool = Field(False, description="Whether video processing service is available")


class TranscriptionLessonInfo(BaseModel):
    """Schema for transcription lesson information"""
    lesson_id: str = Field(..., description="Lesson ID")
    lesson_title: str = Field(..., description="Lesson title")
    lesson_type: str = Field(..., description="Lesson type")
    has_video: bool = Field(False, description="Whether lesson has video")
    video_path: Optional[str] = Field(None, description="Video file path")
    video_size_bytes: int = Field(0, description="Video file size in bytes")
    video_duration: int = Field(0, description="Video duration in seconds")


class TranscriptionCourseInfo(BaseModel):
    """Schema for transcription course information"""
    course_id: str = Field(..., description="Course ID")
    course_title: str = Field(..., description="Course title")
    academy_id: int = Field(..., description="Academy ID")


class TranscriptionStatusResponse(BaseModel):
    """Schema for transcription status response"""
    transcription_id: str = Field(..., description="Transcription ID")
    status: str = Field(..., description="Processing status")
    has_transcription: bool = Field(False, description="Whether transcription is completed")
    language: str = Field("ar", description="Language code")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    
    # Completed transcription fields
    transcription_text: Optional[str] = Field(None, description="Transcription text")
    confidence_score: Optional[float] = Field(None, description="Confidence score")
    duration_seconds: Optional[int] = Field(None, description="Video duration")
    segments_count: Optional[int] = Field(None, description="Number of segments")
    has_subtitles: Optional[bool] = Field(None, description="Whether subtitles exist")
    
    # Processing status fields
    message: Optional[str] = Field(None, description="Status message")
    estimated_completion: Optional[str] = Field(None, description="Estimated completion time")
    
    # Failed transcription fields
    error: Optional[str] = Field(None, description="Error message")
    error_details: Optional[TranscriptionErrorDetails] = Field(None, description="Detailed error information")
    system_info: Optional[TranscriptionSystemInfo] = Field(None, description="System information")
    lesson_info: Optional[TranscriptionLessonInfo] = Field(None, description="Lesson information")
    course_info: Optional[TranscriptionCourseInfo] = Field(None, description="Course information")
    troubleshooting_suggestions: Optional[List[str]] = Field(None, description="Troubleshooting suggestions")

    class Config:
        schema_extra = {
            "example": {
                "transcription_id": "730a6f67-7d75-4ddb-997a-e491c71a0690",
                "status": "FAILED",
                "has_transcription": False,
                "language": "ar",
                "created_at": "2025-07-18T00:36:30",
                "updated_at": "2025-07-18T00:36:30",
                "message": "فشل في تحويل الفيديو إلى نص",
                "error": "يرجى المحاولة مرة أخرى أو الاتصال بالدعم الفني",
                "error_details": {
                    "processing_time_seconds": 0,
                    "file_size_bytes": 0,
                    "duration_seconds": 0,
                    "confidence_score": 0.0,
                    "has_transcription_text": False,
                    "transcription_text_length": 0,
                    "has_segments": False,
                    "segments_count": 0,
                    "has_subtitles": False,
                    "subtitles_length": 0
                },
                "system_info": {
                    "openai_api_key_configured": True,
                    "openai_api_key_length": 123,
                    "ai_transcription_enabled": True,
                    "video_processing_service_available": True
                },
                "lesson_info": {
                    "lesson_id": "e9acf4aa-0464-4cc7-8a00-199d64edc5d2",
                    "lesson_title": "استخدام المتحكمات",
                    "lesson_type": "video",
                    "has_video": True,
                    "video_path": "lessons/video.mp4",
                    "video_size_bytes": 15925248,
                    "video_duration": 1800
                },
                "course_info": {
                    "course_id": "8ad94e43-e8dd-4065-a276-4bdcbc151243",
                    "course_title": "Laravel Course",
                    "academy_id": 75
                },
                "troubleshooting_suggestions": [
                    "تأكد من أن مفتاح OpenAI API صحيح ومفعل",
                    "تحقق من وجود ملف الفيديو في المسار المحدد",
                    "تأكد من أن حجم الفيديو لا يتجاوز الحد المسموح",
                    "تحقق من صيغة الفيديو (MP4, MOV, AVI, etc.)",
                    "تأكد من أن الفيديو يحتوي على صوت واضح",
                    "جرب إعادة رفع الفيديو مرة أخرى"
                ]
            }
        }


class TranscriptionErrorDetailsResponse(BaseModel):
    """Schema for detailed transcription error response"""
    transcription_id: str = Field(..., description="Transcription ID")
    lesson_id: str = Field(..., description="Lesson ID")
    status: str = Field(..., description="Processing status")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    processing_time_seconds: int = Field(0, description="Processing time in seconds")
    file_size_bytes: int = Field(0, description="File size in bytes")
    duration_seconds: int = Field(0, description="Video duration in seconds")
    language: str = Field("ar", description="Language code")
    error_details: Dict[str, Any] = Field(default_factory=dict, description="Error details")
    system_diagnostics: Dict[str, Any] = Field(default_factory=dict, description="System diagnostics")
    file_diagnostics: Dict[str, Any] = Field(default_factory=dict, description="File diagnostics")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended actions")

    class Config:
        schema_extra = {
            "example": {
                "transcription_id": "730a6f67-7d75-4ddb-997a-e491c71a0690",
                "lesson_id": "e9acf4aa-0464-4cc7-8a00-199d64edc5d2",
                "status": "FAILED",
                "created_at": "2025-07-18T00:36:30",
                "updated_at": "2025-07-18T00:36:30",
                "processing_time_seconds": 0,
                "file_size_bytes": 0,
                "duration_seconds": 0,
                "language": "ar",
                "error_details": {
                    "error_message": "خدمة Whisper غير متاحة",
                    "error_type": "Exception",
                    "video_id": "video-uuid",
                    "lesson_id": "lesson-uuid",
                    "video_file_path": "lessons/video.mp4",
                    "full_video_path": "static/uploads/lessons/video.mp4",
                    "file_exists": True,
                    "openai_api_key_configured": True,
                    "ai_service_available": False,
                    "video_processing_service_available": False
                },
                "system_diagnostics": {
                    "openai_api_key_configured": True,
                    "openai_api_key_length": 123,
                    "ai_transcription_enabled": True,
                    "video_processing_service_available": False,
                    "ai_service_available": False
                },
                "file_diagnostics": {
                    "video_path": "lessons/video.mp4",
                    "full_video_path": "static/uploads/lessons/video.mp4",
                    "file_exists": True,
                    "file_size": 15925248,
                    "video_duration": 1800
                },
                "recommended_actions": [
                    "تحقق من مفتاح OpenAI API في ملف .env",
                    "تأكد من وجود ملف الفيديو في المسار الصحيح",
                    "تحقق من صحة ملف الفيديو وصيغته",
                    "تأكد من أن الفيديو يحتوي على صوت واضح",
                    "جرب إعادة رفع الفيديو",
                    "تحقق من سجلات الخادم للحصول على مزيد من التفاصيل"
                ]
            }
        } 


class TranscriptionModelMessage(BaseModel):
    """رسالة النموذج المبسطة للتحويل"""
    message: str = Field(..., description="رسالة النموذج")
    status: str = Field(..., description="حالة التحويل")
    error: Optional[str] = Field(None, description="رسالة الخطأ إذا فشل التحويل")
    solution: Optional[str] = Field(None, description="الحل المقترح للمشكلة") 