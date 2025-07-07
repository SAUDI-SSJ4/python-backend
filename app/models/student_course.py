"""
Student Course relationship model for tracking course enrollments.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class StudentCourse(Base):
    """
    Model for tracking student course enrollments and progress.
    
    This model represents the many-to-many relationship between students and courses,
    with additional metadata about enrollment status, progress, and timestamps.
    """
    
    __tablename__ = "student_courses"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    
    # Enrollment status: active, suspended, completed, cancelled
    status = Column(String(20), default="active", nullable=False, index=True)
    
    # Progress tracking
    progress_percentage = Column(Numeric(5, 2), default=0.00, nullable=False)
    completed_lessons = Column(Integer, default=0, nullable=False)
    total_lessons = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)  # When first lesson was accessed
    completed_at = Column(DateTime, nullable=True)  # When course was completed
    last_accessed_at = Column(DateTime, nullable=True)  # Last activity
    
    # Payment and pricing info
    paid_amount = Column(Numeric(10, 2), nullable=True)
    discount_applied = Column(Numeric(10, 2), nullable=True)
    payment_method = Column(String(50), nullable=True)
    
    # Certificate info
    certificate_issued = Column(Boolean, default=False, nullable=False)
    certificate_issued_at = Column(DateTime, nullable=True)
    
    # Notes and feedback
    notes = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # Student rating for the course (1-5)
    review = Column(Text, nullable=True)
    
    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    student = relationship("Student", back_populates="course_enrollments")
    course = relationship("Course", back_populates="student_enrollments")
    
    def __repr__(self):
        return f"<StudentCourse(student_id={self.student_id}, course_id={self.course_id}, status='{self.status}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if enrollment is active"""
        return self.status == "active" and self.deleted_at is None
    
    @property
    def is_completed(self) -> bool:
        """Check if course is completed"""
        return self.status == "completed" or self.progress_percentage >= 100
    
    @property
    def completion_percentage(self) -> float:
        """Get completion percentage as float"""
        return float(self.progress_percentage) if self.progress_percentage else 0.0
    
    def update_progress(self, completed_lessons: int, total_lessons: int) -> None:
        """Update progress tracking"""
        self.completed_lessons = completed_lessons
        self.total_lessons = total_lessons
        
        if total_lessons > 0:
            self.progress_percentage = (completed_lessons / total_lessons) * 100
            
            # Mark as completed if 100%
            if self.progress_percentage >= 100 and self.status == "active":
                self.status = "completed"
                self.completed_at = datetime.utcnow()
        
        # Update last accessed timestamp
        self.last_accessed_at = datetime.utcnow()
        
        # Set started timestamp if first lesson
        if completed_lessons > 0 and not self.started_at:
            self.started_at = datetime.utcnow() 