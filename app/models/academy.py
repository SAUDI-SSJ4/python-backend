from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum, Date, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.db.base import Base
from app.models.role import Role


class AcademyStatus(str, Enum):
    ACTIVE = "active"
    UNACTIVE = "unactive"
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


class Academy(Base):
    __tablename__ = "academies"

    id = Column(BigInteger, primary_key=True, index=True)
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
    status = Column(SQLEnum(AcademyStatus, values_callable=lambda obj: [e.value for e in obj]), default="active", index=True)
    trial_status = Column(SQLEnum(TrialStatus, values_callable=lambda obj: [e.value for e in obj]), default="available", index=True)
    trial_start = Column(Date, nullable=True)
    trial_end = Column(Date, nullable=True)
    users_count = Column(Integer, default=0)
    courses_count = Column(Integer, default=0)
    package_id = Column(BigInteger, nullable=True)
    slug = Column(String(155), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # العلاقات
    academy_users = relationship("AcademyUser", back_populates="academy")
    coupons = relationship("Coupon", back_populates="academy")


class AcademyUser(Base):
    __tablename__ = "academy_users"

    id = Column(BigInteger, primary_key=True, index=True)
    academy_id = Column(BigInteger, ForeignKey("academies.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    user_role = Column(SQLEnum(AcademyUserRole, values_callable=lambda obj: [e.value for e in obj]), default="admin", index=True)
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy", back_populates="academy_users")
    user = relationship("User", back_populates="academy_memberships")


class Trainer(Base):
    __tablename__ = "trainers"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    academy_id = Column(BigInteger, ForeignKey("academies.id"), nullable=False)
    bio = Column(Text, nullable=True)
    specialization = Column(String(255), nullable=True)
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User")
    academy = relationship("Academy")


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