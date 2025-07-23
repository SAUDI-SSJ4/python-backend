from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.crud.base import CRUDBase
from app.models.template import Template, About, Slider, Faq, Opinion
from app.models.settings import Settings
from app.schemas.template import TemplateCreate, TemplateUpdate
from app.schemas.about import AboutCreate, AboutUpdate
from app.schemas.slider import SliderCreate, SliderUpdate
from app.schemas.faq import FaqCreate, FaqUpdate
from app.schemas.opinion import OpinionCreate, OpinionUpdate
from app.schemas.settings import SettingsCreate, SettingsUpdate


class CRUDAcademyContent:
    """
    Unified CRUD operations for academy content management
    Combines template, about, slider, FAQ, opinion, and settings operations
    """
    
    def __init__(self):
        self.template_crud = CRUDBase[Template, TemplateCreate, TemplateUpdate](Template)
        self.about_crud = CRUDBase[About, AboutCreate, AboutUpdate](About)
        self.slider_crud = CRUDBase[Slider, SliderCreate, SliderUpdate](Slider)
        self.faq_crud = CRUDBase[Faq, FaqCreate, FaqUpdate](Faq)
        self.opinion_crud = CRUDBase[Opinion, OpinionCreate, OpinionUpdate](Opinion)
        self.settings_crud = CRUDBase[Settings, SettingsCreate, SettingsUpdate](Settings)
    
    # Template operations
    def get_template(self, db: Session, academy_id: int) -> Optional[Template]:
        """Get template by academy ID - creates default template if not exists"""
        try:
            template = db.query(Template).filter(Template.academy_id == academy_id).first()
            if not template:
                # Create default template if not exists
                default_template_data = {
                    "academy_id": academy_id,
                    "primary_color": "#007bff",
                    "secondary_color": "#6c757d"
                }
                template = self.template_crud.create(db, obj_in=TemplateCreate(**default_template_data))
            return template
        except Exception as e:
            raise Exception(f"Error retrieving template: {str(e)}")
    
    def create_or_update_template(self, db: Session, academy_id: int, template_data: Dict[str, Any]) -> Template:
        """Create or update template for academy"""
        try:
            existing_template = self.get_template(db, academy_id)
            
            if existing_template:
                return self.template_crud.update(db, db_obj=existing_template, obj_in=template_data)
            else:
                template_data["academy_id"] = academy_id
                return self.template_crud.create(db, obj_in=TemplateCreate(**template_data))
                
        except Exception as e:
            raise Exception(f"Error creating/updating template: {str(e)}")
    
    # About operations
    def get_about(self, db: Session, academy_id: int) -> Optional[About]:
        """Get about information by academy ID - returns None if not exists"""
        try:
            return db.query(About).filter(About.academy_id == academy_id).first()
        except Exception as e:
            raise Exception(f"Error retrieving about information: {str(e)}")
    
    def create_or_update_about(self, db: Session, academy_id: int, about_data: Dict[str, Any]) -> About:
        """Create or update about information for academy"""
        try:
            existing_about = self.get_about(db, academy_id)
            
            if existing_about:
                return self.about_crud.update(db, db_obj=existing_about, obj_in=about_data)
            else:
                about_data["academy_id"] = academy_id
                return self.about_crud.create(db, obj_in=AboutCreate(**about_data))
                
        except Exception as e:
            raise Exception(f"Error creating/updating about information: {str(e)}")
    
    # Slider operations
    def get_sliders(self, db: Session, academy_id: int, skip: int = 0, limit: int = 100) -> List[Slider]:
        """Get all sliders for academy"""
        try:
            return db.query(Slider).filter(
                Slider.academy_id == academy_id
            ).order_by(Slider.order, Slider.id).offset(skip).limit(limit).all()
        except Exception as e:
            raise Exception(f"Error retrieving sliders: {str(e)}")
    
    def get_active_sliders(self, db: Session, academy_id: int) -> List[Slider]:
        """Get active sliders for academy"""
        try:
            return db.query(Slider).filter(
                and_(
                    Slider.academy_id == academy_id,
                    Slider.is_active == True
                )
            ).order_by(Slider.order, Slider.id).all()
        except Exception as e:
            raise Exception(f"Error retrieving active sliders: {str(e)}")
    
    def create_slider(self, db: Session, academy_id: int, slider_data: Dict[str, Any]) -> Slider:
        """Create new slider for academy"""
        try:
            slider_data["academy_id"] = academy_id
            
            if "order" not in slider_data:
                max_order = db.query(Slider).filter(Slider.academy_id == academy_id).order_by(desc(Slider.order)).first()
                slider_data["order"] = (max_order.order + 1) if max_order else 1
            
            return self.slider_crud.create(db, obj_in=SliderCreate(**slider_data))
            
        except Exception as e:
            raise Exception(f"Error creating slider: {str(e)}")
    
    def update_slider(self, db: Session, slider_id: int, academy_id: int, slider_data: Dict[str, Any]) -> Slider:
        """Update slider for academy"""
        try:
            slider = db.query(Slider).filter(
                and_(
                    Slider.id == slider_id,
                    Slider.academy_id == academy_id
                )
            ).first()
            
            if not slider:
                raise Exception("Slider not found")
            
            return self.slider_crud.update(db, db_obj=slider, obj_in=slider_data)
            
        except Exception as e:
            raise Exception(f"Error updating slider: {str(e)}")
    
    def delete_slider(self, db: Session, slider_id: int, academy_id: int) -> bool:
        """Delete slider for academy"""
        try:
            slider = db.query(Slider).filter(
                and_(
                    Slider.id == slider_id,
                    Slider.academy_id == academy_id
                )
            ).first()
            
            if not slider:
                raise Exception("Slider not found")
            
            db.delete(slider)
            db.commit()
            return True
            
        except Exception as e:
            raise Exception(f"Error deleting slider: {str(e)}")
    
    # FAQ operations
    def get_faqs(self, db: Session, academy_id: int, skip: int = 0, limit: int = 100) -> List[Faq]:
        """Get all FAQs for academy"""
        try:
            return db.query(Faq).filter(
                and_(
                    Faq.academy_id == academy_id,
                    Faq.is_active == True
                )
            ).order_by(Faq.order, Faq.id).offset(skip).limit(limit).all()
        except Exception as e:
            raise Exception(f"Error retrieving FAQs: {str(e)}")
    
    def create_faq(self, db: Session, academy_id: int, faq_data: Dict[str, Any]) -> Faq:
        """Create new FAQ for academy"""
        try:
            faq_data["academy_id"] = academy_id
            
            if "order" not in faq_data:
                max_order = db.query(Faq).filter(Faq.academy_id == academy_id).order_by(desc(Faq.order)).first()
                faq_data["order"] = (max_order.order + 1) if max_order else 1
            
            return self.faq_crud.create(db, obj_in=FaqCreate(**faq_data))
            
        except Exception as e:
            raise Exception(f"Error creating FAQ: {str(e)}")
    
    def update_faq(self, db: Session, faq_id: int, academy_id: int, faq_data: Dict[str, Any]) -> Faq:
        """Update FAQ for academy"""
        try:
            faq = db.query(Faq).filter(
                and_(
                    Faq.id == faq_id,
                    Faq.academy_id == academy_id
                )
            ).first()
            
            if not faq:
                raise Exception("FAQ not found")
            
            return self.faq_crud.update(db, db_obj=faq, obj_in=faq_data)
            
        except Exception as e:
            raise Exception(f"Error updating FAQ: {str(e)}")
    
    def delete_faq(self, db: Session, faq_id: int, academy_id: int) -> bool:
        """Delete FAQ for academy (soft delete)"""
        try:
            faq = db.query(Faq).filter(
                and_(
                    Faq.id == faq_id,
                    Faq.academy_id == academy_id
                )
            ).first()
            
            if not faq:
                raise Exception("FAQ not found")
            
            faq.is_active = False
            db.commit()
            return True
            
        except Exception as e:
            raise Exception(f"Error deleting FAQ: {str(e)}")
    
    # Opinion operations
    def get_opinions(self, db: Session, academy_id: int, skip: int = 0, limit: int = 100) -> List[Opinion]:
        """Get all opinions for academy"""
        try:
            return db.query(Opinion).filter(
                Opinion.academy_id == academy_id
            ).order_by(desc(Opinion.created_at)).offset(skip).limit(limit).all()
        except Exception as e:
            raise Exception(f"Error retrieving opinions: {str(e)}")
    
    def get_approved_opinions(self, db: Session, academy_id: int, skip: int = 0, limit: int = 100) -> List[Opinion]:
        """Get approved opinions for academy"""
        try:
            return db.query(Opinion).filter(
                and_(
                    Opinion.academy_id == academy_id,
                    Opinion.is_approved == True
                )
            ).order_by(desc(Opinion.created_at)).offset(skip).limit(limit).all()
        except Exception as e:
            raise Exception(f"Error retrieving approved opinions: {str(e)}")
    
    def create_opinion(self, db: Session, academy_id: int, opinion_data: Dict[str, Any]) -> Opinion:
        """Create new opinion for academy"""
        try:
            opinion_data["academy_id"] = academy_id
            
            if "rating" not in opinion_data:
                opinion_data["rating"] = 5
            if "is_approved" not in opinion_data:
                opinion_data["is_approved"] = False
            if "is_featured" not in opinion_data:
                opinion_data["is_featured"] = False
            
            return self.opinion_crud.create(db, obj_in=OpinionCreate(**opinion_data))
            
        except Exception as e:
            raise Exception(f"Error creating opinion: {str(e)}")
    
    def approve_opinion(self, db: Session, opinion_id: int, academy_id: int) -> Opinion:
        """Approve opinion for academy"""
        try:
            opinion = db.query(Opinion).filter(
                and_(
                    Opinion.id == opinion_id,
                    Opinion.academy_id == academy_id
                )
            ).first()
            
            if not opinion:
                raise Exception("Opinion not found")
            
            opinion.is_approved = True
            db.commit()
            db.refresh(opinion)
            return opinion
            
        except Exception as e:
            raise Exception(f"Error approving opinion: {str(e)}")
    
    def delete_opinion(self, db: Session, opinion_id: int, academy_id: int) -> bool:
        """Delete opinion for academy"""
        try:
            opinion = db.query(Opinion).filter(
                and_(
                    Opinion.id == opinion_id,
                    Opinion.academy_id == academy_id
                )
            ).first()
            
            if not opinion:
                raise Exception("Opinion not found")
            
            db.delete(opinion)
            db.commit()
            return True
            
        except Exception as e:
            raise Exception(f"Error deleting opinion: {str(e)}")
    
    # Settings operations
    def get_settings(self, db: Session) -> Optional[Settings]:
        """Get current platform settings - creates default settings if not exists"""
        try:
            settings = db.query(Settings).first()
            if not settings:
                # Create default settings if not exists
                default_settings_data = {
                    "title": "SAYAN Academy Platform",
                    "email": "contact@sayan.academy",
                    "phone": "+966501234567",
                    "address": "Riyadh, Saudi Arabia"
                }
                settings = self.settings_crud.create(db, obj_in=SettingsCreate(**default_settings_data))
            return settings
        except Exception as e:
            raise Exception(f"Error retrieving settings: {str(e)}")
    
    def create_or_update_settings(self, db: Session, settings_data: Dict[str, Any]) -> Settings:
        """Create or update platform settings"""
        try:
            existing_settings = self.get_settings(db)
            
            if existing_settings:
                return self.settings_crud.update(db, db_obj=existing_settings, obj_in=settings_data)
            else:
                return self.settings_crud.create(db, obj_in=SettingsCreate(**settings_data))
                
        except Exception as e:
            raise Exception(f"Error creating/updating settings: {str(e)}")
    
    def get_academy_content_summary(self, db: Session, academy_id: int) -> Dict[str, Any]:
        """Get summary of all academy content"""
        try:
            template = self.get_template(db, academy_id)
            about = self.get_about(db, academy_id)
            sliders_count = db.query(Slider).filter(Slider.academy_id == academy_id).count()
            faqs_count = db.query(Faq).filter(
                and_(
                    Faq.academy_id == academy_id,
                    Faq.is_active == True
                )
            ).count()
            opinions_count = db.query(Opinion).filter(
                and_(
                    Opinion.academy_id == academy_id,
                    Opinion.is_approved == True
                )
            ).count()

            return {
                "academy_id": academy_id,
                "has_template": template is not None,
                "has_about": about is not None,
                "sliders_count": sliders_count,
                "faqs_count": faqs_count,
                "opinions_count": opinions_count
            }

        except Exception as e:
            raise Exception(f"Error getting academy content summary: {str(e)}")
    
    def get_sliders_count(self, db: Session, academy_id: int) -> int:
        """Get count of sliders for academy"""
        try:
            return db.query(Slider).filter(Slider.academy_id == academy_id).count()
        except Exception as e:
            raise Exception(f"Error getting sliders count: {str(e)}")
    
    def get_faqs_count(self, db: Session, academy_id: int) -> int:
        """Get count of active FAQs for academy"""
        try:
            return db.query(Faq).filter(
                and_(
                    Faq.academy_id == academy_id,
                    Faq.is_active == True
                )
            ).count()
        except Exception as e:
            raise Exception(f"Error getting FAQs count: {str(e)}")
    
    def get_opinions_count(self, db: Session, academy_id: int) -> int:
        """Get count of approved opinions for academy"""
        try:
            return db.query(Opinion).filter(
                and_(
                    Opinion.academy_id == academy_id,
                    Opinion.is_approved == True
                )
            ).count()
        except Exception as e:
            raise Exception(f"Error getting opinions count: {str(e)}")
    
    def get_active_sliders(self, db: Session, academy_id: int, limit: int = 10) -> List[Slider]:
        """Get active sliders for academy"""
        try:
            return db.query(Slider).filter(
                and_(
                    Slider.academy_id == academy_id,
                    Slider.is_active == True
                )
            ).order_by(Slider.order).limit(limit).all()
        except Exception as e:
            raise Exception(f"Error getting active sliders: {str(e)}")
    
    def get_active_faqs(self, db: Session, academy_id: int, limit: int = 10) -> List[Faq]:
        """Get active FAQs for academy"""
        try:
            return db.query(Faq).filter(
                and_(
                    Faq.academy_id == academy_id,
                    Faq.is_active == True
                )
            ).order_by(Faq.order).limit(limit).all()
        except Exception as e:
            raise Exception(f"Error getting active FAQs: {str(e)}")
    
    def get_approved_opinions(self, db: Session, academy_id: int, limit: int = 10) -> List[Opinion]:
        """Get approved opinions for academy"""
        try:
            return db.query(Opinion).filter(
                and_(
                    Opinion.academy_id == academy_id,
                    Opinion.is_approved == True
                )
            ).order_by(desc(Opinion.created_at)).limit(limit).all()
        except Exception as e:
            raise Exception(f"Error getting approved opinions: {str(e)}")


academy_content = CRUDAcademyContent() 
 
 
 