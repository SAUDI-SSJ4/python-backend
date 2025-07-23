"""
FastAPI Main Application
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from pathlib import Path
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine, text
from app.db.session import engine
from app.core.response_utils import create_error_response, ERROR_MESSAGES, ERROR_TYPES
from datetime import datetime
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.response_handler import SayanErrorResponse

# Setup logging
logger = logging.getLogger(__name__)


class VideoProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to protect video files in /static/uploads/lessons/
    Blocks access to lesson videos while allowing other static files
    """
    
    async def dispatch(self, request: Request, call_next):
        # Check if request is for lesson videos
        if request.url.path.startswith("/static/uploads/lessons/"):
            # Block access to lesson videos
            return JSONResponse(
                status_code=403,
                content={
                    "status": "error",
                    "status_code": 403,
                    "error_type": "ACCESS_DENIED",
                    "message": "الوصول المباشر للفيديوهات غير مسموح. يرجى استخدام روابط التشغيل المحمية.",
                    "data": {
                        "protected_endpoint": "/api/v1/videos/get-video-url/",
                        "authentication_required": True
                    },
                    "path": request.url.path,
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Allow all other requests to proceed
        response = await call_next(request)
        return response


class CORSLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log CORS-related requests for debugging
    """
    
    async def dispatch(self, request: Request, call_next):
        # Log CORS preflight requests
        if request.method == "OPTIONS":
            logger.info(f"🔧 CORS Preflight request from: {request.headers.get('origin', 'Unknown')}")
            logger.info(f"🔧 Request headers: {dict(request.headers)}")
        
        response = await call_next(request)
        
        # Log CORS response headers
        if "Access-Control-Allow-Origin" in response.headers:
            logger.info(f"🔧 CORS Response - Origin: {response.headers.get('Access-Control-Allow-Origin')}")
        
        return response

from app.models import (
    User, UserType, UserStatus, AccountType, Student, Gender, Academy, AcademyUser, AcademyStatus, AcademyUserRole,
    OTP, OTPPurpose, AcademyFinance, StudentFinance, Transaction, Admin, Coupon, Course, CourseStatus, CourseType,
    CourseLevel, Category, Product, DigitalProduct, Package, StudentProduct, ProductStatus, ProductType, PackageType,
    Chapter, Lesson, LessonType, VideoType, Video, Cart, Invoice, InvoiceProduct, Payment, PaymentGatewayLog,
    CouponUsage, PaymentStatus, PaymentGateway, Exam, Question, QuestionOption, QuestionType, InteractiveTool,
    LessonProgress, StudentCourse
)

from app.api.v1.auth import router as main_auth_router
print("Successfully loaded main authentication router")

try:
    from app.api.v1.me import router as me_router
    me_available = True
    print("Successfully loaded user profile router")
except Exception as e:
    me_available = False
    me_router = None
    print(f"Failed to load user profile router: {e}")

try:
    from app.api.v1.courses.main import router as courses_main_router
    courses_main_available = True
    print("Successfully loaded courses main router")
except Exception as e:
    courses_main_available = False
    courses_main_router = None
    print(f"Failed to load courses main router: {e}")

try:
    from app.api.v1.courses.chapters import router as chapters_router
    chapters_available = True
    print("Successfully loaded chapters router")
except Exception as e:
    chapters_available = False
    chapters_router = None
    print(f"Failed to load chapters router: {e}")

try:
    from app.api.v1.courses.public import router as public_courses_router
    public_courses_available = True
    print("Successfully loaded public courses router")
except Exception as e:
    public_courses_available = False
    public_courses_router = None
    print(f"Failed to load public courses router: {e}")

try:
    from app.api.v1.videos import router as videos_router
    videos_available = True
    print("Successfully loaded videos router")
except Exception as e:
    videos_available = False
    videos_router = None
    print(f"Failed to load videos router: {e}")

try:
    from app.api.v1.videos_direct import router as videos_direct_router
    videos_direct_available = True
    print("Successfully loaded direct videos router")
except Exception as e:
    videos_direct_available = False
    videos_direct_router = None
    print(f"Failed to load direct videos router: {e}")

# Force import video test router - DIRECT APPROACH
print("🔧 DIRECT: Loading video test router...")
try:
    from app.api.v1.video_test import router as video_test_router
    video_test_available = True
    print("✅ DIRECT: Video test router loaded successfully")
except Exception as e:
    video_test_available = False
    video_test_router = None
    print(f"❌ DIRECT: Failed to load video test router: {e}")
    import traceback
    traceback.print_exc()

try:
    from app.api.v1.students import router as students_router
    students_available = True
    print("Successfully loaded students router")
except Exception as e:
    students_available = False
    students_router = None
    print(f"Failed to load students router: {e}")

try:
    from app.api.v1.lessons import router as lessons_router
    lessons_available = True
    print("Successfully loaded lessons router")
except Exception as e:
    lessons_available = False
    lessons_router = None
    print(f"Failed to load lessons router: {e}")

try:
    from app.api.v1.cart import router as cart_router
    cart_available = True
    print("Successfully loaded cart router")
except Exception as e:
    cart_available = False
    cart_router = None
    print(f"Failed to load cart router: {e}")

try:
    from app.api.v1.academy_profile import router as academy_profile_router
    academy_profile_available = True
    print("Successfully loaded academy profile router")
except Exception as e:
    academy_profile_available = False
    academy_profile_router = None
    print(f"Failed to load academy profile router: {e}")

try:
    from app.api.v1.payment import router as payment_router
    payment_available = True
    print("Successfully loaded payment router")
except Exception as e:
    payment_available = False
    payment_router = None
    print(f"Failed to load payment router: {e}")

try:
    from app.api.v1.categories import router as categories_router
    categories_available = True
    print("Successfully loaded categories router")
except Exception as e:
    categories_available = False
    categories_router = None
    print(f"Failed to load categories router: {e}")

try:
    from app.api.v1.courses import router as courses_router
    courses_available = True
    print("Successfully loaded courses router")
except Exception as e:
    courses_available = False
    courses_router = None
    print(f"Failed to load courses router: {e}")

try:
    from app.api.v1.blogs import router as blogs_router
    blogs_available = True
    print("Successfully loaded blogs router")
except Exception as e:
    blogs_available = False
    blogs_router = None
    print(f"Failed to load blogs router: {e}")

try:
    from app.api.v1.digital_products import router as digital_products_router
    digital_products_available = True
    print("Successfully loaded digital products router")
except Exception as e:
    digital_products_available = False
    digital_products_router = None
    print(f"Failed to load digital products router: {e}")

try:
    from app.api.v1.wallet import router as wallet_router
    wallet_available = True
    print("Successfully loaded wallet router")
except Exception as e:
    wallet_available = False
    wallet_router = None
    print(f"Failed to load wallet router: {e}")

try:
    from app.api.v1.exams import router as exams_router
    exams_available = True
    print("Successfully loaded exams router")
except Exception as e:
    exams_available = False
    exams_router = None
    print(f"Failed to load exams router: {e}")

try:
    from app.api.v1.interactive_tools import router as interactive_tools_router
    interactive_tools_available = True
    print("Successfully loaded interactive tools router")
except Exception as e:
    interactive_tools_available = False
    interactive_tools_router = None
    print(f"Failed to load interactive tools router: {e}")

try:
    from app.api.v1.ai_endpoints import router as ai_assistant_router
    ai_assistant_available = True
    print("Successfully loaded AI Assistant router")
except Exception as e:
    ai_assistant_available = False
    ai_assistant_router = None
    print(f"Failed to load AI Assistant router: {e}")

try:
    from app.api.v1.ai_test import router as ai_test_router
    ai_test_available = True
    print("Successfully loaded AI Test router")
except Exception as e:
    ai_test_available = False
    ai_test_router = None
    print(f"Failed to load AI Test router: {e}")

static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
(static_dir / "uploads").mkdir(exist_ok=True)

app = FastAPI(
    title="SAYAN AI Powered Learning Platform API",
    openapi_url="/api/v1/openapi.json",
    description="Complete Course Management System with Authentication, Video Streaming & Progress Tracking",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middlewares
app.add_middleware(CORSLoggingMiddleware)
app.add_middleware(VideoProtectionMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Get CORS origins from settings
from app.core.config import settings

# Convert CORS origins to list of strings
cors_origins = []
if settings.BACKEND_CORS_ORIGINS:
    for origin in settings.BACKEND_CORS_ORIGINS:
        if isinstance(origin, str):
            cors_origins.append(origin)
        else:
            cors_origins.append(str(origin))

# Add default origins for development
if settings.DEBUG:
    cors_origins.extend([
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8001",
        "http://127.0.0.1:3001",
        "https://sayan.website",
        "https://sayan.pro",
        "https://fast.sayan-server.com"
    ])

# Log CORS origins for debugging
print(f"🔧 CORS Origins configured: {cors_origins}")

# Remove duplicates while preserving order
cors_origins = list(dict.fromkeys(cors_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight requests for 24 hours
)

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    # If detail is already a dict with our unified format, use it
    if isinstance(exc.detail, dict):
        error_content = exc.detail.copy()
        error_content["status"] = "error"
        error_content["status_code"] = exc.status_code
        if "error" in error_content and "error_type" not in error_content:
            error_content["error_type"] = error_content.pop("error")
        
        # Ensure unified format
        error_content.setdefault("path", str(request.url.path))
        error_content.setdefault("timestamp", datetime.utcnow().isoformat())
        
        # Clean up any extra keys not in our unified format
        allowed_keys = {"status", "status_code", "error_type", "message", "path", "timestamp", "data"}
        error_content = {k: v for k, v in error_content.items() if k in allowed_keys}
        
        return JSONResponse(status_code=exc.status_code, content=error_content)

    # Use unified error response format
    error_type = ERROR_TYPES.get(exc.status_code, "API Error")
    error_message = str(exc.detail) if exc.detail else ERROR_MESSAGES.get(exc.status_code, "حدث خطأ غير متوقع")
    
    error_response = create_error_response(
        message=error_message,
        status_code=exc.status_code,
        error_type=error_type,
        path=str(request.url.path)
    )

    return JSONResponse(status_code=exc.status_code, content=error_response)


# Add handler for 404 Not Found errors specifically
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    # Override default 404 response
    return SayanErrorResponse(
        message="الرابط المطلوب غير موجود",
        error_type="NOT_FOUND_ERROR",
        status_code=404
    )


# Add general exception handler for any other status codes
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle any other unexpected exceptions"""
    import traceback
    
    # Log the full error for debugging
    logger.error(f"Unexpected error: {str(exc)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    error_response = create_error_response(
        message="حدث خطأ داخلي في الخادم",
        status_code=500,
        error_type="Internal Server Error",
        path=str(request.url.path)
    )
    return JSONResponse(status_code=500, content=error_response)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    
    def _make_json_serializable(err_list):
        serializable = []
        for err in err_list:
            safe_err = {}
            for k, v in err.items():
                try:
                    import json
                    json.dumps(v, default=str)
                    safe_err[k] = v
                except TypeError:
                    safe_err[k] = str(v)
            serializable.append(safe_err)
        return serializable

    errors_serialized = _make_json_serializable(exc.errors()) if exc.errors() else None
    
    # Create detailed error message in Arabic
    if first_error:
        field_name = " -> ".join(str(item) for item in first_error.get("loc", []))
        error_msg = first_error.get("msg", "خطأ في التحقق من البيانات")
        message = f"خطأ في الحقل '{field_name}': {error_msg}"
    else:
        message = "خطأ في التحقق من صحة البيانات"

    error_response = create_error_response(
        message=message,
        status_code=422,
        error_type="Validation Error",
        path=str(request.url.path),
        details={"errors": errors_serialized} if errors_serialized else None
    )

    return JSONResponse(status_code=422, content=jsonable_encoder(error_response))

app.include_router(
    main_auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)
print("Main authentication router registered successfully")

if me_available:
    app.include_router(
        me_router,
        prefix="/api/v1",
        tags=["User Profile"]
    )
    print("User profile router registered successfully")

if courses_main_available:
    app.include_router(
        courses_main_router,
        prefix="/api/v1",
        tags=["Courses Management"]
    )
    print("Courses main router registered successfully")

if chapters_available:
    app.include_router(
        chapters_router,
        prefix="/api/v1",
        tags=["Chapters Management"]
    )
    print("Chapters router registered successfully")

if public_courses_available:
    app.include_router(
        public_courses_router,
        prefix="/api/v1",
        tags=["Public Courses"]
    )
    print("Public courses router registered successfully")

if videos_available:
    app.include_router(
        videos_router,
        prefix="/api/v1/videos",
        tags=["Video Streaming"]
    )
    print("Videos router registered successfully")

if videos_direct_available:
    app.include_router(
        videos_direct_router,
        prefix="/api/v1/videos",
        tags=["Direct Video Streaming"]
    )
    print("Direct videos router registered successfully")

# Force register video test router - DIRECT APPROACH
print(f"🔧 DIRECT: video_test_available = {video_test_available}")
if video_test_available and video_test_router:
    print("🔧 DIRECT: Registering video test router...")
    app.include_router(
        video_test_router,
        prefix="/api/v1/video-test",
        tags=["Video Test"]
    )
    print("✅ DIRECT: Video test router registered successfully!")
    
    # Verify registration
    print(f"🔧 DIRECT: Router routes: {[r.path for r in video_test_router.routes]}")
else:
    print("❌ DIRECT: Cannot register video test router - not available or None")

if students_available:
    app.include_router(
        students_router,
        prefix="/api/v1/students",
        tags=["Students Management"]
    )
    print("Students router registered successfully")

if lessons_available:
    app.include_router(
        lessons_router,
        prefix="/api/v1/lessons",
        tags=["Lessons Management"]
    )
    print("Lessons router registered successfully")

if cart_available:
    app.include_router(
        cart_router,
        prefix="/api/v1/cart",
        tags=["Cart Management"]
    )
    print("Cart router registered successfully")

if academy_profile_available:
    app.include_router(
        academy_profile_router,
        prefix="/api/v1/academy",
        tags=["Academy Profile"]
    )
    print("Academy profile router registered successfully")

if payment_available:
    app.include_router(
        payment_router,
        prefix="/api/v1",
        tags=["Payment Operations"]
    )
    print("Payment router registered successfully")

if categories_available:
    app.include_router(
        categories_router,
        prefix="/api/v1",
        tags=["Categories"]
    )
    print("Categories router registered successfully")

if courses_available:
    app.include_router(
        courses_router,
        prefix="/api/v1/courses",
        tags=["Courses"]
    )
    print("Courses router registered successfully")

if blogs_available:
    app.include_router(
        blogs_router,
        prefix="/api/v1/blogs",
        tags=["Blogs"]
    )
    print("Blogs router registered successfully")

if digital_products_available:
    app.include_router(
        digital_products_router,
        prefix="/api/v1/digital_products",
        tags=["Digital Products"]
    )
    print("Digital products router registered successfully")

if wallet_available:
    app.include_router(
        wallet_router,
        prefix="/api/v1/wallet",
        tags=["Wallet"]
    )
    print("Wallet router registered successfully")

if exams_available:
    app.include_router(
        exams_router,
        prefix="/api/v1/exams",
        tags=["Exams"]
    )
    print("Exams router registered successfully")

if interactive_tools_available:
    app.include_router(
        interactive_tools_router,
        prefix="/api/v1/interactive_tools",
        tags=["Interactive Tools"]
    )
    print("Interactive tools router registered successfully")

if ai_assistant_available:
    app.include_router(
        ai_assistant_router,
        prefix="/api/v1",
        tags=["AI Assistant - فهد"]
    )
    print("AI Assistant router registered successfully")

if ai_test_available:
    app.include_router(
        ai_test_router,
        prefix="/api/v1/ai/test",
        tags=["AI Test"]
    )
    print("AI Test router registered successfully")

@app.get("/", summary="Root Endpoint")
def root():
    return RedirectResponse(url="/docs")

@app.get("/health", summary="Health Check")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "available_endpoints": [
            "/docs - API Documentation",
            "/redoc - ReDoc Documentation", 
            "/api/v1/auth/* - Authentication endpoints",
            "/api/v1/courses/* - Course management endpoints",
            "/api/v1/lessons/* - Lessons management endpoints",
            "/api/v1/videos/* - Video streaming endpoints",
            "/api/v1/public/courses/* - Public course browsing",
            "/api/v1/students/* - Student management",
            "/api/v1/cart/* - Shopping cart management",
            "/api/v1/checkout/* - Payment processing",
            "/api/v1/transaction/* - Payment verification",
            "/api/v1/ai/* - AI Assistant endpoints"
        ],
        "features": {
            "authentication": "Available",
            "course_management": "Available",
            "lesson_management": "Available", 
            "video_streaming": "Available",
            "chapter_management": "Available",
            "public_browsing": "Available",
            "student_management": "Available",
            "shopping_cart": "Available",
            "payment_processing": "Available",
            "moyasar_integration": "Available",
            "course_enrollment": "Available",
            "invoice_management": "Available",
            "coupon_system": "Available",
            "otp_system": "Available",
            "email_service": "Available",
            "static_files": "Available",
            "ai_assistant": "Available",
            "ai_transcription": "Available",
            "ai_chat": "Available",
            "ai_exam_correction": "Available",
            "ai_question_generation": "Available",
            "ai_summarization": "Available"
        }
    }


@app.on_event("startup")
def on_startup():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection established successfully")
    except Exception as e:
        import traceback
        print("Failed to connect to database:", e)
        print(traceback.format_exc())
