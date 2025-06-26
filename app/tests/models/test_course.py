"""
Tests for Course model and related functionality.

This module contains unit tests for the Course model including:
- Model creation and validation
- Property methods testing
- Relationship testing
- Enum validation
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.course import Course, CourseStatus, CourseType, CourseLevel
from app.models.academy import Academy
from app.models.user import User


@pytest.mark.models
class TestCourseModel:
    """Test suite for Course model"""
    
    def test_create_course_with_required_fields(self, db_session: Session, test_academy: Academy):
        """Test creating a course with only required fields"""
        course = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="Test Course",
            slug="test-course",
            image="test-image.jpg",
            content="Course content",
            short_content="Short description"
        )
        
        db_session.add(course)
        db_session.commit()
        db_session.refresh(course)
        
        assert course.id is not None
        assert course.title == "Test Course"
        assert course.status == CourseStatus.DRAFT  # Default status
        assert course.type == CourseType.RECORDED  # Default type
        assert course.level == CourseLevel.BEGINNER  # Default level
        assert course.price == Decimal('0.00')  # Default price
        assert course.featured is False  # Default featured
        assert course.created_at is not None
        assert course.updated_at is not None
    
    def test_course_with_all_fields(self, db_session: Session, test_academy: Academy):
        """Test creating a course with all fields populated"""
        future_date = datetime.utcnow() + timedelta(days=30)
        
        course = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="Complete Course",
            slug="complete-course",
            image="course-image.jpg",
            content="Detailed course content",
            short_content="Brief description",
            preparations="Course preparations",
            requirements="Course requirements",
            learning_outcomes="Learning outcomes",
            gallery=["image1.jpg", "image2.jpg"],
            preview_video="preview.mp4",
            status=CourseStatus.PUBLISHED,
            featured=True,
            type=CourseType.LIVE,
            url="https://example.com/live-course",
            level=CourseLevel.ADVANCED,
            price=Decimal('499.99'),
            discount_price=Decimal('399.99'),
            discount_ends_at=future_date,
            platform_fee_percentage=Decimal('10.00'),
            avg_rating=Decimal('4.5'),
            ratings_count=100,
            students_count=250,
            lessons_count=20,
            duration_seconds=36000,
            completion_rate=Decimal('85.5')
        )
        
        db_session.add(course)
        db_session.commit()
        db_session.refresh(course)
        
        assert course.title == "Complete Course"
        assert course.status == CourseStatus.PUBLISHED
        assert course.featured is True
        assert course.type == CourseType.LIVE
        assert course.level == CourseLevel.ADVANCED
        assert course.price == Decimal('499.99')
        assert course.discount_price == Decimal('399.99')
        assert course.gallery == ["image1.jpg", "image2.jpg"]
    
    def test_course_enum_validation(self, db_session: Session, test_academy: Academy):
        """Test that enum fields accept only valid values"""
        course = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="Enum Test Course",
            slug="enum-test-course",
            image="test.jpg",
            content="Content",
            short_content="Short",
            status=CourseStatus.ARCHIVED,
            type=CourseType.ATTEND,
            level=CourseLevel.INTERMEDIATE
        )
        
        db_session.add(course)
        db_session.commit()
        db_session.refresh(course)
        
        assert course.status == CourseStatus.ARCHIVED
        assert course.type == CourseType.ATTEND
        assert course.level == CourseLevel.INTERMEDIATE
    
    def test_course_is_published_property(self, db_session: Session, test_academy: Academy):
        """Test the is_published property"""
        # Test published course
        published_course = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="Published Course",
            slug="published-course",
            image="test.jpg",
            content="Content",
            short_content="Short",
            status=CourseStatus.PUBLISHED
        )
        
        assert published_course.is_published is True
        
        # Test draft course
        draft_course = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="Draft Course",
            slug="draft-course",
            image="test.jpg",
            content="Content",
            short_content="Short",
            status=CourseStatus.DRAFT
        )
        
        assert draft_course.is_published is False
    
    def test_course_is_free_property(self, db_session: Session, test_academy: Academy):
        """Test the is_free property"""
        # Test free course
        free_course = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="Free Course",
            slug="free-course",
            image="test.jpg",
            content="Content",
            short_content="Short",
            price=Decimal('0.00')
        )
        
        assert free_course.is_free is True
        
        # Test paid course
        paid_course = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="Paid Course",
            slug="paid-course",
            image="test.jpg",
            content="Content",
            short_content="Short",
            price=Decimal('99.99')
        )
        
        assert paid_course.is_free is False
    
    def test_course_current_price_property(self, db_session: Session, test_academy: Academy):
        """Test the current_price property with and without discounts"""
        # Test course without discount
        course_no_discount = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="No Discount Course",
            slug="no-discount-course",
            image="test.jpg",
            content="Content",
            short_content="Short",
            price=Decimal('199.99')
        )
        
        assert course_no_discount.current_price == Decimal('199.99')
        
        # Test course with valid discount
        future_date = datetime.utcnow() + timedelta(days=10)
        course_with_discount = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="Discount Course",
            slug="discount-course",
            image="test.jpg",
            content="Content",
            short_content="Short",
            price=Decimal('199.99'),
            discount_price=Decimal('149.99'),
            discount_ends_at=future_date
        )
        
        assert course_with_discount.current_price == Decimal('149.99')
        
        # Test course with expired discount
        past_date = datetime.utcnow() - timedelta(days=1)
        course_expired_discount = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="Expired Discount Course",
            slug="expired-discount-course",
            image="test.jpg",
            content="Content",
            short_content="Short",
            price=Decimal('199.99'),
            discount_price=Decimal('149.99'),
            discount_ends_at=past_date
        )
        
        assert course_expired_discount.current_price == Decimal('199.99')
    
    def test_course_duration_formatted_property(self, db_session: Session, test_academy: Academy):
        """Test the duration_formatted property"""
        # Test course with hours and minutes
        course_long = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="Long Course",
            slug="long-course",
            image="test.jpg",
            content="Content",
            short_content="Short",
            duration_seconds=7380  # 2 hours and 3 minutes
        )
        
        assert course_long.duration_formatted == "2h 3m"
        
        # Test course with only minutes
        course_short = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="Short Course",
            slug="short-course",
            image="test.jpg",
            content="Content",
            short_content="Short",
            duration_seconds=1800  # 30 minutes
        )
        
        assert course_short.duration_formatted == "30m"
    
    def test_course_relationships(self, db_session: Session, test_academy: Academy):
        """Test course relationships with other models"""
        course = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="Relationship Test Course",
            slug="relationship-test-course",
            image="test.jpg",
            content="Content",
            short_content="Short"
        )
        
        db_session.add(course)
        db_session.commit()
        db_session.refresh(course)
        
        # Test academy relationship
        assert course.academy is not None
        assert course.academy.id == test_academy.id
        
        # Test trainer relationship (should be accessible through User model)
        assert course.trainer_id == test_academy.users_id
    
    def test_course_str_representation(self, db_session: Session, test_academy: Academy):
        """Test the string representation of Course model"""
        course = Course(
            academy_id=test_academy.id,
            category_id=1,
            trainer_id=test_academy.users_id,
            title="String Test Course",
            slug="string-test-course",
            image="test.jpg",
            content="Content",
            short_content="Short",
            status=CourseStatus.PUBLISHED
        )
        
        db_session.add(course)
        db_session.commit()
        db_session.refresh(course)
        
        str_repr = str(course)
        assert "String Test Course" in str_repr
        assert "published" in str_repr
        assert course.id in str_repr 