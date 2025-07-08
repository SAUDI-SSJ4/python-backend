"""
Cart API endpoints
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import uuid

from app.deps.database import get_db
from app.deps.auth import get_optional_current_user, get_current_student
from app.models.student import Student
from app.services.cart_service import CartService
from app.core.response_handler import SayanSuccessResponse


router = APIRouter()


class AddToCartRequest(BaseModel):
    item_type: str = Field(..., description="Type of item: course or digital_product")
    item_id: str = Field(..., description="ID of the item to add")
    quantity: int = Field(1, ge=1, le=10, description="Quantity of items to add")


class UpdateCartRequest(BaseModel):
    quantity: int = Field(1, ge=1, le=10, description="New quantity")


class ApplyCouponRequest(BaseModel):
    code: str = Field(..., description="Coupon code to apply")


@router.get("/")
def get_cart(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Optional[Student] = Depends(get_optional_current_user),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    try:
        cart_service = CartService(db)
        
        cookie_id = cart_service.extract_cookie_id(the_cookie)
        if not cookie_id:
            cookie_id = cart_service.get_or_create_cookie_id()
        
        student_id = current_user.id if current_user else None
        
        cart_summary = cart_service.get_cart_summary(
            student_id=student_id,
            cookie_id=cookie_id
        )
        
        response.headers["Set-Cookie"] = f"cart_id={cookie_id}; Path=/; HttpOnly"
        
        return SayanSuccessResponse(
            data={**cart_summary, "cookie_id": cookie_id},
            message="سلتك" if cart_summary["items"] else "سلة فارغة",
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في جلب السلة: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.post("/add", status_code=status.HTTP_201_CREATED)
def add_to_cart(
    cart_data: AddToCartRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Optional[Student] = Depends(get_optional_current_user),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    try:
        cart_service = CartService(db)
        
        cookie_id = cart_service.extract_cookie_id(the_cookie)
        student_id = current_user.id if current_user else None
        
        result = cart_service.add_to_cart(
            item_type=cart_data.item_type,
            item_id=cart_data.item_id,
            student_id=student_id,
            cookie_id=cookie_id,
            quantity=cart_data.quantity
        )
        
        response.headers["Set-Cookie"] = f"cart_id={result['cookie_id']}; Path=/; HttpOnly"
        
        cart_summary = cart_service.get_cart_summary(
            student_id=student_id,
            cookie_id=result['cookie_id']
        )
        
        return SayanSuccessResponse(
            data={
                "action": result["action"],
                "cart": cart_summary,
                "cookie_id": result['cookie_id']
            },
            message=result["message"],
            request=request
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "error_type": "Bad Request"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في إضافة العنصر: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.put("/update/{cart_item_id}")
def update_cart_item(
    cart_item_id: int,
    update_data: UpdateCartRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[Student] = Depends(get_optional_current_user),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    try:
        cart_service = CartService(db)
        
        cookie_id = cart_service.extract_cookie_id(the_cookie)
        student_id = current_user.id if current_user else None
        
        result = cart_service.update_cart_item(
            cart_item_id=cart_item_id,
            quantity=update_data.quantity,
            student_id=student_id,
            cookie_id=cookie_id
        )
        
        cart_summary = cart_service.get_cart_summary(
            student_id=student_id,
            cookie_id=cookie_id
        )
        
        return SayanSuccessResponse(
            data={"cart": cart_summary},
            message=result["message"],
            request=request
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "error_type": "Bad Request"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في تحديث العنصر: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.delete("/delete/{cart_item_id}")
def remove_from_cart(
    cart_item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[Student] = Depends(get_optional_current_user),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    try:
        cart_service = CartService(db)
        
        cookie_id = cart_service.extract_cookie_id(the_cookie)
        student_id = current_user.id if current_user else None
        
        result = cart_service.remove_from_cart(
            cart_item_id=cart_item_id,
            student_id=student_id,
            cookie_id=cookie_id
        )
        
        cart_summary = cart_service.get_cart_summary(
            student_id=student_id,
            cookie_id=cookie_id
        )
        
        return SayanSuccessResponse(
            data={"cart": cart_summary},
            message=result["message"],
            request=request
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "error_type": "Bad Request"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في حذف العنصر: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.delete("/clear")
def clear_cart(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[Student] = Depends(get_optional_current_user),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    try:
        cart_service = CartService(db)
        
        cookie_id = cart_service.extract_cookie_id(the_cookie)
        student_id = current_user.id if current_user else None
        
        result = cart_service.clear_cart(
            student_id=student_id,
            cookie_id=cookie_id
        )
        
        return SayanSuccessResponse(
            data={"items_cleared": result["items_cleared"]},
            message=result["message"],
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في مسح السلة: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.post("/apply-coupon")
def apply_coupon(
    coupon_data: ApplyCouponRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[Student] = Depends(get_optional_current_user),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    try:
        cart_service = CartService(db)
        
        cookie_id = cart_service.extract_cookie_id(the_cookie)
        student_id = current_user.id if current_user else None
        
        cart_summary = cart_service.get_cart_summary(
            student_id=student_id,
            cookie_id=cookie_id,
            coupon_code=coupon_data.code
        )
        
        if cart_summary["coupon_applied"]:
            return SayanSuccessResponse(
                data=cart_summary,
                message="تم تطبيق الكوبون بنجاح",
                request=request
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "كوبون غير صالح أو منتهي الصلاحية", "error_type": "Bad Request"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في تطبيق الكوبون: {str(e)}", "error_type": "Internal Server Error"}
        )


@router.post("/merge-guest-cart")
def merge_guest_cart(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_student),
    the_cookie: Optional[str] = Header(None, alias="TheCookie")
) -> Any:
    try:
        cart_service = CartService(db)
        
        cookie_id = cart_service.extract_cookie_id(the_cookie)
        
        if not cookie_id:
            return SayanSuccessResponse(
                data={"items_merged": 0},
                message="لا توجد سلة ضيف للدمج",
                request=request
            )
        
        result = cart_service.merge_guest_cart_to_student(
            student_id=current_user.id,
            cookie_id=cookie_id
        )
        
        return SayanSuccessResponse(
            data={"items_merged": result["items_merged"]},
            message=result["message"],
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"خطأ في دمج السلة: {str(e)}", "error_type": "Internal Server Error"}
        ) 