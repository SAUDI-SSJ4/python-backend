"""
Cart API endpoints
"""

from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from app.deps.database import get_db
from app.deps.auth import get_optional_current_user, get_current_student
from app.models.student import Student
from app.models.user import User
from app.services.cart_service import CartService
from app.core.response_handler import SayanSuccessResponse


router = APIRouter()


def _get_user_identifier(current_user: Optional[User]) -> Optional[int]:
    """Get student ID from current user"""
    if not current_user:
        return None
    
    if current_user.user_type == "student" and current_user.student_profile:
        return current_user.student_profile.id
    
    return None


def _get_or_create_cookie_id(the_cookie: Optional[str]) -> str:
    """Get or create cookie ID"""
    if the_cookie:
        return the_cookie
    return str(uuid.uuid4())


class AddToCartRequest(BaseModel):
    item_type: str = Field(..., description="Type of item: course or digital_product")
    item_id: str = Field(..., description="ID of the item to add")


@router.get("/")
def get_cart(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    """Get cart contents with complete summary"""
    try:
        cookie_id = _get_or_create_cookie_id(the_cookie)
        student_id = _get_user_identifier(current_user)
        
        # Get cart summary instead of just items
        result = CartService.get_cart_summary(
            db=db,
            student_id=student_id,
            cookie_id=cookie_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": result.get("message", "خطأ في جلب السلة")}
            )
        
        # Set cookie
        response.set_cookie(key="TheCookie", value=cookie_id, httponly=True)
        
        # Add cookie info to response
        cart_data = result.get("data", {})
        cart_data["cookie_info"] = {
            "cookie_id": cookie_id,
            "user_id": student_id,
            "is_authenticated": current_user is not None
        }
        
        return SayanSuccessResponse(
            data=cart_data,
            message=result.get("message", "تم جلب السلة بنجاح"),
            request=request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في جلب السلة: {str(e)}"}
        )


@router.post("/add", status_code=status.HTTP_201_CREATED)
def add_to_cart(
    cart_data: AddToCartRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    """Add item to cart"""
    try:
        cookie_id = _get_or_create_cookie_id(the_cookie)
        student_id = _get_user_identifier(current_user)
        
        result = CartService.add_to_cart(
            db=db,
            item_type=cart_data.item_type,
            item_id=cart_data.item_id,
            student_id=student_id,
            cookie_id=cookie_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": result.get("message", "خطأ في إضافة المنتج")}
            )
        
        # Set cookie
        response.set_cookie(key="TheCookie", value=cookie_id, httponly=True)
        
        # Add cookie info to response
        cart_data = result.get("data", {})
        cart_data["cookie_info"] = {
            "cookie_id": cookie_id,
            "user_id": student_id,
            "is_authenticated": current_user is not None
        }
        
        return SayanSuccessResponse(
            data=cart_data,
            message=result.get("message", "تم إضافة المنتج بنجاح"),
            request=request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في إضافة المنتج: {str(e)}"}
        )


@router.delete("/delete/{cart_id}")
def remove_from_cart(
    cart_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    """Remove item from cart"""
    try:
        cookie_id = _get_or_create_cookie_id(the_cookie)
        student_id = _get_user_identifier(current_user)
        
        result = CartService.remove_from_cart(
            db=db,
            cart_id=cart_id,
            student_id=student_id,
            cookie_id=cookie_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": result.get("message", "خطأ في حذف المنتج")}
            )
        
        return SayanSuccessResponse(
            data=result.get("data", {}),
            message=result.get("message", "تم حذف المنتج بنجاح"),
            request=request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في حذف المنتج: {str(e)}"}
        )


@router.delete("/clear")
def clear_cart(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    """Clear all items from cart"""
    try:
        cookie_id = _get_or_create_cookie_id(the_cookie)
        student_id = _get_user_identifier(current_user)
        
        result = CartService.clear_cart(
            db=db,
            student_id=student_id,
            cookie_id=cookie_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": result.get("message", "خطأ في مسح السلة")}
            )
        
        return SayanSuccessResponse(
            data=result.get("data", {}),
            message=result.get("message", "تم مسح السلة بنجاح"),
            request=request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في مسح السلة: {str(e)}"}
        ) 