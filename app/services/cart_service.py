"""
Cart service for managing shopping cart operations.
Supports both authenticated students and guest users through cookies.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta

from app.models.cart import Cart
from app.models.product import Product
from app.models.course import Course
from app.models.product import DigitalProduct
from app.models.student import Student
from app.core.response_handler import ResponseHandler


class CartService:
    @staticmethod
    def add_to_cart(
        db: Session,
        item_type: str,
        item_id: str,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None
    ) -> dict:
        """Add item to cart using unified product reference"""
        try:
            # Get product ID from item_type and item_id
            product_id = CartService._get_product_id(db, item_type, item_id)
            if not product_id:
                return ResponseHandler.error(
                    message=f"المنتج غير موجود أو غير مرتبط بجدول المنتجات (نوع: {item_type}, معرف: {item_id})",
                    status_code=404
                )
            
            # Check if item already exists (no duplicates allowed)
            existing_item = CartService._get_existing_cart_item(
                db, product_id, student_id, cookie_id
            )
            
            if existing_item:
                return ResponseHandler.error(
                    message="المنتج موجود بالفعل في السلة",
                    status_code=400
                )
            
            # Create new cart item
            cart_item = Cart(
                id=str(uuid.uuid4()),
                student_id=student_id,
                cookie_id=cookie_id,
                product_id=product_id
            )
            
            db.add(cart_item)
            db.commit()
            db.refresh(cart_item)
            
            return ResponseHandler.success(
                message="تم إضافة المنتج إلى السلة بنجاح",
                data={
                    "cart_id": cart_item.id,
                    "product_id": product_id,
                    "item_type": item_type,
                    "item_id": item_id
                }
            )
            
        except Exception as e:
            try:
                db.rollback()
            except:
                pass
            
            # Check if it's a connection error
            if "Lost connection" in str(e) or "Can't connect" in str(e):
                return ResponseHandler.error(
                    message="مشكلة في الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.",
                    status_code=503
                )
            else:
                return ResponseHandler.error(
                    message=f"خطأ في إضافة المنتج: {str(e)}",
                    status_code=500
                )

    @staticmethod
    def _get_product_id(db: Session, item_type: str, item_id: str) -> Optional[int]:
        """Get product ID based on item type and item ID - with improved error handling"""
        try:
            if item_type == "course":
                # Try raw SQL first (more efficient)
                try:
                    from sqlalchemy import text
                    result = db.execute(
                        text("SELECT product_id FROM courses WHERE id = :course_id LIMIT 1"),
                        {"course_id": item_id}
                    ).fetchone()
                    
                    if result and result.product_id:
                        return result.product_id
                    elif result:
                        print(f"Course found but no product_id: {item_id}")
                        return None
                    else:
                        print(f"Course not found: {item_id}")
                        return None
                        
                except Exception as sql_error:
                    print(f"Raw SQL failed, trying ORM: {sql_error}")
                    # Fallback to ORM
                    course = db.query(Course).filter(Course.id == item_id).first()
                    if course:
                        if course.product_id:
                            return course.product_id
                        else:
                            print(f"Course found but no product_id: {item_id}")
                            return None
                    else:
                        print(f"Course not found: {item_id}")
                        return None
                
            elif item_type == "digital_product":
                # Try raw SQL first
                try:
                    from sqlalchemy import text
                    result = db.execute(
                        text("SELECT product_id FROM digital_products WHERE id = :item_id LIMIT 1"),
                        {"item_id": item_id}
                    ).fetchone()
                    
                    if result and result.product_id:
                        return result.product_id
                    elif result:
                        print(f"DigitalProduct found but no product_id: {item_id}")
                        return None
                    else:
                        print(f"DigitalProduct not found: {item_id}")
                        return None
                        
                except Exception as sql_error:
                    print(f"Raw SQL failed, trying ORM: {sql_error}")
                    # Fallback to ORM
                    digital_product = db.query(DigitalProduct).filter(DigitalProduct.id == item_id).first()
                    if digital_product:
                        if digital_product.product_id:
                            return digital_product.product_id
                        else:
                            print(f"DigitalProduct found but no product_id: {item_id}")
                            return None
                    else:
                        print(f"DigitalProduct not found: {item_id}")
                        return None
                
            return None
            
        except Exception as e:
            print(f"Error getting product_id: {e}")
            try:
                db.rollback()
            except:
                pass
            return None

    @staticmethod
    def _get_existing_cart_item(
        db: Session,
        product_id: int,
        student_id: Optional[int],
        cookie_id: Optional[str]
    ) -> Optional[Cart]:
        """Find existing cart item by product ID - check both student and guest carts"""
        try:
            # Build base query for this product
            base_query = db.query(Cart).filter(Cart.product_id == product_id)
            
            # If user is authenticated, check both student cart and guest cart
            if student_id:
                # Check if student already has this product
                student_item = base_query.filter(Cart.student_id == student_id).first()
                if student_item:
                    return student_item
                
                # Also check if there's a guest item with this cookie
                if cookie_id:
                    guest_item = base_query.filter(
                        and_(Cart.cookie_id == cookie_id, Cart.student_id.is_(None))
                    ).first()
                    if guest_item:
                        return guest_item
                        
            elif cookie_id:
                # For guest users, only check guest cart
                return base_query.filter(
                    and_(Cart.cookie_id == cookie_id, Cart.student_id.is_(None))
                ).first()
                
            return None
        except Exception:
            return None

    @staticmethod
    def get_cart_items(
        db: Session,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None
    ) -> dict:
        """Get all cart items for user"""
        try:
            # Migrate guest cart if authenticated user
            if student_id and cookie_id:
                CartService._migrate_guest_cart(db, student_id, cookie_id)
            
            # Build query
            query = db.query(Cart)
            
            if student_id:
                query = query.filter(Cart.student_id == student_id)
            elif cookie_id:
                query = query.filter(
                    and_(Cart.cookie_id == cookie_id, Cart.student_id.is_(None))
                )
            else:
                return ResponseHandler.success(
                    message="السلة فارغة",
                    data={
                        "items": [],
                        "total": 0,
                        "count": 0,
                        "currency": "SAR"
                    }
                )
            
            cart_items = query.all()
            
            if not cart_items:
                return ResponseHandler.success(
                    message="السلة فارغة",
                    data={
                        "items": [],
                        "total": 0,
                        "count": 0,
                        "currency": "SAR"
                    }
                )
            
            # Calculate totals
            total = sum(item.price for item in cart_items)
            
            items_data = []
            for item in cart_items:
                item_details = item.get_item_details()
                item_details['cart_id'] = item.id
                items_data.append(item_details)
            
            return ResponseHandler.success(
                message=f"تم العثور على {len(cart_items)} منتجات في السلة",
                data={
                    "items": items_data,
                    "total": total,
                    "count": len(cart_items),
                    "currency": "SAR"
                }
            )
            
        except Exception as e:
            return ResponseHandler.error(
                message=f"خطأ في استرجاع السلة: {str(e)}",
                status_code=500
            )

    @staticmethod
    def _migrate_guest_cart(db: Session, student_id: int, cookie_id: str):
        """Migrate guest cart items to authenticated user"""
        try:
            # Find guest cart items
            guest_items = db.query(Cart).filter(
                and_(Cart.cookie_id == cookie_id, Cart.student_id.is_(None))
            ).all()
            
            if not guest_items:
                return
            
            # Update guest items to be owned by the student
            for item in guest_items:
                # Check if student already has this product
                existing = db.query(Cart).filter(
                    and_(
                        Cart.student_id == student_id,
                        Cart.product_id == item.product_id
                    )
                ).first()
                
                if existing:
                    # Delete duplicate guest item
                    db.delete(item)
                else:
                    # Transfer ownership
                    item.student_id = student_id
                    item.updated_at = datetime.utcnow()
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            print(f"Error migrating guest cart: {e}")

    @staticmethod
    def remove_from_cart(
        db: Session,
        cart_id: str,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None
    ) -> dict:
        """Remove item from cart by cart_id"""
        try:
            # Build query to find the cart item
            query = db.query(Cart).filter(Cart.id == cart_id)
            
            # Add ownership filter
            if student_id:
                query = query.filter(Cart.student_id == student_id)
            elif cookie_id:
                query = query.filter(
                    and_(Cart.cookie_id == cookie_id, Cart.student_id.is_(None))
                )
            else:
                return ResponseHandler.error(
                    message="غير مخول لحذف هذا العنصر",
                    status_code=401
                )
            
            cart_item = query.first()
            
            if not cart_item:
                return ResponseHandler.error(
                    message="العنصر غير موجود في السلة",
                    status_code=404
                )
            
            # Store item details for response
            item_details = cart_item.get_item_details()
            
            # Remove the item
            db.delete(cart_item)
            db.commit()
            
            return ResponseHandler.success(
                message="تم حذف المنتج من السلة بنجاح",
                data={
                    "removed_item": item_details,
                    "cart_id": cart_id
                }
            )
            
        except Exception as e:
            db.rollback()
            return ResponseHandler.error(
                message=f"خطأ في حذف المنتج: {str(e)}",
                status_code=500
            )

    @staticmethod
    def clear_cart(
        db: Session,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None
    ) -> dict:
        """Clear cart with priority for authenticated users"""
        try:
            deleted_count = 0
            
            if student_id:
                # Clear authenticated user's cart
                cart_items = db.query(Cart).filter(Cart.student_id == student_id).all()
                for item in cart_items:
                    db.delete(item)
                deleted_count = len(cart_items)
                
            elif cookie_id:
                # Clear guest cart
                cart_items = db.query(Cart).filter(
                    and_(Cart.cookie_id == cookie_id, Cart.student_id.is_(None))
                ).all()
                for item in cart_items:
                    db.delete(item)
                deleted_count = len(cart_items)
                
            else:
                return ResponseHandler.error(
                    message="لا يمكن تحديد السلة المراد مسحها",
                    status_code=400
                )
            
            if deleted_count > 0:
                db.commit()
                return ResponseHandler.success(
                    message=f"تم مسح {deleted_count} منتجات من السلة",
                    data={
                        "deleted_count": deleted_count,
                        "user_type": "authenticated" if student_id else "guest"
                    }
                )
            else:
                return ResponseHandler.success(
                    message="السلة فارغة بالفعل",
                    data={
                        "deleted_count": 0,
                        "user_type": "authenticated" if student_id else "guest"
                    }
                )
                
        except Exception as e:
            db.rollback()
            return ResponseHandler.error(
                message=f"خطأ في مسح السلة: {str(e)}",
                status_code=500
            )

    @staticmethod
    def get_cart_summary(
        db: Session,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None
    ) -> dict:
        """Get cart summary with totals"""
        try:
            cart_result = CartService.get_cart_items(db, student_id, cookie_id)
            
            if not cart_result.get("success"):
                return cart_result
            
            cart_data = cart_result.get("data", {})
            items = cart_data.get("items", [])
            
            # Calculate detailed totals
            subtotal = sum(item.get("price", 0) for item in items)
            total_discount = sum(item.get("discount_amount", 0) for item in items)
            total = subtotal - total_discount
            
            return ResponseHandler.success(
                message="ملخص السلة",
                data={
                    "count": len(items),
                    "subtotal": subtotal,
                    "total_discount": total_discount,
                    "total": total,
                    "currency": "SAR",
                    "items": items
                }
            )
            
        except Exception as e:
            return ResponseHandler.error(
                message=f"خطأ في حساب ملخص السلة: {str(e)}",
                status_code=500
            ) 