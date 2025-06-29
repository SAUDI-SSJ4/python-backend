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

# Import authentication router with error handling
try:
    from app.api.v1.auth import router as main_auth_router
    main_auth_available = True
    print("Successfully loaded main authentication router")
except Exception as e:
    main_auth_available = False
    main_auth_router = None
    print(f"Failed to load main authentication router: {e}")

# Check if we can import the auth module from the auth directory as fallback
try:
    from app.api.v1.auth.auth_basic import router as modular_auth_router
    auth_available = True
    print("Successfully loaded modular authentication router")
except Exception as e:
    auth_available = False
    modular_auth_router = None
    print(f"Failed to load modular authentication router: {e}")

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
    from app.api.v1.academy import router as academy_router
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
    allow_origins=["*"],
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
        allowed_keys = {"status", "status_code", "error_type", "message", "path", "timestamp", "data"}

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

# Include authentication routers
if main_auth_available:
    app.include_router(
        main_auth_router,
        prefix="/api/v1/auth"
    )
    print("Main authentication router registered successfully")
    
    if auth_available:
        pass

elif auth_available:
    pass

# Include courses routers
if courses_main_available:
    app.include_router(
        courses_main_router,
        prefix="/api/v1/courses",
        tags=["Courses Management"]
    )
    print("Courses main router registered successfully")

if chapters_available:
    app.include_router(
        chapters_router,
        prefix="/api/v1/courses",
        tags=["Chapters Management"]
    )
    print("Chapters router registered successfully")

if public_courses_available:
    app.include_router(
        public_courses_router,
        prefix="/api/v1/public/courses",
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

@app.get("/", summary="Root Endpoint")
def root():
    return RedirectResponse(url="/docs")

@app.get("/health", summary="Health Check")
def health_check():
    total_auth_available = auth_available or main_auth_available
    
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
            "/api/v1/academy/* - Academy management"
        ],
        "loaded_routers": {
            "main_auth_router": main_auth_available,
            "modular_auth_router": auth_available,
            "courses_main_router": courses_main_available,
            "chapters_router": chapters_available,
            "public_courses_router": public_courses_available,
            "lessons_router": lessons_available,
            "videos_router": videos_available,
            "students_router": students_available,
            "academy_router": academy_available
        },
        "features": {
            "authentication": "Available" if total_auth_available else "Unavailable",
            "course_management": "Available" if courses_main_available else "Unavailable",
            "lesson_management": "Available" if lessons_available else "Unavailable",
            "video_streaming": "Available" if videos_available else "Unavailable",
            "chapter_management": "Available" if chapters_available else "Unavailable",
            "public_browsing": "Available" if public_courses_available else "Unavailable",
            "student_management": "Available" if students_available else "Unavailable",
            "academy_management": "Available" if academy_available else "Unavailable",
            "otp_system": "Available",
            "email_service": "Available",
            "static_files": "Available"
        }
    }
