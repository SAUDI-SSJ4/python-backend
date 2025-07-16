from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from typing import Optional, Any, List, Union, Dict

def SayanSuccessResponse(
    data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    message: str = "Success",
    status_code: int = 200,
    request: Optional[Request] = None,
):
    """
    Creates a standardized success response.
    """
    response_data = {
        "status": "success",
        "status_code": status_code,
        "error_type": None,
        "message": message,
        "data": jsonable_encoder(data),
        "path": request.url.path if request else None,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    # FastAPI automatically handles dicts as JSONResponse, but using it explicitly is clearer
    return JSONResponse(status_code=status_code, content=response_data)


def SayanErrorResponse(
    message: str = "خطأ في الطلب",
    error_type: str = "VALIDATION_ERROR",
    status_code: int = 400,
    request: Optional[Request] = None,
    data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
):
    """
    Creates a standardized error response.
    """
    response_data = {
        "status": "error",
        "status_code": status_code,
        "error_type": error_type,
        "message": message,
        "data": jsonable_encoder(data) if data else None,
        "path": request.url.path if request else None,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    return JSONResponse(status_code=status_code, content=response_data)


class ResponseHandler:
    """Helper class for standardized API responses"""
    
    @staticmethod
    def success(message: str = "Success", data: Optional[Any] = None, status_code: int = 200) -> dict:
        """Create a success response"""
        return {
            "success": True,
            "message": message,
            "data": data,
            "status_code": status_code
        }
    
    @staticmethod
    def error(message: str = "Error", data: Optional[Any] = None, status_code: int = 400) -> dict:
        """Create an error response"""
        return {
            "success": False,
            "message": message,
            "data": data,
            "status_code": status_code
        } 