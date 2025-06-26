import os
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Generator, BinaryIO
from pathlib import Path
from fastapi import HTTPException, status, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.video import Video
from app.models.lesson import Lesson
from app.models.student import Student
from app.models.student_course import StudentCourse


class VideoStreamingService:
    """
    Comprehensive video streaming service with security and performance features.
    
    Features:
    - JWT-based access control
    - Range request support for efficient streaming
    - Student enrollment verification
    - Video access logging
    - Support for multiple video formats
    - HLS (HTTP Live Streaming) compatibility
    """
    
    # Supported video formats and their MIME types
    SUPPORTED_FORMATS = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.ogg': 'video/ogg',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska'
    }
    
    # Default token expiration (2 hours)
    DEFAULT_TOKEN_EXPIRY = timedelta(hours=2)
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.video_storage_path = getattr(settings, 'VIDEO_STORAGE_PATH', "static/videos")
        
    def generate_video_token(
        self, 
        video_id: str, 
        student_id: int, 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Generate a secure JWT token for video access.
        
        Args:
            video_id: Video UUID
            student_id: Student ID
            expires_delta: Token expiration time
            
        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = self.DEFAULT_TOKEN_EXPIRY
            
        expire = datetime.utcnow() + expires_delta
        
        # Create token payload with video access permissions
        payload = {
            "video_id": video_id,
            "student_id": student_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "video_access",
            # Add checksum for additional security
            "checksum": self._generate_checksum(video_id, student_id)
        }
        
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_video_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode video access token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            # Verify token type
            if payload.get("type") != "video_access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="نوع رمز الوصول غير صحيح"
                )
            
            # Verify checksum
            expected_checksum = self._generate_checksum(
                payload.get("video_id"), 
                payload.get("student_id")
            )
            if payload.get("checksum") != expected_checksum:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="رمز الوصول غير صالح"
                )
                
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="انتهت صلاحية رمز الوصول"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="رمز الوصول غير صالح"
            )
    
    def verify_student_access(
        self, 
        db: Session, 
        video_id: str, 
        student_id: int
    ) -> tuple[Video, bool]:
        """
        Verify student has access to the video.
        
        Args:
            db: Database session
            video_id: Video UUID
            student_id: Student ID
            
        Returns:
            Tuple of (Video object, is_enrolled boolean)
            
        Raises:
            HTTPException: If video not found or access denied
        """
        # Get video and its lesson
        video = db.query(Video).filter(
            Video.id == video_id,
            Video.status == True,
            Video.deleted_at.is_(None)
        ).first()
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الفيديو غير موجود"
            )
        
        # Get lesson and course information
        lesson = db.query(Lesson).filter(Lesson.id == video.lesson_id).first()
        if not lesson or not lesson.status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الدرس غير متاح"
            )
        
        # Check if lesson is free preview
        if lesson.is_free_preview:
            return video, True
        
        # Check if student is enrolled in the course
        enrollment = db.query(StudentCourse).filter(
            StudentCourse.student_id == student_id,
            StudentCourse.course_id == lesson.course_id,
            StudentCourse.status == "active"
        ).first()
        
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="يجب التسجيل في الدورة للوصول إلى هذا المحتوى"
            )
        
        return video, True
    
    def get_video_file_path(self, video: Video) -> Path:
        """
        Get the full file path for a video.
        
        Args:
            video: Video object
            
        Returns:
            Path object to video file
            
        Raises:
            HTTPException: If file not found
        """
        if not video.video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ملف الفيديو غير موجود"
            )
        
        # Handle both absolute and relative paths
        if os.path.isabs(video.video):
            file_path = Path(video.video)
        else:
            file_path = Path(self.video_storage_path) / video.video
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ملف الفيديو غير موجود على الخادم"
            )
        
        return file_path
    
    def get_video_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get video file information.
        
        Args:
            file_path: Path to video file
            
        Returns:
            Dictionary with video information
        """
        stat = file_path.stat()
        file_ext = file_path.suffix.lower()
        
        return {
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "mime_type": self.SUPPORTED_FORMATS.get(file_ext, "video/mp4"),
            "extension": file_ext
        }
    
    def create_range_response(
        self, 
        file_path: Path, 
        range_header: Optional[str] = None
    ) -> StreamingResponse:
        """
        Create a range-aware streaming response for video playback.
        
        Args:
            file_path: Path to video file
            range_header: HTTP Range header value
            
        Returns:
            StreamingResponse with appropriate headers
        """
        video_info = self.get_video_info(file_path)
        file_size = video_info["size"]
        
        # Parse range header
        start = 0
        end = file_size - 1
        
        if range_header:
            range_match = range_header.replace("bytes=", "").split("-")
            if len(range_match) == 2:
                if range_match[0]:
                    start = int(range_match[0])
                if range_match[1]:
                    end = int(range_match[1])
        
        # Ensure valid range
        start = max(0, start)
        end = min(file_size - 1, end)
        content_length = end - start + 1
        
        # Create file generator
        def file_generator() -> Generator[bytes, None, None]:
            with open(file_path, "rb") as video_file:
                video_file.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(8192, remaining)  # 8KB chunks
                    chunk = video_file.read(chunk_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        # Prepare response headers
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": video_info["mime_type"],
            "Cache-Control": "private, max-age=3600",  # Cache for 1 hour
            "X-Content-Type-Options": "nosniff"
        }
        
        # Return partial content if range requested
        status_code = 206 if range_header else 200
        
        return StreamingResponse(
            file_generator(),
            status_code=status_code,
            headers=headers,
            media_type=video_info["mime_type"]
        )
    
    def log_video_access(
        self, 
        db: Session, 
        video_id: str, 
        student_id: int, 
        request: Request
    ) -> None:
        """
        Log video access for analytics.
        
        Args:
            db: Database session
            video_id: Video UUID
            student_id: Student ID
            request: FastAPI request object
        """
        try:
            # Update video views count
            db.query(Video).filter(Video.id == video_id).update({
                "views_count": Video.views_count + 1
            })
            
            # Update lesson views count
            lesson = db.query(Lesson).join(Video).filter(Video.id == video_id).first()
            if lesson:
                lesson.views_count += 1
            
            db.commit()
            
            # Here you could add more detailed logging to a separate analytics table
            # For example: IP address, user agent, timestamp, etc.
            
        except Exception as e:
            # Don't let logging errors affect video streaming
            db.rollback()
            print(f"Error logging video access: {e}")
    
    def _generate_checksum(self, video_id: str, student_id: int) -> str:
        """
        Generate a checksum for additional token security.
        
        Args:
            video_id: Video UUID
            student_id: Student ID
            
        Returns:
            Hexadecimal checksum string
        """
        data = f"{video_id}:{student_id}:{self.secret_key}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


# Global service instance
video_streaming_service = VideoStreamingService() 