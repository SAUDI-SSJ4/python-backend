"""
Tests for Course-related Pydantic schemas.

This module contains unit tests for course schemas including:
- Schema validation
- Field validation with custom validators
- Error handling for invalid data
- Schema serialization and deserialization
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from pydantic import ValidationError

from app.schemas.course import (
    CourseCreate, CourseUpdate, CourseResponse, CourseFilters,
    CourseStatusUpdate, CourseStatusEnum, CourseTypeEnum, CourseLevelEnum
)


@pytest.mark.unit
class TestCourseSchemas:
    """Test suite for Course schemas"""
    
    def test_course_create_valid_data(self):
        """Test CourseCreate schema with valid data"""
        valid_data = {
            "category_id": 1,
            "trainer_id": 2,
            "title": "تطوير المواقع الإلكترونية",
            "content": "دورة شاملة في تطوير المواقع الإلكترونية باستخدام أحدث التقنيات",
            "short_content": "تعلم تطوير المواقع من الصفر",
            "preparations": "حاسوب محمول واتصال إنترنت",
            "requirements": "معرفة أساسية بالحاسوب",
            "learning_outcomes": "بناء مواقع إلكترونية متكاملة",
            "type": "recorded",
            "level": "beginner",
            "price": 299.99,
            "image": "courses/web-dev-course.jpg"
        }
        
        course = CourseCreate(**valid_data)
        
        assert course.title == "تطوير المواقع الإلكترونية"
        assert course.type == CourseTypeEnum.RECORDED
        assert course.level == CourseLevelEnum.BEGINNER
        assert course.price == Decimal('299.99')
        assert course.featured is False  # Default value
    
    def test_course_create_with_optional_fields(self):
        """Test CourseCreate schema with optional fields"""
        future_date = datetime.utcnow() + timedelta(days=30)
        
        data_with_optionals = {
            "category_id": 1,
            "trainer_id": 2,
            "title": "دورة متقدمة في البرمجة",
            "content": "دورة متقدمة للمطورين المحترفين",
            "short_content": "برمجة متقدمة",
            "type": "live",
            "level": "advanced",
            "price": 599.99,
            "discount_price": 449.99,
            "discount_ends_at": future_date,
            "url": "https://example.com/live-session",
            "featured": True,
            "image": "courses/advanced-course.jpg",
            "gallery": ["image1.jpg", "image2.jpg"],
            "preview_video": "preview.mp4"
        }
        
        course = CourseCreate(**data_with_optionals)
        
        assert course.type == CourseTypeEnum.LIVE
        assert course.level == CourseLevelEnum.ADVANCED
        assert course.discount_price == Decimal('449.99')
        assert course.featured is True
        assert course.gallery == ["image1.jpg", "image2.jpg"]
    
    def test_course_create_validation_errors(self):
        """Test CourseCreate schema validation errors"""
        # Test missing required fields
        with pytest.raises(ValidationError) as exc_info:
            CourseCreate()
        
        errors = exc_info.value.errors()
        required_fields = ['category_id', 'trainer_id', 'title', 'content', 'short_content', 'image']
        for field in required_fields:
            assert any(error['loc'][0] == field for error in errors)
        
        # Test invalid field values
        with pytest.raises(ValidationError) as exc_info:
            CourseCreate(
                category_id=0,  # Invalid: must be > 0
                trainer_id=-1,  # Invalid: must be > 0
                title="AB",  # Invalid: too short
                content="Short",  # Invalid: too short
                short_content="X" * 501,  # Invalid: too long
                image="test.jpg"
            )
        
        errors = exc_info.value.errors()
        assert len(errors) > 0
    
    def test_course_create_discount_validation(self):
        """Test CourseCreate discount price validation"""
        # Test invalid discount (higher than regular price)
        with pytest.raises(ValidationError, match="سعر الخصم يجب أن يكون أقل من السعر الأصلي"):
            CourseCreate(
                category_id=1,
                trainer_id=2,
                title="Test Course",
                content="Course content",
                short_content="Short description",
                price=100.00,
                discount_price=150.00,  # Invalid: higher than price
                image="test.jpg"
            )
    
    def test_course_create_discount_end_date_validation(self):
        """Test CourseCreate discount end date validation"""
        past_date = datetime.utcnow() - timedelta(days=1)
        
        # Test invalid discount end date (in the past)
        with pytest.raises(ValidationError, match="تاريخ انتهاء الخصم يجب أن يكون في المستقبل"):
            CourseCreate(
                category_id=1,
                trainer_id=2,
                title="Test Course",
                content="Course content",
                short_content="Short description",
                price=100.00,
                discount_price=80.00,
                discount_ends_at=past_date,  # Invalid: in the past
                image="test.jpg"
            )
    
    def test_course_create_live_course_url_validation(self):
        """Test CourseCreate URL validation for live courses"""
        # Test live course without URL (should fail)
        with pytest.raises(ValidationError, match="رابط الدورة مطلوب للدورات المباشرة"):
            CourseCreate(
                category_id=1,
                trainer_id=2,
                title="Live Course",
                content="Live course content",
                short_content="Live course",
                type="live",  # Live course requires URL
                price=199.99,
                image="test.jpg"
                # Missing URL
            )
    
    def test_course_update_schema(self):
        """Test CourseUpdate schema with partial updates"""
        # Test updating only some fields
        update_data = {
            "title": "Updated Course Title",
            "price": 399.99,
            "featured": True
        }
        
        course_update = CourseUpdate(**update_data)
        
        assert course_update.title == "Updated Course Title"
        assert course_update.price == Decimal('399.99')
        assert course_update.featured is True
        assert course_update.content is None  # Not provided
        assert course_update.type is None  # Not provided
    
    def test_course_filters_schema(self):
        """Test CourseFilters schema for search and filtering"""
        filter_data = {
            "category_id": 1,
            "level": "intermediate",
            "price_from": 100.00,
            "price_to": 500.00,
            "featured": True,
            "search": "JavaScript",
            "page": 2,
            "per_page": 20
        }
        
        filters = CourseFilters(**filter_data)
        
        assert filters.category_id == 1
        assert filters.level == CourseLevelEnum.INTERMEDIATE
        assert filters.price_from == Decimal('100.00')
        assert filters.price_to == Decimal('500.00')
        assert filters.featured is True
        assert filters.search == "JavaScript"
        assert filters.page == 2
        assert filters.per_page == 20
    
    def test_course_filters_price_range_validation(self):
        """Test CourseFilters price range validation"""
        # Test invalid price range (price_to < price_from)
        with pytest.raises(ValidationError, match="السعر الأقصى يجب أن يكون أكبر من السعر الأدنى"):
            CourseFilters(
                price_from=500.00,
                price_to=200.00  # Invalid: less than price_from
            )
    
    def test_course_filters_pagination_validation(self):
        """Test CourseFilters pagination validation"""
        # Test invalid page number
        with pytest.raises(ValidationError):
            CourseFilters(page=0)  # Invalid: must be >= 1
        
        # Test invalid per_page
        with pytest.raises(ValidationError):
            CourseFilters(per_page=0)  # Invalid: must be >= 1
        
        with pytest.raises(ValidationError):
            CourseFilters(per_page=101)  # Invalid: must be <= 100
    
    def test_course_filters_search_validation(self):
        """Test CourseFilters search validation"""
        # Test search term too short
        with pytest.raises(ValidationError):
            CourseFilters(search="A")  # Invalid: too short
        
        # Test search term too long
        with pytest.raises(ValidationError):
            CourseFilters(search="A" * 101)  # Invalid: too long
    
    def test_course_status_update_schema(self):
        """Test CourseStatusUpdate schema"""
        status_update = CourseStatusUpdate(status="published")
        
        assert status_update.status == CourseStatusEnum.PUBLISHED
        
        # Test with different status
        draft_update = CourseStatusUpdate(status="draft")
        assert draft_update.status == CourseStatusEnum.DRAFT
        
        archived_update = CourseStatusUpdate(status="archived")
        assert archived_update.status == CourseStatusEnum.ARCHIVED
    
    def test_course_status_update_invalid_status(self):
        """Test CourseStatusUpdate with invalid status"""
        with pytest.raises(ValidationError):
            CourseStatusUpdate(status="invalid_status")
    
    def test_course_response_schema(self):
        """Test CourseResponse schema serialization"""
        # This would typically be tested with actual model data
        response_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "academy_id": 1,
            "category_id": 1,
            "trainer_id": 2,
            "title": "Test Course",
            "slug": "test-course",
            "image": "test.jpg",
            "content": "Course content",
            "short_content": "Short content",
            "type": "recorded",
            "level": "beginner",
            "price": 299.99,
            "status": "published",
            "platform_fee_percentage": 10.00,
            "avg_rating": 4.5,
            "ratings_count": 100,
            "students_count": 250,
            "lessons_count": 20,
            "duration_seconds": 36000,
            "completion_rate": 85.5,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            # Computed properties
            "current_price": 299.99,
            "duration_formatted": "10h 0m",
            "is_published": True,
            "is_free": False,
            "featured": False
        }
        
        # Test that schema accepts the data structure
        course_response = CourseResponse(**response_data)
        
        assert course_response.title == "Test Course"
        assert course_response.type == CourseTypeEnum.RECORDED
        assert course_response.level == CourseLevelEnum.BEGINNER
        assert course_response.status == CourseStatusEnum.PUBLISHED


@pytest.mark.unit
class TestCourseSchemaEdgeCases:
    """Test edge cases and boundary conditions for course schemas"""
    
    def test_course_create_boundary_values(self):
        """Test CourseCreate with boundary values"""
        # Test minimum valid title length
        min_title_course = CourseCreate(
            category_id=1,
            trainer_id=2,
            title="ABC",  # Minimum 3 characters
            content="A" * 10,  # Minimum 10 characters
            short_content="B" * 10,  # Minimum 10 characters
            image="test.jpg"
        )
        
        assert len(min_title_course.title) == 3
        assert len(min_title_course.content) == 10
        
        # Test maximum valid title length
        max_title = "A" * 255
        max_title_course = CourseCreate(
            category_id=1,
            trainer_id=2,
            title=max_title,
            content="Course content here",
            short_content="Short description here",
            image="test.jpg"
        )
        
        assert len(max_title_course.title) == 255
    
    def test_course_create_zero_price(self):
        """Test CourseCreate with zero price (free course)"""
        free_course = CourseCreate(
            category_id=1,
            trainer_id=2,
            title="Free Course",
            content="Free course content",
            short_content="Free course description",
            price=0.00,  # Free course
            image="test.jpg"
        )
        
        assert free_course.price == Decimal('0.00')
    
    def test_course_filters_default_values(self):
        """Test CourseFilters with default values"""
        filters = CourseFilters()
        
        assert filters.page == 1  # Default page
        assert filters.per_page == 10  # Default per_page
        assert filters.category_id is None
        assert filters.search is None
        assert filters.featured is None 