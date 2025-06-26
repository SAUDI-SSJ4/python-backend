from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.db.base import Base
import enum
import uuid


class LessonType(str, enum.Enum):
    """Lesson content type enumeration"""
    VIDEO = "video"         # Video-based lesson
    EXAM = "exam"          # Quiz/examination lesson
    TOOL = "tool"          # Interactive tool lesson
    TEXT = "text"          # Text/document-based lesson


class VideoType(str, enum.Enum):
    """Video source type enumeration"""
    UPLOAD = "upload"      # Uploaded video file
    EMBED = "embed"        # Embedded video (iframe)
    YOUTUBE = "youtube"    # YouTube video
    VIMEO = "vimeo"       # Vimeo video


class Lesson(Base):
    """
    Lesson model representing individual learning units within a chapter.
    
    Lessons can contain different types of content: videos, exams, interactive tools, or text.
    Each lesson belongs to a chapter and course, and has a specific order for sequential learning.
    """
    __tablename__ = "lessons"

    # Primary identification
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    
    # Lesson basic information
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    order_number = Column(Integer, default=0, index=True)
    type = Column(SQLEnum(LessonType), default=LessonType.VIDEO, nullable=False, index=True)
    status = Column(Boolean, default=True, nullable=False)
    is_free_preview = Column(Boolean, default=False, nullable=False)
    
    # Video-specific fields
    video = Column(String(255))  # Video file path or URL
    video_type = Column(SQLEnum(VideoType), default=VideoType.UPLOAD)
    video_provider = Column(String(20))  # Provider name for external videos
    video_duration = Column(Integer, default=0)  # Duration in seconds
    size_bytes = Column(Integer, default=0)  # File size in bytes
    
    # Statistics
    views_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    chapter = relationship("Chapter", back_populates="lessons")
    course = relationship("Course", back_populates="lessons")
    videos = relationship("Video", back_populates="lesson", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="lesson", cascade="all, delete-orphan")
    interactive_tools = relationship("InteractiveTool", back_populates="lesson", cascade="all, delete-orphan")
    # lesson_progress = relationship("LessonProgress", back_populates="lesson", cascade="all, delete-orphan")
    # ai_answers = relationship("AIAnswer", back_populates="lesson", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lesson(id={self.id}, title='{self.title}', type='{self.type}')>"
    
    @property
    def is_video_lesson(self) -> bool:
        """Check if this is a video-based lesson"""
        return self.type == LessonType.VIDEO
    
    @property
    def is_exam_lesson(self) -> bool:
        """Check if this is an exam/quiz lesson"""
        return self.type == LessonType.EXAM
    
    @property
    def is_tool_lesson(self) -> bool:
        """Check if this is an interactive tool lesson"""
        return self.type == LessonType.TOOL
    
    @property
    def is_accessible(self) -> bool:
        """Check if lesson is accessible (published and course is published)"""
        return self.status and self.chapter.is_published and self.course.is_published
    
    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string"""
        if not self.video_duration:
            return "0m"
        
        hours = self.video_duration // 3600
        minutes = (self.video_duration % 3600) // 60
        seconds = self.video_duration % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"
        else:
            return f"{seconds}s"
    
    @property
    def file_size_formatted(self) -> str:
        """Get formatted file size string"""
        if not self.size_bytes:
            return "Unknown"
        
        # Convert bytes to human readable format
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.size_bytes < 1024.0:
                return f"{self.size_bytes:.1f} {unit}"
            self.size_bytes /= 1024.0
        return f"{self.size_bytes:.1f} TB" 