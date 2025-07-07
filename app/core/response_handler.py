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