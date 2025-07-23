from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.crud.base import CRUDBase
from app.models.template import Opinion
from app.schemas.opinion import OpinionCreate, OpinionUpdate


class CRUDOpinion(CRUDBase[Opinion, OpinionCreate, OpinionUpdate]):
    """
    CRUD operations for Opinion model
    Handles student opinions and reviews for academies
    """
    
    def get_by_academy_id(self, db: Session, academy_id: int, skip: int = 0, limit: int = 100) -> List[Opinion]:
        """Get all opinions for a specific academy"""
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
    
    def get_featured_opinions(self, db: Session, academy_id: int, limit: int = 10) -> List[Opinion]:
        """Get featured opinions for academy"""
        try:
            return db.query(Opinion).filter(
                and_(
                    Opinion.academy_id == academy_id,
                    Opinion.is_approved == True,
                    Opinion.is_featured == True
                )
            ).order_by(desc(Opinion.created_at)).limit(limit).all()
        except Exception as e:
            raise Exception(f"Error retrieving featured opinions: {str(e)}")
    
    def get_by_student_id(self, db: Session, student_id: int, academy_id: int) -> List[Opinion]:
        """Get opinions by student for academy"""
        try:
            return db.query(Opinion).filter(
                and_(
                    Opinion.student_id == student_id,
                    Opinion.academy_id == academy_id
                )
            ).order_by(desc(Opinion.created_at)).all()
        except Exception as e:
            raise Exception(f"Error retrieving student opinions: {str(e)}")
    
    def search_opinions(self, db: Session, academy_id: int, search_term: str) -> List[Opinion]:
        """Search opinions by student name or content"""
        try:
            search_pattern = f"%{search_term}%"
            return db.query(Opinion).filter(
                and_(
                    Opinion.academy_id == academy_id,
                    (Opinion.name.ilike(search_pattern) | Opinion.content.ilike(search_pattern))
                )
            ).order_by(desc(Opinion.created_at)).all()
        except Exception as e:
            raise Exception(f"Error searching opinions: {str(e)}")
    
    def get_by_rating(self, db: Session, academy_id: int, rating: int) -> List[Opinion]:
        """Get opinions by specific rating"""
        try:
            return db.query(Opinion).filter(
                and_(
                    Opinion.academy_id == academy_id,
                    Opinion.rating == rating,
                    Opinion.is_approved == True
                )
            ).order_by(desc(Opinion.created_at)).all()
        except Exception as e:
            raise Exception(f"Error retrieving opinions by rating: {str(e)}")
    
    def create_opinion(self, db: Session, academy_id: int, opinion_data: Dict[str, Any]) -> Opinion:
        """Create new opinion for academy"""
        try:
            opinion_data["academy_id"] = academy_id
            
            # Set default values
            if "rating" not in opinion_data:
                opinion_data["rating"] = 5
            if "is_approved" not in opinion_data:
                opinion_data["is_approved"] = False
            if "is_featured" not in opinion_data:
                opinion_data["is_featured"] = False
            
            return self.create(db, obj_in=OpinionCreate(**opinion_data))
            
        except Exception as e:
            raise Exception(f"Error creating opinion: {str(e)}")
    
    def update_opinion(self, db: Session, opinion_id: int, academy_id: int, opinion_data: Dict[str, Any]) -> Opinion:
        """Update opinion for academy"""
        try:
            opinion = db.query(Opinion).filter(
                and_(
                    Opinion.id == opinion_id,
                    Opinion.academy_id == academy_id
                )
            ).first()
            
            if not opinion:
                raise Exception("Opinion not found")
            
            return self.update(db, db_obj=opinion, obj_in=opinion_data)
            
        except Exception as e:
            raise Exception(f"Error updating opinion: {str(e)}")
    
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
    
    def feature_opinion(self, db: Session, opinion_id: int, academy_id: int, featured: bool = True) -> Opinion:
        """Feature or unfeature opinion for academy"""
        try:
            opinion = db.query(Opinion).filter(
                and_(
                    Opinion.id == opinion_id,
                    Opinion.academy_id == academy_id
                )
            ).first()
            
            if not opinion:
                raise Exception("Opinion not found")
            
            opinion.is_featured = featured
            db.commit()
            db.refresh(opinion)
            return opinion
            
        except Exception as e:
            raise Exception(f"Error featuring opinion: {str(e)}")
    
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
    
    def get_rating_stats(self, db: Session, academy_id: int) -> Dict[str, Any]:
        """Get rating statistics for academy"""
        try:
            opinions = db.query(Opinion).filter(
                and_(
                    Opinion.academy_id == academy_id,
                    Opinion.is_approved == True
                )
            ).all()
            
            if not opinions:
                return {
                    "total_opinions": 0,
                    "average_rating": 0,
                    "rating_distribution": {}
                }
            
            total_opinions = len(opinions)
            total_rating = sum(op.rating for op in opinions)
            average_rating = total_rating / total_opinions
            
            # Calculate rating distribution
            rating_distribution = {}
            for i in range(1, 6):
                count = len([op for op in opinions if op.rating == i])
                rating_distribution[f"{i}_star"] = count
            
            return {
                "total_opinions": total_opinions,
                "average_rating": round(average_rating, 2),
                "rating_distribution": rating_distribution
            }
            
        except Exception as e:
            raise Exception(f"Error calculating rating stats: {str(e)}")


opinion = CRUDOpinion(Opinion) 
 
 
 