from typing import Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import random
import string

from app.deps import get_db, get_current_student, get_optional_current_user

router = APIRouter()


# Mock payment storage
mock_payments = {}


def generate_payment_id():
    """Generate unique payment ID"""
    return "PAY_" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


def generate_transaction_id():
    """Generate unique transaction ID"""
    return "TRX_" + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))


# Payment endpoints
@router.get("/verify/{payment_id}")
def verify_payment(payment_id: str) -> Any:
    """Verify payment status"""
    if payment_id in mock_payments:
        payment = mock_payments[payment_id]
        
        # Simulate payment processing
        if payment["status"] == "pending":
            # Randomly succeed or fail for demo
            payment["status"] = random.choice(["paid", "failed"])
            payment["updated_at"] = datetime.now().isoformat()
            
            if payment["status"] == "paid":
                payment["paid_at"] = datetime.now().isoformat()
                payment["transaction_id"] = generate_transaction_id()
        
        return payment
    
    raise HTTPException(status_code=404, detail="Payment not found")


@router.post("/process")
def process_payment(
    payment_data: dict,
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Process new payment"""
    payment_id = generate_payment_id()
    
    payment = {
        "id": payment_id,
        "student_id": current_user.id if current_user else None,
        "amount": payment_data.get("amount", 0),
        "currency": payment_data.get("currency", "SAR"),
        "status": "pending",
        "payment_method": payment_data.get("payment_method", "credit_card"),
        "items": payment_data.get("items", []),
        "coupon_code": payment_data.get("coupon_code"),
        "discount_amount": payment_data.get("discount_amount", 0),
        "final_amount": payment_data.get("amount", 0) - payment_data.get("discount_amount", 0),
        "customer": payment_data.get("customer", {}),
        "billing_address": payment_data.get("billing_address", {}),
        "payment_gateway": payment_data.get("payment_gateway", "moyasar"),
        "callback_url": f"/api/v1/payment/callback/{payment_id}",
        "return_url": payment_data.get("return_url", "/payment/success"),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    mock_payments[payment_id] = payment
    
    # Generate payment gateway URL
    gateway_urls = {
        "moyasar": f"https://api.moyasar.com/v1/payments/{payment_id}",
        "stripe": f"https://checkout.stripe.com/pay/{payment_id}",
        "paypal": f"https://www.paypal.com/checkoutnow/{payment_id}"
    }
    
    payment["payment_url"] = gateway_urls.get(payment["payment_gateway"], f"https://payment.example.com/{payment_id}")
    
    return payment


@router.post("/callback/{payment_id}")
def payment_callback(
    payment_id: str,
    callback_data: dict
) -> Any:
    """Handle payment gateway callback"""
    if payment_id not in mock_payments:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = mock_payments[payment_id]
    
    # Update payment status based on callback
    gateway_status = callback_data.get("status", "failed")
    
    if gateway_status == "success" or gateway_status == "paid":
        payment["status"] = "paid"
        payment["paid_at"] = datetime.now().isoformat()
        payment["transaction_id"] = callback_data.get("transaction_id", generate_transaction_id())
        payment["payment_data"] = callback_data
    else:
        payment["status"] = "failed"
        payment["failure_reason"] = callback_data.get("error", "Payment failed")
    
    payment["updated_at"] = datetime.now().isoformat()
    
    return {
        "status": "success",
        "payment": payment
    }


# Student payment history
@router.get("/my-payments")
def get_my_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    current_user = Depends(get_current_student)
) -> Any:
    """Get student payment history"""
    # Generate mock payment history
    payments = []
    
    for i in range(1, 21):
        payment = {
            "id": f"PAY_{current_user.id}_{i}",
            "student_id": current_user.id,
            "amount": round(random.uniform(50, 500), 2),
            "currency": "SAR",
            "status": random.choice(["paid", "failed", "refunded"]),
            "payment_method": random.choice(["credit_card", "debit_card", "bank_transfer"]),
            "invoice_id": f"INV_{current_user.id}_{i}",
            "items": [
                {
                    "type": random.choice(["course", "product", "subscription"]),
                    "name": f"Item {i}",
                    "price": round(random.uniform(50, 500), 2)
                }
            ],
            "created_at": (datetime.now() - timedelta(days=i)).isoformat(),
            "paid_at": (datetime.now() - timedelta(days=i)).isoformat() if i % 3 != 0 else None
        }
        
        if payment["status"] == "paid":
            payment["transaction_id"] = generate_transaction_id()
        
        payments.append(payment)
    
    # Filter by status if provided
    if status:
        payments = [p for p in payments if p["status"] == status]
    
    return {
        "data": payments[skip:skip + limit],
        "total": len(payments),
        "skip": skip,
        "limit": limit
    }


@router.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: str,
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Get invoice details"""
    # Generate mock invoice
    invoice = {
        "id": invoice_id,
        "payment_id": f"PAY_{invoice_id.replace('INV_', '')}",
        "invoice_number": invoice_id,
        "status": "paid",
        "issue_date": datetime.now().isoformat(),
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "customer": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "0500000000",
            "address": "123 Main St, Riyadh, Saudi Arabia"
        },
        "items": [
            {
                "description": "Advanced Programming Course",
                "quantity": 1,
                "unit_price": 299.99,
                "total": 299.99
            },
            {
                "description": "Python E-Book",
                "quantity": 1,
                "unit_price": 49.99,
                "total": 49.99
            }
        ],
        "subtotal": 349.98,
        "tax_rate": 15,
        "tax_amount": 52.50,
        "total": 402.48,
        "currency": "SAR",
        "academy": {
            "name": "Tech Academy",
            "address": "456 Education Blvd, Riyadh",
            "tax_id": "123456789"
        }
    }
    
    return invoice


