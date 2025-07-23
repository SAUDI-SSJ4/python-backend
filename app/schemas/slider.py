from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class SliderBase(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    image: str
    link: Optional[str] = None
    button_text: Optional[str] = None
    order: Optional[int] = 0
    is_active: Optional[bool] = True


class SliderCreate(SliderBase):
    academy_id: int


class SliderUpdate(SliderBase):
    pass


class Slider(SliderBase):
    id: int
    academy_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True 
 
 
 