from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON, TIMESTAMP
from sqlalchemy.types import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class ProductType(str, enum.Enum):
    course = "course"
    digital_product = "digital_product"
    package = "package"


class ProductStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class Product(Base):
    """
    Product model that serves as unified reference for all product types
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False, default=0.00)
    discount_price = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), nullable=False, default='SAR')
    product_type = Column(SQLEnum(ProductType), nullable=True)
    status = Column(SQLEnum(ProductStatus), nullable=False, default=ProductStatus.draft)
    discount_ends_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    academy = relationship("Academy")
    courses = relationship("Course", back_populates="product")
    student_products = relationship("StudentProduct", back_populates="product")
    cart_items = relationship("Cart", back_populates="product")


class PackageType(str, enum.Enum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    CUSTOM = "custom"


class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(PackageType), default=PackageType.BASIC)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    duration_days = Column(Integer, nullable=False)  # Subscription duration
    features = Column(JSON, nullable=True)
    limits = Column(JSON, nullable=True)  # e.g., max_courses, max_students
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    subscriptions = relationship("Subscription", foreign_keys="Subscription.package_id")


class DigitalProduct(Base):
    __tablename__ = "digital_products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), index=True)
    description = Column(Text, nullable=True)
    excerpt = Column(String(255), nullable=True)
    price = Column(Numeric(10, 2), nullable=False, default=0.00)
    discount_price = Column(Numeric(10, 2), nullable=True)
    discount_ends_at = Column(DateTime, nullable=True)
    file = Column(String(255), nullable=True)
    file_type = Column(String(50), nullable=True)
    file_size_bytes = Column(Integer, nullable=True, default=0)
    preview_image = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    downloads_count = Column(Integer, nullable=False, default=0)
    avg_rating = Column(Numeric(3, 2), nullable=False, default=0.00)
    ratings_count = Column(Integer, nullable=False, default=0)
    platform_fee_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    academy = relationship("Academy")
    student_digital_products = relationship("StudentDigitalProduct", back_populates="digital_product")
    ratings = relationship("DigitalProductRating", back_populates="digital_product")


class StudentDigitalProduct(Base):
    __tablename__ = "student_digital_products"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    digital_product_id = Column(Integer, ForeignKey("digital_products.id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    download_count = Column(Integer, default=0)
    last_download_at = Column(DateTime(timezone=True), nullable=True)
    purchased_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("Student", back_populates="student_digital_products")
    digital_product = relationship("DigitalProduct", back_populates="student_digital_products")
    payment = relationship("Payment")


class DigitalProductRating(Base):
    __tablename__ = "digital_product_ratings"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    digital_product_id = Column(Integer, ForeignKey("digital_products.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    student = relationship("Student", back_populates="digital_product_ratings")
    digital_product = relationship("DigitalProduct", back_populates="ratings")


class StudentProduct(Base):
    __tablename__ = "student_products"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    quantity = Column(Integer, default=1)
    purchased_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("Student", back_populates="student_products")
    product = relationship("Product", back_populates="student_products")
    payment = relationship("Payment") 