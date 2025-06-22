from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from app.db.base import Base


class UserType(PyEnum):
    STUDENT = "student"
    ACADEMY = "academy"


class AccountType(PyEnum):
    LOCAL = "local"
    GOOGLE = "google"


class UserStatus(PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    PENDING_VERIFICATION = "pending_verification"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    fname = Column(String(50), nullable=False)
    mname = Column(String(50), nullable=True)
    lname = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone_number = Column(String(20), unique=True, index=True, nullable=True)
    password = Column(String(255), nullable=True)
    
    # User classification
    user_type = Column(String(20), nullable=False)  # Using String instead of Enum
    account_type = Column(String(20), default="local")  # Using String instead of Enum
    status = Column(String(30), default="pending_verification")  # Using String instead of Enum
    
    # Verification
    verified = Column(Boolean, default=False)
    
    # Google OAuth fields
    google_id = Column(String(255), nullable=True, unique=True, index=True)
    
    # Profile information
    avatar = Column(String(255), nullable=True)
    banner = Column(String(255), nullable=True)
    
    # Referral system
    refere_id = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    student_profile = relationship("Student", back_populates="user", uselist=False)
    academy_profile = relationship("Academy", back_populates="user", uselist=False)
    academy_memberships = relationship("AcademyUser", back_populates="user")
    otps = relationship("OTP", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', user_type='{self.user_type}')>"

    @property
    def full_name(self):
        """Get user's full name"""
        if self.mname:
            return f"{self.fname} {self.mname} {self.lname}"
        return f"{self.fname} {self.lname}"

    @property
    def is_active(self):
        """Check if user account is active"""
        return self.status == "active"

    @property
    def is_verified(self):
        """Check if user is verified"""
        return self.verified

    def can_login(self):
        """Check if user can login"""
        return self.is_active and not self.status == "blocked"