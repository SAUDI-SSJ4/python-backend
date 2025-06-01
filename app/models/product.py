from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class ProductType(str, enum.Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"
    SERVICE = "service"


class PackageType(str, enum.Enum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    CUSTOM = "custom"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    discount_price = Column(Float, nullable=True)
    type = Column(SQLEnum(ProductType), default=ProductType.DIGITAL)
    image = Column(String(255), nullable=True)
    features = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    stock_quantity = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy")
    student_products = relationship("StudentProduct", back_populates="product")


class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(PackageType), default=PackageType.BASIC)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    duration_days = Column(Integer, nullable=False)  # Subscription duration
    features = Column(JSON, nullable=True)
    limits = Column(JSON, nullable=True)  # e.g., max_courses, max_students
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academies = relationship("Academy", back_populates="package")
    subscriptions = relationship("Subscription", back_populates="package")


class DigitalProduct(Base):
    __tablename__ = "digital_products"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    discount_price = Column(Float, nullable=True)
    file_url = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)  # In bytes
    file_type = Column(String(50), nullable=True)
    thumbnail = Column(String(255), nullable=True)
    preview_url = Column(String(500), nullable=True)
    download_limit = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    sales_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy", back_populates="digital_products")
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