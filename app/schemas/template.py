from typing import Optional, Dict, Any
from pydantic import BaseModel, validator
from datetime import datetime
import re


class TemplateBase(BaseModel):
    primary_color: Optional[str] = "#007bff"
    secondary_color: Optional[str] = "#6c757d"
    custom_css: Optional[str] = None
    custom_js: Optional[str] = None

    @validator('primary_color', 'secondary_color')
    def validate_color(cls, v):
        if v and not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be a valid hex color (e.g., #007bff)')
        return v




class TemplateCreate(TemplateBase):
    academy_id: int


class TemplateUpdate(TemplateBase):
    pass


class Template(TemplateBase):
    id: int
    academy_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True 
 
 
 