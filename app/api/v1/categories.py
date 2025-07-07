from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.deps.database import get_db
from app.models.course import Category
from app.core.response_handler import SayanSuccessResponse

router = APIRouter()

@router.get("/categories", tags=["Categories"])
def get_all_categories(request: Request, db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    categories_data = [
        {
            "id": c.id,
            "title": c.title,
            "slug": c.slug,
            "content": c.content,
            "image": c.image,
            "parent_id": c.parent_id,
            "status": c.status,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        for c in categories
    ]
    return SayanSuccessResponse(
        request=request,
        data=categories_data,
        message="تم جلب التصنيفات بنجاح"
    ) 