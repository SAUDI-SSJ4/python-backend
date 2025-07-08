from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum
import pytz


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
        """Validate discount end date is in the future - Updated"""
        if v is not None:
            # التعامل الصحيح مع التواريخ بنوعيها timezone-aware و timezone-naive
            if v.tzinfo is not None:
                # إذا كان التاريخ timezone-aware
                current_time = datetime.now(pytz.UTC)
            else:
                # إذا كان التاريخ timezone-naive
                current_time = datetime.utcnow()
            
            if v <= current_time:
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
    trainer_id: Optional[int] = Field(None, description="Trainer user ID (optional)")
    product_id: Optional[int] = Field(None, gt=0, description="Product ID (optional)")
    image: str = Field(..., description="Course main image path")
    gallery: Optional[List[str]] = Field(None, description="Gallery image paths")
    preview_video: Optional[str] = Field(None, description="Preview video path")

    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "category_id": 1,
                "trainer_id": 2,
                "product_id": 1,
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
    product_id: Optional[int] = Field(None, gt=0, description="Product ID")


class CourseResponse(BaseModel):
    """Schema for course response"""
    id: str
    academy_id: int
    category_id: int
    trainer_id: Optional[int] = None
    slug: str
    image: str
    content: str
    short_content: str
    preparations: Optional[str] = None
    requirements: Optional[str] = None
    learning_outcomes: Optional[str] = None
    gallery: Optional[List[str]] = None
    preview_video: Optional[str] = None
    course_state: str  # course_state بدلاً من status
    featured: bool
    type: str
    level: str
    url: Optional[str] = None
    platform_fee_percentage: Decimal
    avg_rating: Decimal
    ratings_count: int
    students_count: int
    lessons_count: int
    completion_rate: Decimal
    created_at: datetime
    updated_at: datetime
    
    # Properties that come from Product relationship
    title: str
    price: Decimal
    discount_price: Optional[Decimal] = None
    discount_ends_at: Optional[datetime] = None

    # Computed properties
    @property
    def current_price(self) -> Decimal:
        """Get current effective price (considering discounts)"""
        if self.discount_price and self.discount_ends_at:
            if datetime.utcnow() < self.discount_ends_at:
                return self.discount_price
        return self.price
    
    @property
    def duration_formatted(self) -> str:
        return "N/A"
    
    @property
    def is_published(self) -> bool:
        """Check if the course is published"""
        return self.course_state == "published"
    
    @property
    def is_free(self) -> bool:
        """Check if the course is free"""
        return self.price <= 0

    @classmethod
    def from_course_model(cls, course):
        """Convert course model to response schema"""
        from app.core.config import settings
        from decimal import Decimal
        from datetime import datetime
        # Get product data
        product_data = {
            "title": course.product.title if getattr(course, 'product', None) and course.product else "",
            "price": course.product.price if getattr(course, 'product', None) and course.product and course.product.price is not None else Decimal('0.00'),
            "discount_price": course.product.discount_price if getattr(course, 'product', None) and course.product else None,
            "discount_ends_at": course.product.discount_ends_at if getattr(course, 'product', None) and course.product else None
        }
        # Ensure image path starts with /static/uploads/
        image_path = course.image if getattr(course, 'image', None) else ""
        if image_path and not image_path.startswith('/static/uploads/'):
            if image_path.startswith('static/uploads/'):
                image_path = '/' + image_path
            else:
                image_path = f'/static/uploads/{image_path}'
        # Convert preview video path
        preview_video_path = course.preview_video if getattr(course, 'preview_video', None) else None
        if preview_video_path and not preview_video_path.startswith('/static/uploads/'):
            if preview_video_path.startswith('static/uploads/'):
                preview_video_path = '/' + preview_video_path
            else:
                preview_video_path = f'/static/uploads/{preview_video_path}'
        # Convert gallery paths if they exist
        gallery_paths = None
        if getattr(course, 'gallery', None):
            gallery_paths = []
            for path in course.gallery:
                if path and not path.startswith('/static/uploads/'):
                    if path.startswith('static/uploads/'):
                        gallery_paths.append('/' + path)
                    else:
                        gallery_paths.append(f'/static/uploads/{path}')
                else:
                    gallery_paths.append(path)
        # Create response data
        response_data = {
            "id": getattr(course, 'id', ""),
            "academy_id": getattr(course, 'academy_id', 0),
            "category_id": getattr(course, 'category_id', 0),
            "trainer_id": getattr(course, 'trainer_id', None),
            "slug": getattr(course, 'slug', ""),
            "image": image_path,
            "content": getattr(course, 'content', ""),
            "short_content": getattr(course, 'short_content', ""),
            "preparations": getattr(course, 'preparations', None),
            "requirements": getattr(course, 'requirements', None),
            "learning_outcomes": getattr(course, 'learning_outcomes', None),
            "gallery": gallery_paths,
            "preview_video": preview_video_path,
            "course_state": getattr(course, 'course_state', "draft"),
            "featured": getattr(course, 'featured', False),
            "type": getattr(course, 'type', "recorded"),
            "level": getattr(course, 'level', "beginner"),
            "url": getattr(course, 'url', None),
            "platform_fee_percentage": getattr(course, 'platform_fee_percentage', Decimal('0.00')),
            "avg_rating": getattr(course, 'avg_rating', Decimal('0.00')),
            "ratings_count": getattr(course, 'ratings_count', 0),
            "students_count": getattr(course, 'students_count', 0),
            "lessons_count": getattr(course, 'lessons_count', 0),
            "completion_rate": getattr(course, 'completion_rate', Decimal('0.00')),
            "created_at": getattr(course, 'created_at', datetime.utcnow()),
            "updated_at": getattr(course, 'updated_at', datetime.utcnow()),
            **product_data
        }
        return cls(**response_data)

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

    @classmethod
    def from_course_model(cls, course, chapters=None):
        """Create CourseDetailResponse from Course model with product relationship"""
        base_data = super().from_course_model(course)
        base_dict = base_data.dict()
        response_data = base_dict.copy()
        # Add category data if available
        if hasattr(course, 'category') and course.category:
            response_data['category'] = {
                'id': getattr(course.category, 'id', 0),
                'title': getattr(course.category, 'title', ""),
                'slug': getattr(course.category, 'slug', ""),
                'content': getattr(course.category, 'content', ""),
                'image': getattr(course.category, 'image', None),
                'status': getattr(course.category, 'status', None)
            }
        else:
            response_data['category'] = None
        # Add trainer data if available
        if hasattr(course, 'trainer') and course.trainer:
            response_data['trainer'] = {
                'id': getattr(course.trainer, 'id', 0),
                'fname': getattr(course.trainer, 'fname', ""),
                'lname': getattr(course.trainer, 'lname', ""),
                'email': getattr(course.trainer, 'email', ""),
                'avatar': getattr(course.trainer, 'avatar', None),
                'user_type': getattr(course.trainer, 'user_type', None)
            }
        else:
            response_data['trainer'] = None
        # Add chapters data if provided
        if chapters:
            response_data['chapters'] = [
                {
                    'id': getattr(chapter, 'id', 0),
                    'title': getattr(chapter, 'title', ""),
                    'description': getattr(chapter, 'description', ""),
                    'order_number': getattr(chapter, 'order_number', 0),
                    'is_published': getattr(chapter, 'is_published', False),
                    'created_at': getattr(chapter, 'created_at', None)
                }
                for chapter in chapters
            ]
        else:
            response_data['chapters'] = None
        return cls(**response_data)

    class Config:
        from_attributes = True


