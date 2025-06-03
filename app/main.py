from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.api.v1 import (
    auth, 
    courses, 
    academy, 
    blogs, 
    cart, 
    payment, 
    digital_products,
    wallet,
    students
)

# Create static directory if it doesn't exist
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
(static_dir / "uploads").mkdir(exist_ok=True)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="SAYAN Educational Platform API - Complete Learning Management System",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers with proper hierarchy
# Authentication
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["🔐 Authentication"])

# Public Courses (for students and visitors)
app.include_router(courses.router, prefix=f"{settings.API_V1_STR}/courses", tags=["📚 Public Courses"])

# Academy Management (complete course management)
app.include_router(academy.router, prefix=f"{settings.API_V1_STR}/academies", tags=["🏫 Academy Management"])

# Content Management
app.include_router(blogs.router, prefix=f"{settings.API_V1_STR}/blogs", tags=["📝 Blog System"])
app.include_router(digital_products.router, prefix=f"{settings.API_V1_STR}/digital-products", tags=["💿 Digital Products"])

# E-commerce
app.include_router(cart.router, prefix=f"{settings.API_V1_STR}/cart", tags=["🛒 Shopping Cart"])
app.include_router(payment.router, prefix=f"{settings.API_V1_STR}/payment", tags=["💳 Payment System"])

# Financial Management
app.include_router(wallet.router, prefix=f"{settings.API_V1_STR}/academy/wallet", tags=["💰 Academy Wallet"])

# Student Management
app.include_router(students.router, prefix=f"{settings.API_V1_STR}/students", tags=["👨‍🎓 Student Management"])


@app.get("/")
def root():
    return RedirectResponse(url="/docs")
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "description": "Complete Learning Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "features": [
            "🔐 Multi-role Authentication (Students, Academy, Admin)",
            "🏫 Complete Academy Management",
            "📚 Course Management with Chapters & Lessons",
            "🎥 Video Content Management",
            "📝 Exam & Quiz System",
            "🛠️ Interactive Tools",
            "📝 Blog & Content Management",
            "🛒 E-commerce & Shopping Cart",
            "💳 Payment Processing",
            "💰 Financial Management",
            "💿 Digital Products Marketplace"
        ],
        "api_structure": {
            "auth": "Authentication for all user types",
            "courses": "Public course browsing and enrollment",
            "academies": "Complete academy and course management",
            "blogs": "Blog and content management",
            "cart": "Shopping cart functionality",
            "payment": "Payment processing",
            "digital-products": "Digital products marketplace",
            "academy/wallet": "Academy financial management"
        }
    }
