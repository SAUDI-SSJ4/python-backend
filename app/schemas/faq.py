from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class FaqBase(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None
    order: Optional[int] = 0
    is_active: Optional[bool] = True


class FaqCreate(FaqBase):
    academy_id: int


class FaqUpdate(FaqBase):
    pass


class Faq(FaqBase):
    id: int
    academy_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True 
 
 
 