"""
Tests for Lesson model and related functionality.

This module contains unit tests for the Lesson model including:
- Model creation with different lesson types
- Property methods testing
- Relationship validation
- Duration and size formatting
"""

import pytest
from sqlalchemy.orm import Session

from app.models.lesson import Lesson, LessonType, VideoType
from app.models.chapter import Chapter
from app.models.course import Course


@pytest.mark.models
class TestLessonModel:
    """Test suite for Lesson model"""
    
    def test_create_video_lesson(self, db_session: Session, test_course: Course, test_chapter: Chapter):
        """Test creating a video lesson with all video-specific fields"""
        lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Video Lesson Test",
            description="A test video lesson",
            type=LessonType.VIDEO,
            order_number=1,
            status=True,
            is_free_preview=True,
            video="lessons/test-video.mp4",
            video_type=VideoType.UPLOAD,
            video_provider="local",
            video_duration=1800,
            size_bytes=104857600  # 100MB
        )
        
        db_session.add(lesson)
        db_session.commit()
        db_session.refresh(lesson)
        
        assert lesson.id is not None
        assert lesson.title == "Video Lesson Test"
        assert lesson.type == LessonType.VIDEO
        assert lesson.is_video_lesson is True
        assert lesson.is_exam_lesson is False
        assert lesson.is_tool_lesson is False
        assert lesson.video_type == VideoType.UPLOAD
        assert lesson.video_duration == 1800
        assert lesson.size_bytes == 104857600
        assert lesson.is_free_preview is True
    
    def test_create_exam_lesson(self, db_session: Session, test_course: Course, test_chapter: Chapter):
        """Test creating an exam lesson"""
        lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Exam Lesson Test",
            description="A test exam lesson",
            type=LessonType.EXAM,
            order_number=2,
            status=True
        )
        
        db_session.add(lesson)
        db_session.commit()
        db_session.refresh(lesson)
        
        assert lesson.type == LessonType.EXAM
        assert lesson.is_video_lesson is False
        assert lesson.is_exam_lesson is True
        assert lesson.is_tool_lesson is False
        assert lesson.video is None  # No video for exam lesson
    
    def test_create_tool_lesson(self, db_session: Session, test_course: Course, test_chapter: Chapter):
        """Test creating an interactive tool lesson"""
        lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Tool Lesson Test",
            description="A test interactive tool lesson",
            type=LessonType.TOOL,
            order_number=3,
            status=True
        )
        
        db_session.add(lesson)
        db_session.commit()
        db_session.refresh(lesson)
        
        assert lesson.type == LessonType.TOOL
        assert lesson.is_video_lesson is False
        assert lesson.is_exam_lesson is False
        assert lesson.is_tool_lesson is True
    
    def test_create_text_lesson(self, db_session: Session, test_course: Course, test_chapter: Chapter):
        """Test creating a text-based lesson"""
        lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Text Lesson Test",
            description="A test text lesson with reading material",
            type=LessonType.TEXT,
            order_number=4,
            status=True
        )
        
        db_session.add(lesson)
        db_session.commit()
        db_session.refresh(lesson)
        
        assert lesson.type == LessonType.TEXT
        assert lesson.is_video_lesson is False
        assert lesson.is_exam_lesson is False
        assert lesson.is_tool_lesson is False
    
    def test_lesson_video_types(self, db_session: Session, test_course: Course, test_chapter: Chapter):
        """Test different video types for lessons"""
        # YouTube video lesson
        youtube_lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="YouTube Lesson",
            description="Lesson with YouTube video",
            type=LessonType.VIDEO,
            video="https://youtube.com/watch?v=example",
            video_type=VideoType.YOUTUBE,
            video_provider="youtube",
            video_duration=900
        )
        
        db_session.add(youtube_lesson)
        db_session.commit()
        db_session.refresh(youtube_lesson)
        
        assert youtube_lesson.video_type == VideoType.YOUTUBE
        assert youtube_lesson.video_provider == "youtube"
        
        # Vimeo video lesson
        vimeo_lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Vimeo Lesson",
            description="Lesson with Vimeo video",
            type=LessonType.VIDEO,
            video="https://vimeo.com/example",
            video_type=VideoType.VIMEO,
            video_provider="vimeo",
            video_duration=1200
        )
        
        db_session.add(vimeo_lesson)
        db_session.commit()
        db_session.refresh(vimeo_lesson)
        
        assert vimeo_lesson.video_type == VideoType.VIMEO
        assert vimeo_lesson.video_provider == "vimeo"
    
    def test_lesson_duration_formatted_property(self, db_session: Session, test_course: Course, test_chapter: Chapter):
        """Test the duration_formatted property for different durations"""
        # Test lesson with hours, minutes, and seconds
        long_lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Long Lesson",
            description="A long lesson",
            type=LessonType.VIDEO,
            video_duration=7265  # 2h 1m 5s
        )
        
        assert long_lesson.duration_formatted == "2h 1m"
        
        # Test lesson with only minutes and seconds
        medium_lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Medium Lesson",
            description="A medium lesson",
            type=LessonType.VIDEO,
            video_duration=375  # 6m 15s
        )
        
        assert medium_lesson.duration_formatted == "6m 15s"
        
        # Test lesson with only seconds
        short_lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Short Lesson",
            description="A short lesson",
            type=LessonType.VIDEO,
            video_duration=45  # 45s
        )
        
        assert short_lesson.duration_formatted == "45s"
        
        # Test lesson with no duration
        no_duration_lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="No Duration Lesson",
            description="A lesson with no duration",
            type=LessonType.TEXT
        )
        
        assert no_duration_lesson.duration_formatted == "0m"
    
    def test_lesson_file_size_formatted_property(self, db_session: Session, test_course: Course, test_chapter: Chapter):
        """Test the file_size_formatted property for different file sizes"""
        # Test bytes
        bytes_lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Bytes Lesson",
            description="Small file",
            type=LessonType.VIDEO,
            size_bytes=512  # 512 B
        )
        
        assert "512" in bytes_lesson.file_size_formatted
        assert "B" in bytes_lesson.file_size_formatted
        
        # Test kilobytes
        kb_lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="KB Lesson",
            description="Medium file",
            type=LessonType.VIDEO,
            size_bytes=2048  # 2 KB
        )
        
        assert "2.0" in kb_lesson.file_size_formatted
        assert "KB" in kb_lesson.file_size_formatted
        
        # Test megabytes
        mb_lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="MB Lesson",
            description="Large file",
            type=LessonType.VIDEO,
            size_bytes=52428800  # 50 MB
        )
        
        assert "50.0" in mb_lesson.file_size_formatted
        assert "MB" in mb_lesson.file_size_formatted
        
        # Test gigabytes
        gb_lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="GB Lesson",
            description="Very large file",
            type=LessonType.VIDEO,
            size_bytes=2147483648  # 2 GB
        )
        
        assert "2.0" in gb_lesson.file_size_formatted
        assert "GB" in gb_lesson.file_size_formatted
    
    def test_lesson_is_accessible_property(self, db_session: Session, test_course: Course, test_chapter: Chapter):
        """Test the is_accessible property"""
        # Create accessible lesson (published chapter and course)
        accessible_lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Accessible Lesson",
            description="This lesson should be accessible",
            type=LessonType.VIDEO,
            status=True
        )
        
        # Since test_course and test_chapter are published by default in fixtures
        assert accessible_lesson.is_accessible is True
        
        # Create inaccessible lesson (lesson is disabled)
        inaccessible_lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Inaccessible Lesson",
            description="This lesson should not be accessible",
            type=LessonType.VIDEO,
            status=False  # Lesson disabled
        )
        
        assert inaccessible_lesson.is_accessible is False
    
    def test_lesson_relationships(self, db_session: Session, test_course: Course, test_chapter: Chapter):
        """Test lesson relationships with other models"""
        lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Relationship Test Lesson",
            description="Testing relationships",
            type=LessonType.VIDEO
        )
        
        db_session.add(lesson)
        db_session.commit()
        db_session.refresh(lesson)
        
        # Test chapter relationship
        assert lesson.chapter is not None
        assert lesson.chapter.id == test_chapter.id
        
        # Test course relationship
        assert lesson.course is not None
        assert lesson.course.id == test_course.id
    
    def test_lesson_defaults(self, db_session: Session, test_course: Course, test_chapter: Chapter):
        """Test default values for lesson fields"""
        lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="Defaults Test Lesson",
            description="Testing default values"
        )
        
        db_session.add(lesson)
        db_session.commit()
        db_session.refresh(lesson)
        
        assert lesson.type == LessonType.VIDEO  # Default type
        assert lesson.order_number == 0  # Default order
        assert lesson.status is True  # Default status
        assert lesson.is_free_preview is False  # Default preview
        assert lesson.video_type == VideoType.UPLOAD  # Default video type
        assert lesson.video_duration == 0  # Default duration
        assert lesson.size_bytes == 0  # Default size
        assert lesson.views_count == 0  # Default views
    
    def test_lesson_str_representation(self, db_session: Session, test_course: Course, test_chapter: Chapter):
        """Test the string representation of Lesson model"""
        lesson = Lesson(
            chapter_id=test_chapter.id,
            course_id=test_course.id,
            title="String Test Lesson",
            description="Testing string representation",
            type=LessonType.EXAM
        )
        
        db_session.add(lesson)
        db_session.commit()
        db_session.refresh(lesson)
        
        str_repr = str(lesson)
        assert "String Test Lesson" in str_repr
        assert "exam" in str_repr
        assert lesson.id in str_repr 