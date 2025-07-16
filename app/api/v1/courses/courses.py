from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
from dateutil import parser

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user, get_current_student, get_current_user
from app.models.course import Course, CourseStatus, CourseType, CourseLevel
from app.models.academy import Academy
from app.models.user import User
from app.models.product import Product, ProductType, ProductStatus
from app.schemas.course import (
    CourseCreate, CourseUpdate, CourseResponse, CourseDetailResponse,
    CourseListResponse, CourseFilters, CourseStatusUpdate
)
from app.services.file_service import file_service
from app.core.config import settings

router = APIRouter()


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
        # Build base query for academy's courses with product join
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
        
        return CourseListResponse(
            courses=[CourseResponse.from_course_model(course) for course in courses],
            total=total,
            page=filters.page,
            per_page=filters.per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء جلب الدورات: {str(e)}"
        )


@router.post("/academy/courses", response_model=CourseResponse)
async def create_course(
    category_id: int = Form(..., description="معرف الفئة"),
    trainer_id: int = Form(..., description="معرف المدرب"),
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
                from dateutil import parser
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
                image_path = await file_service.upload_course_image(image, None)  # course_id will be set after creation
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"خطأ في رفع الصورة: {str(e)}"
                )
        
        # Convert types
        from decimal import Decimal
        price_decimal = Decimal(str(price))
        discount_price_decimal = Decimal(str(discount_price)) if discount_price else None
        
        # إنشاء المنتج تلقائياً للكورس
        product = Product(
            academy_id=current_user.academy.id,
            title=title,
            description=short_content,
            price=price_decimal,
            discount_price=discount_price_decimal,
            currency="SAR",
            product_type="course",  # string value
            status="draft",  # string value
            discount_ends_at=parsed_discount_ends_at
        )
        
        db.add(product)
        db.flush()  # للحصول على product.id قبل الـ commit
        
        # Calculate platform fee
        platform_fee = price_decimal * (Decimal(settings.PLATFORM_FEE_PERCENTAGE) / 100)
        
        # Create course object - باستخدام course_state والحقول الصحيحة فقط
        course = Course(
            id=str(uuid.uuid4()),
            academy_id=current_user.academy.id,
            category_id=category_id,
            trainer_id=trainer_id,
            product_id=product_id or product.id,  # استخدام product_id المرسل أو المنتج المُنشأ تلقائياً
            slug=f"{title.lower().replace(' ', '-')}-{str(uuid.uuid4())[:8]}",
            image=image_path or "",
            content=content,
            short_content=short_content,
            preparations=preparations,
            requirements=requirements,
            learning_outcomes=learning_outcomes,
            gallery=None,  # سيتم إضافة دعم المعرض لاحقاً
            preview_video=None,  # سيتم إضافة دعم الفيديو لاحقاً
            type=type,
            level=level,
            url=url,
            featured=featured,
            course_state=CourseStatus.DRAFT,  # استخدام course_state بدلاً من status
            platform_fee_percentage=platform_fee
        )
        
        db.add(course)
        db.commit()
        db.refresh(course)
        
        return CourseResponse.from_course_model(course)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء إنشاء الدورة: {str(e)}"
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
    
    return CourseDetailResponse.from_course_model(course)


@router.put("/academy/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    course_data: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Update an existing course.
    
    Allows updating all course fields with proper validation and
    automatic recalculation of computed fields.
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
    
    try:
        # Update fields
        update_data = course_data.dict(exclude_unset=True)
        
        # Recalculate platform fee if price changed
        if 'price' in update_data:
            from decimal import Decimal
            update_data['platform_fee_percentage'] = update_data['price'] * (Decimal(settings.PLATFORM_FEE_PERCENTAGE) / 100)
        
        # Update slug if title changed
        if 'title' in update_data:
            update_data['slug'] = f"{update_data['title'].lower().replace(' ', '-')}-{str(uuid.uuid4())[:8]}"
        
        # تحديث المنتج المرتبط بالكورس
        product = db.query(Product).filter(Product.id == course.product_id).first()
        if product:
            # تحديث بيانات المنتج حسب تحديثات الكورس
            product_updates = {}
            if 'title' in update_data:
                product_updates['title'] = update_data['title']
            if 'short_content' in update_data:
                product_updates['description'] = update_data['short_content']
            if 'price' in update_data:
                product_updates['price'] = update_data['price']
            if 'discount_price' in update_data:
                product_updates['discount_price'] = update_data['discount_price']
            if 'discount_ends_at' in update_data:
                product_updates['discount_ends_at'] = update_data['discount_ends_at']
            
            for field, value in product_updates.items():
                setattr(product, field, value)
        
        # تحديث الكورس
        for field, value in update_data.items():
            setattr(course, field, value)
        
        db.commit()
        db.refresh(course)
        
        return CourseResponse.from_course_model(course)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء تحديث الدورة: {str(e)}"
        )


@router.patch("/academy/courses/{course_id}/status", response_model=CourseResponse)
async def update_course_status(
    course_id: str,
    status_data: CourseStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
):
    """
    Update course status (publish/unpublish/archive).
    
    Allows quick status changes for course management.
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
    
    try:
        # تحديث حالة الكورس
        course.course_state = status_data.status
        
        # تحديث حالة المنتج المرتبط لتتطابق مع حالة الكورس
        product = db.query(Product).filter(Product.id == course.product_id).first()
        if product:
            # تحويل حالة الكورس إلى حالة منتج مناسبة
            if status_data.status == CourseStatus.PUBLISHED:
                product.status = "published"
            elif status_data.status == CourseStatus.ARCHIVED:
                product.status = "archived"
            else:  # DRAFT
                product.status = "draft"
        
        db.commit()
        db.refresh(course)
        
        return CourseResponse.from_course_model(course)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء تحديث حالة الدورة: {str(e)}"
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
    
    try:
        # Delete associated files
        if course.image:
            file_service.delete_file(course.image)
        
        if course.preview_video:
            file_service.delete_file(course.preview_video)
        
        if course.gallery:
            for image in course.gallery:
                file_service.delete_file(image)
        
        # حذف المنتج المرتبط بالكورس
        product = db.query(Product).filter(Product.id == course.product_id).first()
        if product:
            db.delete(product)
        
        db.delete(course)
        db.commit()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": True,
                "message": "تم حذف الدورة بنجاح"
            }
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
        # Build base query for published courses only with product join
        query = db.query(Course).options(
            joinedload(Course.category),
            joinedload(Course.trainer),
            joinedload(Course.product)
        ).join(Product).filter(Course.course_state == CourseStatus.PUBLISHED)
        
        # Apply filters (same as academy endpoint but only for published courses)
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
        
        return CourseListResponse(
            courses=[CourseResponse.from_course_model(course) for course in courses],
            total=total,
            page=filters.page,
            per_page=filters.per_page,
            total_pages=total_pages
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
        Course.course_state == CourseStatus.PUBLISHED
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
                    detail="الدورة غير موجودة أو غير متاحة"
    )
    
    return CourseDetailResponse.from_course_model(course) 