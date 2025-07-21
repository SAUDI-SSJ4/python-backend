from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from typing import List, Optional, Any, Dict
import uuid
from datetime import datetime
from dateutil import parser
from decimal import Decimal

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user, get_current_student, get_current_user
from app.models.course import Course, CourseStatus, CourseType, CourseLevel
from app.models.academy import Academy, AcademyUser
from app.models.user import User
from app.schemas.course import (
    CourseCreate, CourseResponse, CourseDetailResponse,
    CourseListResponse, CourseFilters, CourseStatusUpdate
)
from app.services.file_service import file_service
from app.core.config import settings
from app.models.product import Product, ProductType, ProductStatus
from app.models.chapter import Chapter
from app.api.v1.courses.progression import router as progression_router

router = APIRouter()
router.include_router(progression_router, prefix="/api/v1/courses")


def convert_to_json_safe(obj: Any) -> Any:
    """تحويل الكائن إلى نوع يمكن تحويله إلى JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_to_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_safe(item) for item in obj]
    return obj


# دالة مساعدة لبناء استجابة موحدة مطابقة لتنسيق message.png
def build_response(message: str, data: Any, path: str, status_code: int = 200):
    """Return unified JSONResponse"""
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "success" if status_code < 400 else "error",
            "status_code": status_code,
            "error_type": None if status_code < 400 else "Error",
            "message": message,
            "data": convert_to_json_safe(data) if data is not None else None,
            "path": path,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        }
    )


# Academy endpoints (Course management)
@router.get("/academy/trainers")
async def get_academy_trainers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Get all trainers (academy users) for the current academy.
    
    Returns list of all users associated with the academy who can be assigned as trainers.
    """
    try:
        # Get all academy users for this academy
        academy_users = db.query(AcademyUser).options(
            joinedload(AcademyUser.user)
        ).filter(
            AcademyUser.academy_id == current_user.academy.id,
            AcademyUser.is_active == True
        ).all()
        
        trainers = []
        for academy_user in academy_users:
            user = academy_user.user
            if user:
                # Get trainer stats (courses taught)
                courses_count = db.query(Course).filter(
                    Course.trainer_id == user.id,
                    Course.academy_id == current_user.academy.id
                ).count()
                
                trainer_data = {
                    "id": user.id,
                    "fname": user.fname,
                    "lname": user.lname,
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone_number": user.phone_number,
                    "avatar": user.avatar,
                    "status": user.status,
                    "verified": user.verified,
                    "user_role": academy_user.user_role,
                    "is_owner": academy_user.user_role == "owner",
                    "joined_at": academy_user.joined_at,
                    "stats": {
                        "courses_count": courses_count,
                        "is_active": academy_user.is_active
                    }
                }
                trainers.append(trainer_data)
        
        return build_response(
            message="تم جلب المدربين بنجاح",
            data={
                "trainers": trainers,
                "total": len(trainers)
            },
            path="/api/v1/academy/trainers"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء جلب المدربين: {str(e)}"
        )


