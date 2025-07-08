from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class ItemType(str, enum.Enum):
    COURSE = "course"
    DIGITAL_PRODUCT = "digital_product"


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    cookie_id = Column(String(255), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    item_type = Column(Enum(ItemType), nullable=False, default=ItemType.COURSE)
    item_id = Column(String(255), nullable=False, index=True)
    course_id = Column(String(255), ForeignKey("courses.id"), nullable=True, index=True)
    digital_product_id = Column(Integer, ForeignKey("digital_products.id"), nullable=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=True, index=True)
    quantity = Column(Integer, default=1, nullable=False)
    price = Column(Numeric(10, 2), nullable=True)
    price_at_time = Column(Numeric(10, 2), nullable=True)
    extra_data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    student = relationship("Student", back_populates="cart_items")
    course = relationship("Course", back_populates="cart_items")
    digital_product = relationship("DigitalProduct", back_populates="cart_items")
    academy = relationship("Academy")
    
    @property
    def item(self):
        if self.item_type == ItemType.COURSE:
            return self.course
        elif self.item_type == ItemType.DIGITAL_PRODUCT:
            return self.digital_product
        return None
    
    @property
    def total_price(self):
        price = self.price or self.price_at_time or 0
        return float(price) * self.quantity
    
    def soft_delete(self):
        self.deleted_at = datetime.utcnow()
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None
    
    def get_item_details(self):
        item = self.item
        if item:
            return {
                'id': item.id,
                'title': getattr(item, 'title', 'غير متوفر'),
                'price': getattr(item, 'price', 0),
                'image': getattr(item, 'image', None),
                'description': getattr(item, 'description', '')
            }
        return None


class CartSession(Base):
    __tablename__ = "cart_sessions"
    
    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    cookie_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False) 