"""
خدمة معالجة الفيديو باستخدام OpenAI Whisper API فقط
"""

import os
import logging
from typing import Dict, Any, Optional
from app.services.ai.openai_service import OpenAITranscriptionService
from app.core.ai_config import AIServiceConfig
from app.core.config import settings

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
                api_key=settings.OPENAI_API_KEY,
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
        تحويل الفيديو إلى نص باستخدام OpenAI Whisper مباشرة مع مراقبة التقدم
        """
        import asyncio
        import time
        
        try:
            if not self.transcription_service:
                raise Exception("خدمة Whisper غير متاحة")
            
            # التحقق من وجود الملف
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"ملف الفيديو غير موجود: {video_path}")
            
            # الحصول على حجم الملف للمعلومات فقط
            file_size = os.path.getsize(video_path)
            file_size_mb = file_size / (1024*1024)
            
            logger.info(f"بدء تحويل الفيديو إلى نص باستخدام Whisper: {video_path} (حجم: {file_size_mb:.2f}MB)")
            
            # بدء مراقبة التقدم
            start_time = time.time()
            progress_task = asyncio.create_task(self._monitor_progress(start_time, file_size_mb))
            
            try:
                # محاولة تحويل الفيديو إلى نص باستخدام Whisper مباشرة
                try:
                    with open(video_path, "rb") as video_file:
                        result = await self.transcription_service.transcribe_audio(
                            audio_file=video_file,
                            language=language,
                            academy_id=academy_id
                        )
                    logger.info("تم تحويل الفيديو بنجاح باستخدام Whisper المباشر")
                except Exception as whisper_error:
                    logger.warning(f"فشل Whisper المباشر: {whisper_error}")
                    
                    # إذا فشل، جرب استخراج الصوت
                    audio_path = await self._extract_audio_from_video(video_path)
                    
                    if audio_path and os.path.exists(audio_path):
                        try:
                            with open(audio_path, "rb") as audio_file:
                                result = await self.transcription_service.transcribe_audio(
                                    audio_file=audio_file,
                                    language=language,
                                    academy_id=academy_id
                                )
                            # حذف ملف الصوت المؤقت
                            os.unlink(audio_path)
                            logger.info("تم تحويل الفيديو بنجاح بعد استخراج الصوت")
                        except Exception as audio_error:
                            raise Exception(f"فشل في تحويل الصوت المستخرج: {audio_error}")
                    else:
                        # إذا فشل استخراج الصوت، جرب إرسال الفيديو كما هو
                        logger.info("محاولة إرسال الفيديو كما هو إلى Whisper...")
                        with open(video_path, "rb") as video_file:
                            result = await self.transcription_service.transcribe_audio(
                                audio_file=video_file,
                                language=language,
                                academy_id=academy_id
                            )
                
                # إيقاف مراقبة التقدم
                progress_task.cancel()
                
                # خدمة OpenAI ترجع النتيجة مباشرة بدون status
                if result and "text" in result:
                    processing_time = time.time() - start_time
                    logger.info(f"تم الانتهاء من التحويل في {processing_time:.2f} ثانية")
                    
                    return {
                        "status": "success",
                        "text": result.get("text", ""),
                        "language": result.get("language", language),
                        "duration": result.get("duration", 0),
                        "segments": result.get("segments", []),
                        "confidence": result.get("confidence", 0.0),
                        "file_size_mb": round(file_size_mb, 2),
                        "processing_time_seconds": round(processing_time, 2)
                    }
                else:
                    raise Exception("فشل في تحويل الفيديو إلى نص - لم يتم الحصول على نص")
                    
            except Exception as e:
                # إيقاف مراقبة التقدم في حالة الخطأ
                progress_task.cancel()
                raise e
            
            # محاولة تحويل الفيديو إلى نص باستخدام Whisper مباشرة
            try:
                with open(video_path, "rb") as video_file:
                    result = await self.transcription_service.transcribe_audio(
                        audio_file=video_file,
                        language=language,
                        academy_id=academy_id
                    )
                logger.info("تم تحويل الفيديو بنجاح باستخدام Whisper المباشر")
            except Exception as whisper_error:
                logger.warning(f"فشل Whisper المباشر: {whisper_error}")
                
                # إذا فشل، جرب استخراج الصوت
                audio_path = await self._extract_audio_from_video(video_path)
                
                if audio_path and os.path.exists(audio_path):
                    try:
                        with open(audio_path, "rb") as audio_file:
                            result = await self.transcription_service.transcribe_audio(
                                audio_file=audio_file,
                                language=language,
                                academy_id=academy_id
                            )
                        # حذف ملف الصوت المؤقت
                        os.unlink(audio_path)
                        logger.info("تم تحويل الفيديو بنجاح بعد استخراج الصوت")
                    except Exception as audio_error:
                        raise Exception(f"فشل في تحويل الصوت المستخرج: {audio_error}")
                else:
                    # إذا فشل استخراج الصوت، جرب إرسال الفيديو كما هو
                    logger.info("محاولة إرسال الفيديو كما هو إلى Whisper...")
                    with open(video_path, "rb") as video_file:
                        result = await self.transcription_service.transcribe_audio(
                            audio_file=video_file,
                            language=language,
                            academy_id=academy_id
                        )
            
            # خدمة OpenAI ترجع النتيجة مباشرة بدون status
            if result and "text" in result:
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
                raise Exception("فشل في تحويل الفيديو إلى نص - لم يتم الحصول على نص")
            
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
    
    async def _extract_audio_from_video(self, video_path: str) -> Optional[str]:
        """
        استخراج الصوت من الفيديو باستخدام ffmpeg أو مكتبة Python
        """
        try:
            import tempfile
            import subprocess
            
            # محاولة استخدام ffmpeg أولاً
            try:
                # إنشاء ملف صوت مؤقت
                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                temp_audio_path = temp_audio.name
                temp_audio.close()
                
                # استخدام ffmpeg لاستخراج الصوت
                cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-vn",  # لا فيديو
                    "-acodec", "pcm_s16le",  # كودك صوت WAV
                    "-ar", "16000",  # معدل عينات 16kHz
                    "-ac", "1",  # قناة صوت واحدة (mono)
                    "-y",  # استبدال الملف إذا كان موجود
                    temp_audio_path
                ]
                
                logger.info(f"استخراج الصوت من الفيديو باستخدام ffmpeg: {' '.join(cmd)}")
                
                # تنفيذ الأمر
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 دقائق كحد أقصى
                )
                
                if result.returncode == 0 and os.path.exists(temp_audio_path):
                    logger.info(f"تم استخراج الصوت بنجاح باستخدام ffmpeg: {temp_audio_path}")
                    return temp_audio_path
                else:
                    logger.warning(f"فشل ffmpeg: {result.stderr}")
                    if os.path.exists(temp_audio_path):
                        os.unlink(temp_audio_path)
                        
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
                logger.warning(f"ffmpeg غير متاح أو فشل: {e}")
            
            # محاولة استخدام مكتبة Python كبديل
            try:
                import ffmpeg
                
                logger.info("محاولة استخراج الصوت باستخدام ffmpeg-python...")
                
                # إنشاء ملف صوت مؤقت
                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                temp_audio_path = temp_audio.name
                temp_audio.close()
                
                # استخراج الصوت باستخدام ffmpeg-python
                stream = ffmpeg.input(video_path)
                stream = ffmpeg.output(stream, temp_audio_path, acodec='pcm_s16le', ar=16000, ac=1)
                ffmpeg.run(stream, overwrite_output=True, quiet=True)
                
                if os.path.exists(temp_audio_path):
                    logger.info(f"تم استخراج الصوت بنجاح باستخدام ffmpeg-python: {temp_audio_path}")
                    return temp_audio_path
                else:
                    logger.error("فشل في إنشاء ملف الصوت")
                    
            except ImportError:
                logger.warning("ffmpeg-python غير مثبت")
            except Exception as e:
                logger.error(f"فشل ffmpeg-python: {e}")
            
            # محاولة استخدام pydub كبديل
            try:
                from pydub import AudioSegment
                
                logger.info("محاولة استخراج الصوت باستخدام pydub...")
                
                # إنشاء ملف صوت مؤقت
                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                temp_audio_path = temp_audio.name
                temp_audio.close()
                
                # استخراج الصوت باستخدام pydub
                audio = AudioSegment.from_file(video_path)
                
                if audio is not None and len(audio) > 0:
                    # تحويل الصوت إلى WAV 16kHz mono
                    audio = audio.set_frame_rate(16000).set_channels(1)
                    audio.export(temp_audio_path, format="wav")
                    
                    if os.path.exists(temp_audio_path):
                        logger.info(f"تم استخراج الصوت بنجاح باستخدام pydub: {temp_audio_path}")
                        return temp_audio_path
                else:
                    logger.error("الفيديو لا يحتوي على مسار صوتي")
                    
            except ImportError:
                logger.warning("pydub غير مثبت")
            except Exception as e:
                logger.error(f"فشل pydub: {e}")
            
            # إذا وصلنا هنا، فشلت جميع المحاولات
            logger.error("فشلت جميع محاولات استخراج الصوت")
            return None
                
        except Exception as e:
            logger.error(f"خطأ في استخراج الصوت: {e}")
            if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            return None
    
    async def _monitor_progress(self, start_time: float, file_size_mb: float):
        """
        مراقبة تقدم عملية التحويل وإرسال رسائل كل 30 ثانية
        """
        import asyncio
        import time
        
        try:
            interval = 30  # كل 30 ثانية
            message_count = 0
            
            while True:
                await asyncio.sleep(interval)
                
                elapsed_time = time.time() - start_time
                message_count += 1
                
                # رسائل مختلفة حسب الوقت المنقضي
                if elapsed_time < 60:
                    message = f"🔄 جاري معالجة الفيديو... (الوقت المنقضي: {elapsed_time:.0f} ثانية)"
                elif elapsed_time < 300:  # أقل من 5 دقائق
                    message = f"⏳ استخراج الصوت من الفيديو... (الوقت المنقضي: {elapsed_time/60:.1f} دقيقة)"
                elif elapsed_time < 600:  # أقل من 10 دقائق
                    message = f"🎬 تحويل الصوت إلى نص... (الوقت المنقضي: {elapsed_time/60:.1f} دقيقة)"
                else:
                    message = f"📝 معالجة النص النهائي... (الوقت المنقضي: {elapsed_time/60:.1f} دقيقة)"
                
                # إضافة معلومات إضافية للفيديوهات الكبيرة
                if file_size_mb > 100:
                    message += f" | حجم الفيديو: {file_size_mb:.1f}MB"
                
                logger.info(f"📊 تقدم المعالجة #{message_count}: {message}")
                
        except asyncio.CancelledError:
            logger.info("✅ تم إيقاف مراقبة التقدم - اكتملت المعالجة")
        except Exception as e:
            logger.error(f"خطأ في مراقبة التقدم: {e}")

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