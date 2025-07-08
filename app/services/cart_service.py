"""
Cart service for managing shopping cart operations.
Supports both authenticated students and guest users through cookies.
"""

from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from app.models.cart import Cart, ItemType
from app.models.course import Course
from app.models.student import Student
from app.models.product import Product, DigitalProduct
from app.models.payment import Coupon, CouponUsage
from app.core.config import settings


class CartService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def extract_cookie_id(self, cookie_header: Optional[str]) -> Optional[str]:
        """Extract cookie ID from header safely"""
        if not cookie_header:
            return None
        
        if '=' in cookie_header:
            parts = cookie_header.split('=', 1)
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
        else:
            return cookie_header.strip()
        
        return None
    
    def get_or_create_cookie_id(self, cookie_id: Optional[str] = None) -> str:
        if cookie_id:
            return cookie_id
        return str(uuid.uuid4())
    
    def get_cart_items(
        self, 
        student_id: Optional[int] = None, 
        cookie_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[Cart]:
        query = self.db.query(Cart).filter(Cart.deleted_at.is_(None))
        
        if student_id:
            query = query.filter(
                or_(
                    Cart.student_id == student_id,
                    Cart.cookie_id == cookie_id
                )
            )
        elif cookie_id:
            query = query.filter(Cart.cookie_id == cookie_id)
        elif session_id:
            query = query.filter(
                and_(
                    Cart.student_id.is_(None),
                    Cart.session_id == session_id
                )
            )
        else:
            return []
        
        return query.all()
    
    def add_to_cart(
        self,
        item_type: str,
        item_id: str,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None,
        session_id: Optional[str] = None,
        quantity: int = 1
    ) -> Dict[str, Any]:
        try:
            if item_type not in ['course', 'digital_product']:
                raise ValueError("Invalid item type")
            
            item = self._get_item(item_type, item_id)
            if not item:
                raise ValueError(f"{item_type.title()} not found")
            
            if hasattr(item, 'is_published') and not item.is_published:
                raise ValueError(f"{item_type.title()} is not available for purchase")
            
            price = getattr(item, 'price', 0)
            if hasattr(item, 'current_price'):
                price = item.current_price
            
            if not student_id and not cookie_id:
                cookie_id = self.get_or_create_cookie_id()
            
            existing_item = self._get_existing_cart_item(
                item_type, item_id, student_id, cookie_id, session_id
            )
            
            if existing_item:
                existing_item.quantity += quantity
                existing_item.updated_at = datetime.utcnow()
                self.db.commit()
                return {
                    "message": "Cart item quantity updated",
                    "item": existing_item,
                    "action": "updated",
                    "cookie_id": cookie_id
                }
            else:
                cart_item = Cart(
                    student_id=student_id,
                    cookie_id=cookie_id,
                    session_id=session_id if not student_id else None,
                    item_type=ItemType(item_type),
                    item_id=item_id,
                    quantity=quantity,
                    price=price
                )
                
                if item_type == 'course':
                    cart_item.course_id = item_id
                    cart_item.academy_id = getattr(item, 'academy_id', None)
                elif item_type == 'digital_product':
                    cart_item.digital_product_id = item_id
                
                self.db.add(cart_item)
                self.db.commit()
                self.db.refresh(cart_item)
                
                return {
                    "message": "Item added to cart",
                    "item": cart_item,
                    "action": "added",
                    "cookie_id": cookie_id
                }
        except Exception as e:
            self.db.rollback()
            raise e
    
    def remove_from_cart(
        self,
        cart_item_id: int,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            cart_item = self._get_cart_item(cart_item_id, student_id, cookie_id, session_id)
            
            if not cart_item:
                raise ValueError("Cart item not found")
            
            cart_item.soft_delete()
            self.db.commit()
            
            return {
                "message": "Item removed from cart",
                "item_id": cart_item_id
            }
        except Exception as e:
            self.db.rollback()
            raise e
    
    def update_cart_item(
        self,
        cart_item_id: int,
        quantity: int,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            if quantity <= 0:
                return self.remove_from_cart(cart_item_id, student_id, cookie_id, session_id)
            
            cart_item = self._get_cart_item(cart_item_id, student_id, cookie_id, session_id)
            
            if not cart_item:
                raise ValueError("Cart item not found")
            
            cart_item.quantity = quantity
            cart_item.updated_at = datetime.utcnow()
            self.db.commit()
            
            return {
                "message": "Cart item updated",
                "item": cart_item
            }
        except Exception as e:
            self.db.rollback()
            raise e
    
    def clear_cart(
        self,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            cart_items = self.get_cart_items(student_id, cookie_id, session_id)
            
            for item in cart_items:
                item.soft_delete()
            
            self.db.commit()
            
            return {
                "message": "Cart cleared successfully",
                "items_cleared": len(cart_items)
            }
        except Exception as e:
            self.db.rollback()
            raise e
    
    def get_cart_summary(
        self,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None,
        session_id: Optional[str] = None,
        coupon_code: Optional[str] = None
    ) -> Dict[str, Any]:
        cart_items = self.get_cart_items(student_id, cookie_id, session_id)
        
        if not cart_items:
            return {
                "items": [],
                "subtotal": 0.00,
                "tax_amount": 0.00,
                "discount_amount": 0.00,
                "total": 0.00,
                "currency": "SAR",
                "items_count": 0,
                "total_quantity": 0,
                "coupon_applied": None
            }
        
        subtotal = sum(item.total_price for item in cart_items)
        
        discount_amount = 0.00
        coupon_applied = None
        
        if coupon_code:
            coupon_result = self.apply_coupon(coupon_code, subtotal, student_id)
            if coupon_result["valid"]:
                discount_amount = coupon_result["discount_amount"]
                coupon_applied = coupon_result["coupon"]
        
        tax_rate = Decimal('0.15')
        discounted_subtotal = subtotal - discount_amount
        tax_amount = discounted_subtotal * tax_rate
        total = discounted_subtotal + tax_amount
        
        items_data = []
        for item in cart_items:
            item_details = item.get_item_details()
            if item_details:
                items_data.append({
                    "cart_id": item.id,
                    "item_id": item.item_id,
                    "item_type": item.item_type.value,
                    "title": item_details['title'],
                    "price": item_details['price'],
                    "image": item_details['image'],
                    "quantity": item.quantity,
                    "total_price": item.total_price
                })
        
        return {
            "items": items_data,
            "subtotal": float(subtotal),
            "tax_amount": float(tax_amount),
            "discount_amount": float(discount_amount),
            "total": float(total),
            "currency": "SAR",
            "items_count": len(cart_items),
            "total_quantity": sum(item.quantity for item in cart_items),
            "coupon_applied": coupon_applied
        }
    
    def apply_coupon(
        self,
        coupon_code: str,
        subtotal: Decimal,
        student_id: Optional[int] = None
    ) -> Dict[str, Any]:
        coupon_code = coupon_code.strip().upper()
        
        coupon = self.db.query(Coupon).filter(
            and_(
                Coupon.code == coupon_code,
                Coupon.is_active == True
            )
        ).first()
        
        if not coupon:
            return {"valid": False, "error": "كوبون غير صالح"}
        
        current_date = datetime.now().date()
        if coupon.start_date and current_date < coupon.start_date:
            return {"valid": False, "error": "الكوبون لم يصبح ساري المفعول بعد"}
        
        if coupon.end_date and current_date > coupon.end_date:
            return {"valid": False, "error": "انتهت صلاحية الكوبون"}
        
        if coupon.minimum_amount and subtotal < coupon.minimum_amount:
            return {"valid": False, "error": f"الحد الأدنى للطلب هو {float(coupon.minimum_amount)} ريال سعودي"}
        
        if coupon.maximum_amount and subtotal > coupon.maximum_amount:
            return {"valid": False, "error": f"الحد الأقصى للطلب هو {float(coupon.maximum_amount)} ريال سعودي"}
        
        if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
            return {"valid": False, "error": "تم استنفاد عدد مرات استخدام هذا الكوبون"}
        
        if student_id and coupon.usage_limit_per_user:
            user_usage = self.db.query(CouponUsage).filter(
                and_(
                    CouponUsage.coupon_id == coupon.id,
                    CouponUsage.student_id == student_id
                )
            ).count()
            
            if user_usage >= coupon.usage_limit_per_user:
                return {"valid": False, "error": "لقد وصلت للحد الأقصى من استخدام هذا الكوبون"}
        
        discount_amount = Decimal('0')
        
        if coupon.discount_type == "percentage":
            discount_amount = subtotal * (coupon.discount_value / 100)
            if coupon.maximum_discount_amount:
                discount_amount = min(discount_amount, coupon.maximum_discount_amount)
        elif coupon.discount_type == "fixed":
            discount_amount = min(coupon.discount_value, subtotal)
        else:
            return {"valid": False, "error": "نوع خصم غير مدعوم"}
        
        discount_amount = min(discount_amount, subtotal)
        
        return {
            "valid": True,
            "coupon": {
                "id": coupon.id,
                "code": coupon.code,
                "name": coupon.name,
                "description": coupon.description,
                "discount_type": coupon.discount_type,
                "discount_value": float(coupon.discount_value),
                "minimum_amount": float(coupon.minimum_amount) if coupon.minimum_amount else None,
                "maximum_amount": float(coupon.maximum_amount) if coupon.maximum_amount else None,
                "maximum_discount_amount": float(coupon.maximum_discount_amount) if coupon.maximum_discount_amount else None,
                "usage_count": coupon.usage_count,
                "usage_limit": coupon.usage_limit,
                "usage_limit_per_user": coupon.usage_limit_per_user,
                "start_date": coupon.start_date.isoformat() if coupon.start_date else None,
                "end_date": coupon.end_date.isoformat() if coupon.end_date else None
            },
            "discount_amount": float(discount_amount),
            "final_amount": float(subtotal - discount_amount)
        }
    
    def merge_guest_cart_to_student(
        self,
        student_id: int,
        cookie_id: str
    ) -> Dict[str, Any]:
        try:
            guest_items = self.get_cart_items(cookie_id=cookie_id)
            
            if not guest_items:
                return {
                    "message": "No guest cart items to merge",
                    "items_merged": 0
                }
            
            merged_count = 0
            
            for guest_item in guest_items:
                existing_item = self._get_existing_cart_item(
                    guest_item.item_type.value,
                    guest_item.item_id,
                    student_id,
                    None,
                    None
                )
                
                if existing_item:
                    existing_item.quantity += guest_item.quantity
                    existing_item.updated_at = datetime.utcnow()
                else:
                    guest_item.student_id = student_id
                    guest_item.updated_at = datetime.utcnow()
                    merged_count += 1
                
                guest_item.student_id = student_id
            
            self.db.commit()
            
            return {
                "message": f"Successfully merged {merged_count} items from guest cart",
                "items_merged": merged_count
            }
        except Exception as e:
            self.db.rollback()
            raise e
    
    def _get_item(self, item_type: str, item_id: str) -> Optional[Any]:
        if item_type == 'course':
            return self.db.query(Course).filter(Course.id == item_id).first()
        elif item_type == 'digital_product':
            return self.db.query(DigitalProduct).filter(DigitalProduct.id == item_id).first()
        return None
    
    def _get_existing_cart_item(
        self,
        item_type: str,
        item_id: str,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[Cart]:
        query = self.db.query(Cart).filter(
            and_(
                Cart.item_type == ItemType(item_type),
                Cart.item_id == item_id,
                Cart.deleted_at.is_(None)
            )
        )
        
        if student_id:
            query = query.filter(
                or_(
                    Cart.student_id == student_id,
                    Cart.cookie_id == cookie_id
                )
            )
        elif cookie_id:
            query = query.filter(Cart.cookie_id == cookie_id)
        elif session_id:
            query = query.filter(
                and_(
                    Cart.student_id.is_(None),
                    Cart.session_id == session_id
                )
            )
        else:
            return None
        
        return query.first()
    
    def _get_cart_item(
        self,
        cart_item_id: int,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[Cart]:
        query = self.db.query(Cart).filter(
            and_(
                Cart.id == cart_item_id,
                Cart.deleted_at.is_(None)
            )
        )
        
        if student_id:
            query = query.filter(
                or_(
                    Cart.student_id == student_id,
                    Cart.cookie_id == cookie_id
                )
            )
        elif cookie_id:
            query = query.filter(Cart.cookie_id == cookie_id)
        elif session_id:
            query = query.filter(
                and_(
                    Cart.student_id.is_(None),
                    Cart.session_id == session_id
                )
            )
        else:
            return None
        
        return query.first()
    
    def cleanup_expired_guest_carts(self, days: int = 30) -> int:
        try:
            expiry_date = datetime.utcnow() - timedelta(days=days)
            
            expired_items = self.db.query(Cart).filter(
                and_(
                    Cart.student_id.is_(None),
                    Cart.created_at < expiry_date,
                    Cart.deleted_at.is_(None)
                )
            ).all()
            
            for item in expired_items:
                item.soft_delete()
            
            self.db.commit()
            
            return len(expired_items)
        except Exception as e:
            self.db.rollback()
            raise e 