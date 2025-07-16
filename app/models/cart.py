from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from app.db.base import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(String(36), primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    cookie_id = Column(String(36), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    student = relationship("Student", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")
    
    @property
    def item_type(self):
        """Get product type from product reference"""
        try:
            if self.product and hasattr(self.product, 'product_type'):
                return self.product.product_type
            return "course"
        except Exception:
            return "course"
    
    @property
    def item_id(self):
        """Return product identifier"""
        return str(self.product_id) if self.product_id else None
    
    @property
    def item(self):
        """Return the specific item (course or digital_product) based on product type"""
        try:
            if not self.product:
                return None
            
            if self.product.product_type == "course":
                for course in self.product.courses:
                    return course
            elif self.product.product_type == "digital_product":
                # For digital products, we can access them through the product relationship
                # when the digital_product model is properly linked
                pass
            
            return None
        except Exception:
            return None
    
    @property
    def title(self):
        """Get product title"""
        try:
            if self.product and hasattr(self.product, 'title'):
                return self.product.title
            return 'عنصر غير محدد'
        except Exception:
            return 'عنصر غير محدد'
    
    @property
    def price(self):
        """Get current effective price considering active discounts"""
        try:
            if not self.product:
                return 0.0
                
            if (self.product.discount_price and 
                self.product.discount_ends_at and 
                datetime.utcnow() < self.product.discount_ends_at):
                return float(self.product.discount_price)
            
            return float(self.product.price) if self.product.price else 0.0
        except Exception:
            return 0.0
    
    @property
    def original_price(self):
        """Get original price before any discounts"""
        try:
            if self.product and self.product.price:
                return float(self.product.price)
            return 0.0
        except Exception:
            return 0.0
    
    @property
    def discount_amount(self):
        """Calculate discount amount"""
        try:
            return max(0.0, self.original_price - self.price)
        except Exception:
            return 0.0
    
    @property
    def has_discount(self):
        """Check if product currently has an active discount"""
        try:
            return self.discount_amount > 0
        except Exception:
            return False
    
    def get_item_details(self):
        """Get comprehensive item details"""
        try:
            if not self.product:
                return {
                    'id': self.item_id or 'unknown',
                    'title': 'منتج غير متوفر',
                    'price': 0,
                    'original_price': 0,
                    'discount_amount': 0,
                    'has_discount': False,
                    'image': None,
                    'description': 'المنتج غير متوفر حالياً',
                    'currency': 'SAR',
                    'type': 'unknown'
                }
            
            item = self.item
            
            return {
                'id': self.item_id,
                'title': self.title,
                'price': self.price,
                'original_price': self.original_price,
                'discount_amount': self.discount_amount,
                'has_discount': self.has_discount,
                'image': getattr(item, 'image', None) if item else None,
                'description': self.product.description or (getattr(item, 'short_content', '') if item else ''),
                'currency': self.product.currency or 'SAR',
                'type': self.item_type
            }
        except Exception as e:
            return {
                'id': self.item_id or 'unknown',
                'title': f'{self.item_type} - خطأ في التحميل',
                'price': 0,
                'original_price': 0,
                'discount_amount': 0,
                'has_discount': False,
                'image': None,
                'description': f'خطأ في تحميل البيانات: {str(e)}',
                'currency': 'SAR',
                'type': self.item_type
            }

    def soft_delete(self):
        """Soft delete cart item"""
        self.deleted_at = datetime.utcnow()
    
    @property
    def is_deleted(self):
        """Check if cart item is soft deleted"""
        return self.deleted_at is not None


class CartSession(Base):
    __tablename__ = "cart_sessions"
    
    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    cookie_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False) 