from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum, JSON, CHAR
from sqlalchemy.types import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from decimal import Decimal
import enum
import uuid


class CourseStatus(str, enum.Enum):
    """Course status enumeration for clear status management"""
    draft = "draft"
    ready = "ready" 
    published = "published"
    archived = "archived"


class CourseType(str, enum.Enum):
    """Course delivery type enumeration"""
    live = "live"          # Live streaming course
    recorded = "recorded"   # Pre-recorded video course
    attend = "attend"      # In-person attendance required


class CourseLevel(str, enum.Enum):
    """Course difficulty level enumeration"""
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True)
    content = Column(Text, nullable=True)
    image = Column(String(255), nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    status = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    parent = relationship("Category", remote_side=[id])
    children = relationship("Category", back_populates="parent")
    courses = relationship("Course", back_populates="category")


class Course(Base):
    """
    Course model - contains only course-specific fields
    Title, price, description are stored in related Product model
    """
    __tablename__ = "courses"

    # Primary fields that match database schema exactly
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Course-specific fields
    slug = Column(String(255), nullable=False, unique=True, index=True)
    image = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    short_content = Column(Text, nullable=False)
    preparations = Column(Text)
    requirements = Column(Text)
    learning_outcomes = Column(Text)
    gallery = Column(JSON)
    preview_video = Column(String(255))
    
    # Course configuration
    course_state = Column(SQLEnum(CourseStatus), default=CourseStatus.draft, nullable=False, index=True)
    featured = Column(Boolean, default=False, index=True)
    type = Column(SQLEnum(CourseType), default=CourseType.recorded, nullable=False, index=True)
    url = Column(String(255))
    level = Column(SQLEnum(CourseLevel), default=CourseLevel.beginner, nullable=False, index=True)
    
    # Platform-specific fields
    platform_fee_percentage = Column(Numeric(5, 2), default=0.00, nullable=False)
    
    # Statistics
    avg_rating = Column(Numeric(3, 2), default=0.00, nullable=False)
    ratings_count = Column(Integer, default=0, nullable=False)
    students_count = Column(Integer, default=0, nullable=False)
    lessons_count = Column(Integer, default=0, nullable=False)
    completion_rate = Column(Numeric(5, 2), default=0.00, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    product = relationship("Product", back_populates="courses")
    category = relationship("Category", back_populates="courses")
    academy = relationship("Academy")
    trainer = relationship("User", foreign_keys=[trainer_id])
    chapters = relationship("Chapter", back_populates="course", cascade="all, delete-orphan", lazy="dynamic")
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")
    student_enrollments = relationship("StudentCourse", back_populates="course")
    
    # AI Assistant relationships
    ai_exam_templates = relationship("AIExamTemplate", back_populates="course", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Course(id={self.id}, course_state='{self.course_state}')>"
    
    @property
    def is_published(self) -> bool:
        """Check if the course is published and available to students"""
        return self.course_state == CourseStatus.published
    
    @property
    def is_free(self) -> bool:
        """Check if the course is free"""
        if self.product:
            return self.product.price <= 0
        return True
    
    @property
    def current_price(self) -> Decimal:
        """Get current effective price (considering discounts)"""
        if not self.product:
            return Decimal('0.00')
            
        if self.product.discount_price and self.product.discount_ends_at:
            from datetime import datetime
            if datetime.utcnow() < self.product.discount_ends_at:
                return self.product.discount_price
        return self.product.price
    
    @property
    def duration_seconds(self):
        """Compute total duration of all lessons in seconds."""
        total = 0
        for chapter in getattr(self, 'chapters', []) or []:
            for lesson in getattr(chapter, 'lessons', []) or []:
                if lesson.duration_seconds:
                    total += lesson.duration_seconds
        return total

    @property
    def duration_formatted(self):
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        return f"{hours}h {minutes}m" if hours else f"{minutes}m"



 