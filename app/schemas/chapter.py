from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChapterBase(BaseModel):
    """Base chapter schema with common fields"""
    title: str = Field(..., min_length=3, max_length=200, description="Chapter title")
    description: Optional[str] = Field(None, description="Chapter description")
    order_number: int = Field(0, ge=0, description="Chapter order within course")
    is_published: bool = Field(True, description="Whether chapter is published")


class ChapterCreate(ChapterBase):
    """Schema for creating a new chapter"""
    course_id: str = Field(..., description="Course ID that this chapter belongs to")

    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "course_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "مقدمة في تطوير الويب",
                "description": "في هذا الفصل سنتعلم أساسيات تطوير المواقع",
                "order_number": 1,
                "is_published": True
            }
        }


class ChapterUpdate(BaseModel):
    """Schema for updating an existing chapter"""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    order_number: Optional[int] = Field(None, ge=0)
    is_published: Optional[bool] = None


class ChapterResponse(ChapterBase):
    """Schema for chapter response"""
    id: int
    course_id: str
    lessons_count: int
    total_duration_seconds: int
    is_accessible: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration for ORM compatibility"""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChapterDetailResponse(ChapterResponse):
    """Schema for detailed chapter response with lessons"""
    lessons: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class ChapterListResponse(BaseModel):
    """Schema for chapter list response"""
    chapters: List[ChapterResponse]
    total: int

    class Config:
        from_attributes = True


class ChapterOrderUpdate(BaseModel):
    """Schema for updating chapter order"""
    chapter_id: int = Field(..., description="Chapter ID")
    new_order: int = Field(..., ge=0, description="New order number")

    class Config:
        schema_extra = {
            "example": {
                "chapter_id": 1,
                "new_order": 3
            }
        }


class ChaptersBulkOrderUpdate(BaseModel):
    """Schema for bulk updating chapter orders"""
    chapters: List[ChapterOrderUpdate] = Field(..., description="List of chapters with new orders")

    @validator('chapters')
    def validate_unique_orders(cls, v):
        """Validate that order numbers are unique"""
        orders = [chapter.new_order for chapter in v]
        if len(orders) != len(set(orders)):
            raise ValueError('أرقام الترتيب يجب أن تكون فريدة')
        return v

    class Config:
        schema_extra = {
            "example": {
                "chapters": [
                    {"chapter_id": 1, "new_order": 1},
                    {"chapter_id": 2, "new_order": 2},
                    {"chapter_id": 3, "new_order": 3}
                ]
            }
        } 