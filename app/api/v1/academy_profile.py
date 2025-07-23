"""
Academy Profile Management
=========================
Comprehensive academy profile endpoints with all content and settings
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, joinedload
from typing import Optional, Dict, Any
from datetime import datetime

from app.deps import get_db, get_current_academy_user
from app.models.user import User
from app.models.academy import Academy, AcademyUser
from app.models.template import Template, About, Slider, Faq, Opinion
from app.models.settings import Settings
from app.crud import academy_content
from app.core.response_handler import SayanSuccessResponse

router = APIRouter()


@router.get("/profile", response_model=None, summary="Get Academy Profile")
async def get_academy_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> dict:
    """
    Get comprehensive academy profile information
    
    Returns complete academy profile including:
    - Basic academy information
    - Template and styling
    - About information
    - Social media links
    - Domain information
    - Content statistics
    """
    try:
        academy = current_user.academy
        
        # Get academy basic info
        academy_info = {
            "id": academy.id,
            "name": academy.name,
            "slug": academy.slug,
            "about": academy.about,
            "image": academy.image,
            "email": academy.email,
            "phone": academy.phone,
            "address": academy.address,
            "status": academy.status,
            "trial_status": academy.trial_status,
            "trial_start": academy.trial_start,
            "trial_end": academy.trial_end,
            "users_count": academy.users_count,
            "courses_count": academy.courses_count,
            "package_id": academy.package_id,
            "created_at": academy.created_at,
            "updated_at": academy.updated_at,
        }
        
        # Get social media links from academy model
        social_links = {
            "facebook": academy.facebook,
            "twitter": academy.twitter,
            "instagram": academy.instagram,
            "snapchat": academy.snapchat,
        }
        
        # Get template information
        template = academy_content.get_template(db, academy.id)
        template_info = None
        if template:
            template_info = {
                "primary_color": template.primary_color,
                "secondary_color": template.secondary_color,
                "custom_css": template.custom_css,
                "custom_js": template.custom_js,
            }
        
        # Get about information
        about = academy_content.get_about(db, academy.id)
        about_info = None
        if about:
            about_info = {
                "title": about.title,
                "content": about.content,
                "mission": about.mission,
                "vision": about.vision,
                "values": about.values,
                "image": about.image,
                "video_url": about.video_url,
                "statistics": about.statistics,
            }
        
        # Get content statistics
        sliders_count = academy_content.get_sliders_count(db, academy.id)
        faqs_count = academy_content.get_faqs_count(db, academy.id)
        opinions_count = academy_content.get_opinions_count(db, academy.id)
        
        # Get global settings
        settings = academy_content.get_settings(db)
        settings_info = None
        if settings:
            settings_info = {
                "title": settings.title,
                "logo": settings.logo,
                "favicon": settings.favicon,
                "email": settings.email,
                "phone": settings.phone,
                "address": settings.address,
                "terms": settings.terms,
                "privacy": settings.privacy,
                "description": settings.description,
                "keywords": settings.keywords,
                "subdomain": settings.subdomain,
                "domain": settings.domain,
            }
            
            # Add extended social media links from settings
            extended_social_links = {
                "facebook": settings.facebook,
                "twitter": settings.twitter,
                "instagram": settings.instagram,
                "youtube": settings.youtube,
                "linkedin": settings.linkedin,
                "whatsapp": settings.whatsapp,
                "snapchat": settings.snapchat,
                "tiktok": settings.tiktok,
                "telegram": settings.telegram,
                "discord": settings.discord,
            }
            
            # Merge social links (settings take precedence)
            for key, value in extended_social_links.items():
                if value:
                    social_links[key] = value
        
        # Get user membership info
        membership = db.query(AcademyUser).filter(
            AcademyUser.academy_id == academy.id,
            AcademyUser.user_id == current_user.id
        ).first()
        
        membership_info = None
        if membership:
            membership_info = {
                "membership_id": membership.id,
                "user_role": membership.user_role,
                "is_active": membership.is_active,
                "joined_at": membership.joined_at,
                "created_at": membership.created_at,
            }
        
        # Build complete profile response
        profile_data = {
            "academy": academy_info,
            "template": template_info,
            "about": about_info,
            "social_links": social_links,
            "settings": settings_info,
            "membership": membership_info,
            "statistics": {
                "sliders_count": sliders_count,
                "faqs_count": faqs_count,
                "opinions_count": opinions_count,
                "users_count": academy.users_count,
                "courses_count": academy.courses_count,
            }
        }
        
        return SayanSuccessResponse(
            data=profile_data,
            message="تم جلب بروفايل الأكاديمية بنجاح",
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطأ في جلب بروفايل الأكاديمية: {str(e)}"
        )


@router.get("/profile/summary", response_model=None, summary="Get Academy Profile Summary")
async def get_academy_profile_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> dict:
    """
    Get academy profile summary
    
    Returns a condensed version of academy profile with essential information
    """
    try:
        academy = current_user.academy
        
        # Get content summary
        content_summary = academy_content.get_academy_content_summary(db, academy.id)
        
        # Get template basic info
        template = academy_content.get_template(db, academy.id)
        template_summary = None
        if template:
            template_summary = {
                "primary_color": template.primary_color,
            }
        
        # Get about basic info
        about = academy_content.get_about(db, academy.id)
        about_summary = None
        if about:
            about_summary = {
                "title": about.title,
                "has_mission": bool(about.mission),
                "has_vision": bool(about.vision),
                "has_image": bool(about.image),
            }
        
        summary_data = {
            "academy": {
                "id": academy.id,
                "name": academy.name,
                "slug": academy.slug,
                "status": academy.status,
                "email": academy.email,
                "phone": academy.phone,
            },
            "template": template_summary,
            "about": about_summary,
            "content_summary": content_summary,
        }
        
        return SayanSuccessResponse(
            data=summary_data,
            message="تم جلب ملخص بروفايل الأكاديمية بنجاح",
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطأ في جلب ملخص بروفايل الأكاديمية: {str(e)}"
        )


@router.get("/profile/public/{academy_slug}", response_model=None, summary="Get Public Academy Profile")
async def get_public_academy_profile(
    academy_slug: str,
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get public academy profile
    
    Returns public academy information accessible to all users
    """
    try:
        # Get academy by slug
        academy = db.query(Academy).filter(
            Academy.slug == academy_slug,
            Academy.status == "active"
        ).first()
        
        if not academy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الأكاديمية غير موجودة"
            )
        
        # Get public academy info
        academy_info = {
            "id": academy.id,
            "name": academy.name,
            "slug": academy.slug,
            "about": academy.about,
            "image": academy.image,
            "email": academy.email,
            "phone": academy.phone,
            "address": academy.address,
            "users_count": academy.users_count,
            "courses_count": academy.courses_count,
            "created_at": academy.created_at,
        }
        
        # Get public social links
        social_links = {
            "facebook": academy.facebook,
            "twitter": academy.twitter,
            "instagram": academy.instagram,
            "snapchat": academy.snapchat,
        }
        
        # Get public template info
        template = academy_content.get_template(db, academy.id)
        template_info = None
        if template:
            template_info = {
                "primary_color": template.primary_color,
                "secondary_color": template.secondary_color,
            }
        
        # Get public about info
        about = academy_content.get_about(db, academy.id)
        about_info = None
        if about:
            about_info = {
                "title": about.title,
                "content": about.content,
                "mission": about.mission,
                "vision": about.vision,
                "image": about.image,
                "statistics": about.statistics,
            }
        
        # Get active sliders
        sliders = academy_content.get_active_sliders(db, academy.id)
        sliders_info = []
        for slider in sliders:
            sliders_info.append({
                "id": slider.id,
                "title": slider.title,
                "subtitle": slider.subtitle,
                "image": slider.image,
                "link": slider.link,
                "button_text": slider.button_text,
                "order": slider.order,
            })
        
        # Get active FAQs
        faqs = academy_content.get_active_faqs(db, academy.id)
        faqs_info = []
        for faq in faqs:
            faqs_info.append({
                "id": faq.id,
                "question": faq.question,
                "answer": faq.answer,
                "category": faq.category,
                "order": faq.order,
            })
        
        # Get approved opinions
        opinions = academy_content.get_approved_opinions(db, academy.id, limit=10)
        opinions_info = []
        for opinion in opinions:
            opinions_info.append({
                "id": opinion.id,
                "name": opinion.name,
                "title": opinion.title,
                "content": opinion.content,
                "rating": opinion.rating,
                "image": opinion.image,
                "featured": opinion.featured,
                "created_at": opinion.created_at,
            })
        
        public_data = {
            "academy": academy_info,
            "template": template_info,
            "about": about_info,
            "social_links": social_links,
            "sliders": sliders_info,
            "faqs": faqs_info,
            "opinions": opinions_info,
        }
        
        return SayanSuccessResponse(
            data=public_data,
            message="تم جلب بروفايل الأكاديمية العام بنجاح",
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطأ في جلب البروفايل العام: {str(e)}"
        ) 
 
 
 