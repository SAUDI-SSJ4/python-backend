from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class Video(Base):
    """
    Video model for storing video content associated with lessons.
    
    Supports various video sources and provides streaming capabilities
    with security features for protected content delivery.
    """
    __tablename__ = "videos"

    # Primary identification
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    
    # Video information
    title = Column(String(255))
    description = Column(Text)
    video = Column(String(255))  # Video file path or URL
    order_number = Column(Integer, default=0, index=True)
    status = Column(Boolean, default=True, nullable=False)
    duration = Column(Integer, default=0)  # Duration in seconds
    
    # Timestamps and soft delete
    deleted_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    lesson = relationship("Lesson", back_populates="videos")

    def __repr__(self):
        return f"<Video(id={self.id}, title='{self.title}', lesson_id='{self.lesson_id}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if video is active (not soft deleted)"""
        return self.deleted_at is None and self.status
    
    @property
    def stream_url(self) -> str:
        """Generate secure streaming URL for video"""
        # This will be implemented with JWT tokens for security
        return f"/api/v1/videos/{self.id}/stream"
    
    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string"""
        if not self.duration:
            return "0:00"
        
        minutes = self.duration // 60
        seconds = self.duration % 60
        hours = minutes // 60
        minutes = minutes % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}" 