"""
Payment service for managing invoices, payments, and enrollments.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

from app.models.payment import Invoice, InvoiceProduct, Payment, PaymentStatus, PaymentGateway, Coupon, CouponUsage
from app.models.cart import Cart
from app.models.student import Student
from app.models.course import Course
from app.models.student_course import StudentCourse
from app.services.cart_service import CartService
from app.services.moyasar_service import MoyasarService
from app.core.config import settings


class PaymentService:
    """
    Service for managing payment operations and course enrollments.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.cart_service = CartService(db)
        self.moyasar_service = MoyasarService(db)
    
    def create_invoice_from_cart(
        self,
        student_id: int,
        session_id: Optional[str] = None,
        coupon_code: Optional[str] = None,
        billing_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an invoice from cart items.
        """
        # Get cart summary
        cart_summary = self.cart_service.get_cart_summary(
            student_id=student_id,
            session_id=session_id,
            coupon_code=coupon_code
        )
        
        if cart_summary["items_count"] == 0:
            raise ValueError("Cart is empty")
        
        # Get student information
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError("Student not found")
        
        # Generate invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            student_id=student_id,
            academy_id=cart_summary["items"][0]["academy"]["id"],  # Use first item's academy
            subtotal=Decimal(str(cart_summary["subtotal"])),
            tax_amount=Decimal(str(cart_summary["tax_amount"])),
            discount_amount=Decimal(str(cart_summary["discount_amount"])),
            total_amount=Decimal(str(cart_summary["total"])),
            currency=cart_summary["currency"],
            coupon_code=coupon_code,
            billing_name=billing_info.get("name", f"{student.user.fname} {student.user.lname}"),
            billing_email=billing_info.get("email", student.user.email),
            billing_phone=billing_info.get("phone", student.user.phone_number),
            billing_address=billing_info.get("address"),
            status=PaymentStatus.PENDING
        )
        
        self.db.add(invoice)
        self.db.flush()  # To get the invoice ID
        
        # Create invoice products
        for item in cart_summary["items"]:
            course = self.db.query(Course).filter(Course.id == item["course_id"]).first()
            if course and course.product:
                invoice_product = InvoiceProduct(
                    invoice_id=invoice.id,
                    course_id=item["course_id"],
                    product_name=item["course_title"],
                    product_description=course.product.description,
                    unit_price=Decimal(str(item["unit_price"])),
                    quantity=item["quantity"],
                    total_price=Decimal(str(item["total_price"]))
                )
                self.db.add(invoice_product)
        
        # Record coupon usage if applied
        if coupon_code and cart_summary["coupon_applied"]:
            coupon = self.db.query(Coupon).filter(Coupon.code == coupon_code.upper()).first()
            if coupon:
                coupon_usage = CouponUsage(
                    coupon_id=coupon.id,
                    student_id=student_id,
                    invoice_id=invoice.id,
                    discount_amount=Decimal(str(cart_summary["discount_amount"]))
                )
                self.db.add(coupon_usage)
        
        self.db.commit()
        self.db.refresh(invoice)
        
        return {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "total_amount": float(invoice.total_amount),
            "currency": invoice.currency,
            "status": invoice.status.value,
            "items": cart_summary["items"],
            "created_at": invoice.created_at.isoformat()
        }
    
    def process_payment(
        self,
        invoice_id: int,
        payment_method: str = "moyasar",
        return_url: Optional[str] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process payment for an invoice.
        """
        # Get invoice
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")
        
        if invoice.status != PaymentStatus.PENDING:
            raise ValueError("Invoice is not pending payment")
        
        # Generate payment ID
        payment_id = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Create payment record
        payment = Payment(
            payment_id=payment_id,
            invoice_id=invoice.id,
            student_id=invoice.student_id,
            academy_id=invoice.academy_id,
            amount=invoice.total_amount,
            currency=invoice.currency,
            payment_method=payment_method,
            payment_gateway=PaymentGateway.MOYASAR,
            payment_status=PaymentStatus.PENDING,
            net_amount=invoice.total_amount  # Will be updated after fees calculation
        )
        
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        
        # Process with payment gateway
        if payment_method == "moyasar":
            gateway_result = self.moyasar_service.create_payment_intent(
                amount=invoice.total_amount,
                currency=invoice.currency,
                description=f"Payment for invoice {invoice.invoice_number}",
                metadata={
                    "invoice_id": invoice.id,
                    "payment_id": payment.id,
                    "student_id": invoice.student_id
                }
            )
            
            if gateway_result["success"]:
                # Update payment with gateway information
                payment.transaction_id = gateway_result["payment_id"]
                payment.gateway_response = gateway_result["data"]
                self.db.commit()
                
                return {
                    "success": True,
                    "payment_id": payment.id,
                    "gateway_payment_id": gateway_result["payment_id"],
                    "payment_url": gateway_result.get("transaction_url"),
                    "status": gateway_result["status"],
                    "amount": float(invoice.total_amount),
                    "currency": invoice.currency
                }
            else:
                # Update payment status to failed
                payment.payment_status = PaymentStatus.FAILED
                payment.gateway_response = gateway_result
                self.db.commit()
                
                return {
                    "success": False,
                    "error": gateway_result["error"],
                    "payment_id": payment.id
                }
        
        else:
            raise ValueError(f"Unsupported payment method: {payment_method}")
    
    def verify_payment(self, payment_id: int) -> Dict[str, Any]:
        """
        Verify payment status and process enrollment if successful.
        """
        # Get payment record
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError("Payment not found")
        
        # Verify with payment gateway
        if payment.payment_gateway == PaymentGateway.MOYASAR:
            gateway_result = self.moyasar_service.verify_payment(payment.transaction_id)
            
            if gateway_result["success"]:
                # Update payment status based on gateway response
                gateway_status = gateway_result["status"]
                
                if gateway_status == "paid":
                    payment.payment_status = PaymentStatus.PAID
                    payment.confirmed_at = datetime.utcnow()
                    
                    # Update invoice status
                    invoice = payment.invoice
                    invoice.status = PaymentStatus.PAID
                    invoice.paid_at = datetime.utcnow()
                    
                    # Process course enrollments
                    enrollment_result = self._process_course_enrollments(payment.invoice_id)
                    
                    # Clear cart items
                    self._clear_cart_after_payment(payment.student_id)
                    
                    self.db.commit()
                    
                    return {
                        "success": True,
                        "status": "paid",
                        "payment_id": payment.id,
                        "enrollment_result": enrollment_result,
                        "verified_at": datetime.utcnow().isoformat()
                    }
                
                elif gateway_status == "failed":
                    payment.payment_status = PaymentStatus.FAILED
                    payment.gateway_response = gateway_result["data"]
                    self.db.commit()
                    
                    return {
                        "success": False,
                        "status": "failed",
                        "payment_id": payment.id,
                        "error": "Payment failed"
                    }
                
                else:
                    # Still pending or processing
                    return {
                        "success": True,
                        "status": gateway_status,
                        "payment_id": payment.id,
                        "message": "Payment is still processing"
                    }
            
            else:
                return {
                    "success": False,
                    "error": gateway_result["error"],
                    "payment_id": payment.id
                }
        
        else:
            raise ValueError(f"Unsupported payment gateway: {payment.payment_gateway}")
    
    def _process_course_enrollments(self, invoice_id: int) -> Dict[str, Any]:
        """
        Process course enrollments after successful payment.
        """
        # Get invoice and its products
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")
        
        enrolled_courses = []
        
        for invoice_product in invoice.invoice_products:
            # Check if student is already enrolled
            existing_enrollment = self.db.query(StudentCourse).filter(
                StudentCourse.student_id == invoice.student_id,
                StudentCourse.course_id == invoice_product.course_id
            ).first()
            
            if existing_enrollment:
                # Update existing enrollment
                existing_enrollment.status = "active"
                existing_enrollment.paid_amount = invoice_product.total_price
                existing_enrollment.payment_method = "moyasar"
                enrolled_courses.append({
                    "course_id": invoice_product.course_id,
                    "action": "updated",
                    "enrollment_id": existing_enrollment.id
                })
            else:
                # Create new enrollment
                enrollment = StudentCourse(
                    student_id=invoice.student_id,
                    course_id=invoice_product.course_id,
                    status="active",
                    paid_amount=invoice_product.total_price,
                    payment_method="moyasar",
                    enrolled_at=datetime.utcnow()
                )
                self.db.add(enrollment)
                self.db.flush()
                
                enrolled_courses.append({
                    "course_id": invoice_product.course_id,
                    "action": "enrolled",
                    "enrollment_id": enrollment.id
                })
        
        self.db.commit()
        
        return {
            "enrolled_courses": enrolled_courses,
            "total_courses": len(enrolled_courses)
        }
    
    def _clear_cart_after_payment(self, student_id: int) -> None:
        """
        Clear cart items after successful payment.
        """
        cart_items = self.db.query(Cart).filter(
            Cart.student_id == student_id,
            Cart.deleted_at.is_(None)
        ).all()
        
        for item in cart_items:
            item.soft_delete()
        
        self.db.commit()
    
    def get_student_invoices(
        self,
        student_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get student invoices with pagination.
        """
        query = self.db.query(Invoice).filter(Invoice.student_id == student_id)
        
        if status:
            query = query.filter(Invoice.status == status)
        
        query = query.order_by(Invoice.created_at.desc())
        
        total = query.count()
        invoices = query.offset(skip).limit(limit).all()
        
        invoice_data = []
        for invoice in invoices:
            invoice_data.append({
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "total_amount": float(invoice.total_amount),
                "currency": invoice.currency,
                "status": invoice.status.value,
                "created_at": invoice.created_at.isoformat(),
                "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
                "items_count": len(invoice.invoice_products)
            })
        
        return {
            "invoices": invoice_data,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    
    def get_invoice_details(self, invoice_id: int, student_id: int) -> Dict[str, Any]:
        """
        Get detailed invoice information.
        """
        invoice = self.db.query(Invoice).filter(
            Invoice.id == invoice_id,
            Invoice.student_id == student_id
        ).first()
        
        if not invoice:
            raise ValueError("Invoice not found")
        
        # Get invoice products
        products = []
        for product in invoice.invoice_products:
            course = self.db.query(Course).filter(Course.id == product.course_id).first()
            products.append({
                "course_id": product.course_id,
                "course_title": product.product_name,
                "course_image": course.image if course else None,
                "unit_price": float(product.unit_price),
                "quantity": product.quantity,
                "total_price": float(product.total_price)
            })
        
        return {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "status": invoice.status.value,
            "subtotal": float(invoice.subtotal),
            "tax_amount": float(invoice.tax_amount),
            "discount_amount": float(invoice.discount_amount),
            "total_amount": float(invoice.total_amount),
            "currency": invoice.currency,
            "coupon_code": invoice.coupon_code,
            "billing_info": {
                "name": invoice.billing_name,
                "email": invoice.billing_email,
                "phone": invoice.billing_phone,
                "address": invoice.billing_address
            },
            "products": products,
            "created_at": invoice.created_at.isoformat(),
            "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None
        }
    
    def process_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Process payment gateway webhook.
        """
        return self.moyasar_service.process_webhook(payload, signature) 