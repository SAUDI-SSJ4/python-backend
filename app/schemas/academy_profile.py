"""
Academy Profile Schemas
======================
Comprehensive schemas for academy profile responses
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime


class AcademyBasicInfo(BaseModel):
    """Basic academy information"""
    id: int
    name: str
    slug: str
    about: Optional[str] = None
    image: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    status: str
    trial_status: Optional[str] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    users_count: int = 0
    courses_count: int = 0
    package_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class TemplateInfo(BaseModel):
    """Template information"""

    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    custom_css: Optional[str] = None
    custom_js: Optional[str] = None


class AboutInfo(BaseModel):
    """About information"""
    title: Optional[str] = None
    content: Optional[str] = None
    mission: Optional[str] = None
    vision: Optional[str] = None
    values: Optional[Dict[str, Any]] = None
    image: Optional[str] = None
    video_url: Optional[str] = None
    statistics: Optional[Dict[str, Any]] = None


class SocialLinks(BaseModel):
    """Social media links"""
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


class SettingsInfo(BaseModel):
    """Global settings information"""
    title: Optional[str] = None
    logo: Optional[str] = None
    favicon: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    terms: Optional[str] = None
    privacy: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    subdomain: Optional[str] = None
    domain: Optional[str] = None


class MembershipInfo(BaseModel):
    """User membership information"""
    membership_id: int
    user_role: str
    is_active: bool
    joined_at: datetime
    created_at: datetime


class ContentStatistics(BaseModel):
    """Content statistics"""
    sliders_count: int = 0
    faqs_count: int = 0
    opinions_count: int = 0
    users_count: int = 0
    courses_count: int = 0


class SliderInfo(BaseModel):
    """Slider information"""
    id: int
    title: str
    subtitle: str
    image: Optional[str] = None
    link: Optional[str] = None
    button_text: Optional[str] = None
    order: int


class FaqInfo(BaseModel):
    """FAQ information"""
    id: int
    question: str
    answer: str
    category: Optional[str] = None
    order: int


class OpinionInfo(BaseModel):
    """Opinion information"""
    id: int
    name: str
    title: str
    content: str
    rating: int
    image: Optional[str] = None
    featured: bool = False
    created_at: datetime


class AcademyProfileResponse(BaseModel):
    """Complete academy profile response"""
    academy: AcademyBasicInfo
    template: Optional[TemplateInfo] = None
    about: Optional[AboutInfo] = None
    social_links: SocialLinks
    settings: Optional[SettingsInfo] = None
    membership: Optional[MembershipInfo] = None
    statistics: ContentStatistics


class AcademyProfileSummaryResponse(BaseModel):
    """Academy profile summary response"""
    academy: Dict[str, Any]
    template: Optional[Dict[str, Any]] = None
    about: Optional[Dict[str, Any]] = None
    content_summary: Dict[str, Any]


class PublicAcademyProfileResponse(BaseModel):
    """Public academy profile response"""
    academy: AcademyBasicInfo
    template: Optional[TemplateInfo] = None
    about: Optional[AboutInfo] = None
    social_links: SocialLinks
    sliders: List[SliderInfo] = []
    faqs: List[FaqInfo] = []
    opinions: List[OpinionInfo] = [] 
 
 
 