# Refund endpoints
@router.post("/refund/{payment_id}")
def request_refund(
    payment_id: str,
    refund_data: dict,
    current_user = Depends(get_current_student)
) -> Any:
    """Request payment refund"""
    if payment_id not in mock_payments:
        # Create mock payment for demo
        mock_payments[payment_id] = {
            "id": payment_id,
            "status": "paid",
            "amount": 299.99,
            "student_id": current_user.id
        }
    
    payment = mock_payments[payment_id]
    
    if payment["status"] != "paid":
        raise HTTPException(status_code=400, detail="Only paid payments can be refunded")
    
    refund = {
        "id": f"REF_{payment_id}",
        "payment_id": payment_id,
        "amount": refund_data.get("amount", payment["amount"]),
        "reason": refund_data.get("reason", "Customer request"),
        "status": "pending",
        "requested_at": datetime.now().isoformat(),
        "student_id": current_user.id
    }
    
    return {
        "message": "Refund request submitted successfully",
        "refund": refund
    }


# Payment methods
@router.get("/methods")
def get_payment_methods(
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Get available payment methods"""
    methods = [
        {
            "id": "credit_card",
            "name": "Credit Card",
            "icon": "credit-card",
            "supported_currencies": ["SAR", "USD", "EUR"],
            "processing_fee": 2.9,
            "min_amount": 10,
            "max_amount": 10000
        },
        {
            "id": "debit_card",
            "name": "Debit Card",
            "icon": "debit-card",
            "supported_currencies": ["SAR", "USD", "EUR"],
            "processing_fee": 1.5,
            "min_amount": 10,
            "max_amount": 5000
        },
        {
            "id": "bank_transfer",
            "name": "Bank Transfer",
            "icon": "bank",
            "supported_currencies": ["SAR"],
            "processing_fee": 0,
            "min_amount": 100,
            "max_amount": 50000
        },
        {
            "id": "moyasar",
            "name": "Moyasar",
            "icon": "moyasar",
            "supported_currencies": ["SAR"],
            "processing_fee": 2.0,
            "min_amount": 10,
            "max_amount": 10000
        }
    ]
    
    return {"data": methods} 