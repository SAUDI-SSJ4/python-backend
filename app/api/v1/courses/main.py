from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Any, Dict
import uuid
from datetime import datetime
from dateutil import parser
from decimal import Decimal

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user, get_current_student, get_current_user
from app.models.course import Course, CourseStatus, CourseType, CourseLevel
from app.models.academy import Academy
from app.models.user import User
from app.schemas.course import (
    CourseCreate, CourseResponse, CourseDetailResponse,
    CourseListResponse, CourseFilters, CourseStatusUpdate
)
from app.services.file_service import file_service
from app.core.config import settings
from app.models.product import Product, ProductType, ProductStatus
from app.models.chapter import Chapter

router = APIRouter()


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
    """إرجاع JSONResponse موحد"""
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
        # Build base query for academy's courses
        query = db.query(Course).filter(Course.academy_id == current_user.academy.id)
        
        # Apply filters
        if filters.category_id:
            query = query.filter(Course.category_id == filters.category_id)
        
        if filters.trainer_id:
            query = query.filter(Course.trainer_id == filters.trainer_id)
        
        if filters.status:
            query = query.filter(Course.status == filters.status)
        
        if filters.type:
            query = query.filter(Course.type == filters.type)
        
        if filters.level:
            query = query.filter(Course.level == filters.level)
        
        if filters.price_from is not None:
            query = query.filter(Course.price >= filters.price_from)
        
        if filters.price_to is not None:
            query = query.filter(Course.price <= filters.price_to)
        
        if filters.featured is not None:
            query = query.filter(Course.featured == filters.featured)
        
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(Course.title.ilike(search_term))
        
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
        
        # التحقق من وجود المنتج إذا تم تحديد product_id
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
            # إنشاء منتج جديد تلقائياً للكورس
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
            db.flush()  # للحصول على product.id قبل الـ commit
        
        # Create course object
        course = Course(
            id=str(uuid.uuid4()),
            product_id=product.id,  # ربط بالمنتج المُنشأ أو الموجود
            academy_id=current_user.academy.id,
            category_id=category_id,
            trainer_id=trainer_id if trainer_id is not None else current_user.id,
            slug=f"{title.lower().replace(' ', '-')}-{str(uuid.uuid4())[:8]}",
            image=image_path or "",
            content=content,
            short_content=short_content,
            preparations=preparations,
            requirements=requirements,
            learning_outcomes=learning_outcomes,
            gallery=gallery_paths,
            preview_video=preview_video_path,
            course_state=CourseStatus.draft,  # استخدام lowercase enum
            type=CourseType.recorded if type == "recorded" else CourseType.live if type == "live" else CourseType.attend,
            level=CourseLevel.beginner if level == "beginner" else CourseLevel.intermediate if level == "intermediate" else CourseLevel.advanced,
            url=url,
            featured=featured,
            platform_fee_percentage=platform_fee
        )
        
        db.add(course)
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
        
        # التحقق من product_id إذا تم تحديثه
        if 'product_id' in update_data:
            product = db.query(Product).filter(
                Product.id == update_data['product_id'],
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
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة"
        )
    
    try:
        course.course_state = CourseStatus.published
        db.commit()
        db.refresh(course)
        
        return build_response(
            message="تم نشر الكورس بنجاح",
            data=CourseResponse.from_course_model(course).dict(),
            path=f"/api/v1/academy/courses/{course_id}/publish"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء نشر الدورة: {str(e)}"
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
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة"
        )
    
    try:
        course.course_state = CourseStatus.draft
        db.commit()
        db.refresh(course)
        
        return build_response(
            message="تم إلغاء نشر الكورس بنجاح",
            data=CourseResponse.from_course_model(course).dict(),
            path=f"/api/v1/academy/courses/{course_id}/unpublish"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء إلغاء نشر الدورة: {str(e)}"
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
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدورة غير موجودة"
        )
    
    try:
        # Delete associated files
        if course.image:
            file_service.delete_file(course.image)
        
        if course.preview_video:
            file_service.delete_file(course.preview_video)
        
        if course.gallery:
            for image in course.gallery:
                file_service.delete_file(image)
        
        db.delete(course)
        db.commit()
        
        return build_response(
            message="تم حذف الكورس بنجاح",
            data=None,
            path=f"/api/v1/academy/courses/{course_id}"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء حذف الدورة: {str(e)}"
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
        # Build base query for published courses only
        query = db.query(Course).filter(Course.course_state == CourseStatus.published)
        
        # Apply filters (same as academy endpoint but only for published courses)
        if filters.academy_id:
            query = query.filter(Course.academy_id == filters.academy_id)
        if filters.category_id:
            query = query.filter(Course.category_id == filters.category_id)
        if filters.level:
            query = query.filter(Course.level == filters.level)
        if filters.price_from is not None:
            query = query.filter(Course.price >= filters.price_from)
        if filters.price_to is not None:
            query = query.filter(Course.price <= filters.price_to)
        if filters.featured is not None:
            query = query.filter(Course.featured == filters.featured)
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(Course.title.ilike(search_term))
        
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
    course = db.query(Course).filter(
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