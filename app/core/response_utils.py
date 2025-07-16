"""
Core Response Utilities
=======================
Utility functions for creating unified API responses across all endpoints
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel


def get_current_timestamp() -> str:
    """Get current timestamp in ISO 8601 format"""
    return datetime.utcnow().isoformat()


def create_success_response(
    data: Any = None,
    message: str = "تم الطلب بنجاح",
    status_code: int = 200,
    path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a unified success response
    
    Args:
        data: Response payload (can be Pydantic model, dict, list, etc.)
        message: Success message in Arabic
        status_code: HTTP status code
        path: Request path
        
    Returns:
        Unified response dictionary
    """
    # Use FastAPI's jsonable_encoder to handle all serialization properly
    if data is not None:
        data = jsonable_encoder(data)
    
    return {
        "status": "success",
        "status_code": status_code,
        "error_type": None,
        "message": message,
        "data": data,
        "path": path,
        "timestamp": get_current_timestamp()
    }


def create_error_response(
    message: str = "حدث خطأ غير متوقع",
    status_code: int = 400,
    error_type: str = "خطأ في الطلب",
    path: Optional[str] = None,
    details: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Create a unified error response
    
    Args:
        message: Error message in Arabic
        status_code: HTTP status code
        error_type: Type of error
        path: Request path
        details: Additional error details
        
    Returns:
        Unified error response dictionary
    """
    return {
        "status": "error",
        "status_code": status_code,
        "error_type": error_type,
        "message": message,
        "data": details,
        "path": path,
        "timestamp": get_current_timestamp()
    }


def create_list_response(
    items: List[Any],
    total: Optional[int] = None,
    message: str = "تم استرجاع البيانات بنجاح",
    status_code: int = 200,
    path: Optional[str] = None,
    meta: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Create a unified response for list data
    
    Args:
        items: List of items (can be Pydantic models, dicts, etc.)
        total: Total count of items
        message: Success message
        status_code: HTTP status code
        path: Request path
        meta: Additional metadata (pagination, filters, etc.)
        
    Returns:
        Unified list response dictionary
    """
    # Use FastAPI's jsonable_encoder for proper serialization
    processed_items = jsonable_encoder(items)
    
    data = {
        "items": processed_items,
        "total": total if total is not None else len(processed_items)
    }
    
    if meta:
        data.update(jsonable_encoder(meta))
    
    return {
        "status": "success",
        "status_code": status_code,
        "error_type": None,
        "message": message,
        "data": data,
        "path": path,
        "timestamp": get_current_timestamp()
    }


def success_json_response(
    data: Any = None,
    message: str = "تم الطلب بنجاح",
    status_code: int = 200,
    request: Optional[Request] = None
) -> JSONResponse:
    """
    Create a JSONResponse with unified success format
    
    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code
        request: FastAPI Request object to extract path
        
    Returns:
        JSONResponse with unified format
    """
    path = str(request.url.path) if request else None
    response_data = create_success_response(data, message, status_code, path)
    return JSONResponse(status_code=status_code, content=response_data)


def error_json_response(
    message: str = "حدث خطأ غير متوقع",
    status_code: int = 400,
    error_type: str = "خطأ في الطلب",
    request: Optional[Request] = None,
    details: Optional[Dict] = None
) -> JSONResponse:
    """
    Create a JSONResponse with unified error format
    
    Args:
        message: Error message
        status_code: HTTP status code
        error_type: Type of error
        request: FastAPI Request object to extract path
        details: Additional error details
        
    Returns:
        JSONResponse with unified format
    """
    path = str(request.url.path) if request else None
    response_data = create_error_response(message, status_code, error_type, path, details)
    return JSONResponse(status_code=status_code, content=response_data)


# Arabic error messages mapping
ERROR_MESSAGES = {
    400: "طلب غير صحيح",
    401: "غير مصرح بالوصول", 
    403: "محظور الوصول",
    404: "المورد غير موجود",
    405: "الطريقة غير مسموحة",
    422: "خطأ في التحقق من البيانات",
    429: "تم تجاوز عدد الطلبات المسموح",
    500: "خطأ داخلي في الخادم",
    502: "خطأ في البوابة",
    503: "الخدمة غير متاحة"
}

ERROR_TYPES = {
    400: "Bad Request",
    401: "Unauthorized", 
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    422: "Validation Error",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable"
} 