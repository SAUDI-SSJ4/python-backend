from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.core import security
from .auth_utils import get_current_timestamp, generate_user_tokens, send_verification_otp, create_student_profile, create_academy_profile

class RegistrationService:
    """Service for handling user registration"""
    
    @staticmethod
    def create_user_base(
        fname: str,
        lname: str,
        email: str,
        user_type: str,
        account_type: str = "local",
        **kwargs
    ) -> User:
        """Create base user object with common fields"""
        return User(
            fname=fname,
            mname=kwargs.get('mname'),
            lname=lname,
            email=email,
            phone_number=kwargs.get('phone_number'),
            password=kwargs.get('password'),
            user_type=user_type,
            account_type=account_type,
            status=kwargs.get('status', "pending_verification"),
            verified=kwargs.get('verified', False),
            google_id=kwargs.get('google_id'),
            avatar=kwargs.get('avatar'),
            refere_id=kwargs.get('refere_id')
        )
    
    @staticmethod
    async def register_local_user(
        register_data: Any,
        db: Session,
        avatar_file: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Register a local user (email/password)"""
        
        # Check for existing user
        existing_user = db.query(User).filter(
            (User.email == register_data.email) | 
            (User.phone_number == register_data.phone_number)
        ).first()
        
        if existing_user:
            conflict_type = "email" if existing_user.email == register_data.email else "phone"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "status": "error",
                    "error": f"{conflict_type}_already_exists",
                    "message": f"{'البريد الإلكتروني' if conflict_type == 'email' else 'رقم الهاتف'} مستخدم بالفعل",
                    "conflict_field": conflict_type,
                    "timestamp": get_current_timestamp(),
                    "missing_fields": [],
                    "invalid_fields": []
                }
            )
        
        # Hash password
        hashed_password = security.get_password_hash(register_data.password)
        
        # Create user
        new_user = RegistrationService.create_user_base(
            fname=register_data.fname,
            lname=register_data.lname,
            email=register_data.email,
            user_type=register_data.user_type,
            mname=getattr(register_data, 'mname', None),
            phone_number=register_data.phone_number,
            password=hashed_password,
            refere_id=getattr(register_data, 'refere_id', None),
            avatar=getattr(register_data, 'picture', None)
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Handle avatar upload if provided
        if avatar_file:
            try:
                from app.services.file_service import FileService
                file_service = FileService()
                
                # استخدام await مباشرة للحصول على رابط الصورة
                avatar_path = await file_service.upload_profile_image(avatar_file, new_user.id, register_data.user_type)
                
                # حفظ Avatar في جدول users
                new_user.avatar = avatar_path
                db.commit()
                db.refresh(new_user)
                
                print(f"Avatar uploaded successfully: {avatar_path}")
                
            except Exception as e:
                print(f"Error uploading avatar: {e}")
        
        # Create profile
        RegistrationService.create_user_profile(new_user, register_data, db)
        
        # Send verification OTP
        try:
            send_verification_otp(new_user, db)
        except Exception as e:
            print(f"خطأ في إرسال رمز التحقق: {str(e)}")
        
        return generate_user_tokens(new_user, db)
    
    @staticmethod
    def register_google_user(
        google_data: Dict[str, Any],
        user_type: str,
        db: Session
    ) -> Dict[str, Any]:
        """Register a Google OAuth user"""
        
        # Check for existing user
        existing_user = db.query(User).filter(
            (User.google_id == google_data['id']) | 
            (User.email == google_data['email'])
        ).first()
        
        if existing_user:
            if existing_user.google_id == google_data['id']:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "user_already_exists",
                        "message": "يوجد حساب مسجل بهذا Google ID بالفعل",
                        "status_code": 409,
                        "suggestion": "استخدم /google/login لتسجيل الدخول"
                    }
                )
            else:
                # Link existing local account to Google
                return RegistrationService.link_google_account(existing_user, google_data, db)
        
        # Parse name
        name_parts = RegistrationService.parse_google_name(google_data.get('name', ''))
        
        # Create new Google user
        new_user = RegistrationService.create_user_base(
            fname=name_parts.get('fname') or google_data.get('given_name') or 'مستخدم',
            lname=name_parts.get('lname') or google_data.get('family_name') or 'Google',
            email=google_data['email'],
            user_type=user_type,
            account_type="google",
            mname=name_parts.get('mname'),
            status="active",
            verified=True,
            google_id=google_data['id'],
            avatar=google_data.get('picture')
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create profile
        profile_data = type('obj', (object,), {
            'user_type': user_type,
            'birth_date': None,
            'gender': None,
            'academy_name': f"{new_user.fname} {new_user.lname} Academy" if user_type == "academy" else None,
            'academy_about': None
        })
        
        RegistrationService.create_user_profile(new_user, profile_data, db)
        
        return generate_user_tokens(new_user, db)
    
    @staticmethod
    def create_user_profile(user: User, profile_data: Any, db: Session):
        """Create user profile based on user type"""
        if user.user_type == "student":
            create_student_profile(user, profile_data, db)
        else:
            create_academy_profile(user, profile_data, db)
    
    @staticmethod
    def link_google_account(user: User, google_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Link existing local account to Google"""
        user.google_id = google_data['id']
        user.account_type = "google"
        if google_data.get('picture'):
            user.avatar = google_data['picture']
        user.verified = True
        if user.status == "pending_verification":
            user.status = "active"
        
        db.commit()
        db.refresh(user)
        return generate_user_tokens(user, db)
    
    @staticmethod
    def parse_google_name(full_name: str) -> Dict[str, Optional[str]]:
        """Parse Google full name into components"""
        if not full_name:
            return {'fname': None, 'mname': None, 'lname': None}
        
        parts = full_name.split(' ')
        if len(parts) == 1:
            return {'fname': parts[0], 'mname': None, 'lname': None}
        elif len(parts) == 2:
            return {'fname': parts[0], 'mname': None, 'lname': parts[1]}
        else:
            return {
                'fname': parts[0],
                'mname': ' '.join(parts[1:-1]),
                'lname': parts[-1]
            } 