class CourseFilters(BaseModel):
    """Schema for course filtering and search"""
    academy_id: Optional[int] = Field(
        None, 
        description="Filter courses by specific academy ID (e.g., 49 for academy 49)",
        example=49,
        ge=1
    )
    category_id: Optional[int] = Field(
        None, 
        description="Filter courses by category ID",
        example=1,
        ge=1
    )
    trainer_id: Optional[int] = Field(
        None, 
        description="Filter courses by trainer ID",
        example=1,
        ge=1
    )
    status: Optional[CourseStatusEnum] = Field(
        None, 
        description="Filter by course status (draft, published, archived)",
        example="published"
    )
    type: Optional[CourseTypeEnum] = Field(
        None, 
        description="Filter by course type (live, recorded, attend)",
        example="recorded"
    )
    level: Optional[CourseLevelEnum] = Field(
        None, 
        description="Filter by course level (beginner, intermediate, advanced)",
        example="beginner"
    )
    price_from: Optional[Decimal] = Field(
        None, 
        ge=0, 
        description="Minimum price filter (e.g., 100.00)",
        example=100.00
    )
    price_to: Optional[Decimal] = Field(
        None, 
        ge=0, 
        description="Maximum price filter (e.g., 500.00)",
        example=500.00
    )
    featured: Optional[bool] = Field(
        None, 
        description="Filter featured courses only (true/false)",
        example=True
    )
    search: Optional[str] = Field(
        None, 
        min_length=2, 
        max_length=100, 
        description="Search in course title and description",
        example="python"
    )
    page: int = Field(
        1, 
        ge=1, 
        description="Page number for pagination",
        example=1
    )
    per_page: int = Field(
        10, 
        ge=1, 
        le=100, 
        description="Number of items per page (1-100)",
        example=10
    )

    class Config:
        schema_extra = {
            "example": {
                "academy_id": 49,
                "category_id": 1,
                "level": "beginner",
                "featured": True,
                "search": "python",
                "page": 1,
                "per_page": 10
            }
        }

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