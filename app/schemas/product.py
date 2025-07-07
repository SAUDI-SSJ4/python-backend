from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum
import pytz


# Enums for validation
class ProductTypeEnum(str, Enum):
    COURSE = "course"
    DIGITAL_PRODUCT = "digital_product"
    PACKAGE = "package"


class ProductStatusEnum(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PackageTypeEnum(str, Enum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    CUSTOM = "custom"


# Product schemas
class ProductBase(BaseModel):
    """Base product schema with common fields"""
    title: str = Field(..., min_length=3, max_length=255, description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: Decimal = Field(..., ge=0, description="Product price")
    discount_price: Optional[Decimal] = Field(None, ge=0, description="Discounted price")
    currency: str = Field("SAR", description="Currency code")
    product_type: Optional[ProductTypeEnum] = Field(None, description="Product type")
    status: ProductStatusEnum = Field(ProductStatusEnum.DRAFT, description="Product status")
    discount_ends_at: Optional[datetime] = Field(None, description="Discount expiration date")

    @validator('discount_price')
    def validate_discount_price(cls, v, values):
        """Validate discount price is less than regular price"""
        if v is not None and 'price' in values:
            if v >= values['price']:
                raise ValueError('سعر الخصم يجب أن يكون أقل من السعر الأصلي')
        return v

    @validator('discount_ends_at')
    def validate_discount_end_date(cls, v):
        """Validate discount end date is in the future - Fixed timezone handling"""
        if v is not None:
            # التعامل الصحيح مع التواريخ بنوعيها timezone-aware و timezone-naive
            if v.tzinfo is not None:
                # إذا كان التاريخ timezone-aware
                current_time = datetime.now(pytz.UTC)
            else:
                # إذا كان التاريخ timezone-naive
                current_time = datetime.utcnow()
            
            if v <= current_time:
                raise ValueError('تاريخ انتهاء الخصم يجب أن يكون في المستقبل')
        return v


class ProductCreate(ProductBase):
    """Schema for creating a new product"""
    academy_id: int = Field(..., gt=0, description="Academy ID")

    class Config:
        schema_extra = {
            "example": {
                "academy_id": 1,
                "title": "منتج تعليمي متميز",
                "description": "وصف تفصيلي للمنتج التعليمي",
                "price": 199.99,
                "currency": "SAR",
                "product_type": "course",
                "status": "draft"
            }
        }


class ProductUpdate(BaseModel):
    """Schema for updating an existing product"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    discount_price: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = None
    product_type: Optional[ProductTypeEnum] = None
    status: Optional[ProductStatusEnum] = None
    discount_ends_at: Optional[datetime] = None


class ProductResponse(ProductBase):
    """Schema for product response"""
    id: int
    academy_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


# Digital Product schemas
class DigitalProductBase(BaseModel):
    """Base digital product schema"""
    name: str = Field(..., min_length=3, max_length=255, description="Digital product name")
    description: Optional[str] = Field(None, description="Product description")
    price: Decimal = Field(..., ge=0, description="Product price")
    discount_price: Optional[Decimal] = Field(None, ge=0, description="Discounted price")
    file_url: Optional[str] = Field(None, description="File download URL")
    file_size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    file_type: Optional[str] = Field(None, description="File MIME type")
    thumbnail: Optional[str] = Field(None, description="Thumbnail image URL")
    preview_url: Optional[str] = Field(None, description="Preview file URL")
    download_limit: Optional[int] = Field(None, ge=1, description="Maximum downloads per purchase")
    is_active: bool = Field(True, description="Is product active")

    @validator('discount_price')
    def validate_discount_price(cls, v, values):
        if v is not None and 'price' in values:
            if v >= values['price']:
                raise ValueError('سعر الخصم يجب أن يكون أقل من السعر الأصلي')
        return v


class DigitalProductCreate(DigitalProductBase):
    """Schema for creating a digital product"""
    academy_id: int = Field(..., gt=0, description="Academy ID")


class DigitalProductUpdate(BaseModel):
    """Schema for updating a digital product"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    discount_price: Optional[Decimal] = Field(None, ge=0)
    file_url: Optional[str] = None
    file_size: Optional[int] = Field(None, ge=0)
    file_type: Optional[str] = None
    thumbnail: Optional[str] = None
    preview_url: Optional[str] = None
    download_limit: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class DigitalProductResponse(DigitalProductBase):
    """Schema for digital product response"""
    id: int
    academy_id: int
    slug: Optional[str]
    sales_count: int
    rating: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


# Package schemas
class PackageBase(BaseModel):
    """Base package schema"""
    name: str = Field(..., min_length=3, max_length=255, description="Package name")
    type: PackageTypeEnum = Field(PackageTypeEnum.BASIC, description="Package type")
    description: Optional[str] = Field(None, description="Package description")
    price: Decimal = Field(..., ge=0, description="Package price")
    duration_days: int = Field(..., gt=0, description="Package duration in days")
    features: Optional[Dict[str, Any]] = Field(None, description="Package features")
    limits: Optional[Dict[str, Any]] = Field(None, description="Package limits")
    is_active: bool = Field(True, description="Is package active")


class PackageCreate(PackageBase):
    """Schema for creating a package"""
    pass


class PackageUpdate(BaseModel):
    """Schema for updating a package"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    type: Optional[PackageTypeEnum] = None
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    duration_days: Optional[int] = Field(None, gt=0)
    features: Optional[Dict[str, Any]] = None
    limits: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class PackageResponse(PackageBase):
    """Schema for package response"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


# Student Product Purchase schemas
class StudentProductBase(BaseModel):
    """Base student product purchase schema"""
    quantity: int = Field(1, ge=1, description="Quantity purchased")


class StudentProductCreate(StudentProductBase):
    """Schema for student product purchase"""
    student_id: int = Field(..., gt=0, description="Student ID")
    product_id: int = Field(..., gt=0, description="Product ID")
    payment_id: Optional[int] = Field(None, description="Payment ID")


class StudentProductResponse(StudentProductBase):
    """Schema for student product purchase response"""
    id: int
    student_id: int
    product_id: int
    payment_id: Optional[int]
    purchased_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Product List and Search schemas
class ProductFilters(BaseModel):
    """Schema for product filtering and search"""
    academy_id: Optional[int] = Field(None, description="Filter by academy")
    product_type: Optional[ProductTypeEnum] = Field(None, description="Filter by type")
    status: Optional[ProductStatusEnum] = Field(None, description="Filter by status")
    price_from: Optional[Decimal] = Field(None, ge=0, description="Minimum price")
    price_to: Optional[Decimal] = Field(None, ge=0, description="Maximum price")
    search: Optional[str] = Field(None, min_length=2, max_length=100, description="Search query")
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(10, ge=1, le=100, description="Items per page")

    @validator('price_to')
    def validate_price_range(cls, v, values):
        if v is not None and 'price_from' in values and values['price_from'] is not None:
            if v < values['price_from']:
                raise ValueError('السعر الأقصى يجب أن يكون أكبر من السعر الأدنى')
        return v


class ProductListResponse(BaseModel):
    """Schema for product list with pagination"""
    products: List[ProductResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

    class Config:
        from_attributes = True 