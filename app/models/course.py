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
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CourseType(str, enum.Enum):
    """Course delivery type enumeration"""
    LIVE = "live"          # Live streaming course
    RECORDED = "recorded"   # Pre-recorded video course
    ATTEND = "attend"      # In-person attendance required


class CourseLevel(str, enum.Enum):
    """Course difficulty level enumeration"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True)
    description = Column(Text, nullable=True)
    image = Column(String(255), nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    parent = relationship("Category", remote_side=[id])
    children = relationship("Category", back_populates="parent")
    courses = relationship("Course", back_populates="category")


class Course(Base):
    """
    Course model representing a complete learning course within an academy.
    
    A course belongs to an academy and category, contains multiple chapters,
    and can have various types (live, recorded, attend).
    """
    __tablename__ = "courses"

    # Primary identification
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Basic course information
    title = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    image = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    short_content = Column(Text, nullable=False)
    
    # Course details and requirements
    preparations = Column(Text)  # What students need to prepare
    requirements = Column(Text)  # Prerequisites for the course
    learning_outcomes = Column(Text)  # What students will learn
    
    # Media and preview content
    gallery = Column(JSON)  # JSON array of gallery images
    preview_video = Column(String(255))  # Preview/trailer video
    
    # Course configuration
    status = Column(SQLEnum(CourseStatus), default=CourseStatus.DRAFT, nullable=False, index=True)
    featured = Column(Boolean, default=False, index=True)
    type = Column(SQLEnum(CourseType), default=CourseType.RECORDED, nullable=False, index=True)
    url = Column(String(255))  # External URL for live courses
    level = Column(SQLEnum(CourseLevel), default=CourseLevel.BEGINNER, nullable=False, index=True)
    
    # Pricing and financial
    price = Column(Numeric(10, 2), default=0.00, nullable=False, index=True)
    discount_price = Column(Numeric(10, 2))
    discount_ends_at = Column(DateTime)
    platform_fee_percentage = Column(Numeric(5, 2), default=0.00, nullable=False)
    
    # Statistics and metrics
    avg_rating = Column(Numeric(3, 2), default=0.00, nullable=False)
    ratings_count = Column(Integer, default=0, nullable=False)
    students_count = Column(Integer, default=0, nullable=False)
    lessons_count = Column(Integer, default=0, nullable=False)
    duration_seconds = Column(Integer, default=0, nullable=False)
    completion_rate = Column(Numeric(5, 2), default=0.00, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships - معلق مؤقتاً لحل conflicts
    # academy = relationship("Academy", back_populates="courses")
    category = relationship("Category", back_populates="courses")
    chapters = relationship("Chapter", back_populates="course", cascade="all, delete-orphan", order_by="Chapter.order_number")
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")
    # student_enrollments = relationship("StudentCourse", back_populates="course")

    def __repr__(self):
        return f"<Course(id={self.id}, title='{self.title}', status='{self.status}')>"
    
    @property
    def is_published(self) -> bool:
        """Check if the course is published and available to students"""
        return self.status == CourseStatus.PUBLISHED
    
    @property
    def is_free(self) -> bool:
        """Check if the course is free"""
        return self.price <= 0
    
    @property
    def current_price(self) -> Decimal:
        """Get current effective price (considering discounts)"""
        if self.discount_price and self.discount_ends_at:
            from datetime import datetime
            if datetime.utcnow() < self.discount_ends_at:
                return self.discount_price
        return self.price
    
    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string"""
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"



 