from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from app.db.base import Base


class Cart(Base):
    """نموذج السلة لإدارة عناصر الشراء"""
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    
    # معرف الطالب (للمستخدمين المسجلين)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    
    # معرف الجلسة (للضيوف)
    session_id = Column(String(255), nullable=True, index=True)
    
    # معرف الكورس
    course_id = Column(String(255), ForeignKey("courses.id"), nullable=False, index=True)
    
    # معرف الأكاديمية
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=True, index=True)
    
    # الكمية
    quantity = Column(Integer, default=1, nullable=False)
    
    # السعر وقت الإضافة
    price = Column(Numeric(10, 2), nullable=True)
    price_at_time = Column(Numeric(10, 2), nullable=True)
    
    # تواريخ النظام
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # العلاقات
    student = relationship("Student", back_populates="cart_items")
    course = relationship("Course", back_populates="cart_items")
    academy = relationship("Academy")
    
    @property
    def total_price(self):
        """حساب السعر الإجمالي للعنصر"""
        price = self.price or self.price_at_time or 0
        return float(price) * self.quantity
    
    def soft_delete(self):
        """حذف ناعم للعنصر"""
        self.deleted_at = datetime.utcnow()
    
    @property
    def is_deleted(self):
        """فحص إذا كان العنصر محذوف"""
        return self.deleted_at is not None
    
    def __repr__(self):
        return f"<Cart(id={self.id}, student_id={self.student_id}, course_id={self.course_id})>"


class CartSession(Base):
    """نموذج جلسات السلة للضيوف"""
    __tablename__ = "cart_sessions"
    
    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    def __repr__(self):
        return f"<CartSession(id={self.id}, expires_at={self.expires_at})>" 