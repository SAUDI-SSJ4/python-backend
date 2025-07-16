"""
خدمة معالجة الفيديو باستخدام OpenAI Whisper API فقط
"""

import os
import logging
from typing import Dict, Any, Optional
from app.services.ai.openai_service import OpenAITranscriptionService
from app.core.ai_config import AIServiceConfig

logger = logging.getLogger(__name__)

class VideoProcessingService:
    """
    خدمة معالجة الفيديو باستخدام OpenAI Whisper فقط
    """
    
    def __init__(self):
        self.transcription_service = None
        self._init_whisper_service()
    
    def _init_whisper_service(self):
        """تهيئة خدمة OpenAI Whisper"""
        try:
            config = AIServiceConfig(
                service_type="transcription",
                model_name="whisper-1",
                api_key=os.getenv("OPENAI_API_KEY"),
                provider="openai",
                rate_limit_per_minute=40
            )
            self.transcription_service = OpenAITranscriptionService(config)
            logger.info("OpenAI Whisper service initialized successfully")
        except Exception as e:
            logger.error(f"فشل في تهيئة خدمة Whisper: {e}")
    
    async def transcribe_video_with_whisper(
        self, 
        video_path: str, 
        language: str = "ar",
        academy_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        تحويل الفيديو إلى نص باستخدام OpenAI Whisper مباشرة
        """
        try:
            if not self.transcription_service:
                raise Exception("خدمة Whisper غير متاحة")
            
            # التحقق من وجود الملف
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"ملف الفيديو غير موجود: {video_path}")
            
            # الحصول على حجم الملف للمعلومات فقط
            file_size = os.path.getsize(video_path)
            logger.info(f"بدء تحويل الفيديو إلى نص باستخدام Whisper: {video_path} (حجم: {file_size / (1024*1024):.2f}MB)")
            
            # تحويل الفيديو إلى نص باستخدام Whisper (بدون حد للحجم)
            with open(video_path, "rb") as video_file:
                result = await self.transcription_service.transcribe_audio(
                    audio_file=video_file,
                    language=language,
                    academy_id=academy_id
                )
            
            if result.get("status") == "success":
                return {
                    "status": "success",
                    "text": result.get("text", ""),
                    "language": result.get("language", language),
                    "duration": result.get("duration", 0),
                    "segments": result.get("segments", []),
                    "confidence": result.get("confidence", 0.0),
                    "file_size_mb": round(file_size / (1024 * 1024), 2)
                }
            else:
                raise Exception(result.get("error", "فشل في تحويل الفيديو إلى نص"))
            
        except Exception as e:
            logger.error(f"خطأ في تحويل الفيديو إلى نص: {e}")
            return {
                "status": "error",
                "error": str(e),
                "file_size_mb": round(os.path.getsize(video_path) / (1024 * 1024), 2) if os.path.exists(video_path) else 0
            }
    
    def validate_video_file(self, video_path: str) -> Dict[str, Any]:
        """
        التحقق من صحة ملف الفيديو
        """
        try:
            if not os.path.exists(video_path):
                return {
                    "valid": False,
                    "error": "الملف غير موجود"
                }
            
            file_size = os.path.getsize(video_path)
            file_extension = os.path.splitext(video_path)[1].lower()
            
            # الصيغ المدعومة من OpenAI Whisper
            supported_formats = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.mp3', '.wav', '.m4a']
            
            validation_result = {
                "valid": True,
                "file_path": video_path,
                "file_size": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "file_extension": file_extension,
                "is_supported_format": file_extension in supported_formats,
                "can_transcribe": True,  # يمكن تحويل جميع الفيديوهات
                "note": "جميع الأحجام مدعومة للتحويل"
            }
            
            if not validation_result["is_supported_format"]:
                validation_result["valid"] = False
                validation_result["error"] = f"صيغة الملف غير مدعومة: {file_extension}"
            
            return validation_result
            
        except Exception as e:
            logger.error(f"خطأ في التحقق من الملف: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    def create_srt_subtitles(self, segments: list) -> str:
        """
        إنشاء ملف ترجمة SRT من النصوص المحولة
        """
        if not segments:
            return ""
        
        srt_content = ""
        for i, segment in enumerate(segments, 1):
            start_time = self._format_time_srt(segment.get("start", 0))
            end_time = self._format_time_srt(segment.get("end", 0))
            text = segment.get("text", "").strip()
            
            if text:
                srt_content += f"{i}\n"
                srt_content += f"{start_time} --> {end_time}\n"
                srt_content += f"{text}\n\n"
        
        return srt_content
    
    def _format_time_srt(self, seconds: float) -> str:
        """تنسيق الوقت لصيغة SRT"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def get_whisper_capabilities(self) -> Dict[str, Any]:
        """
        معلومات عن قدرات OpenAI Whisper
        """
        return {
            "service": "OpenAI Whisper",
            "model": "whisper-1",
            "supported_formats": [
                {"format": "mp4", "description": "فيديو MP4", "recommended": True},
                {"format": "mov", "description": "فيديو QuickTime", "recommended": True},
                {"format": "avi", "description": "فيديو AVI", "recommended": False},
                {"format": "mkv", "description": "فيديو Matroska", "recommended": False},
                {"format": "webm", "description": "فيديو WebM", "recommended": True},
                {"format": "mp3", "description": "صوت MP3", "recommended": True},
                {"format": "wav", "description": "صوت WAV", "recommended": True},
                {"format": "m4a", "description": "صوت M4A", "recommended": True}
            ],
            "max_file_size": "بدون حد أقصى",
            "supported_languages": ["ar", "en", "fr", "es", "de", "it", "pt", "ru", "ja", "ko", "zh"],
            "features": [
                "تحويل الفيديو إلى نص مباشرة",
                "دعم اللغة العربية",
                "إنشاء ملفات ترجمة SRT",
                "تقسيم النص إلى أجزاء زمنية",
                "تقييم مستوى الثقة في النص",
                "دعم جميع الأحجام"
            ],
            "rate_limit": "40 طلب في الدقيقة"
        } 