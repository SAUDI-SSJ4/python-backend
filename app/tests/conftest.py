"""
Test configuration and fixtures for the SAYAN course management system.

This module provides all necessary fixtures for testing including:
- Database setup and teardown
- Test client configuration
- Authentication fixtures
- Mock data creation
- Cleanup utilities
"""

import pytest
import tempfile
import os
from typing import Generator, Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.config import settings
from app.db.base import Base
from app.deps.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.academy import Academy
from app.models.course import Course, CourseStatus, CourseType, CourseLevel
from app.models.chapter import Chapter
from app.models.lesson import Lesson, LessonType, VideoType
from app.models.video import Video
from app.models.exam import Exam, Question, QuestionOption, QuestionType
from app.models.interactive_tool import InteractiveTool
from app.models.lesson_progress import LessonProgress
from app.services.auth_service import auth_service


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
    """Create test database engine"""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


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


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database session override"""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def temp_directory():
    """Create a temporary directory for file operations"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


# User and Authentication Fixtures
@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Sample user data for testing"""
    return {
        "fname": "Ahmed",
        "mname": "Mohammed",
        "lname": "Ali",
        "phone_number": "+966501234567",
        "email": "ahmed@example.com",
        "password": "SecurePassword123!",
        "user_type": "student",
        "verified": True
    }


@pytest.fixture
def sample_academy_user_data() -> Dict[str, Any]:
    """Sample academy user data for testing"""
    return {
        "fname": "Sarah",
        "mname": "Hassan",
        "lname": "Ahmed",
        "phone_number": "+966507654321",
        "email": "sarah@academy.com",
        "password": "AcademyPass123!",
        "user_type": "academy",
        "verified": True
    }


@pytest.fixture
def test_user(db_session: Session, sample_user_data: Dict[str, Any]) -> User:
    """Create a test user in the database"""
    hashed_password = auth_service.hash_password(sample_user_data["password"])
    
    user = User(
        fname=sample_user_data["fname"],
        mname=sample_user_data["mname"],
        lname=sample_user_data["lname"],
        phone_number=sample_user_data["phone_number"],
        email=sample_user_data["email"],
        password=hashed_password,
        user_type=sample_user_data["user_type"],
        verified=sample_user_data["verified"]
    )
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture
def test_academy_user(db_session: Session, sample_academy_user_data: Dict[str, Any]) -> User:
    """Create a test academy user in the database"""
    hashed_password = auth_service.hash_password(sample_academy_user_data["password"])
    
    user = User(
        fname=sample_academy_user_data["fname"],
        mname=sample_academy_user_data["mname"],
        lname=sample_academy_user_data["lname"],
        phone_number=sample_academy_user_data["phone_number"],
        email=sample_academy_user_data["email"],
        password=hashed_password,
        user_type=sample_academy_user_data["user_type"],
        verified=sample_academy_user_data["verified"]
    )
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture
def test_student(db_session: Session, test_user: User) -> Student:
    """Create a test student profile"""
    student = Student(
        user_id=test_user.id,
        birth_date="1995-01-01",
        gender="male"
    )
    
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    
    return student


@pytest.fixture
def test_academy(db_session: Session, test_academy_user: User) -> Academy:
    """Create a test academy"""
    academy = Academy(
        academy_id=f"ACAD_{test_academy_user.id}",
        users_id=test_academy_user.id,
        name="Test Academy",
        about="A test academy for educational purposes",
        email="info@testacademy.com",
        phone="+966501111111",
        status="active",
        verified=True
    )
    
    db_session.add(academy)
    db_session.commit()
    db_session.refresh(academy)
    
    return academy


# Authentication Fixtures
@pytest.fixture
def student_auth_headers(test_student: Student) -> Dict[str, str]:
    """Generate authentication headers for student"""
    access_token = auth_service.create_access_token(
        data={"sub": str(test_student.user_id), "user_type": "student"}
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def academy_auth_headers(test_academy_user: User) -> Dict[str, str]:
    """Generate authentication headers for academy user"""
    access_token = auth_service.create_access_token(
        data={"sub": str(test_academy_user.id), "user_type": "academy"}
    )
    return {"Authorization": f"Bearer {access_token}"}


# Course-related Fixtures
@pytest.fixture
def sample_course_data(test_academy: Academy) -> Dict[str, Any]:
    """Sample course data for testing"""
    return {
        "category_id": 1,
        "trainer_id": test_academy.users_id,
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
def test_course(db_session: Session, test_academy: Academy, sample_course_data: Dict[str, Any]) -> Course:
    """Create a test course in the database"""
    course = Course(
        academy_id=test_academy.id,
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


@pytest.fixture
def test_lesson_progress(db_session: Session, test_student: Student, test_lesson: Lesson, test_course: Course) -> LessonProgress:
    """Create a test lesson progress record"""
    progress = LessonProgress(
        student_id=test_student.id,
        lesson_id=test_lesson.id,
        course_id=test_course.id,
        progress_percentage=50,
        current_position_seconds=900,
        completed=False
    )
    
    db_session.add(progress)
    db_session.commit()
    db_session.refresh(progress)
    
    return progress


# Utility Fixtures
@pytest.fixture
def mock_file_upload():
    """Mock file upload for testing"""
    return {
        "filename": "test-image.jpg",
        "content_type": "image/jpeg",
        "content": b"fake image content"
    }


@pytest.fixture
def cleanup_files():
    """Cleanup test files after tests"""
    created_files = []
    
    def add_file(filepath: str):
        created_files.append(filepath)
    
    yield add_file
    
    # Cleanup after test
    for filepath in created_files:
        if os.path.exists(filepath):
            os.remove(filepath) 