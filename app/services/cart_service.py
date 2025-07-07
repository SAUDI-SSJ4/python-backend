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

from app.models.cart import Cart
from app.models.course import Course
from app.models.student import Student
from app.models.product import Product
from app.models.payment import Coupon, CouponUsage
from app.core.config import settings


class CartService:
    """
    Service for managing shopping cart operations.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_session_id(self, session_id: Optional[str] = None) -> str:
        """
        Get existing session ID or create a new one for guest users.
        """
        if session_id:
            return session_id
        return str(uuid.uuid4())
    
    def get_cart_items(
        self, 
        student_id: Optional[int] = None, 
        session_id: Optional[str] = None
    ) -> List[Cart]:
        """
        Get cart items for a student or guest user.
        """
        query = self.db.query(Cart).filter(Cart.deleted_at.is_(None))
        
        if student_id:
            # For authenticated students
            query = query.filter(Cart.student_id == student_id)
        elif session_id:
            # For guest users
            query = query.filter(
                and_(
                    Cart.student_id.is_(None),
                    Cart.session_id == session_id
                )
            )
        else:
            # Return empty list if no identifier provided
            return []
        
        return query.all()
    
    def add_to_cart(
        self,
        course_id: str,
        student_id: Optional[int] = None,
        session_id: Optional[str] = None,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        Add a course to the cart.
        """
        # Validate course exists
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError("Course not found")
        
        # Check if course is published
        if not course.is_published:
            raise ValueError("Course is not available for purchase")
        
        # Get course price from product
        if not course.product:
            raise ValueError("Course pricing not available")
        
        price = course.current_price
        
        # Check if item already exists in cart
        existing_item = self._get_existing_cart_item(course_id, student_id, session_id)
        
        if existing_item:
            # Update existing item
            existing_item.quantity += quantity
            existing_item.updated_at = datetime.utcnow()
            self.db.commit()
            return {
                "message": "Cart item quantity updated",
                "item": existing_item,
                "action": "updated"
            }
        else:
            # Create new cart item
            cart_item = Cart(
                student_id=student_id,
                session_id=session_id if not student_id else None,
                course_id=course_id,
                academy_id=course.academy_id,
                quantity=quantity,
                price=price
            )
            
            self.db.add(cart_item)
            self.db.commit()
            self.db.refresh(cart_item)
            
            return {
                "message": "Item added to cart",
                "item": cart_item,
                "action": "added"
            }
    
    def remove_from_cart(
        self,
        cart_item_id: int,
        student_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Remove an item from the cart.
        """
        cart_item = self._get_cart_item(cart_item_id, student_id, session_id)
        
        if not cart_item:
            raise ValueError("Cart item not found")
        
        # Soft delete the item
        cart_item.soft_delete()
        self.db.commit()
        
        return {
            "message": "Item removed from cart",
            "item_id": cart_item_id
        }
    
    def update_cart_item(
        self,
        cart_item_id: int,
        quantity: int,
        student_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update cart item quantity.
        """
        if quantity <= 0:
            return self.remove_from_cart(cart_item_id, student_id, session_id)
        
        cart_item = self._get_cart_item(cart_item_id, student_id, session_id)
        
        if not cart_item:
            raise ValueError("Cart item not found")
        
        cart_item.quantity = quantity
        cart_item.updated_at = datetime.utcnow()
        self.db.commit()
        
        return {
            "message": "Cart item updated",
            "item": cart_item
        }
    
    def clear_cart(
        self,
        student_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clear all items from the cart.
        """
        cart_items = self.get_cart_items(student_id, session_id)
        
        for item in cart_items:
            item.soft_delete()
        
        self.db.commit()
        
        return {
            "message": "Cart cleared successfully",
            "items_cleared": len(cart_items)
        }
    
    def get_cart_summary(
        self,
        student_id: Optional[int] = None,
        session_id: Optional[str] = None,
        coupon_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get cart summary with totals and pricing.
        """
        cart_items = self.get_cart_items(student_id, session_id)
        
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
        
        # Calculate subtotal
        subtotal = sum(item.total_price for item in cart_items)
        
        # Apply coupon if provided
        discount_amount = 0.00
        coupon_applied = None
        
        if coupon_code:
            coupon_result = self.apply_coupon(coupon_code, subtotal, student_id)
            if coupon_result["valid"]:
                discount_amount = coupon_result["discount_amount"]
                coupon_applied = coupon_result["coupon"]
        
        # Calculate tax (VAT 15%)
        tax_rate = Decimal('0.15')
        discounted_subtotal = subtotal - discount_amount
        tax_amount = discounted_subtotal * tax_rate
        
        # Calculate total
        total = discounted_subtotal + tax_amount
        
        # Prepare cart items data
        items_data = []
        for item in cart_items:
            course = self.db.query(Course).filter(Course.id == item.course_id).first()
            if course and course.product:
                items_data.append({
                    "id": item.id,
                    "course_id": item.course_id,
                    "course_title": course.product.title,
                    "course_image": course.image,
                    "quantity": item.quantity,
                    "unit_price": float(item.price),
                    "total_price": item.total_price,
                    "academy": {
                        "id": course.academy_id,
                        "name": course.academy.name if course.academy else "Unknown"
                    }
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
        """
        Apply coupon to cart and calculate discount.
        """
        coupon = self.db.query(Coupon).filter(
            and_(
                Coupon.code == coupon_code.upper(),
                Coupon.is_active == True
            )
        ).first()
        
        if not coupon:
            return {
                "valid": False,
                "error": "Invalid coupon code"
            }
        
        # Check if coupon is valid (dates, usage limits, etc.)
        if not coupon.is_valid:
            return {
                "valid": False,
                "error": "Coupon is not valid or has expired"
            }
        
        # Check minimum amount
        if subtotal < coupon.minimum_amount:
            return {
                "valid": False,
                "error": f"Minimum order amount is {coupon.minimum_amount} SAR"
            }
        
        # Check usage limits
        if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
            return {
                "valid": False,
                "error": "Coupon usage limit reached"
            }
        
        # Check per-user usage limit
        if student_id and coupon.usage_limit_per_user:
            user_usage = self.db.query(CouponUsage).filter(
                and_(
                    CouponUsage.coupon_id == coupon.id,
                    CouponUsage.student_id == student_id
                )
            ).count()
            
            if user_usage >= coupon.usage_limit_per_user:
                return {
                    "valid": False,
                    "error": "You have reached the usage limit for this coupon"
                }
        
        # Calculate discount
        if coupon.discount_type == "percentage":
            discount_amount = subtotal * (coupon.discount_value / 100)
        else:  # fixed amount
            discount_amount = min(coupon.discount_value, subtotal)
        
        return {
            "valid": True,
            "coupon": {
                "code": coupon.code,
                "name": coupon.name,
                "discount_type": coupon.discount_type,
                "discount_value": float(coupon.discount_value)
            },
            "discount_amount": float(discount_amount)
        }
    
    def merge_guest_cart_to_student(
        self,
        student_id: int,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Merge guest cart items to student cart when user logs in.
        """
        # Get guest cart items
        guest_items = self.get_cart_items(session_id=session_id)
        
        if not guest_items:
            return {
                "message": "No guest cart items to merge",
                "items_merged": 0
            }
        
        merged_count = 0
        
        for guest_item in guest_items:
            # Check if student already has this course in cart
            existing_item = self._get_existing_cart_item(
                guest_item.course_id, 
                student_id, 
                None
            )
            
            if existing_item:
                # Update quantity
                existing_item.quantity += guest_item.quantity
                existing_item.updated_at = datetime.utcnow()
            else:
                # Transfer guest item to student
                guest_item.student_id = student_id
                guest_item.session_id = None
                guest_item.updated_at = datetime.utcnow()
                merged_count += 1
            
            # Remove from guest cart
            guest_item.soft_delete()
        
        self.db.commit()
        
        return {
            "message": f"Successfully merged {merged_count} items from guest cart",
            "items_merged": merged_count
        }
    
    def _get_existing_cart_item(
        self,
        course_id: str,
        student_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Optional[Cart]:
        """
        Get existing cart item for the same course.
        """
        query = self.db.query(Cart).filter(
            and_(
                Cart.course_id == course_id,
                Cart.deleted_at.is_(None)
            )
        )
        
        if student_id:
            query = query.filter(Cart.student_id == student_id)
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
        session_id: Optional[str] = None
    ) -> Optional[Cart]:
        """
        Get cart item by ID with ownership validation.
        """
        query = self.db.query(Cart).filter(
            and_(
                Cart.id == cart_item_id,
                Cart.deleted_at.is_(None)
            )
        )
        
        if student_id:
            query = query.filter(Cart.student_id == student_id)
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
        """
        Clean up expired guest cart items.
        """
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