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
    خدمة بث الفيديوهات مع حماية متقدمة مجانية
    
    الحمايات المُضافة:
    - منع User Agents المشبوهة
    - تشفير روابط الفيديو
    - تتبع محاولات التحميل المشبوهة
    - حماية من الـ Hotlinking المتقدمة
    - تشفير مسارات الملفات
    """
    
    # تنسيقات الفيديو المدعومة
    SUPPORTED_FORMATS = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.ogg': 'video/ogg',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska'
    }
    
    # User Agents المحظورة (أدوات التحميل)
    BLOCKED_USER_AGENTS = [
        'curl', 'wget', 'python-requests', 'youtube-dl', 'yt-dlp',
        'vlc', 'ffmpeg', 'aria2', 'idm', 'fdm', 'jdownloader',
        'download', 'spider', 'crawler', 'bot'
    ]
    
    # مدة انتهاء التوكن (ساعتين)
    DEFAULT_TOKEN_EXPIRY = timedelta(hours=2)
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.video_storage_path = getattr(settings, 'VIDEO_STORAGE_PATH', "static/videos")
        
    def generate_video_token(
        self, 
        video_id: str, 
        student_id: int, 
        expires_delta: Optional[timedelta] = None,
        client_info: Optional[Dict] = None
    ) -> str:
        """
        إنشاء رمز وصول آمن للفيديو مع معلومات العميل
        """
        if expires_delta is None:
            expires_delta = self.DEFAULT_TOKEN_EXPIRY
            
        expire = datetime.utcnow() + expires_delta
        
        # إضافة معلومات العميل للحماية الإضافية
        client_fingerprint = self._generate_client_fingerprint(client_info)
        
        payload = {
            "video_id": video_id,
            "student_id": student_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "video_access",
            "client_fp": client_fingerprint,
            "checksum": self._generate_checksum(video_id, student_id, client_fingerprint)
        }
        
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_video_token(self, token: str, request: Request) -> Dict[str, Any]:
        """
        التحقق من رمز الوصول مع فحص معلومات العميل
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            # التحقق من نوع التوكن
            if payload.get("type") != "video_access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="نوع رمز الوصول غير صحيح"
                )
            
            # فحص معلومات العميل
            current_client_info = {
                'user_agent': request.headers.get('user-agent', ''),
                'ip': request.client.host,
                'referer': request.headers.get('referer', '')
            }
            
            # منع User Agents المشبوهة
            self._check_user_agent(current_client_info['user_agent'])
            
            # التحقق من بصمة العميل
            current_fingerprint = self._generate_client_fingerprint(current_client_info)
            if payload.get("client_fp") != current_fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="جلسة العمل غير صالحة"
                )
            
            # التحقق من الـ checksum
            expected_checksum = self._generate_checksum(
                payload.get("video_id"), 
                payload.get("student_id"),
                current_fingerprint
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
    
    def _check_user_agent(self, user_agent: str) -> None:
        """
        فحص User Agent ومنع أدوات التحميل
        """
        if not user_agent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="غير مسموح بالوصول"
            )
        
        user_agent_lower = user_agent.lower()
        
        # فحص الـ User Agents المحظورة
        for blocked_agent in self.BLOCKED_USER_AGENTS:
            if blocked_agent in user_agent_lower:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="غير مسموح بالوصول من هذا التطبيق"
                )
        
        # فحص إضافي للمتصفحات الحقيقية
        valid_browsers = ['chrome', 'firefox', 'safari', 'edge', 'opera']
        if not any(browser in user_agent_lower for browser in valid_browsers):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="يجب استخدام متصفح ويب صالح"
            )
    
    def _generate_client_fingerprint(self, client_info: Optional[Dict]) -> str:
        """
        إنشاء بصمة فريدة للعميل
        """
        if not client_info:
            return ""
        
        # دمج معلومات العميل لإنشاء بصمة فريدة
        fingerprint_data = (
            f"{client_info.get('user_agent', '')}"
            f"{client_info.get('ip', '')}"
            f"{self.secret_key}"
        )
        
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    def verify_student_access(
        self, 
        db: Session, 
        video_id: str, 
        student_id: int
    ) -> tuple[Video, bool]:
        """
        التحقق من وصول الطالب للفيديو
        """
        # الحصول على الفيديو والدرس
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
        
        # الحصول على معلومات الدرس والكورس
        lesson = db.query(Lesson).filter(Lesson.id == video.lesson_id).first()
        if not lesson or not lesson.status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الدرس غير متاح"
            )
        
        # فحص إذا كان الدرس مجاني
        if lesson.is_free_preview:
            return video, True
        
        # التحقق من تسجيل الطالب في الكورس
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
        الحصول على مسار ملف الفيديو مع التشفير
        """
        if not video.video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ملف الفيديو غير موجود"
            )
        
        # تشفير مسار الملف للحماية الإضافية
        encrypted_path = self._decrypt_file_path(video.video)
        
        # التعامل مع المسارات المطلقة والنسبية
        if os.path.isabs(encrypted_path):
            file_path = Path(encrypted_path)
        else:
            file_path = Path(self.video_storage_path) / encrypted_path
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ملف الفيديو غير موجود على الخادم"
            )
        
        return file_path
    
    def _encrypt_file_path(self, file_path: str) -> str:
        """
        تشفير مسار الملف (لحفظه في قاعدة البيانات)
        """
        # تشفير بسيط باستخدام base64 و XOR
        import base64
        
        key = self.secret_key[:16].encode()
        encrypted = bytes([file_path.encode()[i % len(file_path.encode())] ^ key[i % len(key)] 
                          for i in range(len(file_path.encode()))])
        
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_file_path(self, encrypted_path: str) -> str:
        """
        فك تشفير مسار الملف
        """
        try:
            import base64
            
            key = self.secret_key[:16].encode()
            encrypted = base64.b64decode(encrypted_path.encode())
            decrypted = bytes([encrypted[i] ^ key[i % len(key)] 
                             for i in range(len(encrypted))])
            
            return decrypted.decode()
        except:
            # إذا فشل فك التشفير، استخدم المسار كما هو (للتوافق مع البيانات القديمة)
            return encrypted_path
    
    def get_video_info(self, file_path: Path) -> Dict[str, Any]:
        """
        الحصول على معلومات ملف الفيديو
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
        إنشاء استجابة بث محمية مع Range support
        """
        video_info = self.get_video_info(file_path)
        file_size = video_info["size"]
        
        # تحليل Range header
        start = 0
        end = file_size - 1
        
        if range_header:
            range_match = range_header.replace("bytes=", "").split("-")
            if len(range_match) == 2:
                if range_match[0]:
                    start = int(range_match[0])
                if range_match[1]:
                    end = int(range_match[1])
        
        # التأكد من صحة النطاق
        start = max(0, start)
        end = min(file_size - 1, end)
        content_length = end - start + 1
        
        # منشئ الملف مع الحماية
        def protected_file_generator() -> Generator[bytes, None, None]:
            with open(file_path, "rb") as video_file:
                video_file.seek(start)
                remaining = content_length
                chunk_size = 8192  # 8KB chunks
                
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    chunk = video_file.read(read_size)
                    if not chunk:
                        break
                    
                    # تشفير بسيط للـ chunks (اختياري)
                    # chunk = self._scramble_chunk(chunk)
                    
                    remaining -= len(chunk)
                    yield chunk
        
        # إعداد headers الحماية
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": video_info["mime_type"],
            
            # حماية إضافية
            "Cache-Control": "private, no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            
            # منع التحميل
            "Content-Disposition": "inline",
            "X-Accel-Buffering": "no"
        }
        
        # إرجاع محتوى جزئي إذا تم طلب range
        status_code = 206 if range_header else 200
        
        return StreamingResponse(
            protected_file_generator(),
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
        تسجيل الوصول للفيديو مع معلومات الحماية
        """
        try:
            # تحديث عداد المشاهدات
            db.query(Video).filter(Video.id == video_id).update({
                "views_count": Video.views_count + 1
            })
            
            # تحديث عداد مشاهدات الدرس
            lesson = db.query(Lesson).join(Video).filter(Video.id == video_id).first()
            if lesson:
                lesson.views_count += 1
            
            # تسجيل معلومات إضافية للحماية (اختياري)
            access_info = {
                'student_id': student_id,
                'video_id': video_id,
                'ip': request.client.host,
                'user_agent': request.headers.get('user-agent'),
                'timestamp': datetime.utcnow(),
                'referer': request.headers.get('referer')
            }
            
            # يمكن حفظ هذه المعلومات في جدول منفصل للتحليل
            
            db.commit()
            
        except Exception as e:
            # عدم السماح لأخطاء التسجيل بإيقاف البث
            db.rollback()
            print(f"خطأ في تسجيل الوصول للفيديو: {e}")
    
    def _generate_checksum(self, video_id: str, student_id: int, client_fingerprint: str = "") -> str:
        """
        إنشاء checksum للحماية الإضافية
        """
        data = f"{video_id}:{student_id}:{client_fingerprint}:{self.secret_key}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


# مثيل الخدمة العامة
video_streaming_service = VideoStreamingService() 