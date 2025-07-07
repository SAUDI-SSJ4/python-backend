from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum
from app.models.marketing import Coupon


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    WALLET = "wallet"
    PAYPAL = "paypal"
    MOYASAR = "moyasar"


class TransactionType(str, enum.Enum):
    PAYMENT = "payment"
    REFUND = "refund"
    WITHDRAWAL = "withdrawal"
    COMMISSION = "commission"
    SUBSCRIPTION = "subscription"


class WithdrawalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class PaymentRow(Base):
    __tablename__ = "payment_rows"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    item_type = Column(String(50), nullable=False)  # course, product, subscription
    item_id = Column(Integer, nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    payment = relationship("Payment", back_populates="payment_rows")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    type = Column(SQLEnum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=True)
    balance_after = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    reference_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships - معلق مؤقتاً لحل conflicts
    payment = relationship("Payment", back_populates="transactions")
    academy = relationship("Academy")
    # student = relationship("Student")


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(SQLEnum(WithdrawalStatus), default=WithdrawalStatus.PENDING)
    bank_name = Column(String(255), nullable=True)
    account_name = Column(String(255), nullable=True)
    account_number = Column(String(255), nullable=True)
    iban = Column(String(255), nullable=True)
    swift_code = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy")
    # admin = relationship("Admin", foreign_keys=[approved_by])  # معطل مؤقتاً


class AcademyFinance(Base):
    __tablename__ = "academy_finances"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), unique=True, nullable=False)
    total_revenue = Column(Float, default=0.0)
    total_withdrawals = Column(Float, default=0.0)
    pending_withdrawals = Column(Float, default=0.0)
    commission_rate = Column(Float, default=0.15)  # 15% default commission
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships - معلق مؤقتاً لحل conflicts
    # academy = relationship("Academy", back_populates="finance")


class StudentFinance(Base):
    __tablename__ = "student_finances"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=False)
    total_spent = Column(Float, default=0.0)
    total_courses = Column(Integer, default=0)
    total_products = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships - معلق مؤقتاً لحل conflicts
    # student = relationship("Student", back_populates="finance")


class SayanFinance(Base):
    __tablename__ = "sayan_finances"

    id = Column(Integer, primary_key=True, index=True)
    total_revenue = Column(Float, default=0.0)
    total_commissions = Column(Float, default=0.0)
    total_subscriptions = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 