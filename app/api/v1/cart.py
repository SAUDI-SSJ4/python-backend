from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db, get_optional_current_user

router = APIRouter()


# Mock cart session storage (in production, use Redis or database)
mock_cart_data = {}


def get_cart_key(user_id: Optional[int], session_id: str) -> str:
    """Generate cart key based on user or session"""
    if user_id:
        return f"user_{user_id}"
    return f"session_{session_id}"


def generate_mock_cart_item(item_id: int, item_type: str, quantity: int = 1):
    """Generate mock cart item"""
    prices = {"course": 299.99, "product": 149.99, "digital_product": 49.99}
    names = {
        "course": "Advanced Programming Course",
        "product": "Educational Kit",
        "digital_product": "E-Book: Python Mastery"
    }
    
    return {
        "id": item_id,
        "type": item_type,
        "item_id": item_id,
        "name": f"{names.get(item_type, 'Item')} #{item_id}",
        "price": prices.get(item_type, 99.99),
        "quantity": quantity,
        "thumbnail": f"https://example.com/{item_type}{item_id}.jpg",
        "academy_id": (item_id % 3) + 1,
        "academy_name": f"Academy {(item_id % 3) + 1}"
    }


# Cart endpoints
@router.get("/")
def get_cart(
    session_id: str = "default_session",
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Get current cart contents"""
    cart_key = get_cart_key(current_user.id if current_user else None, session_id)
    cart_items = mock_cart_data.get(cart_key, [])
    
    # Calculate totals
    subtotal = sum(item["price"] * item["quantity"] for item in cart_items)
    tax = subtotal * 0.15  # 15% VAT
    total = subtotal + tax
    
    return {
        "items": cart_items,
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
        "currency": "SAR",
        "items_count": len(cart_items),
        "total_quantity": sum(item["quantity"] for item in cart_items)
    }


@router.post("/add")
def add_to_cart(
    cart_data: dict,
    session_id: str = "default_session",
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Add item to cart"""
    cart_key = get_cart_key(current_user.id if current_user else None, session_id)
    
    if cart_key not in mock_cart_data:
        mock_cart_data[cart_key] = []
    
    # Check if item already in cart
    item_type = cart_data.get("type", "course")
    item_id = cart_data.get("item_id", 1)
    quantity = cart_data.get("quantity", 1)
    
    existing_item = None
    for item in mock_cart_data[cart_key]:
        if item["item_id"] == item_id and item["type"] == item_type:
            existing_item = item
            break
    
    if existing_item:
        existing_item["quantity"] += quantity
        message = "Item quantity updated in cart"
    else:
        new_item = generate_mock_cart_item(item_id, item_type, quantity)
        new_item["id"] = len(mock_cart_data[cart_key]) + 1
        mock_cart_data[cart_key].append(new_item)
        message = "Item added to cart"
    
    return {
        "message": message,
        "cart_items_count": len(mock_cart_data[cart_key]),
        "cart": get_cart(session_id, current_user)
    }


@router.put("/update/{item_id}")
def update_cart_item(
    item_id: int,
    update_data: dict,
    session_id: str = "default_session",
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Update cart item quantity"""
    cart_key = get_cart_key(current_user.id if current_user else None, session_id)
    
    if cart_key not in mock_cart_data:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    for item in mock_cart_data[cart_key]:
        if item["id"] == item_id:
            item["quantity"] = update_data.get("quantity", item["quantity"])
            return {
                "message": "Cart item updated",
                "item": item,
                "cart": get_cart(session_id, current_user)
            }
    
    raise HTTPException(status_code=404, detail="Item not found in cart")


@router.delete("/delete/{item_id}")
def remove_from_cart(
    item_id: int,
    session_id: str = "default_session",
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Remove item from cart"""
    cart_key = get_cart_key(current_user.id if current_user else None, session_id)
    
    if cart_key not in mock_cart_data:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    initial_length = len(mock_cart_data[cart_key])
    mock_cart_data[cart_key] = [item for item in mock_cart_data[cart_key] if item["id"] != item_id]
    
    if len(mock_cart_data[cart_key]) < initial_length:
        return {
            "message": "Item removed from cart",
            "cart": get_cart(session_id, current_user)
        }
    
    raise HTTPException(status_code=404, detail="Item not found in cart")


@router.delete("/clear")
def clear_cart(
    session_id: str = "default_session",
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Clear all items from cart"""
    cart_key = get_cart_key(current_user.id if current_user else None, session_id)
    
    if cart_key in mock_cart_data:
        mock_cart_data[cart_key] = []
    
    return {
        "message": "Cart cleared successfully",
        "cart": get_cart(session_id, current_user)
    }


# Checkout endpoint
@router.post("/checkout/process")
def process_checkout(
    checkout_data: dict,
    session_id: str = "default_session",
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Process checkout"""
    cart_key = get_cart_key(current_user.id if current_user else None, session_id)
    
    if cart_key not in mock_cart_data or not mock_cart_data[cart_key]:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    cart = get_cart(session_id, current_user)
    
    # Generate mock payment data
    payment_id = f"PAY_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "payment_id": payment_id,
        "status": "pending",
        "amount": cart["total"],
        "currency": cart["currency"],
        "items": cart["items"],
        "payment_url": f"https://payment-gateway.com/pay/{payment_id}",
        "callback_url": f"/api/v1/payment/verify/{payment_id}",
        "customer": {
            "name": checkout_data.get("name", "Guest User"),
            "email": checkout_data.get("email", "guest@example.com"),
            "phone": checkout_data.get("phone", "0500000000")
        },
        "billing_address": checkout_data.get("billing_address", {}),
        "created_at": datetime.now().isoformat()
    }


# Coupon endpoint
@router.post("/apply-coupon")
def apply_coupon(
    coupon_data: dict,
    session_id: str = "default_session",
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Apply coupon to cart"""
    cart = get_cart(session_id, current_user)
    coupon_code = coupon_data.get("code", "").upper()
    
    # Mock coupon validation
    valid_coupons = {
        "SAVE10": {"type": "percentage", "value": 10, "min_amount": 100},
        "SAVE50": {"type": "fixed", "value": 50, "min_amount": 500},
        "WELCOME": {"type": "percentage", "value": 15, "min_amount": 0}
    }
    
    if coupon_code not in valid_coupons:
        raise HTTPException(status_code=400, detail="Invalid coupon code")
    
    coupon = valid_coupons[coupon_code]
    
    if cart["subtotal"] < coupon["min_amount"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Minimum order amount is {coupon['min_amount']} SAR"
        )
    
    # Calculate discount
    if coupon["type"] == "percentage":
        discount = cart["subtotal"] * (coupon["value"] / 100)
    else:
        discount = coupon["value"]
    
    # Apply discount
    new_total = cart["total"] - discount
    
    return {
        "message": "Coupon applied successfully",
        "coupon_code": coupon_code,
        "discount_type": coupon["type"],
        "discount_value": coupon["value"],
        "discount_amount": round(discount, 2),
        "original_total": cart["total"],
        "new_total": round(new_total, 2),
        "currency": cart["currency"]
    } 