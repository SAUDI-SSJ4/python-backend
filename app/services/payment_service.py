"""
Payment service for managing invoices, payments, and enrollments.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import json

from app.models.payment import Invoice, InvoiceProduct, Payment, PaymentStatus, PaymentGateway, Coupon, CouponUsage
from app.models.cart import Cart
from app.models.student import Student
from app.models.course import Course
from app.models.student_course import StudentCourse
from app.services.cart_service import CartService
from app.services.moyasar_service import MoyasarService
from app.core.config import settings


class PaymentService:
    
    def __init__(self, db: Session):
        self.db = db
        self.cart_service = CartService(db)
        self.moyasar_service = MoyasarService(db)
    
    def create_invoice_from_cart(
        self,
        student_id: Optional[int] = None,
        cookie_id: Optional[str] = None,
        session_id: Optional[str] = None,
        coupon_code: Optional[str] = None,
        billing_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            cart_summary = self.cart_service.get_cart_summary(
                student_id=student_id,
                cookie_id=cookie_id,
                session_id=session_id,
                coupon_code=coupon_code
            )
            
            if cart_summary["items_count"] == 0:
                raise ValueError("لا يمكن إتمام عملية الدفع، سلة المشتريات فارغة")
            
            student = None
            if student_id:
                student = self.db.query(Student).filter(Student.id == student_id).first()
                if not student:
                    raise ValueError("Student not found")
            
            invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            
            invoice = Invoice(
                invoice_number=invoice_number,
                student_id=student_id,
                academy_id=None,
                subtotal=Decimal(str(cart_summary["subtotal"])),
                tax_amount=Decimal(str(cart_summary["tax_amount"])),
                discount_amount=Decimal(str(cart_summary["discount_amount"])),
                total_amount=Decimal(str(cart_summary["total"])),
                currency=cart_summary["currency"],
                coupon_code=coupon_code,
                billing_name=billing_info.get("name", f"{student.user.fname} {student.user.lname}" if student else "Guest"),
                billing_email=billing_info.get("email", student.user.email if student else ""),
                billing_phone=billing_info.get("phone", student.user.phone_number if student else ""),
                billing_address=billing_info.get("address"),
                status=PaymentStatus.PENDING,
                extra_data=json.dumps({
                    "cookie_id": cookie_id,
                    "session_id": session_id,
                    "cart_items_count": cart_summary["items_count"],
                    "guest_checkout": student_id is None
                })
            )
            
            self.db.add(invoice)
            self.db.flush()
            
            for item in cart_summary["items"]:
                if item["item_type"] == "course":
                    course = self.db.query(Course).filter(Course.id == item["item_id"]).first()
                    if course:
                        if not invoice.academy_id:
                            invoice.academy_id = course.academy_id
                        
                        invoice_product = InvoiceProduct(
                            invoice_id=invoice.id,
                            course_id=item["item_id"],
                            product_name=item["title"],
                            product_description=getattr(course, 'description', ''),
                            unit_price=Decimal(str(item["price"])),
                            quantity=item["quantity"],
                            total_price=Decimal(str(item["total_price"]))
                        )
                        self.db.add(invoice_product)
            
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
                "guest_checkout": student_id is None,
                "created_at": invoice.created_at.isoformat()
            }
        except Exception as e:
            self.db.rollback()
            raise e
    
    def process_payment(
        self,
        invoice_id: int,
        payment_method: str = "moyasar",
        success_url: Optional[str] = None,
        back_url: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
            if not invoice:
                raise ValueError("Invoice not found")
            
            if invoice.status != PaymentStatus.PENDING:
                raise ValueError("Invoice is not pending payment")
            
            payment_id = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
            
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
                net_amount=invoice.total_amount
            )
            
            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)
            
            if payment_method == "moyasar":
                frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
                success_url = success_url or f"{frontend_url}/payment-success"
                back_url = back_url or f"{frontend_url}/cart"
                callback_url = callback_url or f"{settings.API_V1_STR}/payment/webhook/moyasar"
                
                gateway_result = self.moyasar_service.create_invoice(
                    amount=int(invoice.total_amount * 100),
                    currency=invoice.currency,
                    description=f"Payment for invoice {invoice.invoice_number}",
                    success_url=success_url,
                    back_url=back_url,
                    callback_url=callback_url,
                    metadata={
                        "invoice_id": invoice.id,
                        "payment_id": payment.id,
                        "student_id": invoice.student_id or "guest"
                    }
                )
                
                if gateway_result["success"]:
                    payment.transaction_id = gateway_result["invoice_id"]
                    payment.gateway_response = gateway_result["data"]
                    self.db.commit()
                    
                    return {
                        "success": True,
                        "payment_id": payment.id,
                        "gateway_invoice_id": gateway_result["invoice_id"],
                        "payment_url": gateway_result.get("payment_url"),
                        "status": gateway_result["status"],
                        "amount": float(invoice.total_amount),
                        "currency": invoice.currency,
                        "expires_at": gateway_result.get("expires_at")
                    }
                else:
                    payment.payment_status = PaymentStatus.FAILED
                    payment.gateway_response = gateway_result
                    self.db.commit()
                    
                    return {
                        "success": False,
                        "error": gateway_result.get("error", "فشل في إنشاء الفاتورة"),
                        "payment_id": payment.id
                    }
            
            else:
                raise ValueError(f"Unsupported payment method: {payment_method}")
        except Exception as e:
            self.db.rollback()
            raise e
    
    def verify_payment(self, payment_id: int) -> Dict[str, Any]:
        try:
            payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment:
                raise ValueError("Payment not found")
            
            if payment.payment_gateway == PaymentGateway.MOYASAR:
                gateway_result = self.moyasar_service.get_invoice_status(payment.transaction_id)
                
                if gateway_result["success"]:
                    gateway_status = gateway_result["status"]
                    
                    if gateway_status == "paid":
                        payment.payment_status = PaymentStatus.PAID
                        payment.confirmed_at = datetime.utcnow()
                        
                        invoice = payment.invoice
                        invoice.status = PaymentStatus.PAID
                        invoice.paid_at = datetime.utcnow()
                        
                        enrollment_result = None
                        if payment.student_id:
                            enrollment_result = self._process_course_enrollments(payment.invoice_id)
                        
                        self._clear_cart_after_payment(payment.student_id, invoice.extra_data)
                        
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
                        return {
                            "success": True,
                            "status": gateway_status,
                            "payment_id": payment.id,
                            "message": "Payment is still processing"
                        }
                
                else:
                    return {
                        "success": False,
                        "error": gateway_result.get("error", "فشل في التحقق من حالة الدفع"),
                        "payment_id": payment.id
                    }
            
            else:
                raise ValueError(f"Unsupported payment gateway: {payment.payment_gateway}")
        except Exception as e:
            self.db.rollback()
            raise e
    
    def _process_course_enrollments(self, invoice_id: int) -> Dict[str, Any]:
        try:
            invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
            if not invoice:
                raise ValueError("Invoice not found")
            
            enrolled_courses = []
            
            for invoice_product in invoice.invoice_products:
                existing_enrollment = self.db.query(StudentCourse).filter(
                    StudentCourse.student_id == invoice.student_id,
                    StudentCourse.course_id == invoice_product.course_id
                ).first()
                
                if existing_enrollment:
                    existing_enrollment.status = "active"
                    existing_enrollment.paid_amount = invoice_product.total_price
                    existing_enrollment.payment_method = "moyasar"
                    enrolled_courses.append({
                        "course_id": invoice_product.course_id,
                        "action": "updated",
                        "enrollment_id": existing_enrollment.id
                    })
                else:
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
        except Exception as e:
            self.db.rollback()
            raise e
    
    def _clear_cart_after_payment(self, student_id: Optional[int], extra_data: Optional[str]) -> None:
        try:
            cookie_id = None
            if extra_data:
                try:
                    data = json.loads(extra_data)
                    cookie_id = data.get("cookie_id")
                except:
                    pass
            
            if student_id:
                cart_items = self.db.query(Cart).filter(
                    Cart.student_id == student_id,
                    Cart.deleted_at.is_(None)
                ).all()
            elif cookie_id:
                cart_items = self.db.query(Cart).filter(
                    Cart.cookie_id == cookie_id,
                    Cart.deleted_at.is_(None)
                ).all()
            else:
                return
            
            for item in cart_items:
                item.soft_delete()
            
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
    
    def get_student_invoices(
        self,
        student_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Dict[str, Any]:
        try:
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
        except Exception as e:
            raise e
    
    def get_invoice_details(self, invoice_id: int, student_id: int) -> Dict[str, Any]:
        try:
            invoice = self.db.query(Invoice).filter(
                Invoice.id == invoice_id,
                Invoice.student_id == student_id
            ).first()
            
            if not invoice:
                raise ValueError("Invoice not found")
            
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
        except Exception as e:
            raise e
    
    def process_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        return self.moyasar_service.process_webhook(payload, signature) 