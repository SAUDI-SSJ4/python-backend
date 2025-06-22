"""
FastAPI Main Application
========================
Main entry point for the Unified Authentication System API.
Includes CORS middleware, static file serving, and authentication routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path

# Import authentication router with error handling
try:
    from app.api.v1.auth import router as auth_router
    auth_available = True
    print("✅ Successfully loaded authentication router")
except ImportError as e:
    auth_available = False
    print(f"❌ Failed to load authentication router: {e}")

# Create static directories if they don't exist
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
(static_dir / "uploads").mkdir(exist_ok=True)

# Create FastAPI application instance
app = FastAPI(
    title="Unified API System - FastAPI Backend",
    openapi_url="/api/v1/openapi.json",
    description="Complete API System with Authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount static files for serving uploaded content
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication router if available
if auth_available:
    app.include_router(
        auth_router,
        prefix="/api/v1/auth",
        tags=["🔐 Authentication"]
    )
    print("✅ Authentication router registered successfully")
else:
    print("❌ Authentication router not registered - router unavailable")


@app.get("/", summary="Root Endpoint", description="Redirects to API documentation")
def root():
    """
    Root endpoint that redirects to API documentation.
    
    Returns:
        RedirectResponse: Redirects to /docs
    """
    return RedirectResponse(url="/docs")


@app.get("/health", summary="Health Check", description="Check API health status")
def health_check():
    """
    Health check endpoint for monitoring API status.
    
    Returns:
        dict: API health status and information
    """
    return {
        "status": "healthy",
        "message": "Unified Authentication System API is running",
        "version": "1.0.0",
        "available_endpoints": [
            "/docs - API Documentation",
            "/redoc - ReDoc Documentation", 
            "/api/v1/auth/* - Authentication endpoints"
        ],
        "auth_router_loaded": auth_available,
        "features": {
            "authentication": "✅ Available" if auth_available else "❌ Unavailable",
            "otp_system": "✅ Available",
            "email_service": "✅ Available",
            "static_files": "✅ Available"
        }
    }
