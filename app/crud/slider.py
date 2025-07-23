from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.crud.base import CRUDBase
from app.models.template import Slider
from app.schemas.slider import SliderCreate, SliderUpdate


class CRUDSlider(CRUDBase[Slider, SliderCreate, SliderUpdate]):
    """
    CRUD operations for Slider model
    Handles academy slider management for homepage banners
    """
    
    def get_by_academy_id(self, db: Session, academy_id: int, skip: int = 0, limit: int = 100) -> List[Slider]:
        """Get all sliders for a specific academy"""
        try:
            return db.query(Slider).filter(
                Slider.academy_id == academy_id
            ).order_by(Slider.order, Slider.id).offset(skip).limit(limit).all()
        except Exception as e:
            raise Exception(f"Error retrieving sliders: {str(e)}")
    
    def get_active_sliders(self, db: Session, academy_id: int) -> List[Slider]:
        """Get all active sliders for academy"""
        try:
            return db.query(Slider).filter(
                and_(
                    Slider.academy_id == academy_id,
                    Slider.is_active == True
                )
            ).order_by(Slider.order, Slider.id).all()
        except Exception as e:
            raise Exception(f"Error retrieving active sliders: {str(e)}")
    
    def get_featured_sliders(self, db: Session, academy_id: int, limit: int = 5) -> List[Slider]:
        """Get featured sliders for academy homepage"""
        try:
            return db.query(Slider).filter(
                and_(
                    Slider.academy_id == academy_id,
                    Slider.is_active == True
                )
            ).order_by(Slider.order, Slider.id).limit(limit).all()
        except Exception as e:
            raise Exception(f"Error retrieving featured sliders: {str(e)}")
    
    def create_slider(self, db: Session, academy_id: int, slider_data: Dict[str, Any]) -> Slider:
        """Create new slider for academy"""
        try:
            slider_data["academy_id"] = academy_id
            
            # Set order if not provided
            if "order" not in slider_data:
                max_order = db.query(Slider).filter(Slider.academy_id == academy_id).order_by(desc(Slider.order)).first()
                slider_data["order"] = (max_order.order + 1) if max_order else 1
            
            # Set default values
            if "is_active" not in slider_data:
                slider_data["is_active"] = True
            
            return self.create(db, obj_in=SliderCreate(**slider_data))
            
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
            
            return self.update(db, db_obj=slider, obj_in=slider_data)
            
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
    
    def toggle_slider_status(self, db: Session, slider_id: int, academy_id: int) -> Slider:
        """Toggle slider active status"""
        try:
            slider = db.query(Slider).filter(
                and_(
                    Slider.id == slider_id,
                    Slider.academy_id == academy_id
                )
            ).first()
            
            if not slider:
                raise Exception("Slider not found")
            
            slider.is_active = not slider.is_active
            db.commit()
            db.refresh(slider)
            return slider
            
        except Exception as e:
            raise Exception(f"Error toggling slider status: {str(e)}")
    
    def reorder_sliders(self, db: Session, academy_id: int, slider_orders: List[Dict[str, int]]) -> bool:
        """Reorder sliders for academy"""
        try:
            for item in slider_orders:
                slider_id = item.get("slider_id")
                new_order = item.get("order")
                
                if slider_id and new_order is not None:
                    slider = db.query(Slider).filter(
                        and_(
                            Slider.id == slider_id,
                            Slider.academy_id == academy_id
                        )
                    ).first()
                    
                    if slider:
                        slider.order = new_order
            
            db.commit()
            return True
            
        except Exception as e:
            raise Exception(f"Error reordering sliders: {str(e)}")
    
    def update_slider_image(self, db: Session, slider_id: int, academy_id: int, image_path: str) -> Slider:
        """Update slider image"""
        try:
            slider = db.query(Slider).filter(
                and_(
                    Slider.id == slider_id,
                    Slider.academy_id == academy_id
                )
            ).first()
            
            if not slider:
                raise Exception("Slider not found")
            
            slider.image = image_path
            db.commit()
            db.refresh(slider)
            return slider
            
        except Exception as e:
            raise Exception(f"Error updating slider image: {str(e)}")
    
    def get_slider_by_order(self, db: Session, academy_id: int, order: int) -> Optional[Slider]:
        """Get slider by specific order for academy"""
        try:
            return db.query(Slider).filter(
                and_(
                    Slider.academy_id == academy_id,
                    Slider.order == order,
                    Slider.is_active == True
                )
            ).first()
        except Exception as e:
            raise Exception(f"Error retrieving slider by order: {str(e)}")
    
    def get_slider_count(self, db: Session, academy_id: int) -> int:
        """Get total number of sliders for academy"""
        try:
            return db.query(Slider).filter(Slider.academy_id == academy_id).count()
        except Exception as e:
            raise Exception(f"Error counting sliders: {str(e)}")


slider = CRUDSlider(Slider) 
 
 
 