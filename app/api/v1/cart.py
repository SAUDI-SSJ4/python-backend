"""
Cart API endpoints - نسخة مبسطة للاختبار
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import uuid

from app.deps.database import get_db
from app.deps.auth import get_optional_current_user, get_current_student
from app.models.student import Student


router = APIRouter()


class AddToCartRequest(BaseModel):
    course_id: str = Field(..., description="Course ID to add to cart")
    quantity: int = Field(1, ge=1, le=10, description="Quantity of items to add")


@router.get("/")
def get_cart() -> Any:
    """جلب محتويات السلة"""
    return {
        "status": "success",
        "message": "Cart retrieved successfully",
        "data": {
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
    }


@router.post("/add")
def add_to_cart(cart_data: AddToCartRequest) -> Any:
    """إضافة كورس للسلة"""
    return {
        "status": "success",
        "message": "Item added to cart successfully",
        "data": {
            "action": "added",
            "cart": {
                "items": [{
                    "id": 1,
                    "course_id": cart_data.course_id,
                    "quantity": cart_data.quantity,
                    "unit_price": 299.99,
                    "total_price": 299.99 * cart_data.quantity
                }],
                "subtotal": 299.99 * cart_data.quantity,
                "total": 299.99 * cart_data.quantity,
                "items_count": 1
            }
        }
    }


@router.put("/update/{cart_item_id}")
def update_cart_item(cart_item_id: int, quantity: int = 1) -> Any:
    """تحديث كمية عنصر السلة"""
    return {
        "status": "success",
        "message": "Cart item updated successfully",
        "data": {
            "cart": {
                "items": [],
                "subtotal": 0.00,
                "total": 0.00,
                "items_count": 0
            }
        }
    }


@router.delete("/delete/{cart_item_id}")
def remove_from_cart(cart_item_id: int) -> Any:
    """حذف عنصر من السلة"""
    return {
        "status": "success",
        "message": "Item removed from cart successfully",
        "data": {
            "cart": {
                "items": [],
                "subtotal": 0.00,
                "total": 0.00,
                "items_count": 0
            }
        }
    }


@router.delete("/clear")
def clear_cart() -> Any:
    """مسح السلة بالكامل"""
    return {
        "status": "success",
        "message": "Cart cleared successfully",
        "data": {
            "items_cleared": 0
        }
    }


@router.post("/apply-coupon")
def apply_coupon(code: str) -> Any:
    """تطبيق كوبون"""
    return {
        "status": "error",
        "message": "Invalid coupon code"
    } 