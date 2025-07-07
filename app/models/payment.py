"""
Payment, Invoice, and related models for handling payments and billing.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Numeric, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from app.db.base import Base
from app.models.marketing import Coupon


class PaymentStatus(PyEnum):
    """Payment status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentGateway(PyEnum):
    """Payment gateway enumeration"""
    MOYASAR = "moyasar"
    STRIPE = "stripe"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    WALLET = "wallet"


class Invoice(Base):
    """
    Invoice model for managing billing and payment tracking.
    """
    
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Invoice identification
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Student association
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False, index=True)
    
    # Payment details
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="SAR", nullable=False)
    
    # Coupon information
    coupon_code = Column(String(50), nullable=True)
    
    # Status and timestamps
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    
    # Billing information
    billing_name = Column(String(255), nullable=False)
    billing_email = Column(String(255), nullable=False)
    billing_phone = Column(String(20), nullable=True)
    billing_address = Column(JSON, nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    extra_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    student = relationship("Student", back_populates="invoices")
    academy = relationship("Academy")
    invoice_products = relationship("InvoiceProduct", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice")
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, invoice_number={self.invoice_number}, status={self.status})>"
    
    @property
    def is_paid(self) -> bool:
        """Check if invoice is paid"""
        return self.status == PaymentStatus.PAID
    
    @property
    def is_pending(self) -> bool:
        """Check if invoice is pending payment"""
        return self.status == PaymentStatus.PENDING


class InvoiceProduct(Base):
    """
    Invoice product/course items model.
    """
    
    __tablename__ = "invoice_products"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Invoice association
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    
    # Product/Course details
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    product_description = Column(Text, nullable=True)
    
    # Pricing
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    
    # Discount information
    discount_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    discount_percentage = Column(Numeric(5, 2), default=0.00, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="invoice_products")
    course = relationship("Course")
    
    def __repr__(self):
        return f"<InvoiceProduct(id={self.id}, invoice_id={self.invoice_id}, course_id={self.course_id})>"


class Payment(Base):
    """
    Payment model for tracking payment transactions.
    """
    
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Payment identification
    payment_id = Column(String(100), unique=True, nullable=False, index=True)
    transaction_id = Column(String(100), nullable=True, index=True)
    
    # Associations
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False, index=True)
    
    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="SAR", nullable=False)
    
    # Payment method and gateway
    payment_method = Column(String(50), nullable=False)
    payment_gateway = Column(Enum(PaymentGateway), nullable=False, index=True)
    
    # Status and processing
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    gateway_response = Column(JSON, nullable=True)
    
    # Fees and charges
    gateway_fee = Column(Numeric(10, 2), default=0.00, nullable=False)
    platform_fee = Column(Numeric(10, 2), default=0.00, nullable=False)
    net_amount = Column(Numeric(10, 2), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    
    # Refund information
    refunded_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    refunded_at = Column(DateTime, nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    extra_metadata = Column(JSON, nullable=True)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
    student = relationship("Student", back_populates="payments")
    academy = relationship("Academy")
    gateway_logs = relationship("PaymentGatewayLog", back_populates="payment", cascade="all, delete-orphan")
    payment_rows = relationship("PaymentRow", back_populates="payment")
    transactions = relationship("Transaction", back_populates="payment")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, payment_id={self.payment_id}, status={self.payment_status})>"
    
    @property
    def is_successful(self) -> bool:
        """Check if payment is successful"""
        return self.payment_status == PaymentStatus.PAID
    
    @property
    def is_pending(self) -> bool:
        """Check if payment is pending"""
        return self.payment_status == PaymentStatus.PENDING
    
    @property
    def is_failed(self) -> bool:
        """Check if payment failed"""
        return self.payment_status == PaymentStatus.FAILED


class PaymentGatewayLog(Base):
    """
    Payment gateway interaction logs.
    """
    
    __tablename__ = "payment_gateway_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Payment association
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False, index=True)
    
    # Gateway information
    gateway = Column(String(50), nullable=False)
    gateway_transaction_id = Column(String(100), nullable=True)
    
    # Request and response data
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    
    # Status and timing
    status = Column(String(50), nullable=False)
    response_code = Column(String(10), nullable=True)
    response_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    payment = relationship("Payment", back_populates="gateway_logs")
    
    def __repr__(self):
        return f"<PaymentGatewayLog(id={self.id}, payment_id={self.payment_id}, gateway={self.gateway})>"


class CouponUsage(Base):
    """
    Coupon usage tracking model.
    """
    
    __tablename__ = "coupon_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Associations
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    
    # Usage details
    discount_amount = Column(Numeric(10, 2), nullable=False)
    
    # Timestamps
    used_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    coupon = relationship("Coupon", back_populates="coupon_usages")
    student = relationship("Student", back_populates="coupon_usages")
    invoice = relationship("Invoice")
    
    def __repr__(self):
        return f"<CouponUsage(id={self.id}, coupon_id={self.coupon_id}, student_id={self.student_id})>" 