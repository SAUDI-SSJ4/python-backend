"""
FastAPI Main Application
========================
Main entry point for the Unified Authentication System API.
Includes CORS middleware, static file serving, and authentication routes.
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

# Import all models to ensure they are registered with SQLAlchemy's Base.metadata
from app.models import (
    User, UserType, UserStatus, AccountType, Student, Gender, Academy, AcademyUser, AcademyStatus, AcademyUserRole,
    OTP, OTPPurpose, AcademyFinance, StudentFinance, Transaction, Admin, Coupon, Course, CourseStatus, CourseType,
    CourseLevel, Category, Product, DigitalProduct, Package, StudentProduct, ProductStatus, ProductType, PackageType,
    Chapter, Lesson, LessonType, VideoType, Video, Cart, Invoice, InvoiceProduct, Payment, PaymentGatewayLog,
    CouponUsage, PaymentStatus, PaymentGateway, Exam, Question, QuestionOption, QuestionType, InteractiveTool,
    LessonProgress, StudentCourse, AIAnswer
)

# Import authentication router
from app.api.v1.auth import router as main_auth_router
print("Successfully loaded main authentication router")

# Import me router for user profile - استيراد راوتر /me للملف الشخصي
try:
    from app.api.v1.me import router as me_router
    me_available = True
    print("Successfully loaded user profile router")
except Exception as e:
    me_available = False
    me_router = None
    print(f"Failed to load user profile router: {e}")

# Import courses routers
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

# Import videos router
try:
    from app.api.v1.videos import router as videos_router
    videos_available = True
    print("Successfully loaded videos router")
except Exception as e:
    videos_available = False
    videos_router = None
    print(f"Failed to load videos router: {e}")

# Import other existing routers
try:
    from app.api.v1.students import router as students_router
    students_available = True
    print("Successfully loaded students router")
except Exception as e:
    students_available = False
    students_router = None
    print(f"Failed to load students router: {e}")

try:
    from app.api.v1.academy_simplified import router as academy_router
    academy_available = True
    print("Successfully loaded academy router")
except Exception as e:
    academy_available = False
    academy_router = None
    print(f"Failed to load academy router: {e}")

try:
    from app.api.v1.lessons import router as lessons_router
    lessons_available = True
    print("Successfully loaded lessons router")
except Exception as e:
    lessons_available = False
    lessons_router = None
    print(f"Failed to load lessons router: {e}")

# Import cart and payment routers
try:
    from app.api.v1.cart import router as cart_router
    cart_available = True
    print("Successfully loaded cart router")
except Exception as e:
    cart_available = False
    cart_router = None
    print(f"Failed to load cart router: {e}")

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

# Create static directories if they don't exist
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
(static_dir / "uploads").mkdir(exist_ok=True)

# Create FastAPI application instance
app = FastAPI(
    title="نظام إدارة الكورسات الشامل - SAYAN API",
    openapi_url="/api/v1/openapi.json",
    description="Complete Course Management System with Authentication, Video Streaming & Progress Tracking",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount static files for serving uploaded content
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sayan.website", "https://sayan.pro", "http://localhost:3000", "https://fast.sayan-server.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        error_content = exc.detail.copy()
        error_content["status"] = "error"
        error_content["status_code"] = exc.status_code
        if "error" in error_content and "error_type" not in error_content:
            error_content["error_type"] = error_content.pop("error")
        allowed_keys = {"status", "status_code", "error_type", "message", "path", "timestamp", "data", "details", "exception_type", "traceback", "debug_info"}

        error_content.setdefault("path", str(request.url.path))

        from datetime import datetime
        error_content.setdefault("timestamp", datetime.utcnow().isoformat())

        keys_to_remove = [key for key in error_content.keys() if key not in allowed_keys]
        for key in keys_to_remove:
            del error_content[key]

        return JSONResponse(status_code=exc.status_code, content=error_content)

    from datetime import datetime
    error_type_mapping = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        422: "Validation Error",
        500: "Internal Server Error"
    }
    error_type = error_type_mapping.get(exc.status_code, "API Error")
    error_message = str(exc.detail) if exc.detail else "حدث خطأ غير متوقع"
    error_response = {
        "status": "error",
        "status_code": exc.status_code,
        "error_type": error_type,
        "message": error_message,
        "data": None,
        "path": str(request.url.path),
        "timestamp": datetime.utcnow().isoformat()
    }

    return JSONResponse(status_code=exc.status_code, content=error_response)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """          (HTTP 422)"""

    from datetime import datetime

    first_error = exc.errors()[0] if exc.errors() else {}
    loc = " -> ".join(str(item) for item in first_error.get("loc", []))

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

    error_response = {
        "status": "error",
        "status_code": 422,
        "error_type": "Validation Error",
        "data": {"errors": errors_serialized} if errors_serialized else None,
        "path": str(request.url.path),
        "timestamp": datetime.utcnow().isoformat()
    }

    return JSONResponse(status_code=422, content=jsonable_encoder(error_response))

# Include authentication router
app.include_router(
    main_auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)
print("Main authentication router registered successfully")

# Include user profile router - تضمين راوتر الملف الشخصي
if me_available:
    app.include_router(
        me_router,
        prefix="/api/v1",
        tags=["User Profile"]
    )
    print("User profile router registered successfully")

# Include courses routers
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

# Include videos router
if videos_available:
    app.include_router(
        videos_router,
        prefix="/api/v1/videos",
        tags=["Video Streaming"]
    )
    print("Videos router registered successfully")

# Include other existing routers
if students_available:
    app.include_router(
        students_router,
        prefix="/api/v1/students",
        tags=["Students Management"]
    )
    print("Students router registered successfully")

if academy_available:
    app.include_router(
        academy_router,
        prefix="/api/v1/academy",
        tags=["Academy Management"]
    )
    print("Academy router registered successfully")

# Include lessons router
if lessons_available:
    app.include_router(
        lessons_router,
        prefix="/api/v1/lessons",
        tags=["Lessons Management"]
    )
    print("Lessons router registered successfully")

# Include cart router
if cart_available:
    app.include_router(
        cart_router,
        prefix="/api/v1/cart",
        tags=["Cart Management"]
    )
    print("Cart router registered successfully")

# Include payment router
if payment_available:
    app.include_router(
        payment_router,
        prefix="/api/v1",
        tags=["Payment Operations"]
    )
    print("Payment router registered successfully")

# Include categories router
if categories_available:
    app.include_router(
        categories_router,
        prefix="/api/v1",
        tags=["Categories"]
    )
    print("Categories router registered successfully")

# Include debug router
try:
    from app.api.v1.debug import router as debug_router
    app.include_router(
        debug_router,
        prefix="/api/v1",
        tags=["Debug"]
    )
    print("Debug router registered successfully")
except Exception as e:
    print(f"Failed to load debug router: {e}")

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
            "/api/v1/academy/* - Academy management",
            "/api/v1/cart/* - Shopping cart management",
            "/api/v1/checkout/* - Payment processing",
            "/api/v1/transaction/* - Payment verification"
        ],
        "features": {
            "authentication": "Available",
            "course_management": "Available",
            "lesson_management": "Available", 
            "video_streaming": "Available",
            "chapter_management": "Available",
            "public_browsing": "Available",
            "student_management": "Available",
            "academy_management": "Available",
            "shopping_cart": "Available",
            "payment_processing": "Available",
            "moyasar_integration": "Available",
            "course_enrollment": "Available",
            "invoice_management": "Available",
            "coupon_system": "Available",
            "otp_system": "Available",
            "email_service": "Available",
            "static_files": "Available"
        }
    }

# التحقق من اتصال قاعدة البيانات فقط (الجداول موجودة مسبقاً)
@app.on_event("startup")
def on_startup():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ تم الاتصال بقاعدة البيانات fast_sayan بنجاح")
    except Exception as e:
        import traceback
        print("❌ تعذّر الاتصال بقاعدة البيانات:", e)
        print(traceback.format_exc())
