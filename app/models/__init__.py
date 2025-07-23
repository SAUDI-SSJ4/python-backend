# Models package 
from .user import User, UserType, UserStatus, AccountType
from .student import Student, Gender
from .academy import Academy, AcademyUser, AcademyStatus, AcademyUserRole
from .otp import OTP, OTPPurpose
from .finance import AcademyFinance, StudentFinance, Transaction
from .admin import Admin
from .marketing import Coupon

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
from .interactive_tool import InteractiveTool, ToolType
from .lesson_progress import LessonProgress
from .student_course import StudentCourse

# AI Assistant models - comprehensive AI functionality
from .ai_assistant import (
    AIAnswer, VideoTranscription, ExamCorrection, QuestionCorrection,
    LessonSummary, AIExamTemplate, AIGeneratedQuestion, AIConversation,
    AIConversationMessage, AIKnowledgeBase, AIPerformanceMetric, AISetting,
    ProcessingStatus, AIAnswerType, ConversationType, ContextType,
    ConversationStatus, SenderType, MessageType, DifficultyLevel,
    QuestionType, ContentType, MetricType, SettingType
)

# Template models
from .template import Template, About, Slider, Faq, Opinion

# Settings model
from .settings import Settings

# Token blacklist model
from .blacklisted_token import BlacklistedToken

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
    
    # Course models
    "Course", "CourseStatus", "CourseType", "CourseLevel", "Category",
    "Product", "DigitalProduct", "Package", "StudentProduct", "ProductStatus", "ProductType", "PackageType",
    "Chapter", "Lesson", "LessonType", "VideoType",
    "Video", "Cart", "CartSession",
    "Invoice", "InvoiceProduct", "Payment", "PaymentGatewayLog", "CouponUsage", "PaymentStatus", "PaymentGateway",
    "Exam", "Question", "QuestionOption", "QuestionType",
    "InteractiveTool", "ToolType", "LessonProgress", "StudentCourse",
    
    # Template models
    "Template", "About", "Slider", "Faq", "Opinion",
    "Settings",
    
    # AI Assistant models
    "AIAnswer", "VideoTranscription", "ExamCorrection", "QuestionCorrection",
    "LessonSummary", "AIExamTemplate", "AIGeneratedQuestion", "AIConversation",
    "AIConversationMessage", "AIKnowledgeBase", "AIPerformanceMetric", "AISetting",
    
    # AI Assistant enums
    "ProcessingStatus", "AIAnswerType", "ConversationType", "ContextType",
    "ConversationStatus", "SenderType", "MessageType", "DifficultyLevel",
    "ContentType", "MetricType", "SettingType",
    
    # Token blacklist
    "BlacklistedToken"
] 