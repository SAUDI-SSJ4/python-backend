# Models package 
from .user import User, UserType, UserStatus, AccountType
from .student import Student, Gender
from .academy import Academy, AcademyUser, AcademyStatus, AcademyUserRole
from .otp import OTP, OTPPurpose
# إعادة تفعيل Finance models بعد إصلاح conflicts
from .finance import AcademyFinance, StudentFinance, Transaction
from .admin import Admin
from .marketing import Coupon
# from .role import Role, Permission, RolePermission

# Course-related models
from .course import Course, CourseStatus, CourseType, CourseLevel, Category
from .product import Product, DigitalProduct, Package, StudentProduct, ProductStatus, ProductType, PackageType
from .chapter import Chapter
from .lesson import Lesson, LessonType, VideoType
from .video import Video
from .cart import Cart, CartSession
from .payment import (
    Invoice, InvoiceProduct, Payment, PaymentGatewayLog, 
    CouponUsage, PaymentStatus, PaymentGateway
)
from .exam import Exam, Question, QuestionOption, QuestionType
from .interactive_tool import InteractiveTool
from .lesson_progress import LessonProgress
from .student_course import StudentCourse

# AI Answer model
from .ai_answer import AIAnswer

# Export all models
__all__ = [
    # User models
    "User", "UserType", "UserStatus", "AccountType",
    "Student", "Gender",
    "Academy", "AcademyUser", "AcademyStatus", "AcademyUserRole",
    "OTP", "OTPPurpose",
    "AcademyFinance", "StudentFinance", "Transaction",
    "Admin",
    "Coupon",
    # "Role", "Permission", "RolePermission",
    
    # Course models
    "Course", "CourseStatus", "CourseType", "CourseLevel", "Category",
    "Product", "DigitalProduct", "Package", "StudentProduct", "ProductStatus", "ProductType", "PackageType",
    "Chapter", "Lesson", "LessonType", "VideoType",
    "Video", "Cart", "CartSession",
    "Invoice", "InvoiceProduct", "Payment", "PaymentGatewayLog", "CouponUsage", "PaymentStatus", "PaymentGateway",
    "Exam", "Question", "QuestionOption", "QuestionType",
    "InteractiveTool", "LessonProgress", "StudentCourse", "AIAnswer"
] 