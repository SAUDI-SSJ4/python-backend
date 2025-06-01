from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models here to ensure they are registered
from app.models.admin import Admin
from app.models.role import Role, Permission, RolePermission
from app.models.academy import Academy, AcademyUser, Trainer, Subscription, AcademyWallet
from app.models.student import Student, StudentCourse, StudentProduct, Favourite, StudentLessonProgress
from app.models.course import Course, Category, Chapter, Lesson, Video, Exam, Question, QuestionOption, Answer, Rate, InteractiveTool
from app.models.finance import Payment, PaymentRow, Transaction, WithdrawalRequest, AcademyFinance, StudentFinance, SayanFinance
from app.models.product import Product, Package, DigitalProduct, StudentDigitalProduct, DigitalProductRating
from app.models.general import Blog, BlogPost, BlogCategory, BlogComment, BlogKeyword, BlogPostKeyword
from app.models.marketing import Coupon, AffiliateLink
from app.models.template import Template, About, Slider, Faq, Opinion 