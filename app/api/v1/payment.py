"""
Payment API endpoints - Student registration required
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.deps.database import get_db
from app.deps.auth import get_current_student
from app.models.student import Student
from app.services.payment_service import PaymentService
from app.services.cart_service import CartService
from app.services.moyasar_service import MoyasarService
from app.core.response_handler import SayanSuccessResponse


router = APIRouter()


class ProcessCheckoutRequest(BaseModel):
    coupon_code: Optional[str] = Field(None, description="Coupon code for discount")
    billing_info: Optional[dict] = Field(None, description="Billing information")
    success_url: Optional[str] = Field(None, description="Success redirect URL")
    back_url: Optional[str] = Field(None, description="Back/Cancel redirect URL")


@router.post("/checkout/process")
def process_checkout(
    checkout_data: ProcessCheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    """
    Process checkout for registered students only
    """
    try:
        # Initialize services
        payment_service = PaymentService(db)
        cart_service = CartService(db)
        
        # Extract cookie for cart identification
        cookie_id = cart_service.extract_cookie_id(the_cookie)
        
        # Create invoice from student's cart
        invoice_result = payment_service.create_invoice_from_cart(
            student_id=current_student.id,
            cookie_id=cookie_id,
            coupon_code=checkout_data.coupon_code,
            billing_info=checkout_data.billing_info
        )
        
        # Process payment through gateway
        payment_result = payment_service.process_payment(
            invoice_id=invoice_result["invoice_id"],
            success_url=checkout_data.success_url,
            back_url=checkout_data.back_url
        )
        
        if payment_result["success"]:
            return SayanSuccessResponse(
                data={
                    "invoice": invoice_result,
                    "payment": payment_result,
                    "student_info": {
                        "id": current_student.id,
                        "name": f"{current_student.user.fname} {current_student.user.lname}",
                        "email": current_student.user.email
                    }
                },
                message="تم إنشاء طلب الدفع بنجاح",
                request=request
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": payment_result["error"],
                    "error_type": "Payment Error",
                    "data": {"invoice": invoice_result, "payment_error": payment_result}
                }
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "error_type": "Bad Request"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في معالجة الدفع: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.get("/transaction/verify/{payment_id}")
def verify_payment(
    payment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    Verify payment status for registered students
    """
    try:
        payment_service = PaymentService(db)
        
        # Verify payment belongs to current student
        verification_result = payment_service.verify_payment(
            payment_id=payment_id,
            student_id=current_student.id
        )
        
        return SayanSuccessResponse(
            data=verification_result,
            message="تم التحقق من حالة الدفع بنجاح",
            request=request
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e), "error_type": "Not Found"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في التحقق من الدفع: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.get("/invoices")
def get_student_invoices(
    skip: int = 0,
    limit: int = 10,
    status_filter: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    Get invoices for current student
    """
    try:
        payment_service = PaymentService(db)
        
        invoices_result = payment_service.get_student_invoices(
            student_id=current_student.id,
            status=status_filter,
            skip=skip,
            limit=limit
        )
        
        return SayanSuccessResponse(
            data=invoices_result,
            message="تم جلب الفواتير بنجاح",
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في جلب الفواتير: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.get("/invoices/{invoice_id}")
def get_invoice_details(
    invoice_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    Get invoice details for current student
    """
    try:
        payment_service = PaymentService(db)
        
        invoice_details = payment_service.get_invoice_details(
            invoice_id=invoice_id,
            student_id=current_student.id
        )
        
        return SayanSuccessResponse(
            data=invoice_details,
            message="تم جلب تفاصيل الفاتورة بنجاح",
            request=request
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e), "error_type": "Not Found"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في جلب تفاصيل الفاتورة: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.get("/methods")
def get_payment_methods(
    request: Request,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    Get available payment methods for students
    """
    try:
        moyasar_service = MoyasarService(db)
        payment_methods = moyasar_service.get_payment_methods()
        
        return SayanSuccessResponse(
            data=payment_methods,
            message="تم جلب طرق الدفع بنجاح",
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في جلب طرق الدفع: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.post("/webhook/moyasar")
async def moyasar_webhook(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Handle Moyasar webhook for payment status updates
    """
    try:
        moyasar_service = MoyasarService(db)
        
        body = await request.body()
        signature = request.headers.get("x-moyasar-signature", "")
        
        webhook_result = moyasar_service.process_webhook(body, signature)
        
        if webhook_result["success"]:
            return SayanSuccessResponse(
                data=webhook_result,
                message="تم معالجة الـ webhook بنجاح",
                request=request
            )
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": webhook_result.get("error", "فشل في معالجة الـ webhook"),
                    "error_type": webhook_result.get("error_code", "Webhook Error"),
                    "data": None
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "status_code": 500,
                "message": f"خطأ في معالجة الـ webhook: {str(e)}",
                "error_type": "Internal Server Error",
                "data": None,
                "path": str(request.url.path),
                "timestamp": "2025-01-01T00:00:00Z"
            }
        )


@router.get("/student/enrollment-history")
def get_student_enrollment_history(
    skip: int = 0,
    limit: int = 10,
    request: Request = None,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    Get student's course enrollment history
    """
    try:
        payment_service = PaymentService(db)
        
        enrollment_history = payment_service.get_student_enrollment_history(
            student_id=current_student.id,
            skip=skip,
            limit=limit
        )
        
        return SayanSuccessResponse(
            data=enrollment_history,
            message="تم جلب تاريخ التسجيل بنجاح",
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في جلب تاريخ التسجيل: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.get("/student/payment-history")
def get_student_payment_history(
    skip: int = 0,
    limit: int = 10,
    request: Request = None,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """
    Get student's payment transaction history
    """
    try:
        payment_service = PaymentService(db)
        
        payment_history = payment_service.get_student_payment_history(
            student_id=current_student.id,
            skip=skip,
            limit=limit
        )
        
        return SayanSuccessResponse(
            data=payment_history,
            message="تم جلب تاريخ المدفوعات بنجاح",
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في جلب تاريخ المدفوعات: {str(e)}", "error_type": "Internal Server Error"}
        ) 