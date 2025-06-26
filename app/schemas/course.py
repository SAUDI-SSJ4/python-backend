from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


# Enums for validation
class CourseStatusEnum(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CourseTypeEnum(str, Enum):
    LIVE = "live"
    RECORDED = "recorded"
    ATTEND = "attend"


class CourseLevelEnum(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# Category schemas
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryInDB(CategoryBase):
    id: int
    slug: str
    image: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Course schemas
class CourseBase(BaseModel):
    """Base course schema with common fields"""
    title: str = Field(..., min_length=3, max_length=255, description="Course title")
    content: str = Field(..., min_length=10, description="Course detailed description")
    short_content: str = Field(..., min_length=10, max_length=500, description="Course short description")
    preparations: Optional[str] = Field(None, description="What students need to prepare")
    requirements: Optional[str] = Field(None, description="Prerequisites for the course")
    learning_outcomes: Optional[str] = Field(None, description="What students will learn")
    type: CourseTypeEnum = Field(CourseTypeEnum.RECORDED, description="Course delivery type")
    level: CourseLevelEnum = Field(CourseLevelEnum.BEGINNER, description="Course difficulty level")
    price: Decimal = Field(0.00, ge=0, description="Course price")
    discount_price: Optional[Decimal] = Field(None, ge=0, description="Discounted price")
    discount_ends_at: Optional[datetime] = Field(None, description="Discount expiration date")
    url: Optional[str] = Field(None, description="External URL for live courses")
    featured: bool = Field(False, description="Whether course is featured")

    @validator('discount_price')
    def validate_discount_price(cls, v, values):
        """Validate discount price is less than regular price"""
        if v is not None and 'price' in values:
            if v >= values['price']:
                raise ValueError('سعر الخصم يجب أن يكون أقل من السعر الأصلي')
        return v

    @validator('discount_ends_at')
    def validate_discount_end_date(cls, v):
        """Validate discount end date is in the future"""
        if v is not None and v <= datetime.utcnow():
            raise ValueError('تاريخ انتهاء الخصم يجب أن يكون في المستقبل')
        return v

    @validator('url')
    def validate_url_for_live_courses(cls, v, values):
        """Validate URL is provided for live courses"""
        if values.get('type') == CourseTypeEnum.LIVE and not v:
            raise ValueError('رابط الدورة مطلوب للدورات المباشرة')
        return v


class CourseCreate(CourseBase):
    """Schema for creating a new course"""
    category_id: int = Field(..., gt=0, description="Category ID")
    trainer_id: int = Field(..., gt=0, description="Trainer user ID")
    image: str = Field(..., description="Course main image path")
    gallery: Optional[List[str]] = Field(None, description="Gallery image paths")
    preview_video: Optional[str] = Field(None, description="Preview video path")

    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "category_id": 1,
                "trainer_id": 2,
                "title": "دورة تطوير الويب الشاملة",
                "content": "دورة شاملة في تطوير المواقع الإلكترونية باستخدام أحدث التقنيات",
                "short_content": "تعلم تطوير المواقع من الصفر",
                "preparations": "حاسوب محمول، اتصال إنترنت",
                "requirements": "معرفة أساسية بالحاسوب",
                "learning_outcomes": "بناء مواقع إلكترونية متكاملة",
                "type": "recorded",
                "level": "beginner",
                "price": 299.99,
                "image": "courses/image.jpg"
            }
        }