@router.get("/academy/trainers/{trainer_id}")
async def get_trainer_details(
    trainer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Get detailed information about a specific trainer.
    
    Returns comprehensive trainer data including courses, performance metrics, and profile.
    """
    try:
        # Check if trainer belongs to current academy
        academy_user = db.query(AcademyUser).options(
            joinedload(AcademyUser.user)
        ).filter(
            AcademyUser.academy_id == current_user.academy.id,
            AcademyUser.user_id == trainer_id,
            AcademyUser.is_active == True
        ).first()
        
        if not academy_user or not academy_user.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المدرب غير موجود في هذه الأكاديمية"
            )
        
        trainer = academy_user.user
        
        # Get trainer's courses
        courses = db.query(Course).options(
            joinedload(Course.category),
            joinedload(Course.product)
        ).filter(
            Course.trainer_id == trainer_id,
            Course.academy_id == current_user.academy.id
        ).all()
        
        # Calculate trainer statistics
        total_courses = len(courses)
        published_courses = len([c for c in courses if c.course_state == CourseStatus.published])
        draft_courses = len([c for c in courses if c.course_state == CourseStatus.draft])
        
        # Note: Enrollment stats temporarily disabled due to database schema compatibility
        # This can be re-enabled once the student_courses table schema is standardized
        total_enrollments = 0  # Placeholder - will be implemented after DB schema fix
        
        trainer_data = {
            "id": trainer.id,
            "fname": trainer.fname,
            "lname": trainer.lname,
            "full_name": trainer.full_name,
            "email": trainer.email,
            "phone_number": trainer.phone_number,
            "avatar": trainer.avatar,
            "status": trainer.status,
            "verified": trainer.verified,
            "created_at": trainer.created_at,
            "updated_at": trainer.updated_at,
            "academy_info": {
                "user_role": academy_user.user_role,
                "is_owner": academy_user.user_role == "owner",
                "joined_at": academy_user.joined_at,
                "is_active": academy_user.is_active
            },
            "statistics": {
                "total_courses": total_courses,
                "published_courses": published_courses,
                "draft_courses": draft_courses,
                "total_enrollments": total_enrollments,
                "average_enrollments_per_course": total_enrollments / total_courses if total_courses > 0 else 0
            },
            "courses": [
                {
                    "id": course.id,
                    "title": course.product.title if course.product else course.short_content,
                    "slug": course.slug,
                    "status": course.course_state,
                    "type": course.type,
                    "level": course.level,
                    "featured": course.featured,
                    "category": course.category.name if course.category else None,
                    "price": float(course.product.price) if course.product else 0,
                    "created_at": course.created_at,
                    "updated_at": course.updated_at
                }
                for course in courses
            ]
        }
        
        return build_response(
            message="تم جلب تفاصيل المدرب بنجاح",
            data=trainer_data,
            path=f"/api/v1/academy/trainers/{trainer_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء جلب تفاصيل المدرب: {str(e)}"
        )


@router.get("/academy/courses", response_model=CourseListResponse)
async def get_academy_courses(
    filters: CourseFilters = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Get all courses for the current academy with filtering and pagination.
    
    Academy owners can view and manage all their courses with comprehensive filtering options.
    """
    try:
        # Build base query for academy's courses with category join
        query = db.query(Course).options(
            joinedload(Course.category),
            joinedload(Course.trainer),
            joinedload(Course.product)
        ).join(Product).filter(Course.academy_id == current_user.academy.id)
        
        # Apply filters
        if filters.category_id:
            query = query.filter(Course.category_id == filters.category_id)
        
        if filters.trainer_id:
            query = query.filter(Course.trainer_id == filters.trainer_id)
        
        if filters.status:
            query = query.filter(Course.course_state == filters.status)
        
        if filters.type:
            query = query.filter(Course.type == filters.type)
        
        if filters.level:
            query = query.filter(Course.level == filters.level)
        
        if filters.price_from is not None:
            query = query.filter(Product.price >= filters.price_from)
        
        if filters.price_to is not None:
            query = query.filter(Product.price <= filters.price_to)
        
        if filters.featured is not None:
            query = query.filter(Course.featured == filters.featured)
        
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(Product.title.ilike(search_term))
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        offset = (filters.page - 1) * filters.per_page
        courses = query.offset(offset).limit(filters.per_page).all()
        
        # Calculate pagination info
        total_pages = (total + filters.per_page - 1) // filters.per_page
        
        data = {
            "courses": [CourseResponse.from_course_model(c).dict() for c in courses],
            "total": total,
            "page": filters.page,
            "per_page": filters.per_page,
            "total_pages": total_pages
        }

        return build_response(
            message="تم جلب الدورات بنجاح",
            data=data,
            path="/api/v1/academy/courses"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء جلب الدورات: {str(e)}"
        )


@router.post("/academy/courses", response_model=CourseResponse)
async def create_course(
    category_id: int = Form(..., description="معرف الفئة"),
    trainer_id: Optional[int] = Form(None, description="معرف المدرب (اختياري)"),
    title: str = Form(..., min_length=3, max_length=255, description="عنوان الكورس"),
    content: str = Form(..., min_length=10, description="وصف الكورس المفصل"),
    short_content: str = Form(..., min_length=10, max_length=500, description="وصف الكورس المختصر"),
    preparations: Optional[str] = Form(None, description="التحضيرات المطلوبة"),
    requirements: Optional[str] = Form(None, description="المتطلبات الأساسية"),
    learning_outcomes: Optional[str] = Form(None, description="نتائج التعلم"),
    type: str = Form("recorded", description="نوع الكورس"),
    level: str = Form("beginner", description="مستوى الكورس"),
    price: float = Form(..., ge=0, description="سعر الكورس"),
    discount_price: Optional[float] = Form(None, ge=0, description="سعر الخصم"),
    discount_ends_at: Optional[str] = Form(None, description="تاريخ انتهاء الخصم"),
    url: Optional[str] = Form(None, description="رابط الكورس المباشر"),
    featured: bool = Form(False, description="كورس مميز"),
    product_id: Optional[int] = Form(None, ge=0, description="معرف المنتج (اختياري)"),
    image: UploadFile = File(..., description="صورة الكورس"),
    preview_video: Optional[UploadFile] = File(None, description="فيديو المعاينة"),
    gallery: Optional[List[UploadFile]] = File(None, description="صور المعرض (يمكن اختيار أكثر من صورة)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Create a new course for the academy.
    
    Creates a comprehensive course with all necessary details including
    pricing, content, and media files.
    """
    try:
        # Verify trainer belongs to the academy
        if trainer_id is not None:
            trainer = db.query(User).filter(
                User.id == trainer_id,
                User.user_type == "academy"  # Trainers are academy users
            ).first()
            if not trainer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="المدرب غير موجود"
                )
        
        # Convert and validate datetime if provided
        parsed_discount_ends_at = None
        if discount_ends_at:
            try:
                parsed_discount_ends_at = parser.parse(discount_ends_at)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="تنسيق التاريخ غير صحيح"
                )
        
        # Handle image upload
        image_path = None
        if image:
            try:
                image_path = await file_service.save_file(image, "courses")
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"خطأ في رفع الصورة: {str(e)}")
        
        # Handle preview video upload (no validation of type)
        preview_video_path = None
        if preview_video:
            try:
                preview_video_path = await file_service.save_any_file(preview_video, "courses/videos")
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"خطأ في رفع فيديو المعاينة: {str(e)}")
        
        # Handle gallery images list
        gallery_paths = None
        if gallery:
            gallery_paths = []
            for gfile in gallery:
                try:
                    path = await file_service.save_file(gfile, "courses/gallery")
                    gallery_paths.append(path)
                except Exception as e:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"خطأ في رفع صورة المعرض: {str(e)}")
        
        # Convert types
        price_decimal = Decimal(str(price))
        discount_price_decimal = Decimal(str(discount_price)) if discount_price else None
        
        # Calculate platform fee
        platform_fee = price_decimal * (Decimal(settings.PLATFORM_FEE_PERCENTAGE) / 100)
        
        # Check if product exists if product_id is specified
        product = None
        if product_id:
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.academy_id == current_user.academy.id
            ).first()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="المنتج غير موجود أو لا ينتمي للأكاديمية"
                )
        else:
            # Create new product automatically for the course
            product = Product(
                academy_id=current_user.academy.id,
                title=title,
                description=short_content,
                price=price_decimal,
                discount_price=discount_price_decimal,
                currency="SAR",
                product_type=ProductType.course,
                status=ProductStatus.draft,
                discount_ends_at=parsed_discount_ends_at
            )
            db.add(product)
            db.flush()  # Get product.id before commit
        
            # Create new course
        course = Course(
            id=str(uuid.uuid4()),
            product_id=product.id,  # Link to created or existing product
            academy_id=current_user.academy.id,
            trainer_id=trainer_id or current_user.id,
            category_id=category_id,
            slug=f"course-{str(uuid.uuid4())[:8]}",  # Generate slug
            content=content,
            short_content=short_content,
            preparations=preparations,
            requirements=requirements,
            learning_outcomes=learning_outcomes,
            type=CourseType(type),
            level=CourseLevel(level),
            url=url,
            featured=featured,
            course_state=CourseStatus.draft,
            platform_fee_percentage=Decimal(settings.PLATFORM_FEE_PERCENTAGE),
            image=image_path,
            preview_video=preview_video_path,
            gallery=gallery_paths
        )
        
        db.add(course)
        db.commit()
        db.refresh(course)
        
        course_data = CourseResponse.from_course_model(course).dict()
        course_data = convert_to_json_safe(course_data)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "status_code": 201,
                "error_type": None,
                "message": "تم إنشاء الكورس بنجاح",
                "data": course_data,
                "path": "/api/v1/academy/courses",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            }
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "status_code": 500,
                "error_type": "Internal Server Error",
                "message": f"حدث خطأ أثناء إنشاء الكورس: {str(e)}",
                "data": None,
                "path": "/api/v1/academy/courses",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            }
        )


@router.get("/academy/courses/{course_id}", response_model=CourseDetailResponse)
async def get_course_details(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Get detailed information for a specific course.
    
    Returns comprehensive course data including chapters, lessons, and analytics.
    """
    course = db.query(Course).options(
        joinedload(Course.category),
        joinedload(Course.trainer),
        joinedload(Course.product)
    ).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة"
        )
    
    # Load chapters separately since it's lazy="dynamic"
    chapters = course.chapters.order_by(Chapter.order_number).all()
    
    # Use the proper method to create response
    course_data = CourseDetailResponse.from_course_model(course, chapters).dict()
    course_data = convert_to_json_safe(course_data)
    
    return build_response(
        message="تم جلب تفاصيل الكورس بنجاح",
        data=course_data,
        path=f"/api/v1/academy/courses/{course_id}"
    )


@router.put("/academy/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    # Optional form fields
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    short_content: Optional[str] = Form(None),
    preparations: Optional[str] = Form(None),
    requirements: Optional[str] = Form(None),
    learning_outcomes: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    level: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    discount_price: Optional[float] = Form(None),
    discount_ends_at: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    featured: Optional[bool] = Form(None),
    product_id: Optional[int] = Form(None),
    category_id: Optional[int] = Form(None),
    trainer_id: Optional[int] = Form(None),
    # Optional files
    image: Optional[UploadFile] = File(None),
    preview_video: Optional[UploadFile] = File(None),
    gallery: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Update an existing course.
    
    Allows updating all course fields with proper validation and
    automatic recalculation of computed fields.
    """
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الكورس غير موجود"
        )
    
    try:
        update_data = {}

        if title is not None:
            update_data['title'] = title
        if content is not None:
            update_data['content'] = content
        if short_content is not None:
            update_data['short_content'] = short_content
        if preparations is not None:
            update_data['preparations'] = preparations
        if requirements is not None:
            update_data['requirements'] = requirements
        if learning_outcomes is not None:
            update_data['learning_outcomes'] = learning_outcomes
        if type is not None:
            update_data['type'] = type
        if level is not None:
            update_data['level'] = level
        if price is not None:
            update_data['price'] = price
        if discount_price is not None:
            update_data['discount_price'] = discount_price
        if discount_ends_at is not None:
            try:
                parsed_discount_ends_at = parser.parse(discount_ends_at)
                update_data['discount_ends_at'] = parsed_discount_ends_at
            except Exception:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="تنسيق التاريخ غير صحيح")
        if url is not None:
            update_data['url'] = url
        if featured is not None:
            update_data['featured'] = featured
        if product_id is not None:
            update_data['product_id'] = product_id
        if category_id is not None:
            update_data['category_id'] = category_id
        if trainer_id is not None:
            update_data['trainer_id'] = trainer_id

        # Handle files
        if image is not None:
            try:
                image_path = await file_service.save_file(image, "courses")
                update_data['image'] = image_path
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"خطأ في رفع الصورة: {str(e)}")

        if preview_video is not None:
            try:
                preview_video_path = await file_service.save_any_file(preview_video, "courses/videos")
                update_data['preview_video'] = preview_video_path
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"خطأ في رفع فيديو المعاينة: {str(e)}")

        if gallery is not None:
            gallery_paths = []
            for gfile in gallery:
                try:
                    path = await file_service.save_file(gfile, "courses/gallery")
                    gallery_paths.append(path)
                except Exception as e:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"خطأ في رفع صورة المعرض: {str(e)}")
            update_data['gallery'] = gallery_paths
        
        # Check product_id if it's being updated
        if product_id is not None:
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.academy_id == current_user.academy.id
            ).first()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="المنتج غير موجود أو لا ينتمي للأكاديمية"
                )
        
        # Recalculate platform fee if price changed
        if 'price' in update_data:
            from decimal import Decimal
            price_decimal = Decimal(str(update_data['price']))
            update_data['platform_fee_percentage'] = price_decimal * (Decimal(settings.PLATFORM_FEE_PERCENTAGE) / 100)
        
        # Update slug if title changed
        if 'title' in update_data:
            update_data['slug'] = f"{update_data['title'].lower().replace(' ', '-')}-{str(uuid.uuid4())[:8]}"
        
        for field, value in update_data.items():
            setattr(course, field, value)
        
        db.commit()
        db.refresh(course)
        
        course_data = CourseResponse.from_course_model(course).dict()
        course_data = convert_to_json_safe(course_data)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "status_code": 200,
                "error_type": None,
                "message": "تم تحديث الكورس بنجاح",
                "data": course_data,
                "path": f"/api/v1/academy/courses/{course_id}",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            }
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "status_code": 500,
                "error_type": "Internal Server Error",
                "message": f"حدث خطأ أثناء تحديث الكورس: {str(e)}",
                "data": None,
                "path": f"/api/v1/academy/courses/{course_id}",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            }
        )


@router.patch("/academy/courses/{course_id}/publish")
async def publish_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Publish a course (change from draft to published).
    
    Quick endpoint to publish a course.
    """
    # First check if course exists at all
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": "error",
                "status_code": 404,
                "error_type": "Not Found",
                "message": "الدورة غير موجودة",
                "data": {
                    "course_id": course_id,
                    "debug_info": "Course not found in database"
                },
                "path": f"/api/v1/academy/courses/{course_id}/publish",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    # Check if course belongs to current academy
    if course.academy_id != current_user.academy.id:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": "error",
                "status_code": 403,
                "error_type": "Forbidden",
                "message": "ليس لديك صلاحية للوصول لهذه الدورة",
                "data": {
                    "course_id": course_id,
                    "course_academy_id": course.academy_id,
                    "user_academy_id": current_user.academy.id,
                    "debug_info": "Course belongs to different academy"
                },
                "path": f"/api/v1/academy/courses/{course_id}/publish",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    # Load course with relationships
    course = db.query(Course).options(
        joinedload(Course.category),
        joinedload(Course.trainer),
        joinedload(Course.product)
    ).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    try:
        course.course_state = CourseStatus.published
        
        # Update related product status
        if course.product:
            course.product.status = "published"
        
        db.commit()
        db.refresh(course)
        
        course_data = CourseResponse.from_course_model(course).dict()
        course_data = convert_to_json_safe(course_data)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "status_code": 200,
                "error_type": None,
                "message": "تم نشر الكورس بنجاح",
                "data": course_data,
                "path": f"/api/v1/academy/courses/{course_id}/publish",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "status_code": 500,
                "error_type": "Internal Server Error",
                "message": f"حدث خطأ أثناء نشر الدورة: {str(e)}",
                "data": None,
                "path": f"/api/v1/academy/courses/{course_id}/publish",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.patch("/academy/courses/{course_id}/unpublish")
async def unpublish_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Unpublish a course (change from published to draft).
    
    Quick endpoint to unpublish a course.
    """
    # First check if course exists at all
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": "error",
                "status_code": 404,
                "error_type": "Not Found",
                "message": "الدورة غير موجودة",
                "data": {
                    "course_id": course_id,
                    "debug_info": "Course not found in database"
                },
                "path": f"/api/v1/academy/courses/{course_id}/unpublish",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    # Check if course belongs to current academy
    if course.academy_id != current_user.academy.id:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": "error",
                "status_code": 403,
                "error_type": "Forbidden",
                "message": "ليس لديك صلاحية للوصول لهذه الدورة",
                "data": {
                    "course_id": course_id,
                    "course_academy_id": course.academy_id,
                    "user_academy_id": current_user.academy.id,
                    "debug_info": "Course belongs to different academy"
                },
                "path": f"/api/v1/academy/courses/{course_id}/unpublish",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    # Load course with relationships
    course = db.query(Course).options(
        joinedload(Course.category),
        joinedload(Course.trainer),
        joinedload(Course.product)
    ).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    try:
        course.course_state = CourseStatus.draft
        
        # Update related product status
        if course.product:
            course.product.status = "draft"
        
        db.commit()
        db.refresh(course)
        
        course_data = CourseResponse.from_course_model(course).dict()
        course_data = convert_to_json_safe(course_data)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "status_code": 200,
                "error_type": None,
                "message": "تم إلغاء نشر الكورس بنجاح",
                "data": course_data,
                "path": f"/api/v1/academy/courses/{course_id}/unpublish",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "status_code": 500,
                "error_type": "Internal Server Error",
                "message": f"حدث خطأ أثناء إلغاء نشر الدورة: {str(e)}",
                "data": None,
                "path": f"/api/v1/academy/courses/{course_id}/unpublish",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.delete("/academy/courses/{course_id}")
async def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Delete a course.
    
    Permanently removes the course and all associated data.
    This action cannot be undone.
    """
    try:
        # Get course without loading relationships to avoid schema conflicts
        course = db.query(Course).filter(
            Course.id == course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": "error",
                    "status_code": 404,
                    "error_type": "Not Found",
                    "message": "الدورة غير موجودة",
                    "data": None,
                    "path": f"/api/v1/academy/courses/{course_id}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Store file paths before deletion for cleanup
        image_path = course.image
        preview_video_path = course.preview_video  
        gallery_paths = course.gallery
        
        # Delete related records safely to avoid constraint issues
        try:
            # Delete any student enrollments (if table exists and has compatible schema)
            db.execute(text("DELETE FROM student_courses WHERE course_id = :course_id"), {"course_id": course_id})
        except Exception as e:
            print(f"Warning: Could not delete student enrollments: {e}")
        
        try:
            # Delete chapters and lessons (cascade should handle this, but be explicit)
            db.execute(text("DELETE FROM lessons WHERE course_id = :course_id"), {"course_id": course_id})
            db.execute(text("DELETE FROM chapters WHERE course_id = :course_id"), {"course_id": course_id})
        except Exception as e:
            print(f"Warning: Could not delete course content: {e}")
        
        # Delete the course from database using raw SQL to avoid relationship loading
        db.execute(text("DELETE FROM courses WHERE id = :course_id"), {"course_id": course_id})
        db.commit()
        
        # Delete associated files safely after successful database deletion
        try:
            if image_path:
                file_service.delete_file(image_path)
        except Exception as e:
            print(f"Warning: Could not delete course image: {e}")
        
        try:
            if preview_video_path:
                file_service.delete_file(preview_video_path)
        except Exception as e:
            print(f"Warning: Could not delete preview video: {e}")
        
        try:
            if gallery_paths:
                for image in gallery_paths:
                    file_service.delete_file(image)
        except Exception as e:
            print(f"Warning: Could not delete gallery images: {e}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "status_code": 200,
                "error_type": None,
                "message": "تم حذف الكورس بنجاح",
                "data": None,
                "path": f"/api/v1/academy/courses/{course_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "status_code": 500,
                "error_type": "Internal Server Error",
                "message": f"حدث خطأ أثناء حذف الدورة: {str(e)}",
                "data": None,
                "path": f"/api/v1/academy/courses/{course_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Public endpoints (Course browsing)
@router.get("/public/courses", response_model=CourseListResponse)
async def get_public_courses(
    filters: CourseFilters = Depends(),
    db: Session = Depends(get_db)
):
    """
    Get published courses for public browsing.
    
    Returns only published courses with comprehensive filtering
    for students and visitors to browse available courses.
    """
    try:
        # Build base query for published courses only with category join
        query = db.query(Course).options(
            joinedload(Course.category),
            joinedload(Course.trainer),
            joinedload(Course.product)
        ).join(Product).filter(Course.course_state == CourseStatus.published)
        
        # Apply filters (same as academy endpoint but only for published courses)
        if filters.academy_id:
            query = query.filter(Course.academy_id == filters.academy_id)
        if filters.category_id:
            query = query.filter(Course.category_id == filters.category_id)
        if filters.level:
            query = query.filter(Course.level == filters.level)
        if filters.price_from is not None:
            query = query.filter(Product.price >= filters.price_from)
        if filters.price_to is not None:
            query = query.filter(Product.price <= filters.price_to)
        if filters.featured is not None:
            query = query.filter(Course.featured == filters.featured)
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(Product.title.ilike(search_term))
        
        # Order by featured first, then by creation date
        query = query.order_by(Course.featured.desc(), Course.created_at.desc())
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        offset = (filters.page - 1) * filters.per_page
        courses = query.offset(offset).limit(filters.per_page).all()
        
        # Calculate pagination info
        total_pages = (total + filters.per_page - 1) // filters.per_page
        
        data = {
            "courses": [CourseResponse.from_course_model(c).dict() for c in courses],
            "total": total,
            "page": filters.page,
            "per_page": filters.per_page,
            "total_pages": total_pages
        }

        return build_response(
            message="تم جلب الدورات بنجاح",
            data=data,
            path="/api/v1/public/courses"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء جلب الدورات: {str(e)}"
        )


@router.get("/public/courses/{course_id}", response_model=CourseDetailResponse)
async def get_public_course_details(
    course_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific published course.
    
    Returns course details available to the public including
    course outline, preview content, and enrollment information.
    """
    course = db.query(Course).options(
        joinedload(Course.category),
        joinedload(Course.trainer),
        joinedload(Course.product)
    ).filter(
        Course.id == course_id,
        Course.course_state == CourseStatus.published
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة أو غير متاحة"
        )
    
    data = CourseDetailResponse.from_orm(course).dict()
    return build_response(
        message="تم جلب تفاصيل الكورس بنجاح",
        data=data,
        path=f"/api/v1/public/courses/{course_id}"
    ) 