from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.db.base import Base


class Chapter(Base):
    """
    Chapter model representing a section/module within a course.
    
    Each chapter belongs to a course and contains multiple lessons.
    Chapters are ordered sequentially to provide structured learning.
    """
    __tablename__ = "chapters"

    # Primary identification
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_id = Column(CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    
    # Chapter information
    title = Column(String(200), nullable=False)
    description = Column(Text)
    order_number = Column(Integer, nullable=False, default=0, index=True)
    is_published = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    course = relationship("Course", back_populates="chapters")
    lessons = relationship(
        "Lesson", 
        back_populates="chapter", 
        cascade="all, delete-orphan",
        order_by="Lesson.order_number"
    )

    def __repr__(self):
        return f"<Chapter(id={self.id}, title='{self.title}', order={self.order_number})>"
    
    @property
    def lessons_count(self) -> int:
        """Get the total number of lessons in this chapter"""
        return len(self.lessons) if self.lessons else 0
    
    @property
    def total_duration_seconds(self) -> int:
        """Calculate total duration of all lessons in this chapter"""
        if not self.lessons:
            return 0
        return sum(lesson.video_duration or 0 for lesson in self.lessons if lesson.video_duration)
    
    @property
    def is_accessible(self) -> bool:
        """Check if chapter is accessible to students"""
        return self.is_published and self.course.is_published 