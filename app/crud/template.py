from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.template import Template
from app.schemas.template import TemplateCreate, TemplateUpdate


class CRUDTemplate(CRUDBase[Template, TemplateCreate, TemplateUpdate]):
    def get_by_academy_id(self, db: Session, academy_id: int) -> Optional[Template]:
        """Get template by academy ID"""
        return db.query(Template).filter(Template.academy_id == academy_id).first()
    
    def create_or_update(self, db: Session, academy_id: int, template_data: dict) -> Template:
        """Create or update template for academy"""
        existing_template = self.get_by_academy_id(db, academy_id)
        
        if existing_template:
            return self.update(db, db_obj=existing_template, obj_in=template_data)
        else:
            template_data["academy_id"] = academy_id
            return self.create(db, obj_in=TemplateCreate(**template_data))


template = CRUDTemplate(Template) 