class CourseUpdate(BaseModel):
    """Schema for updating an existing course"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    content: Optional[str] = Field(None, min_length=10)
    short_content: Optional[str] = Field(None, min_length=10, max_length=500)
    preparations: Optional[str] = None
    requirements: Optional[str] = None
    learning_outcomes: Optional[str] = None
    type: Optional[CourseTypeEnum] = None
    level: Optional[CourseLevelEnum] = None
    price: Optional[Decimal] = Field(None, ge=0)
    discount_price: Optional[Decimal] = Field(None, ge=0)
    discount_ends_at: Optional[datetime] = None
    url: Optional[str] = None
    featured: Optional[bool] = None
    status: Optional[CourseStatusEnum] = None
    image: Optional[str] = None
    gallery: Optional[List[str]] = None
    preview_video: Optional[str] = None


class CourseResponse(CourseBase):
    """Schema for course response"""
    id: str
    academy_id: int
    category_id: int
    trainer_id: int
    slug: str
    image: str
    gallery: Optional[List[str]] = None
    preview_video: Optional[str] = None
    status: CourseStatusEnum
    platform_fee_percentage: Decimal
    avg_rating: Decimal
    ratings_count: int
    students_count: int
    lessons_count: int
    duration_seconds: int
    completion_rate: Decimal
    created_at: datetime
    updated_at: datetime

    # Computed properties
    current_price: Decimal
    duration_formatted: str
    is_published: bool
    is_free: bool

    class Config:
        """Pydantic configuration for ORM compatibility"""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class CourseListResponse(BaseModel):
    """Schema for course list with pagination"""
    courses: List[CourseResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

    class Config:
        from_attributes = True


class CourseDetailResponse(CourseResponse):
    """Schema for detailed course response with relationships"""
    # Related data will be included via separate schemas
    category: Optional[Dict[str, Any]] = None
    trainer: Optional[Dict[str, Any]] = None
    chapters: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class CourseFilters(BaseModel):
    """Schema for course filtering and search"""
    category_id: Optional[int] = Field(None, description="Filter by category")
    trainer_id: Optional[int] = Field(None, description="Filter by trainer")
    status: Optional[CourseStatusEnum] = Field(None, description="Filter by status")
    type: Optional[CourseTypeEnum] = Field(None, description="Filter by type")
    level: Optional[CourseLevelEnum] = Field(None, description="Filter by level")
    price_from: Optional[Decimal] = Field(None, ge=0, description="Minimum price")
    price_to: Optional[Decimal] = Field(None, ge=0, description="Maximum price")
    featured: Optional[bool] = Field(None, description="Filter featured courses")
    search: Optional[str] = Field(None, min_length=2, max_length=100, description="Search query")
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(10, ge=1, le=100, description="Items per page")

    @validator('price_to')
    def validate_price_range(cls, v, values):
        """Validate price range"""
        if v is not None and 'price_from' in values and values['price_from'] is not None:
            if v < values['price_from']:
                raise ValueError('السعر الأقصى يجب أن يكون أكبر من السعر الأدنى')
        return v


class CourseStatusUpdate(BaseModel):
    """Schema for updating course status"""
    status: CourseStatusEnum = Field(..., description="New course status")

    class Config:
        schema_extra = {
            "example": {
                "status": "published"
            }
        }


# Chapter schemas
class ChapterBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    order: int = Field(..., ge=1)
    is_free: bool = False


class ChapterCreate(ChapterBase):
    course_id: int


class ChapterUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    order: Optional[int] = Field(None, ge=1)
    is_free: Optional[bool] = None


class ChapterInDB(ChapterBase):
    id: int
    course_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Lesson schemas
class LessonBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    order: int = Field(..., ge=1)
    duration: Optional[int] = Field(None, ge=0)  # In minutes
    is_free: bool = False
    is_published: bool = True


class LessonCreate(LessonBase):
    chapter_id: int


class LessonUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    order: Optional[int] = Field(None, ge=1)
    duration: Optional[int] = Field(None, ge=0)
    is_free: Optional[bool] = None
    is_published: Optional[bool] = None


class LessonInDB(LessonBase):
    id: int
    chapter_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Video schemas
class VideoBase(BaseModel):
    url: str
    duration: Optional[int] = Field(None, ge=0)  # In seconds
    format: Optional[str] = None
    resolution: Optional[str] = None
    provider: Optional[str] = None
    thumbnail: Optional[str] = None
    subtitles_url: Optional[str] = None
    is_downloadable: bool = False


class VideoCreate(VideoBase):
    lesson_id: int


class VideoUpdate(BaseModel):
    url: Optional[str] = None
    duration: Optional[int] = Field(None, ge=0)
    format: Optional[str] = None
    resolution: Optional[str] = None
    provider: Optional[str] = None
    thumbnail: Optional[str] = None
    subtitles_url: Optional[str] = None
    is_downloadable: Optional[bool] = None


class VideoInDB(VideoBase):
    id: int
    lesson_id: int
    size: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True 