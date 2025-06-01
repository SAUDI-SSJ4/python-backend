from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
import random

from app.deps import get_db, get_current_student, get_optional_current_user

router = APIRouter()


def generate_mock_digital_product(product_id: int, academy_id: int):
    """Generate mock digital product"""
    product_types = ["ebook", "template", "course_material", "video_series", "software"]
    product_names = [
        "Python Programming Guide",
        "Web Development Templates",
        "Data Science Notebook",
        "UI/UX Design Kit",
        "Mobile App Source Code"
    ]
    
    return {
        "id": product_id,
        "academy_id": academy_id,
        "name": product_names[(product_id - 1) % len(product_names)],
        "slug": f"product-{product_id}-{product_names[(product_id - 1) % len(product_names)].lower().replace(' ', '-')}",
        "description": f"High-quality digital product for {product_names[(product_id - 1) % len(product_names)]}",
        "price": round(random.uniform(19.99, 199.99), 2),
        "discount_price": round(random.uniform(9.99, 99.99), 2) if product_id % 3 == 0 else None,
        "file_type": ["pdf", "zip", "mp4", "docx"][product_id % 4],
        "file_size": random.randint(1000000, 50000000),  # In bytes
        "thumbnail": f"https://example.com/digital-product-{product_id}.jpg",
        "preview_url": f"https://example.com/preview-{product_id}.pdf",
        "download_limit": random.choice([None, 3, 5, 10]),
        "is_active": True,
        "sales_count": random.randint(10, 500),
        "rating": round(random.uniform(3.5, 5.0), 1),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


# Digital products endpoints
@router.get("/")
def get_digital_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    academy_id: Optional[int] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|price|rating|sales_count)$"),
    order: str = Query("desc", pattern="^(asc|desc)$")
) -> Any:
    """Get list of digital products"""
    products = [generate_mock_digital_product(i, (i % 3) + 1) for i in range(1, 31)]
    
    # Apply filters
    if academy_id:
        products = [p for p in products if p["academy_id"] == academy_id]
    if min_price:
        products = [p for p in products if p["price"] >= min_price]
    if max_price:
        products = [p for p in products if p["price"] <= max_price]
    
    # Sort products
    reverse = order == "desc"
    products.sort(key=lambda x: x[sort_by], reverse=reverse)
    
    return {
        "data": products[skip:skip + limit],
        "total": len(products),
        "skip": skip,
        "limit": limit
    }


@router.get("/{product_id}")
def get_digital_product(
    product_id: int,
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Get digital product details"""
    product = generate_mock_digital_product(product_id, 1)
    
    # Add additional details
    product["features"] = [
        "Instant download",
        "Lifetime access",
        "Free updates",
        "Support included"
    ]
    
    # Check if user has purchased this product
    product["is_purchased"] = False
    product["can_download"] = False
    
    if current_user:
        # Mock check - randomly assign purchase status for demo
        product["is_purchased"] = product_id % 5 == 0
        product["can_download"] = product["is_purchased"]
        
        if product["is_purchased"]:
            product["purchase_date"] = datetime.now().isoformat()
            product["downloads_remaining"] = product["download_limit"] - 1 if product["download_limit"] else None
    
    # Add reviews
    product["reviews"] = [
        {
            "id": i,
            "student_name": f"Student {i}",
            "rating": random.randint(4, 5),
            "comment": f"Great product! Review #{i}",
            "created_at": datetime.now().isoformat()
        }
        for i in range(1, 6)
    ]
    
    # Add related products
    product["related_products"] = [
        generate_mock_digital_product(i, product["academy_id"])
        for i in range(product_id + 1, product_id + 4)
    ]
    
    return product


@router.post("/{product_id}/purchase")
def purchase_digital_product(
    product_id: int,
    purchase_data: dict,
    current_user = Depends(get_current_student)
) -> Any:
    """Purchase digital product"""
    product = generate_mock_digital_product(product_id, 1)
    
    # Check if already purchased
    if product_id % 5 == 0:  # Mock check
        raise HTTPException(
            status_code=400,
            detail="You have already purchased this product"
        )
    
    # Create purchase record
    purchase = {
        "id": f"PUR_{current_user.id}_{product_id}",
        "student_id": current_user.id,
        "digital_product_id": product_id,
        "payment_id": f"PAY_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "amount": product.get("discount_price", product["price"]),
        "download_count": 0,
        "download_limit": product["download_limit"],
        "purchased_at": datetime.now().isoformat(),
        "status": "completed"
    }
    
    return {
        "message": "Product purchased successfully",
        "purchase": purchase,
        "download_url": f"/api/v1/digital-products/{product_id}/download"
    }


@router.get("/{product_id}/download")
def download_digital_product(
    product_id: int,
    current_user = Depends(get_current_student)
) -> Any:
    """Download digital product"""
    # Check if user has purchased the product
    if product_id % 5 != 0:  # Mock check
        raise HTTPException(
            status_code=403,
            detail="You have not purchased this product"
        )
    
    # Check download limit
    download_limit = 5
    downloads_used = 2
    
    if download_limit and downloads_used >= download_limit:
        raise HTTPException(
            status_code=403,
            detail="Download limit exceeded"
        )
    
    # Generate download URL (in production, this would be a secure S3 URL)
    download_url = f"https://secure-download.example.com/products/{product_id}/file.pdf?token=secure_token"
    
    return {
        "download_url": download_url,
        "expires_at": (datetime.now().timestamp() + 3600),  # 1 hour expiry
        "downloads_used": downloads_used + 1,
        "downloads_remaining": download_limit - downloads_used - 1 if download_limit else None
    }


@router.post("/{product_id}/rate")
def rate_digital_product(
    product_id: int,
    rating_data: dict,
    current_user = Depends(get_current_student)
) -> Any:
    """Rate a purchased digital product"""
    # Check if user has purchased the product
    if product_id % 5 != 0:  # Mock check
        raise HTTPException(
            status_code=403,
            detail="You can only rate products you have purchased"
        )
    
    rating = {
        "id": f"RATE_{current_user.id}_{product_id}",
        "student_id": current_user.id,
        "digital_product_id": product_id,
        "rating": rating_data.get("rating", 5),
        "comment": rating_data.get("comment", ""),
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Rating submitted successfully",
        "rating": rating
    }


# My purchased products
@router.get("/my-products")
def get_my_digital_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user = Depends(get_current_student)
) -> Any:
    """Get student's purchased digital products"""
    # Generate mock purchased products
    purchased_products = []
    
    for i in range(1, 11):
        if i % 3 == 0:  # Mock some purchases
            product = generate_mock_digital_product(i, (i % 3) + 1)
            product["purchase_date"] = datetime.now().isoformat()
            product["download_count"] = random.randint(0, 5)
            product["download_limit"] = product.get("download_limit")
            product["can_download"] = True
            
            purchased_products.append(product)
    
    return {
        "data": purchased_products[skip:skip + limit],
        "total": len(purchased_products),
        "skip": skip,
        "limit": limit
    }


# Academy digital products management
@router.get("/academy/{academy_id}/products")
def get_academy_digital_products(
    academy_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
) -> Any:
    """Get digital products by academy"""
    products = [
        generate_mock_digital_product(i, academy_id)
        for i in range(1, 16)
        if (i % 3) + 1 == academy_id
    ]
    
    return {
        "data": products[skip:skip + limit],
        "total": len(products),
        "academy_id": academy_id,
        "skip": skip,
        "limit": limit
    } 