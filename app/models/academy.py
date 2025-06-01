from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class AcademyStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Academy(Base):
    __tablename__ = "academies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True)
    user_name = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    phone2 = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    logo = Column(String(255), nullable=True)
    cover = Column(String(255), nullable=True)
    status = Column(SQLEnum(AcademyStatus), default=AcademyStatus.ACTIVE)
    verified = Column(Boolean, default=False)
    featured = Column(Boolean, default=False)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    package = relationship("Package", back_populates="academies")
    users = relationship("AcademyUser", back_populates="academy")
    courses = relationship("Course", back_populates="academy")
    trainers = relationship("Trainer", back_populates="academy")
    wallet = relationship("AcademyWallet", back_populates="academy", uselist=False)
    finance = relationship("AcademyFinance", back_populates="academy", uselist=False)
    subscriptions = relationship("Subscription", back_populates="academy")
    coupons = relationship("Coupon", back_populates="academy")
    blogs = relationship("Blog", back_populates="academy")
    blog_posts = relationship("BlogPost", back_populates="academy")
    templates = relationship("Template", back_populates="academy")
    digital_products = relationship("DigitalProduct", back_populates="academy")


class AcademyUser(Base):
    __tablename__ = "academy_users"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    profile_image = Column(String(255), nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_owner = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy", back_populates="users")
    role = relationship("Role", back_populates="academy_users")


class Trainer(Base):
    __tablename__ = "trainers"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    specialization = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    image = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy", back_populates="trainers")
    courses = relationship("Course", back_populates="trainer")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy", back_populates="subscriptions")
    package = relationship("Package", back_populates="subscriptions")
    payment = relationship("Payment", back_populates="subscription")


class AcademyWallet(Base):
    __tablename__ = "academy_wallets"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), unique=True, nullable=False)
    balance = Column(Float, default=0.0)
    total_earned = Column(Float, default=0.0)
    total_withdrawn = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy", back_populates="wallet") 