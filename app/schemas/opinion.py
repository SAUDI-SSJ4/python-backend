from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class OpinionBase(BaseModel):
    name: str
    title: Optional[str] = None
    content: str
    rating: Optional[int] = Field(default=5, ge=1, le=5)
    image: Optional[str] = None
    is_featured: Optional[bool] = False
    is_approved: Optional[bool] = False


class OpinionCreate(OpinionBase):
    academy_id: int
    student_id: Optional[int] = None


class OpinionUpdate(OpinionBase):
    pass


class Opinion(OpinionBase):
    id: int
    academy_id: int
    student_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True 
 
 
 