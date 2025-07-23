from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.crud.base import CRUDBase
from app.models.settings import Settings
from app.schemas.settings import SettingsCreate, SettingsUpdate


class CRUDSettings(CRUDBase[Settings, SettingsCreate, SettingsUpdate]):
    """
    CRUD operations for Settings model
    Handles general platform settings and configuration
    """
    
    def get_settings(self, db: Session) -> Optional[Settings]:
        """Get current platform settings"""
        try:
            return db.query(Settings).first()
        except Exception as e:
            raise Exception(f"Error retrieving settings: {str(e)}")
    
    def create_or_update_settings(self, db: Session, settings_data: Dict[str, Any]) -> Settings:
        """Create new settings or update existing ones"""
        try:
            existing_settings = self.get_settings(db)
            
            if existing_settings:
                # Update existing settings
                return self.update(db, db_obj=existing_settings, obj_in=settings_data)
            else:
                # Create new settings
                return self.create(db, obj_in=SettingsCreate(**settings_data))
                
        except Exception as e:
            raise Exception(f"Error creating/updating settings: {str(e)}")
    
    def update_basic_info(self, db: Session, title: str, description: Optional[str] = None, keywords: Optional[str] = None) -> Settings:
        """Update basic platform information"""
        try:
            settings = self.get_settings(db)
            if not settings:
                raise Exception("Settings not found")
            
            update_data = {"title": title}
            if description is not None:
                update_data["description"] = description
            if keywords is not None:
                update_data["keywords"] = keywords
            
            return self.update(db, db_obj=settings, obj_in=update_data)
            
        except Exception as e:
            raise Exception(f"Error updating basic info: {str(e)}")
    
    def update_contact_info(self, db: Session, email: Optional[str] = None, phone: Optional[str] = None, address: Optional[str] = None) -> Settings:
        """Update contact information"""
        try:
            settings = self.get_settings(db)
            if not settings:
                raise Exception("Settings not found")
            
            update_data = {}
            if email is not None:
                update_data["email"] = email
            if phone is not None:
                update_data["phone"] = phone
            if address is not None:
                update_data["address"] = address
            
            return self.update(db, db_obj=settings, obj_in=update_data)
            
        except Exception as e:
            raise Exception(f"Error updating contact info: {str(e)}")
    
    def update_social_links(self, db: Session, social_data: Dict[str, str]) -> Settings:
        """Update social media links"""
        try:
            settings = self.get_settings(db)
            if not settings:
                raise Exception("Settings not found")
            
            return self.update(db, db_obj=settings, obj_in=social_data)
            
        except Exception as e:
            raise Exception(f"Error updating social links: {str(e)}")
    
    def update_logo_favicon(self, db: Session, logo: Optional[str] = None, favicon: Optional[str] = None) -> Settings:
        """Update logo and favicon"""
        try:
            settings = self.get_settings(db)
            if not settings:
                raise Exception("Settings not found")
            
            update_data = {}
            if logo is not None:
                update_data["logo"] = logo
            if favicon is not None:
                update_data["favicon"] = favicon
            
            return self.update(db, db_obj=settings, obj_in=update_data)
            
        except Exception as e:
            raise Exception(f"Error updating logo/favicon: {str(e)}")
    
    def update_legal_pages(self, db: Session, terms: Optional[str] = None, privacy: Optional[str] = None) -> Settings:
        """Update legal pages content"""
        try:
            settings = self.get_settings(db)
            if not settings:
                raise Exception("Settings not found")
            
            update_data = {}
            if terms is not None:
                update_data["terms"] = terms
            if privacy is not None:
                update_data["privacy"] = privacy
            
            return self.update(db, db_obj=settings, obj_in=update_data)
            
        except Exception as e:
            raise Exception(f"Error updating legal pages: {str(e)}")
    
    def get_public_settings(self, db: Session) -> Optional[Dict[str, Any]]:
        """Get public settings (excluding sensitive data)"""
        try:
            settings = self.get_settings(db)
            if not settings:
                return None
            
            return {
                "title": settings.title,
                "description": settings.description,
                "keywords": settings.keywords,
                "logo": settings.logo,
                "favicon": settings.favicon,
                "email": settings.email,
                "phone": settings.phone,
                "address": settings.address,
                "facebook": settings.facebook,
                "twitter": settings.twitter,
                "instagram": settings.instagram,
                "youtube": settings.youtube,
                "linkedin": settings.linkedin,
                "whatsapp": settings.whatsapp
            }
            
        except Exception as e:
            raise Exception(f"Error retrieving public settings: {str(e)}")
    
    def get_social_links(self, db: Session) -> Dict[str, Optional[str]]:
        """Get all social media links"""
        try:
            settings = self.get_settings(db)
            if not settings:
                return {}
            
            return {
                "facebook": settings.facebook,
                "twitter": settings.twitter,
                "instagram": settings.instagram,
                "youtube": settings.youtube,
                "linkedin": settings.linkedin,
                "whatsapp": settings.whatsapp,
                "snapchat": settings.snapchat,
                "tiktok": settings.tiktok,
                "telegram": settings.telegram,
                "discord": settings.discord
            }
            
        except Exception as e:
            raise Exception(f"Error retrieving social links: {str(e)}")
    
    def update_single_social_link(self, db: Session, platform: str, url: str) -> Settings:
        """Update single social media link"""
        try:
            settings = self.get_settings(db)
            if not settings:
                raise Exception("Settings not found")
            
            valid_platforms = [
                "facebook", "twitter", "instagram", "youtube", "linkedin", 
                "whatsapp", "snapchat", "tiktok", "telegram", "discord"
            ]
            
            if platform not in valid_platforms:
                raise Exception(f"Invalid social platform: {platform}")
            
            update_data = {platform: url}
            return self.update(db, db_obj=settings, obj_in=update_data)
            
        except Exception as e:
            raise Exception(f"Error updating social link: {str(e)}")
    
    def update_domain_info(self, db: Session, subdomain: Optional[str] = None, domain: Optional[str] = None) -> Settings:
        """Update domain and subdomain information"""
        try:
            settings = self.get_settings(db)
            if not settings:
                raise Exception("Settings not found")
            
            update_data = {}
            if subdomain is not None:
                update_data["subdomain"] = subdomain
            if domain is not None:
                update_data["domain"] = domain
            
            return self.update(db, db_obj=settings, obj_in=update_data)
            
        except Exception as e:
            raise Exception(f"Error updating domain info: {str(e)}")
    
    def get_domain_info(self, db: Session) -> Dict[str, Optional[str]]:
        """Get domain and subdomain information"""
        try:
            settings = self.get_settings(db)
            if not settings:
                return {}
            
            return {
                "subdomain": settings.subdomain,
                "domain": settings.domain
            }
            
        except Exception as e:
            raise Exception(f"Error retrieving domain info: {str(e)}")


settings = CRUDSettings(Settings) 
 
 
 