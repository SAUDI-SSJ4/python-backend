from typing import Optional
from pydantic import BaseModel, validator
from datetime import datetime
import re


class SettingsBase(BaseModel):
    title: str
    logo: Optional[str] = None
    favicon: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None
    linkedin: Optional[str] = None
    whatsapp: Optional[str] = None
    snapchat: Optional[str] = None
    tiktok: Optional[str] = None
    telegram: Optional[str] = None
    discord: Optional[str] = None
    terms: Optional[str] = None
    privacy: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    subdomain: Optional[str] = None
    domain: Optional[str] = None

    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v

    @validator('subdomain')
    def validate_subdomain(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9-]+$', v):
            raise ValueError('Subdomain can only contain letters, numbers, and hyphens')
        return v

    @validator('domain')
    def validate_domain(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid domain format')
        return v


class SettingsCreate(SettingsBase):
    pass


class SettingsUpdate(SettingsBase):
    pass


class Settings(SettingsBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True 
 
 
 