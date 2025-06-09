from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class CourseStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CourseLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ALL_LEVELS = "all_levels"


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
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    category_id: int
    trainer_id: Optional[int] = None
    price: float = Field(..., ge=0)
    discount_price: Optional[float] = Field(None, ge=0)
    duration: Optional[int] = Field(None, ge=0)  # In minutes
    level: CourseLevel = CourseLevel.ALL_LEVELS
    language: str = "ar"
    requirements: Optional[List[str]] = None
    what_will_learn: Optional[List[str]] = None
    is_featured: bool = False
    is_free: bool = False
    certificate_enabled: bool = True


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[int] = None
    trainer_id: Optional[int] = None
    price: Optional[float] = Field(None, ge=0)
    discount_price: Optional[float] = Field(None, ge=0)
    duration: Optional[int] = Field(None, ge=0)
    level: Optional[CourseLevel] = None
    language: Optional[str] = None
    requirements: Optional[List[str]] = None
    what_will_learn: Optional[List[str]] = None
    status: Optional[CourseStatus] = None
    is_featured: Optional[bool] = None
    is_free: Optional[bool] = None
    certificate_enabled: Optional[bool] = None


class CourseInDB(CourseBase):
    id: int
    academy_id: int
    slug: str
    thumbnail: Optional[str] = None
    preview_video: Optional[str] = None
    status: CourseStatus
    views_count: int
    enrollment_count: int
    rating: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


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