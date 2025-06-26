"""
Simplified test configuration for testing specific models only.

This conftest imports only the models we want to test to avoid 
foreign key reference issues with missing tables.
"""

import pytest
import tempfile
import os
from typing import Generator, Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Import only the base and models we want to test
from app.db.base import Base

# Import specific models for testing
from app.models.course import Course, Category, CourseStatus, CourseType, CourseLevel  
from app.models.chapter import Chapter
from app.models.lesson import Lesson, LessonType, VideoType
from app.models.video import Video
from app.models.exam import Exam, Question, QuestionOption, QuestionType
from app.models.interactive_tool import InteractiveTool
from app.models.lesson_progress import LessonProgress
from app.models.ai_answer import AIAnswer


# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine with only required tables"""
    
    # Create only the tables we need for testing
    tables_to_create = [
        Category.__table__,
        Course.__table__,
        Chapter.__table__,
        Lesson.__table__,
        Video.__table__,
        Exam.__table__,
        Question.__table__,
        QuestionOption.__table__,
        InteractiveTool.__table__,
        LessonProgress.__table__,
        AIAnswer.__table__,
    ]
    
    for table in tables_to_create:
        table.create(bind=engine, checkfirst=True)
    
    yield engine
    
    # Drop tables after testing
    for table in reversed(tables_to_create):
        table.drop(bind=engine, checkfirst=True)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a fresh database session for each test"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


# Data Fixtures for Testing
@pytest.fixture
def sample_category(db_session: Session) -> Category:
    """Create a test category"""
    category = Category(
        name="Web Development",
        slug="web-development",
        description="Learn web development technologies",
        is_active=True
    )
    
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    
    return category


@pytest.fixture  
def sample_course_data(sample_category: Category) -> Dict[str, Any]:
    """Sample course data for testing"""
    return {
        "academy_id": 1,  # Mock academy ID
        "category_id": sample_category.id,
        "trainer_id": 1,  # Mock trainer ID
        "title": "Test Course: Web Development",
        "content": "A comprehensive course on web development covering HTML, CSS, and JavaScript",
        "short_content": "Learn web development from scratch",
        "preparations": "Basic computer knowledge",
        "requirements": "Computer with internet connection",
        "learning_outcomes": "Build modern web applications",
        "type": "recorded",
        "level": "beginner",
        "price": 299.99,
        "image": "courses/test-course.jpg"
    }


@pytest.fixture
def test_course(db_session: Session, sample_category: Category, sample_course_data: Dict[str, Any]) -> Course:
    """Create a test course in the database"""
    course = Course(
        academy_id=sample_course_data["academy_id"],
        category_id=sample_course_data["category_id"],
        trainer_id=sample_course_data["trainer_id"],
        title=sample_course_data["title"],
        slug="test-course-web-development",
        image=sample_course_data["image"],
        content=sample_course_data["content"],
        short_content=sample_course_data["short_content"],
        preparations=sample_course_data["preparations"],
        requirements=sample_course_data["requirements"],
        learning_outcomes=sample_course_data["learning_outcomes"],
        type=CourseType.RECORDED,
        level=CourseLevel.BEGINNER,
        price=sample_course_data["price"],
        status=CourseStatus.PUBLISHED
    )
    
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)
    
    return course


@pytest.fixture
def test_chapter(db_session: Session, test_course: Course) -> Chapter:
    """Create a test chapter"""
    chapter = Chapter(
        course_id=test_course.id,
        title="Introduction to Web Development",
        description="Basic concepts and setup",
        order_number=1,
        is_published=True
    )
    
    db_session.add(chapter)
    db_session.commit()
    db_session.refresh(chapter)
    
    return chapter


@pytest.fixture
def test_lesson(db_session: Session, test_course: Course, test_chapter: Chapter) -> Lesson:
    """Create a test lesson"""
    lesson = Lesson(
        chapter_id=test_chapter.id,
        course_id=test_course.id,
        title="HTML Basics",
        description="Introduction to HTML markup",
        type=LessonType.VIDEO,
        order_number=1,
        status=True,
        video_duration=1800  # 30 minutes
    )
    
    db_session.add(lesson)
    db_session.commit()
    db_session.refresh(lesson)
    
    return lesson


@pytest.fixture  
def test_video(db_session: Session, test_lesson: Lesson) -> Video:
    """Create a test video"""
    video = Video(
        lesson_id=test_lesson.id,
        title="HTML Basics Video",
        description="Learn HTML fundamentals",
        video="lessons/videos/html-basics.mp4",
        duration=1800,
        status=True
    )
    
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    
    return video


@pytest.fixture
def test_exam(db_session: Session, test_lesson: Lesson) -> Exam:
    """Create a test exam"""
    exam = Exam(
        lesson_id=test_lesson.id,
        title="HTML Quiz",
        question="What does HTML stand for?",
        answers=["HyperText Markup Language", "High Tech Modern Language", "Home Tool Markup Language"],
        correct_answer=["HyperText Markup Language"],
        question_type=QuestionType.SINGLE,
        duration=600  # 10 minutes
    )
    
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)
    
    return exam


@pytest.fixture
def test_interactive_tool(db_session: Session, test_lesson: Lesson) -> InteractiveTool:
    """Create a test interactive tool"""
    tool = InteractiveTool(
        lesson_id=test_lesson.id,
        title="HTML Code Editor",
        description="Practice HTML coding with live preview",
        color="#007bff",
        order_number=1
    )
    
    db_session.add(tool)
    db_session.commit()
    db_session.refresh(tool)
    
    return tool 