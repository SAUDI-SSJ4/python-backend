import requests
from typing import Optional, Dict, Any
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import urllib.parse

from app.core.config import settings


class GoogleAuthService:
    """Service for handling Google authentication"""
    
    @staticmethod
    def generate_auth_url(redirect_uri: str, state: Optional[str] = None) -> str:
        """
        توليد رابط Google OAuth للمصادقة
        
        Args:
            redirect_uri: رابط الإرجاع بعد المصادقة
            state: بيانات إضافية (مثل user_type)
            
        Returns:
            رابط Google OAuth الكامل
        """
        params = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        if state:
            params['state'] = state
            
        query_string = urllib.parse.urlencode(params)
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"
    
    @staticmethod
    def exchange_code_for_token(auth_code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """
        تبديل authorization code بـ access token
        
        Args:
            auth_code: الكود المُستلم من Google
            redirect_uri: نفس الرابط المُستخدم في المصادقة
            
        Returns:
            معلومات الـ token أو None في حالة الفشل
        """
        try:
            token_data = {
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri
            }
            
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data=token_data,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Token exchange failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Token exchange error: {str(e)}")
            return None
    
    @staticmethod
    def get_user_info(access_token: str) -> Optional[Dict[str, Any]]:
        """
        الحصول على معلومات المستخدم باستخدام access token
        
        Args:
            access_token: الـ token المُستلم من Google
            
        Returns:
            معلومات المستخدم أو None في حالة الفشل
        """
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    'google_id': user_data.get('id'),
                    'email': user_data.get('email'),
                    'name': user_data.get('name'),
                    'given_name': user_data.get('given_name'),
                    'family_name': user_data.get('family_name'),
                    'picture': user_data.get('picture'),
                    'email_verified': user_data.get('verified_email', False)
                }
            else:
                print(f"Get user info failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Get user info error: {str(e)}")
            return None
    
    @staticmethod
    def verify_google_token(id_token_string: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google ID token and return user information
        """
        try:
            print(f"Attempting to verify Google ID token...")
            print(f"Client ID: {settings.GOOGLE_CLIENT_ID}")
            print(f"Token (first 50 chars): {id_token_string[:50]}...")
            
            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                id_token_string,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
            
            print(f"Token verification successful!")
            print(f"Token info: {idinfo}")
            
            # Token is valid, return user info
            return {
                'id': idinfo.get('sub'),
                'email': idinfo.get('email'),
                'verified_email': idinfo.get('email_verified', True),
                'name': idinfo.get('name'),
                'picture': idinfo.get('picture'),
                'given_name': idinfo.get('given_name'),
                'family_name': idinfo.get('family_name'),
                'locale': idinfo.get('locale')
            }
            
        except ValueError as e:
            print(f"Google token verification failed: {e}")
            
            # Try alternative method using tokeninfo endpoint
            try:
                print(f"Trying alternative tokeninfo endpoint...")
                response = requests.get(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token_string}"
                )
                
                if response.status_code == 200:
                    tokeninfo = response.json()
                    print(f"Alternative verification successful!")
                    
                    # Verify audience (client_id)
                    if tokeninfo.get('aud') != settings.GOOGLE_CLIENT_ID:
                        print(f"Invalid audience in token")
                        return None
                    
                    return {
                        'id': tokeninfo.get('sub'),
                        'email': tokeninfo.get('email'),
                        'verified_email': tokeninfo.get('email_verified') == 'true',
                        'name': tokeninfo.get('name'),
                        'picture': tokeninfo.get('picture'),
                        'given_name': tokeninfo.get('given_name'),
                        'family_name': tokeninfo.get('family_name'),
                        'locale': tokeninfo.get('locale')
                    }
                else:
                    print(f"Alternative verification also failed: {response.status_code}")
                    return None
                    
            except Exception as alt_error:
                print(f"Alternative verification error: {alt_error}")
                return None
            
        except Exception as e:
            print(f"Unexpected error during token verification: {e}")
            return None
    
    @staticmethod
    def verify_google_access_token(access_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google access token using Google's tokeninfo endpoint
        Alternative method when ID token is not available
        """
        try:
            # Call Google's tokeninfo endpoint
            response = requests.get(
                f'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}',
                timeout=10
            )
            
            if response.status_code == 200:
                token_info = response.json()
                
                # Verify the token is for our application
                if token_info.get('audience') == settings.GOOGLE_CLIENT_ID:
                    # Get user profile information
                    profile_response = requests.get(
                        f'https://www.googleapis.com/oauth2/v1/userinfo?access_token={access_token}',
                        timeout=10
                    )
                    
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        return {
                            'google_id': profile_data.get('id'),
                            'email': profile_data.get('email'),
                            'name': profile_data.get('name'),
                            'given_name': profile_data.get('given_name'),
                            'family_name': profile_data.get('family_name'),
                            'picture': profile_data.get('picture'),
                            'email_verified': profile_data.get('verified_email', False)
                        }
            
            return None
            
        except Exception as e:
            print(f"Google access token verification failed: {str(e)}")
            return None
    
    @staticmethod
    def get_user_info_from_google_data(google_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and format user information from Google authentication data
        """
        name_parts = GoogleAuthService.parse_name(google_data.get('name', ''))
        
        return {
            'google_id': google_data.get('google_id'),
            'email': google_data.get('email'),
            'fname': name_parts.get('fname', google_data.get('given_name', '')),
            'lname': name_parts.get('lname', google_data.get('family_name', '')),
            'mname': name_parts.get('mname'),
            'picture': google_data.get('picture'),
            'email_verified': google_data.get('email_verified', False)
        }
    
    @staticmethod
    def parse_name(full_name: str) -> Dict[str, Optional[str]]:
        """
        Parse full name into first, middle, and last names
        """
        if not full_name:
            return {'fname': None, 'mname': None, 'lname': None}
        
        # Split name by spaces
        name_parts = full_name.strip().split()
        
        if len(name_parts) == 1:
            # Only first name
            return {'fname': name_parts[0], 'mname': None, 'lname': None}
        elif len(name_parts) == 2:
            # First and last name
            return {'fname': name_parts[0], 'mname': None, 'lname': name_parts[1]}
        elif len(name_parts) >= 3:
            # First, middle(s), and last name
            fname = name_parts[0]
            lname = name_parts[-1]
            mname = ' '.join(name_parts[1:-1])  # Join all middle names
            return {'fname': fname, 'mname': mname, 'lname': lname}
        
        return {'fname': None, 'mname': None, 'lname': None}
    
    @staticmethod
    def validate_google_client_setup() -> bool:
        """
        Validate that Google client is properly configured
        """
        return bool(
            hasattr(settings, 'GOOGLE_CLIENT_ID') and 
            settings.GOOGLE_CLIENT_ID and
            hasattr(settings, 'GOOGLE_CLIENT_SECRET') and
            settings.GOOGLE_CLIENT_SECRET
        ) 