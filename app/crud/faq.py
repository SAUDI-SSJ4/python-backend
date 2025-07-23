from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.crud.base import CRUDBase
from app.models.template import Faq
from app.schemas.faq import FaqCreate, FaqUpdate


class CRUDFaq(CRUDBase[Faq, FaqCreate, FaqUpdate]):
    """
    CRUD operations for FAQ model
    Handles frequently asked questions for academies
    """
    
    def get_by_academy_id(self, db: Session, academy_id: int, skip: int = 0, limit: int = 100) -> List[Faq]:
        """Get all FAQs for a specific academy"""
        try:
            return db.query(Faq).filter(
                and_(
                    Faq.academy_id == academy_id,
                    Faq.is_active == True
                )
            ).order_by(Faq.order, Faq.id).offset(skip).limit(limit).all()
        except Exception as e:
            raise Exception(f"Error retrieving FAQs: {str(e)}")
    
    def get_active_faqs(self, db: Session, academy_id: int) -> List[Faq]:
        """Get all active FAQs for academy"""
        try:
            return db.query(Faq).filter(
                and_(
                    Faq.academy_id == academy_id,
                    Faq.is_active == True
                )
            ).order_by(Faq.order, Faq.id).all()
        except Exception as e:
            raise Exception(f"Error retrieving active FAQs: {str(e)}")
    
    def get_by_category(self, db: Session, academy_id: int, category: str) -> List[Faq]:
        """Get FAQs by category for academy"""
        try:
            return db.query(Faq).filter(
                and_(
                    Faq.academy_id == academy_id,
                    Faq.category == category,
                    Faq.is_active == True
                )
            ).order_by(Faq.order, Faq.id).all()
        except Exception as e:
            raise Exception(f"Error retrieving FAQs by category: {str(e)}")
    
    def search_faqs(self, db: Session, academy_id: int, search_term: str) -> List[Faq]:
        """Search FAQs by question or answer content"""
        try:
            search_pattern = f"%{search_term}%"
            return db.query(Faq).filter(
                and_(
                    Faq.academy_id == academy_id,
                    Faq.is_active == True,
                    (Faq.question.ilike(search_pattern) | Faq.answer.ilike(search_pattern))
                )
            ).order_by(Faq.order, Faq.id).all()
        except Exception as e:
            raise Exception(f"Error searching FAQs: {str(e)}")
    
    def create_faq(self, db: Session, academy_id: int, faq_data: Dict[str, Any]) -> Faq:
        """Create new FAQ for academy"""
        try:
            faq_data["academy_id"] = academy_id
            
            # Set order if not provided
            if "order" not in faq_data:
                max_order = db.query(Faq).filter(Faq.academy_id == academy_id).order_by(desc(Faq.order)).first()
                faq_data["order"] = (max_order.order + 1) if max_order else 1
            
            return self.create(db, obj_in=FaqCreate(**faq_data))
            
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
            
            return self.update(db, db_obj=faq, obj_in=faq_data)
            
        except Exception as e:
            raise Exception(f"Error updating FAQ: {str(e)}")
    
    def delete_faq(self, db: Session, faq_id: int, academy_id: int) -> bool:
        """Delete FAQ for academy (soft delete by setting is_active to False)"""
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
    
    def reorder_faqs(self, db: Session, academy_id: int, faq_orders: List[Dict[str, int]]) -> bool:
        """Reorder FAQs for academy"""
        try:
            for item in faq_orders:
                faq_id = item.get("faq_id")
                new_order = item.get("order")
                
                if faq_id and new_order is not None:
                    faq = db.query(Faq).filter(
                        and_(
                            Faq.id == faq_id,
                            Faq.academy_id == academy_id
                        )
                    ).first()
                    
                    if faq:
                        faq.order = new_order
            
            db.commit()
            return True
            
        except Exception as e:
            raise Exception(f"Error reordering FAQs: {str(e)}")
    
    def get_categories(self, db: Session, academy_id: int) -> List[str]:
        """Get all FAQ categories for academy"""
        try:
            categories = db.query(Faq.category).filter(
                and_(
                    Faq.academy_id == academy_id,
                    Faq.is_active == True,
                    Faq.category.isnot(None)
                )
            ).distinct().all()
            
            return [cat[0] for cat in categories if cat[0]]
            
        except Exception as e:
            raise Exception(f"Error retrieving FAQ categories: {str(e)}")


faq = CRUDFaq(Faq) 
 
 
 