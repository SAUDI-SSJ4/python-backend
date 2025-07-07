from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.deps.database import get_db
from app.deps.auth import get_current_user
from app.models.user import User
from app.models.academy import Academy, AcademyUser
from app.models.course import Category
from app.core import security

security_scheme = HTTPBearer()

router = APIRouter()

@router.get("/debug/simple")
async def debug_simple():
    """Very simple debug endpoint"""
    return {"message": "Debug endpoint working", "status": "ok"}

@router.get("/debug/jwt")
async def debug_jwt():
    """Debug JWT configuration"""
    from app.core.config import settings
    
    return {
        "algorithm": settings.ALGORITHM,
        "secret_key_length": len(settings.SECRET_KEY),
        "academy_secret_key_length": len(settings.ACADEMY_SECRET_KEY),
        "student_secret_key_length": len(settings.STUDENT_SECRET_KEY),
        "admin_secret_key_length": len(settings.ADMIN_SECRET_KEY),
        "secret_keys_match": {
            "academy_vs_default": settings.ACADEMY_SECRET_KEY == settings.SECRET_KEY,
            "student_vs_default": settings.STUDENT_SECRET_KEY == settings.SECRET_KEY,
            "admin_vs_default": settings.ADMIN_SECRET_KEY == settings.SECRET_KEY
        }
    }

@router.get("/debug/auth")
async def debug_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
):
    """Debug authentication directly"""
    try:
        token = credentials.credentials
        
        # استخدام نفس منطق فك التشفير المُستخدم في /me endpoint
        from jose import jwt, JWTError
        from app.core.config import settings
        
        payload = None
        user_type = None
        
        # Try each user type's key until one works - تجربة مفتاح كل نوع مستخدم حتى نجد المناسب
        for try_type in ["academy", "student", "admin"]:
            try:
                secret_key = security.get_secret_key_by_type(try_type)
                test_payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
                if test_payload.get("type") == try_type:  # Found the right key
                    payload = test_payload
                    user_type = try_type
                    break
            except JWTError:
                continue
        
        if not payload:
            return {"error": "No key worked for token"}
            
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {"error": "User not found"}
        
        # Get academy memberships - simple version
        academy_memberships = db.query(AcademyUser).filter(AcademyUser.user_id == user.id).all()
        
        return {
            "token_valid": True,
            "user_id": user.id,
            "email": user.email,
            "user_type": user.user_type,
            "status": user.status,
            "decoded_type": user_type,
            "payload": payload,
            "academy_memberships_count": len(academy_memberships),
            "academy_memberships": [
                {
                    "id": am.id,
                    "academy_id": am.academy_id,
                    "user_role": am.user_role,
                    "is_active": am.is_active
                } for am in academy_memberships
            ] if academy_memberships else []
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}

@router.get("/debug/user")
async def debug_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check user information"""
    
    try:
        # Get academy memberships
        academy_memberships = db.query(AcademyUser).filter(AcademyUser.user_id == current_user.id).all()
        
        return {
            "user_id": current_user.id,
            "email": current_user.email,
            "user_type": current_user.user_type,
            "academy_memberships_count": len(academy_memberships),
            "academy_memberships": [
                {
                    "id": am.id,
                    "academy_id": am.academy_id,
                    "user_role": am.user_role,
                    "is_active": am.is_active,
                    "academy_name": am.academy.name if am.academy else None
                } for am in academy_memberships
            ],
            "has_academy_property": hasattr(current_user, 'academy'),
            "academy_property": str(current_user.academy) if hasattr(current_user, 'academy') else None
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}

@router.post("/debug/simple-course")
async def debug_simple_course(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Simple endpoint to test course creation without complex dependencies"""
    
    if current_user.user_type != "academy":
        raise HTTPException(status_code=403, detail="Not an academy user")
    
    # Get academy_user directly
    academy_user = db.query(AcademyUser).filter(AcademyUser.user_id == current_user.id).first()
    if not academy_user:
        raise HTTPException(status_code=404, detail="Academy not found")
    
    return {
        "message": "Academy user validated successfully",
        "academy_id": academy_user.academy_id,
        "academy_name": academy_user.academy.name if academy_user.academy else None,
        "user_role": academy_user.user_role
    }

@router.post("/debug/simple-category")
async def debug_simple_category(db: Session = Depends(get_db)):
    """Create a simple category without any complex relationships"""
    try:
        from sqlalchemy import text
        
        # تجاوز model relationship issues باستخدام raw SQL
        result = db.execute(
            text("SELECT id FROM categories WHERE id = 1 LIMIT 1")
        ).fetchone()
        
        if not result:
            db.execute(
                text("INSERT INTO categories (id, title, slug, content, status, created_at, updated_at) VALUES (1, 'Test Category', 'test-category', 'Test category for debugging', 1, NOW(), NOW())")
            )
            db.commit()
            return {"message": "Category created successfully", "category_id": 1}
        else:
            return {"message": "Category already exists", "category_id": 1}
            
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}

@router.get("/debug/test-imports")
async def debug_test_imports():
    """Test importing models to check for issues"""
    try:
        from app.models.product import Product, ProductStatus, ProductType
        
        return {
            "message": "Essential models imported successfully",
            "product_available": True,
            "product_statuses": [status.value for status in ProductStatus],
            "product_types": [ptype.value for ptype in ProductType]
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__} 