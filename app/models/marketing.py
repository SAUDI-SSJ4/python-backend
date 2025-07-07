from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class CouponType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    type = Column(SQLEnum(CouponType), default=CouponType.PERCENTAGE)
    value = Column(Float, nullable=False)  # Percentage or fixed amount
    minimum_amount = Column(Float, nullable=True)
    maximum_discount = Column(Float, nullable=True)  # For percentage coupons
    usage_limit = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy", back_populates="coupons")
    coupon_usages = relationship("CouponUsage", back_populates="coupon")


class AffiliateLink(Base):
    __tablename__ = "affiliate_links"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    affiliate_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)
    commission_rate = Column(Float, default=0.10)  # 10% default
    clicks_count = Column(Integer, default=0)
    conversions_count = Column(Integer, default=0)
    total_earned = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy")
    affiliate = relationship("Student")
