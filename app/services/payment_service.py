"""
Payment service for managing invoices, payments, and enrollments.
Student registration required for all payment operations.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import json

from app.models.payment import Invoice, InvoiceProduct, Payment, PaymentStatus, PaymentGateway, CouponUsage
from app.models.marketing import Coupon
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
        student_id: int,
        cookie_id: Optional[str] = None,
        coupon_code: Optional[str] = None,
        billing_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create invoice from student's cart - Student registration required
        """
        try:
            # Verify student exists
            student = self.db.query(Student).filter(Student.id == student_id).first()
            if not student:
                raise ValueError("الطالب غير موجود")
            
            # Get cart summary with student validation
            cart_summary = self.cart_service.get_cart_summary(
                student_id=student_id,
                cookie_id=cookie_id,
                coupon_code=coupon_code
            )
            
            if cart_summary["items_count"] == 0:
                raise ValueError("لا يمكن إتمام عملية الدفع، سلة المشتريات فارغة")
            
            # Generate unique invoice number
            invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            
            # Prepare billing information
            billing_name = billing_info.get("name") if billing_info else f"{student.user.fname} {student.user.lname}"
            billing_email = billing_info.get("email") if billing_info else student.user.email
            billing_phone = billing_info.get("phone") if billing_info else student.user.phone_number
            
            # Create invoice
            invoice = Invoice(
                invoice_number=invoice_number,
                student_id=student_id,
                academy_id=None,  # Will be set from first course
                subtotal=Decimal(str(cart_summary["subtotal"])),
                tax_amount=Decimal(str(cart_summary["tax_amount"])),
                discount_amount=Decimal(str(cart_summary["discount_amount"])),
                total_amount=Decimal(str(cart_summary["total"])),
                currency=cart_summary["currency"],
                coupon_code=coupon_code,
                billing_name=billing_name,
                billing_email=billing_email,
                billing_phone=billing_phone,
                billing_address=billing_info.get("address") if billing_info else None,
                status=PaymentStatus.PENDING,
                extra_metadata=json.dumps({
                    "cookie_id": cookie_id,
                    "cart_items_count": cart_summary["items_count"],
                    "student_verification": "verified"
                })
            )
            
            self.db.add(invoice)
            self.db.flush()
            
            # Add invoice products
            for item in cart_summary["items"]:
                if item["item_type"] == "course":
                    course = self.db.query(Course).filter(Course.id == item["item_id"]).first()
                    if course:
                        # Set academy_id from first course
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
            
            # Handle coupon usage
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
                    
                    # Update coupon usage count
                    coupon.used_count += 1
            
            self.db.commit()
            self.db.refresh(invoice)
            
            return {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "total_amount": float(invoice.total_amount),
                "currency": invoice.currency,
                "status": invoice.status.value,
                "items": cart_summary["items"],
                "student_verified": True,
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
        """
        Process payment for verified student invoice
        """
        try:
            # Get invoice with student verification
            invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
            if not invoice:
                raise ValueError("الفاتورة غير موجودة")
            
            if invoice.status != PaymentStatus.PENDING:
                raise ValueError("حالة الفاتورة لا تسمح بالدفع")
            
            # Verify student exists
            student = self.db.query(Student).filter(Student.id == invoice.student_id).first()
            if not student:
                raise ValueError("الطالب غير موجود")
            
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
                net_amount=invoice.total_amount,
                extra_metadata=json.dumps({
                    "student_name": f"{student.user.fname} {student.user.lname}",
                    "student_email": student.user.email
                })
            )
            
            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)
            
            # Process through Moyasar gateway
            if payment_method == "moyasar":
                frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
                success_url = success_url or f"{frontend_url}/payment-success"
                back_url = back_url or f"{frontend_url}/cart"
                callback_url = callback_url or f"{settings.API_V1_STR}/payment/webhook/moyasar"
                
                gateway_result = self.moyasar_service.create_invoice(
                    amount=int(invoice.total_amount * 100),  # Convert to halalas
                    currency=invoice.currency,
                    description=f"Payment for invoice {invoice.invoice_number} - Student: {student.user.fname} {student.user.lname}",
                    success_url=success_url,
                    back_url=back_url,
                    callback_url=callback_url,
                    metadata={
                        "invoice_id": invoice.id,
                        "payment_id": payment.id,
                        "student_id": invoice.student_id,
                        "student_email": student.user.email
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
                raise ValueError(f"طريقة الدفع غير مدعومة: {payment_method}")
                
        except Exception as e:
            self.db.rollback()
            raise e
    
    def verify_payment(self, payment_id: int, student_id: int) -> Dict[str, Any]:
        """
        Verify payment status with student validation
        """
        try:
            # Get payment with student verification
            payment = self.db.query(Payment).filter(
                Payment.id == payment_id,
                Payment.student_id == student_id
            ).first()
            
            if not payment:
                raise ValueError("المعاملة غير موجودة أو غير مخولة")
            
            # Process through Moyasar gateway
            if payment.payment_gateway == PaymentGateway.MOYASAR:
                gateway_result = self.moyasar_service.get_invoice_status(payment.transaction_id)
                
                if gateway_result["success"]:
                    gateway_status = gateway_result["status"]
                    
                    if gateway_status == "paid":
                        # Update payment status
                        payment.payment_status = PaymentStatus.PAID
                        payment.confirmed_at = datetime.utcnow()
                        
                        # Update invoice status
                        invoice = payment.invoice
                        invoice.status = PaymentStatus.PAID
                        invoice.paid_at = datetime.utcnow()
                        
                        # Process course enrollments
                        enrollment_result = self._process_course_enrollments(payment.invoice_id)
                        
                        # Clear student's cart
                        self._clear_student_cart(payment.student_id, invoice.extra_metadata)
                        
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
                            "error": "فشل في عملية الدفع"
                        }
                    
                    else:
                        return {
                            "success": True,
                            "status": gateway_status,
                            "payment_id": payment.id,
                            "message": "عملية الدفع قيد المعالجة"
                        }
                
                else:
                    return {
                        "success": False,
                        "error": gateway_result.get("error", "فشل في التحقق من حالة الدفع"),
                        "payment_id": payment.id
                    }
            
            else:
                raise ValueError(f"بوابة الدفع غير مدعومة: {payment.payment_gateway}")
                
        except Exception as e:
            self.db.rollback()
            raise e
    
    def _process_course_enrollments(self, invoice_id: int) -> Dict[str, Any]:
        """
        Process course enrollments for paid invoice
        """
        try:
            invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
            if not invoice:
                raise ValueError("الفاتورة غير موجودة")
            
            enrolled_courses = []
            
            for invoice_product in invoice.invoice_products:
                # Check for existing enrollment
                existing_enrollment = self.db.query(StudentCourse).filter(
                    StudentCourse.student_id == invoice.student_id,
                    StudentCourse.course_id == invoice_product.course_id
                ).first()
                
                if existing_enrollment:
                    # Update existing enrollment
                    existing_enrollment.status = "active"
                    existing_enrollment.paid_amount = invoice_product.total_price
                    existing_enrollment.last_accessed_at = datetime.utcnow()
                    
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
                        enrolled_at=datetime.utcnow(),
                        last_accessed_at=datetime.utcnow()
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
    
    def _clear_student_cart(self, student_id: int, extra_metadata: Optional[str]) -> None:
        """
        Clear student's cart after successful payment
        """
        try:
            # Extract cookie_id if available
            cookie_id = None
            if extra_metadata:
                try:
                    data = json.loads(extra_metadata)
                    cookie_id = data.get("cookie_id")
                except:
                    pass
            
            # Clear cart items for student
            cart_items = self.db.query(Cart).filter(
                Cart.student_id == student_id,
                Cart.deleted_at.is_(None)
            ).all()
            
            # Also clear any items with matching cookie_id
            if cookie_id:
                cookie_items = self.db.query(Cart).filter(
                    Cart.cookie_id == cookie_id,
                    Cart.deleted_at.is_(None)
                ).all()
                cart_items.extend(cookie_items)
            
            # Soft delete all cart items
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
        """
        Get invoices for specific student
        """
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
        """
        Get invoice details for specific student
        """
        try:
            invoice = self.db.query(Invoice).filter(
                Invoice.id == invoice_id,
                Invoice.student_id == student_id
            ).first()
            
            if not invoice:
                raise ValueError("الفاتورة غير موجودة")
            
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
    
    def get_student_enrollment_history(
        self,
        student_id: int,
        skip: int = 0,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get student's course enrollment history
        """
        try:
            query = self.db.query(StudentCourse).filter(StudentCourse.student_id == student_id)
            query = query.order_by(StudentCourse.enrolled_at.desc())
            
            total = query.count()
            enrollments = query.offset(skip).limit(limit).all()
            
            enrollment_data = []
            for enrollment in enrollments:
                from sqlalchemy.orm import joinedload
                course = self.db.query(Course).options(
                    joinedload(Course.product)
                ).filter(Course.id == enrollment.course_id).first()
                enrollment_data.append({
                    "enrollment_id": enrollment.id,
                    "course_id": enrollment.course_id,
                    "course_title": course.product.title if course and course.product else "Unknown Course",
                    "course_image": course.image if course else None,
                    "status": enrollment.status,
                    "paid_amount": float(enrollment.paid_amount) if enrollment.paid_amount else 0.0,
                    "completion_percentage": float(enrollment.progress_percentage),
                    "enrolled_at": enrollment.enrolled_at.isoformat(),
                    "started_at": enrollment.started_at.isoformat() if enrollment.started_at else None,
                    "last_accessed_at": enrollment.last_accessed_at.isoformat() if enrollment.last_accessed_at else None
                })
            
            return {
                "enrollments": enrollment_data,
                "total": total,
                "skip": skip,
                "limit": limit
            }
            
        except Exception as e:
            raise e
    
    def get_student_payment_history(
        self,
        student_id: int,
        skip: int = 0,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get student's payment transaction history
        """
        try:
            query = self.db.query(Payment).filter(Payment.student_id == student_id)
            query = query.order_by(Payment.created_at.desc())
            
            total = query.count()
            payments = query.offset(skip).limit(limit).all()
            
            payment_data = []
            for payment in payments:
                payment_data.append({
                    "payment_id": payment.id,
                    "payment_reference": payment.payment_id,
                    "invoice_number": payment.invoice.invoice_number,
                    "amount": float(payment.amount),
                    "currency": payment.currency,
                    "payment_method": payment.payment_method,
                    "status": payment.payment_status.value,
                    "created_at": payment.created_at.isoformat(),
                    "confirmed_at": payment.confirmed_at.isoformat() if payment.confirmed_at else None
                })
            
            return {
                "payments": payment_data,
                "total": total,
                "skip": skip,
                "limit": limit
            }
            
        except Exception as e:
            raise e
    
    def process_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Process webhook from payment gateway
        """
        return self.moyasar_service.process_webhook(payload, signature) 