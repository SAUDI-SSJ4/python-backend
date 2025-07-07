"""
Payment API endpoints - نسخة مبسطة للاختبار
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.deps.database import get_db
from app.deps.auth import get_current_student
from app.models.student import Student


router = APIRouter()


class ProcessCheckoutRequest(BaseModel):
    coupon: Optional[str] = Field(None, description="Coupon code for discount")
    billing_info: Optional[dict] = Field(None, description="Billing information")


@router.post("/checkout/process")
def process_checkout(
    checkout_data: ProcessCheckoutRequest,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_student)
) -> Any:
    """معالجة عملية الدفع"""
    return {
        "status": "success",
        "message": "Payment data ready",
        "data": {
            "payment_data": {
                "amount": 29999,  # 299.99 SAR in halalas
                "currency": "SAR",
                "description": "Purchase educational courses",
                "callback_url": "/api/v1/checkout/callback/1/1/moyasar"
            },
            "payment_key": "pk_test_vnkFtCmh3soMRKwHN45PrW5472GxvTd3GJdEnAhB",
            "payment_url": "https://test-payment-url",
            "total_price": 299.99,
            "items_count": 1,
            "invoice_id": 1,
            "payment_id": 1
        }
    }


@router.get("/transaction/verify/{payment_id}")
def verify_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_student)
) -> Any:
    """التحقق من حالة الدفع"""
    return {
        "status": "success",
        "message": "Payment verified successfully",
        "data": {
            "payment_status": "pending",
            "verified_at": "2025-07-07T18:00:00Z"
        }
    }


@router.get("/invoices")
def get_student_invoices(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_student)
) -> Any:
    """جلب قائمة الفواتير"""
    return {
        "status": "success",
        "message": "Invoices retrieved successfully",
        "data": {
            "invoices": [],
            "total": 0,
            "page": 1,
            "per_page": limit
        }
    }


@router.get("/invoices/{invoice_id}")
def get_invoice_details(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_student)
) -> Any:
    """جلب تفاصيل فاتورة محددة"""
    return {
        "status": "success",
        "message": "Invoice details retrieved successfully",
        "data": {
            "id": invoice_id,
            "invoice_number": f"INV-{invoice_id:06d}",
            "total_amount": 299.99,
            "status": "pending",
            "items": []
        }
    }


@router.get("/methods")
def get_payment_methods() -> Any:
    """جلب طرق الدفع المتاحة"""
    return {
        "status": "success",
        "message": "Payment methods retrieved successfully",
        "data": [
            {
                "id": "creditcard",
                "name": "Credit Card",
                "type": "card",
                "supported_cards": ["visa", "mastercard", "amex"],
                "currency": "SAR",
                "min_amount": 1.0,
                "max_amount": 10000.0,
                "fees": {"percentage": 2.9, "fixed": 0.0}
            },
            {
                "id": "stcpay",
                "name": "STC Pay",
                "type": "wallet",
                "currency": "SAR",
                "min_amount": 1.0,
                "max_amount": 5000.0,
                "fees": {"percentage": 2.0, "fixed": 0.0}
            },
            {
                "id": "applepay",
                "name": "Apple Pay",
                "type": "wallet",
                "currency": "SAR",
                "min_amount": 1.0,
                "max_amount": 10000.0,
                "fees": {"percentage": 2.9, "fixed": 0.0}
            }
        ]
    }


@router.post("/webhook/moyasar")
async def moyasar_webhook(request: Request) -> Any:
    """معالج Webhook من Moyasar"""
    try:
        body = await request.body()
        signature = request.headers.get("x-moyasar-signature", "")
        
        return {
            "status": "success",
            "message": "Webhook processed successfully"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Error processing webhook: {str(e)}"
            }
        ) 