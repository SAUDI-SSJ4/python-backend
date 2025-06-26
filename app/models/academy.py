from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.db.base import Base
from app.models.role import Role


class AcademyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "unactive"
    DRAFT = "draft"


class TrialStatus(str, Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    EXPIRED = "expired"
    USED = "used"
    NOT_ELIGIBLE = "not_eligible"


class AcademyUserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    TRAINER = "trainer"
    STAFF = "staff"


class Academy(Base):
    __tablename__ = "academies"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(String(255), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    license = Column(String(255), nullable=True)
    name = Column(String(200), nullable=False)
    about = Column(Text, nullable=True)
    image = Column(String(255), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    facebook = Column(String(255), nullable=True)
    twitter = Column(String(255), nullable=True)
    instagram = Column(String(255), nullable=True)
    snapchat = Column(String(255), nullable=True)
    status = Column(SQLEnum(AcademyStatus), default="active", index=True)
    trial_status = Column(SQLEnum(TrialStatus), default=TrialStatus.AVAILABLE, index=True)
    trial_start = Column(Date, nullable=True)
    trial_end = Column(Date, nullable=True)
    users_count = Column(Integer, default=0)
    courses_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    package_id = Column(Integer, nullable=True)
    slug = Column(String(155), unique=True, index=True, nullable=True)

    # العلاقات الأساسية فقط - بدون النماذج غير الموجودة
    user = relationship("User", back_populates="academy_profile")
    academy_users = relationship("AcademyUser", back_populates="academy")
    # معلق مؤقتاً حتى يتم إصلاح models conflicts
    # finance = relationship("AcademyFinance", uselist=False, back_populates="academy")
    # coupons = relationship("Coupon", back_populates="academy")


class AcademyUser(Base):
    __tablename__ = "academy_users"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_role = Column(SQLEnum(AcademyUserRole), default="staff", index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy", back_populates="academy_users")
    user = relationship("User", back_populates="academy_memberships")
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

    # Relationships - معلق مؤقتاً لحل conflicts
    # courses = relationship("Course", back_populates="trainer")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy")
    payment = relationship("Payment", foreign_keys=[payment_id])


class AcademyWallet(Base):
    __tablename__ = "academy_wallets"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), unique=True, nullable=False)
    balance = Column(Float, default=0.0)
    total_earned = Column(Float, default=0.0)
    total_withdrawn = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships (تم إزالة العلاقة لتجنب المشاكل) 