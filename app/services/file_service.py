import os
import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import uuid
from datetime import datetime

class FileService:
    """File and image management service"""
    
    def __init__(self):
        self.upload_dir = Path("static/uploads")
        self.academy_logos_dir = self.upload_dir / "academy" / "logos"
        self.academy_covers_dir = self.upload_dir / "academy" / "covers"
        self.profile_images_dir = self.upload_dir / "profiles"
        
        # Create directories if they don't exist
        self._create_directories()
        
        # Allowed file types
        self.allowed_image_types = {
            "image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"
        }
        
        # Maximum file size (5MB)
        self.max_file_size = 5 * 1024 * 1024
        
        # Image dimensions
        self.logo_size = (400, 400)
        self.cover_size = (1200, 300)
        self.profile_size = (200, 200)
    
    def _create_directories(self):
        """Create required directories"""
        directories = [
            self.upload_dir,
            self.academy_logos_dir,
            self.academy_covers_dir,
            self.profile_images_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _validate_file(self, file: UploadFile) -> bool:
        """Validate file"""
        # Check file type
        if file.content_type not in self.allowed_image_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not supported. Supported types: {', '.join(self.allowed_image_types)}"
            )
        
        # Check file size
        if hasattr(file, 'size') and file.size > self.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {self.max_file_size / (1024*1024):.1f} MB"
            )
        
        return True
    
    def _generate_filename(self, original_filename: str) -> str:
        """Generate unique filename"""
        # Get file extension
        file_extension = Path(original_filename).suffix.lower()
        
        # Generate unique name
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"{timestamp}_{unique_id}{file_extension}"
    
    def _resize_image(self, image_path: Path, target_size: tuple, crop: bool = False):
        """Resize image"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                if crop:
                    # Crop image while maintaining aspect ratio
                    img.thumbnail(target_size, Image.Resampling.LANCZOS)
                else:
                    # Resize while maintaining aspect ratio
                    img.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # Save optimized image
                img.save(image_path, optimize=True, quality=85)
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image processing error: {str(e)}"
            )
    
    async def upload_academy_logo(self, file: UploadFile, academy_id: int) -> str:
        """Upload academy logo"""
        self._validate_file(file)
        
        # Generate filename
        filename = self._generate_filename(file.filename)
        file_path = self.academy_logos_dir / filename
        
        try:
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Resize image
            self._resize_image(file_path, self.logo_size, crop=True)
            
            # Return relative path
            return f"academy/logos/{filename}"
            
        except Exception as e:
            # Delete file on error
            if file_path.exists():
                file_path.unlink()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File upload failed: {str(e)}"
            )
    
    async def upload_academy_cover(self, file: UploadFile, academy_id: int) -> str:
        """Upload academy cover"""
        self._validate_file(file)
        
        # Generate filename
        filename = self._generate_filename(file.filename)
        file_path = self.academy_covers_dir / filename
        
        try:
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Resize image
            self._resize_image(file_path, self.cover_size, crop=False)
            
            # Return relative path
            return f"academy/covers/{filename}"
            
        except Exception as e:
            # Delete file on error
            if file_path.exists():
                file_path.unlink()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File upload failed: {str(e)}"
            )
    
    async def upload_profile_image(self, file: UploadFile, user_id: int, user_type: str) -> str:
        """Upload user profile image"""
        self._validate_file(file)
        
        # Generate filename
        filename = self._generate_filename(file.filename)
        file_path = self.profile_images_dir / filename
        
        try:
            # Reset file cursor to beginning
            await file.seek(0)
            
            # Save file
            with open(file_path, "wb") as buffer:
                contents = await file.read()
                buffer.write(contents)
            
            # Resize image
            self._resize_image(file_path, self.profile_size, crop=True)
            
            # Return relative path for static serving
            return f"static/uploads/profiles/{filename}"
            
        except Exception as e:
            # Delete file on error
            if file_path.exists():
                file_path.unlink()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File upload failed: {str(e)}"
            )
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file"""
        try:
            full_path = self.upload_dir / file_path
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def get_file_url(self, file_path: str, base_url: str = "") -> str:
        """Get file URL"""
        if not file_path:
            return ""
        
        if base_url:
            return f"{base_url}/static/uploads/{file_path}"
        else:
            return f"/static/uploads/{file_path}"


# Create singleton service instance
file_service = FileService() 