from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.db.base import Base


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class StudentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    birth_date = Column(Date, nullable=True)
    gender = Column(SQLEnum(Gender), default="male")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="student_profile")
    # course_enrollments = relationship("StudentCourse", back_populates="student", lazy="dynamic")
    
    # Temporarily disabled relationships until models are properly defined
    # payments = relationship("Payment", back_populates="student")
    # finance = relationship("StudentFinance", back_populates="student", uselist=False)
    # student_products = relationship("StudentProduct", back_populates="student")
    # student_digital_products = relationship("StudentDigitalProduct", back_populates="student")
    # digital_product_ratings = relationship("DigitalProductRating", back_populates="student")
    # blog_comments = relationship("BlogComment", back_populates="student")
    # answers = relationship("Answer", back_populates="student")
    # rates = relationship("Rate", back_populates="student")
    # student_courses = relationship("StudentCourse", back_populates="student")
    # lesson_progress = relationship("StudentLessonProgress", back_populates="student")
    # favourites = relationship("Favourite", back_populates="student")
   
    def __repr__(self):
        return f"<Student(id={self.id}, user_id={self.user_id})>"
   