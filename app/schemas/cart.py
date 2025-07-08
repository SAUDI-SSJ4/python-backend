from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ItemType(str, Enum):
    course = "course"
    digital_product = "digital_product"


class CartItemAdd(BaseModel):
    item_type: ItemType = Field(..., description="نوع العنصر")
    item_id: str = Field(..., description="معرف العنصر")
    quantity: int = Field(default=1, ge=1, description="الكمية")


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1, description="الكمية الجديدة")


class CouponApply(BaseModel):
    code: str = Field(..., description="رمز الكوبون")


class CartItemResponse(BaseModel):
    id: int
    item_type: ItemType
    item_id: str
    quantity: int
    price: Optional[float] = None
    price_at_time: Optional[float] = None
    total_price: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Item details
    item_details: Optional[dict] = None
    
    class Config:
        from_attributes = True


class CartSummary(BaseModel):
    items: List[CartItemResponse]
    total_items: int
    subtotal: float
    discount: float = 0.0
    total: float
    coupon_code: Optional[str] = None
    
    class Config:
        from_attributes = True 