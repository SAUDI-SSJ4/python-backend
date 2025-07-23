from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.crud.base import CRUDBase
from app.models.template import About
from app.schemas.about import AboutCreate, AboutUpdate


class CRUDAbout(CRUDBase[About, AboutCreate, AboutUpdate]):
    """
    CRUD operations for About model
    Handles academy about information including mission, vision, and values
    """
    
    def get_by_academy_id(self, db: Session, academy_id: int) -> Optional[About]:
        """Get about information by academy ID"""
        try:
            return db.query(About).filter(About.academy_id == academy_id).first()
        except Exception as e:
            raise Exception(f"Error retrieving about information: {str(e)}")
    
    def create_or_update(self, db: Session, academy_id: int, about_data: Dict[str, Any]) -> About:
        """Create new about information or update existing one for academy"""
        try:
            existing_about = self.get_by_academy_id(db, academy_id)
            
            if existing_about:
                # Update existing about information
                return self.update(db, db_obj=existing_about, obj_in=about_data)
            else:
                # Create new about information
                about_data["academy_id"] = academy_id
                return self.create(db, obj_in=AboutCreate(**about_data))
                
        except Exception as e:
            raise Exception(f"Error creating/updating about information: {str(e)}")
    
    def update_content(self, db: Session, academy_id: int, title: str, content: str) -> About:
        """Update about content for academy"""
        try:
            about = self.get_by_academy_id(db, academy_id)
            if not about:
                raise Exception("About information not found for this academy")
            
            update_data = {
                "title": title,
                "content": content
            }
            
            return self.update(db, db_obj=about, obj_in=update_data)
            
        except Exception as e:
            raise Exception(f"Error updating about content: {str(e)}")
    
    def update_mission_vision(self, db: Session, academy_id: int, mission: Optional[str] = None, vision: Optional[str] = None) -> About:
        """Update mission and vision for academy"""
        try:
            about = self.get_by_academy_id(db, academy_id)
            if not about:
                raise Exception("About information not found for this academy")
            
            update_data = {}
            if mission is not None:
                update_data["mission"] = mission
            if vision is not None:
                update_data["vision"] = vision
            
            return self.update(db, db_obj=about, obj_in=update_data)
            
        except Exception as e:
            raise Exception(f"Error updating mission/vision: {str(e)}")
    
    def update_values(self, db: Session, academy_id: int, values: Dict[str, Any]) -> About:
        """Update values for academy"""
        try:
            about = self.get_by_academy_id(db, academy_id)
            if not about:
                raise Exception("About information not found for this academy")
            
            update_data = {"values": values}
            return self.update(db, db_obj=about, obj_in=update_data)
            
        except Exception as e:
            raise Exception(f"Error updating values: {str(e)}")
    
    def update_media(self, db: Session, academy_id: int, image: Optional[str] = None, video_url: Optional[str] = None) -> About:
        """Update image and video URL for academy"""
        try:
            about = self.get_by_academy_id(db, academy_id)
            if not about:
                raise Exception("About information not found for this academy")
            
            update_data = {}
            if image is not None:
                update_data["image"] = image
            if video_url is not None:
                update_data["video_url"] = video_url
            
            return self.update(db, db_obj=about, obj_in=update_data)
            
        except Exception as e:
            raise Exception(f"Error updating media: {str(e)}")
    
    def get_public_about(self, db: Session, academy_id: int) -> Optional[Dict[str, Any]]:
        """Get public about information for academy (excluding sensitive data)"""
        try:
            about = self.get_by_academy_id(db, academy_id)
            if not about:
                return None
            
            return {
                "id": about.id,
                "title": about.title,
                "content": about.content,
                "mission": about.mission,
                "vision": about.vision,
                "values": about.values,
                "image": about.image,
                "video_url": about.video_url,
                "created_at": about.created_at,
                "updated_at": about.updated_at
            }
            
        except Exception as e:
            raise Exception(f"Error retrieving public about information: {str(e)}")
    
    def update_statistics(self, db: Session, academy_id: int, statistics: Dict[str, Any]) -> About:
        """Update statistics in values field"""
        try:
            about = self.get_by_academy_id(db, academy_id)
            if not about:
                raise Exception("About information not found for this academy")
            
            current_values = about.values or {}
            current_values["statistics"] = statistics
            
            update_data = {"values": current_values}
            return self.update(db, db_obj=about, obj_in=update_data)
            
        except Exception as e:
            raise Exception(f"Error updating statistics: {str(e)}")
    
    def get_statistics(self, db: Session, academy_id: int) -> Optional[Dict[str, Any]]:
        """Get statistics from values field"""
        try:
            about = self.get_by_academy_id(db, academy_id)
            if not about or not about.values:
                return None
            
            return about.values.get("statistics")
            
        except Exception as e:
            raise Exception(f"Error retrieving statistics: {str(e)}")


about = CRUDAbout(About) 
 
 
 