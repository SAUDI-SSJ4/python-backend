from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class AboutBase(BaseModel):
    title: str
    content: str
    mission: Optional[str] = None
    vision: Optional[str] = None
    values: Optional[Dict[str, Any]] = None
    image: Optional[str] = None
    video_url: Optional[str] = None


class AboutCreate(AboutBase):
    academy_id: int


class AboutUpdate(AboutBase):
    pass


class About(AboutBase):
    id: int
    academy_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True 
 
 
 