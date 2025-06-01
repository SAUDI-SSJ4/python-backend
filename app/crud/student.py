from typing import Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.student import Student
from app.schemas.auth import StudentRegister
from app.core.security import get_password_hash, verify_password


class CRUDStudent(CRUDBase[Student, StudentRegister, dict]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[Student]:
        """Get student by email."""
        return db.query(Student).filter(Student.email == email).first()
    
    def get_by_phone(self, db: Session, *, phone: str) -> Optional[Student]:
        """Get student by phone."""
        return db.query(Student).filter(Student.phone == phone).first()
    
    def create(self, db: Session, *, obj_in: StudentRegister) -> Student:
        """Create new student."""
        db_obj = Student(
            name=obj_in.name,
            email=obj_in.email,
            phone=obj_in.phone,
            hashed_password=get_password_hash(obj_in.password),
            date_of_birth=obj_in.date_of_birth,
            gender=obj_in.gender,
            country=obj_in.country,
            city=obj_in.city
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[Student]:
        """Authenticate student by email and password."""
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def authenticate_by_phone(self, db: Session, *, phone: str, password: str) -> Optional[Student]:
        """Authenticate student by phone and password."""
        user = self.get_by_phone(db, phone=phone)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def is_active(self, user: Student) -> bool:
        """Check if student is active."""
        return user.status == "active"
    
    def update_password(self, db: Session, *, db_obj: Student, new_password: str) -> Student:
        """Update student password."""
        hashed_password = get_password_hash(new_password)
        db_obj.hashed_password = hashed_password
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


student = CRUDStudent(Student) 