from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class LessonProgress(Base):
    """
    Lesson progress model for tracking student completion and progress through lessons.
    
    This model tracks video watch time, completion status, and learning analytics
    to provide insights into student engagement and course effectiveness.
    """
    __tablename__ = "lesson_progress"

    # Primary identification
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    
    # Progress tracking
    progress_percentage = Column(Integer, default=0, nullable=False)  # 0-100
    completed = Column(Boolean, default=False, nullable=False, index=True)
    current_position_seconds = Column(Integer, default=0)  # Current video position
    last_watched_at = Column(DateTime)  # Last time student accessed this lesson
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships - معلق مؤقتاً لحل conflicts
    # student = relationship("Student", back_populates="lesson_progress")
    # lesson = relationship("Lesson", back_populates="lesson_progress")
    course = relationship("Course")  # No back_populates to avoid circular reference

    # Unique constraint handled at database level
    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<LessonProgress(student_id={self.student_id}, lesson_id='{self.lesson_id}', progress={self.progress_percentage}%)>"
    
    @property
    def is_completed(self) -> bool:
        """Check if lesson is marked as completed"""
        return self.completed
    
    @property
    def is_started(self) -> bool:
        """Check if student has started the lesson"""
        return self.progress_percentage > 0 or self.current_position_seconds > 0
    
    @property
    def completion_status(self) -> str:
        """Get human-readable completion status"""
        if self.completed:
            return "Completed"
        elif self.is_started:
            return f"In Progress ({self.progress_percentage}%)"
        else:
            return "Not Started"
    
    def mark_completed(self):
        """Mark lesson as completed with 100% progress"""
        self.completed = True
        self.progress_percentage = 100
        self.last_watched_at = func.now()
    
    def update_progress(self, progress_percentage: int, current_position: int = None):
        """Update lesson progress with validation"""
        # Ensure progress is within valid range
        self.progress_percentage = max(0, min(100, progress_percentage))
        
        if current_position is not None:
            self.current_position_seconds = max(0, current_position)
        
        # Auto-complete if progress reaches 100%
        if self.progress_percentage >= 100:
            self.completed = True
        
        self.last_watched_at = func.now() 