"""
اختبار الاتصال مع OpenAI API
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging
import os
import time

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user
from app.core.config import settings
from app.services.ai.openai_service import OpenAITranscriptionService, OpenAIChatService
from app.core.ai_config import AIServiceConfig, AIProvider, AIServiceType
from app.core.response_handler import SayanSuccessResponse, SayanErrorResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/test-openai-connection")
async def test_openai_connection(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    اختبار الاتصال مع OpenAI API (يتطلب مصادقة)
    """
    try:
        # التحقق من وجود مفتاح API
        if not settings.OPENAI_API_KEY:
            return SayanErrorResponse(
                message="مفتاح OpenAI API غير مُعد",
                error_type="OPENAI_API_KEY_MISSING",
                status_code=400
            )
        
        # إنشاء إعدادات الخدمة
        config = AIServiceConfig(
            provider=AIProvider.OPENAI,
            service_type=AIServiceType.CHAT_COMPLETION,
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_MODEL,
            max_tokens=100,
            temperature=0.7,
            rate_limit_per_minute=40
        )
        
        # إنشاء خدمة المحادثة
        chat_service = OpenAIChatService(config)
        
        # رسالة اختبار بسيطة
        test_messages = [
            {"role": "user", "content": "قل مرحباً باللغة العربية فقط"}
        ]
        
        # استدعاء OpenAI API
        logger.info("جاري اختبار الاتصال مع OpenAI API...")
        
        result = await chat_service.generate_completion(
            messages=test_messages,
            academy_id=current_user.academy.id
        )
        
        if result and "content" in result:
            return SayanSuccessResponse(
                data={
                    "message": "تم الاتصال بنجاح مع OpenAI API",
                    "response": result.get("content", ""),
                    "model_used": settings.OPENAI_MODEL,
                    "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                    "processing_time_ms": 0,  # سيتم حسابها من قاعدة البيانات
                    "finish_reason": result.get("finish_reason", "unknown"),
                    "usage_details": result.get("usage", {})
                },
                message="تم اختبار الاتصال بنجاح"
            )
        else:
            return SayanErrorResponse(
                message=f"فشل في الاتصال مع OpenAI API: {result}",
                error_type="OPENAI_API_ERROR",
                status_code=500
            )
            
    except Exception as e:
        logger.error(f"خطأ في اختبار OpenAI API: {str(e)}")
        return SayanErrorResponse(
            message=f"حدث خطأ في اختبار الاتصال: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )


@router.post("/test-openai-connection-public")
async def test_openai_connection_public() -> Any:
    """
    اختبار الاتصال مع OpenAI API (بدون مصادقة)
    """
    try:
        # التحقق من وجود مفتاح API
        if not settings.OPENAI_API_KEY:
            return SayanErrorResponse(
                message="مفتاح OpenAI API غير مُعد",
                error_type="OPENAI_API_KEY_MISSING",
                status_code=400
            )
        
        # إنشاء إعدادات الخدمة
        config = AIServiceConfig(
            provider=AIProvider.OPENAI,
            service_type=AIServiceType.CHAT_COMPLETION,
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_MODEL,
            max_tokens=100,
            temperature=0.7,
            rate_limit_per_minute=40
        )
        
        # إنشاء خدمة المحادثة
        chat_service = OpenAIChatService(config)
        
        # رسالة اختبار بسيطة
        test_messages = [
            {"role": "user", "content": "قل مرحباً باللغة العربية فقط"}
        ]
        
        # استدعاء OpenAI API
        logger.info("جاري اختبار الاتصال مع OpenAI API...")
        
        result = await chat_service.generate_completion(
            messages=test_messages,
            academy_id=1  # قيمة افتراضية للاختبار العام
        )
        
        if result and "content" in result:
            return SayanSuccessResponse(
                data={
                    "message": "تم الاتصال بنجاح مع OpenAI API",
                    "response": result.get("content", ""),
                    "model_used": settings.OPENAI_MODEL,
                    "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                    "processing_time_ms": 0,
                    "finish_reason": result.get("finish_reason", "unknown"),
                    "usage_details": result.get("usage", {}),
                    "note": "هذا endpoint عام ولا يتطلب مصادقة"
                },
                message="تم اختبار الاتصال بنجاح"
            )
        else:
            return SayanErrorResponse(
                message=f"فشل في الاتصال مع OpenAI API: {result}",
                error_type="OPENAI_API_ERROR",
                status_code=500
            )
            
    except Exception as e:
        logger.error(f"خطأ في اختبار OpenAI API: {str(e)}")
        return SayanErrorResponse(
            message=f"حدث خطأ في اختبار الاتصال: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )


@router.get("/openai-status")
async def get_openai_status(
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    الحصول على حالة إعدادات OpenAI (يتطلب مصادقة)
    """
    try:
        status_info = {
            "api_key_configured": bool(settings.OPENAI_API_KEY),
            "api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
            "model": settings.OPENAI_MODEL,
            "max_tokens": settings.OPENAI_MAX_TOKENS,
            "temperature": settings.OPENAI_TEMPERATURE,
            "rate_limit": settings.OPENAI_RATE_LIMIT,
            "ai_transcription_enabled": settings.AI_TRANSCRIPTION_ENABLED,
            "ai_chat_enabled": settings.AI_CHAT_ENABLED,
            "ai_exam_correction_enabled": settings.AI_EXAM_CORRECTION_ENABLED,
            "ai_question_generation_enabled": settings.AI_QUESTION_GENERATION_ENABLED,
            "ai_summarization_enabled": settings.AI_SUMMARIZATION_ENABLED
        }
        
        return SayanSuccessResponse(
            data=status_info,
            message="تم جلب حالة OpenAI بنجاح"
        )
        
    except Exception as e:
        logger.error(f"خطأ في جلب حالة OpenAI: {str(e)}")
        return SayanErrorResponse(
            message=f"حدث خطأ في جلب الحالة: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )


@router.get("/openai-status-public")
async def get_openai_status_public() -> Any:
    """
    الحصول على حالة إعدادات OpenAI (بدون مصادقة)
    """
    try:
        status_info = {
            "api_key_configured": bool(settings.OPENAI_API_KEY),
            "api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
            "model": settings.OPENAI_MODEL,
            "max_tokens": settings.OPENAI_MAX_TOKENS,
            "temperature": settings.OPENAI_TEMPERATURE,
            "rate_limit": settings.OPENAI_RATE_LIMIT,
            "ai_transcription_enabled": settings.AI_TRANSCRIPTION_ENABLED,
            "ai_chat_enabled": settings.AI_CHAT_ENABLED,
            "ai_exam_correction_enabled": settings.AI_EXAM_CORRECTION_ENABLED,
            "ai_question_generation_enabled": settings.AI_QUESTION_GENERATION_ENABLED,
            "ai_summarization_enabled": settings.AI_SUMMARIZATION_ENABLED,
            "note": "هذا endpoint عام ولا يتطلب مصادقة"
        }
        
        return SayanSuccessResponse(
            data=status_info,
            message="تم جلب حالة OpenAI بنجاح"
        )
        
    except Exception as e:
        logger.error(f"خطأ في جلب حالة OpenAI: {str(e)}")
        return SayanErrorResponse(
            message=f"حدث خطأ في جلب الحالة: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )


@router.post("/test-whisper-transcription")
async def test_whisper_transcription(
    text: str = "مرحباً، هذا اختبار لخدمة Whisper",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """
    اختبار خدمة Whisper (تحويل النص إلى صوت ثم تحويله مرة أخرى)
    ملاحظة: هذا اختبار نظري لأننا لا نستطيع إنشاء ملف صوتي هنا
    """
    try:
        # التحقق من وجود مفتاح API
        if not settings.OPENAI_API_KEY:
            return SayanErrorResponse(
                message="مفتاح OpenAI API غير مُعد",
                error_type="OPENAI_API_KEY_MISSING",
                status_code=400
            )
        
        # إنشاء إعدادات خدمة Whisper
        config = AIServiceConfig(
            provider=AIProvider.OPENAI,
            service_type=AIServiceType.TRANSCRIPTION,
            api_key=settings.OPENAI_API_KEY,
            model_name="whisper-1",
            rate_limit_per_minute=40
        )
        
        # إنشاء خدمة التحويل
        transcription_service = OpenAITranscriptionService(config)
        
        return SayanSuccessResponse(
            data={
                "message": "خدمة Whisper مُعدة بنجاح",
                "test_text": text,
                "model": "whisper-1",
                "note": "لا يمكن اختبار التحويل الفعلي بدون ملف صوتي",
                "service_ready": True
            },
            message="تم اختبار إعدادات Whisper بنجاح"
        )
        
    except Exception as e:
        logger.error(f"خطأ في اختبار Whisper: {str(e)}")
        return SayanErrorResponse(
            message=f"حدث خطأ في اختبار Whisper: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )


@router.get("/test-video-transcription")
async def test_video_transcription():
    """
    اختبار تحويل الفيديو إلى نص
    """
    try:
        from app.services.video_processing import VideoProcessingService
        from app.core.config import settings
        
        # تهيئة الخدمة
        video_service = VideoProcessingService()
        
        if not video_service.transcription_service:
            return {
                "status": "error",
                "message": "خدمة تحويل الفيديو غير متاحة",
                "details": {
                    "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                    "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                    "transcription_service_initialized": False
                }
            }
        
        # اختبار ملف فيديو صغير (إذا كان موجود)
        test_video_path = "static/uploads/test_video.mp4"
        
        if not os.path.exists(test_video_path):
            return {
                "status": "success",
                "message": "خدمة تحويل الفيديو جاهزة للاستخدام",
                "details": {
                    "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                    "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                    "transcription_service_initialized": True,
                    "test_video_exists": False,
                    "note": "يمكنك رفع فيديو للاختبار"
                }
            }
        
        # اختبار التحويل
        result = await video_service.transcribe_video_with_whisper(
            video_path=test_video_path,
            language="ar"
        )
        
        return {
            "status": "success",
            "message": "تم اختبار تحويل الفيديو بنجاح",
            "transcription_result": result,
            "details": {
                "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                "transcription_service_initialized": True,
                "test_video_exists": True
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"خطأ في اختبار تحويل الفيديو: {str(e)}",
            "details": {
                "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        } 


@router.post("/test-video-transcription-file")
async def test_video_transcription_file(
    video_file: UploadFile = File(...)
):
    """
    اختبار تحويل فيديو محدد إلى نص
    """
    try:
        from app.services.video_processing import VideoProcessingService
        from app.core.config import settings
        import tempfile
        import os
        
        # تهيئة الخدمة
        video_service = VideoProcessingService()
        
        if not video_service.transcription_service:
            return {
                "status": "error",
                "message": "خدمة تحويل الفيديو غير متاحة",
                "details": {
                    "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                    "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                    "transcription_service_initialized": False
                }
            }
        
        # حفظ الملف مؤقتاً
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            content = await video_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # التحقق من صحة الملف
            validation_result = video_service.validate_video_file(temp_file_path)
            
            if not validation_result.get("valid", False):
                return {
                    "status": "error",
                    "message": f"ملف الفيديو غير صالح: {validation_result.get('error', 'خطأ غير معروف')}",
                    "validation_details": validation_result
                }
            
            # تحويل الفيديو إلى نص
            result = await video_service.transcribe_video_with_whisper(
                video_path=temp_file_path,
                language="ar"
            )
            
            return {
                "status": "success",
                "message": "تم اختبار تحويل الفيديو بنجاح",
                "transcription_result": result,
                "validation_details": validation_result,
                "details": {
                    "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                    "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                    "transcription_service_initialized": True,
                    "file_size_mb": validation_result.get("file_size_mb", 0),
                    "file_extension": validation_result.get("file_extension", ""),
                    "processing_time_seconds": 0
                }
            }
            
        finally:
            # حذف الملف المؤقت
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"خطأ في اختبار تحويل الفيديو: {str(e)}",
            "details": {
                "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        } 


@router.get("/test-video-transcription-existing/{lesson_id}")
async def test_video_transcription_existing(
    lesson_id: str,
    db: Session = Depends(get_db)
):
    """
    اختبار تحويل فيديو موجود في النظام
    """
    try:
        from app.services.video_processing import VideoProcessingService
        from app.core.config import settings
        from app.models.lesson import Lesson
        from app.models.video import Video as VideoModel
        
        # البحث عن الدرس
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return {
                "status": "error",
                "message": "الدرس غير موجود",
                "lesson_id": lesson_id
            }
        
        # البحث عن الفيديو المرتبط بالدرس
        video = db.query(VideoModel).filter(VideoModel.lesson_id == lesson_id).first()
        if not video:
            return {
                "status": "error",
                "message": "لا يوجد فيديو مرتبط بهذا الدرس",
                "lesson_id": lesson_id,
                "lesson_title": lesson.title
            }
        
        # تهيئة الخدمة
        video_service = VideoProcessingService()
        
        if not video_service.transcription_service:
            return {
                "status": "error",
                "message": "خدمة تحويل الفيديو غير متاحة",
                "details": {
                    "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                    "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                    "transcription_service_initialized": False
                }
            }
        
        # بناء مسار الفيديو
        video_path = f"static/uploads/{video.video}"
        
        if not os.path.exists(video_path):
            return {
                "status": "error",
                "message": "ملف الفيديو غير موجود في النظام",
                "video_path": video_path,
                "lesson_id": lesson_id,
                "lesson_title": lesson.title
            }
        
        # التحقق من صحة الملف
        validation_result = video_service.validate_video_file(video_path)
        
        if not validation_result.get("valid", False):
            return {
                "status": "error",
                "message": f"ملف الفيديو غير صالح: {validation_result.get('error', 'خطأ غير معروف')}",
                "validation_details": validation_result,
                "lesson_id": lesson_id,
                "lesson_title": lesson.title
            }
        
        # تحويل الفيديو إلى نص
        result = await video_service.transcribe_video_with_whisper(
            video_path=video_path,
            language="ar"
        )
        
        return {
            "status": "success",
            "message": "تم اختبار تحويل الفيديو بنجاح",
            "transcription_result": result,
            "validation_details": validation_result,
            "lesson_info": {
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "lesson_type": lesson.type,
                "video_id": video.id,
                "video_path": video.video,
                "video_size_bytes": video.file_size,
                "video_duration": video.duration
            },
            "details": {
                "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                "transcription_service_initialized": True,
                "file_size_mb": validation_result.get("file_size_mb", 0),
                "file_extension": validation_result.get("file_extension", ""),
                "processing_time_seconds": 0
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"خطأ في اختبار تحويل الفيديو: {str(e)}",
            "details": {
                "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "lesson_id": lesson_id if 'lesson_id' in locals() else None
            }
        } 


@router.get("/test-audio-extraction/{lesson_id}")
async def test_audio_extraction(
    lesson_id: str,
    db: Session = Depends(get_db)
):
    """
    اختبار استخراج الصوت من فيديو موجود
    """
    try:
        from app.services.video_processing import VideoProcessingService
        from app.core.config import settings
        from app.models.lesson import Lesson
        from app.models.video import Video as VideoModel
        
        # البحث عن الدرس
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return {
                "status": "error",
                "message": "الدرس غير موجود",
                "lesson_id": lesson_id
            }
        
        # البحث عن الفيديو المرتبط بالدرس
        video = db.query(VideoModel).filter(VideoModel.lesson_id == lesson_id).first()
        if not video:
            return {
                "status": "error",
                "message": "لا يوجد فيديو مرتبط بهذا الدرس",
                "lesson_id": lesson_id,
                "lesson_title": lesson.title
            }
        
        # بناء مسار الفيديو
        video_path = f"static/uploads/{video.video}"
        
        if not os.path.exists(video_path):
            return {
                "status": "error",
                "message": "ملف الفيديو غير موجود في النظام",
                "video_path": video_path,
                "lesson_id": lesson_id,
                "lesson_title": lesson.title
            }
        
        # تهيئة الخدمة
        video_service = VideoProcessingService()
        
        # اختبار استخراج الصوت
        audio_path = await video_service._extract_audio_from_video(video_path)
        
        if audio_path and os.path.exists(audio_path):
            # الحصول على معلومات ملف الصوت
            audio_size = os.path.getsize(audio_path)
            
            result = {
                "status": "success",
                "message": "تم استخراج الصوت بنجاح",
                "audio_info": {
                    "audio_path": audio_path,
                    "audio_size_bytes": audio_size,
                    "audio_size_mb": round(audio_size / (1024 * 1024), 2),
                    "audio_format": "WAV",
                    "sample_rate": "16kHz",
                    "channels": "mono"
                },
                "video_info": {
                    "video_path": video_path,
                    "video_size_bytes": video.file_size,
                    "video_size_mb": round(video.file_size / (1024 * 1024), 2),
                    "video_duration": video.duration
                },
                "lesson_info": {
                    "lesson_id": lesson.id,
                    "lesson_title": lesson.title,
                    "lesson_type": lesson.type
                }
            }
            
            # حذف ملف الصوت المؤقت
            os.unlink(audio_path)
            
            return result
        else:
            return {
                "status": "error",
                "message": "فشل في استخراج الصوت من الفيديو",
                "video_path": video_path,
                "lesson_id": lesson_id,
                "lesson_title": lesson.title,
                "details": {
                    "ffmpeg_available": "تحقق من تثبيت ffmpeg",
                    "video_has_audio": "تحقق من وجود مسار صوتي في الفيديو"
                }
            }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"خطأ في اختبار استخراج الصوت: {str(e)}",
            "details": {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "lesson_id": lesson_id if 'lesson_id' in locals() else None
            }
        } 


@router.get("/test-video-info/{lesson_id}")
async def test_video_info(
    lesson_id: str,
    db: Session = Depends(get_db)
):
    """
    فحص معلومات الفيديو
    """
    try:
        from app.models.lesson import Lesson
        from app.models.video import Video as VideoModel
        import os
        
        # البحث عن الدرس
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return {
                "status": "error",
                "message": "الدرس غير موجود",
                "lesson_id": lesson_id
            }
        
        # البحث عن الفيديو المرتبط بالدرس
        video = db.query(VideoModel).filter(VideoModel.lesson_id == lesson_id).first()
        if not video:
            return {
                "status": "error",
                "message": "لا يوجد فيديو مرتبط بهذا الدرس",
                "lesson_id": lesson_id,
                "lesson_title": lesson.title
            }
        
        # بناء مسار الفيديو
        video_path = f"static/uploads/{video.video}"
        
        if not os.path.exists(video_path):
            return {
                "status": "error",
                "message": "ملف الفيديو غير موجود في النظام",
                "video_path": video_path,
                "lesson_id": lesson_id,
                "lesson_title": lesson.title
            }
        
        # فحص معلومات الملف
        file_size = os.path.getsize(video_path)
        file_stats = os.stat(video_path)
        
        # محاولة فحص معلومات الفيديو باستخدام moviepy
        video_info = {
            "file_exists": True,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "file_extension": os.path.splitext(video_path)[1].lower(),
            "created_time": file_stats.st_ctime,
            "modified_time": file_stats.st_mtime,
            "has_audio": False,
            "duration": 0,
            "fps": 0,
            "resolution": "unknown"
        }
        
        try:
            from pydub import AudioSegment
            
            # فحص معلومات الفيديو باستخدام pydub
            audio = AudioSegment.from_file(video_path)
            
            video_info.update({
                "has_audio": len(audio) > 0,
                "duration": len(audio) / 1000.0,  # تحويل من milliseconds إلى seconds
                "audio_fps": audio.frame_rate,
                "audio_channels": audio.channels,
                "audio_sample_width": audio.sample_width
            })
            
        except ImportError as e:
            video_info["pydub_error"] = f"مكتبة pydub غير متاحة: {str(e)}"
            video_info["note"] = "يمكن استخدام ffmpeg لاستخراج الصوت"
        except Exception as e:
            video_info["pydub_error"] = str(e)
            video_info["note"] = "فشل في قراءة معلومات الفيديو"
        
        return {
            "status": "success",
            "message": "تم فحص معلومات الفيديو بنجاح",
            "video_info": video_info,
            "lesson_info": {
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "lesson_type": lesson.type
            },
            "database_info": {
                "video_id": video.id,
                "video_title": video.title,
                "video_duration_db": video.duration,
                "video_size_db": video.file_size,
                "video_format_db": video.format
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"خطأ في فحص معلومات الفيديو: {str(e)}",
            "details": {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "lesson_id": lesson_id if 'lesson_id' in locals() else None
            }
        } 


@router.get("/test-video-transcription-enhanced/{lesson_id}")
async def test_video_transcription_enhanced(
    lesson_id: str,
    db: Session = Depends(get_db)
):
    """
    اختبار محسن لتحويل فيديو موجود في النظام
    """
    try:
        from app.services.video_processing import VideoProcessingService
        from app.core.config import settings
        from app.models.lesson import Lesson
        from app.models.video import Video as VideoModel
        
        # البحث عن الدرس
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return {
                "status": "error",
                "message": "الدرس غير موجود",
                "lesson_id": lesson_id
            }
        
        # البحث عن الفيديو المرتبط بالدرس
        video = db.query(VideoModel).filter(VideoModel.lesson_id == lesson_id).first()
        if not video:
            return {
                "status": "error",
                "message": "لا يوجد فيديو مرتبط بهذا الدرس",
                "lesson_id": lesson_id,
                "lesson_title": lesson.title
            }
        
        # بناء مسار الفيديو
        video_path = f"static/uploads/{video.video}"
        
        if not os.path.exists(video_path):
            return {
                "status": "error",
                "message": "ملف الفيديو غير موجود في النظام",
                "video_path": video_path,
                "lesson_id": lesson_id,
                "lesson_title": lesson.title
            }
        
        # تهيئة الخدمة
        video_service = VideoProcessingService()
        
        if not video_service.transcription_service:
            return {
                "status": "error",
                "message": "خدمة تحويل الفيديو غير متاحة",
                "details": {
                    "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                    "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                    "transcription_service_initialized": False
                }
            }
        
        # التحقق من صحة الملف
        validation_result = video_service.validate_video_file(video_path)
        
        if not validation_result.get("valid", False):
            return {
                "status": "error",
                "message": f"ملف الفيديو غير صالح: {validation_result.get('error', 'خطأ غير معروف')}",
                "validation_details": validation_result,
                "lesson_id": lesson_id,
                "lesson_title": lesson.title
            }
        
        # تحويل الفيديو إلى نص مع معالجة محسنة
        start_time = time.time()
        result = await video_service.transcribe_video_with_whisper(
            video_path=video_path,
            language="ar"
        )
        processing_time = time.time() - start_time
        
        return {
            "status": "success",
            "message": "تم اختبار تحويل الفيديو بنجاح",
            "transcription_result": result,
            "validation_details": validation_result,
            "lesson_info": {
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "lesson_type": lesson.type,
                "video_id": video.id,
                "video_path": video.video,
                "video_size_bytes": video.file_size,
                "video_duration": video.duration
            },
            "processing_info": {
                "processing_time_seconds": round(processing_time, 2),
                "file_size_mb": validation_result.get("file_size_mb", 0),
                "file_extension": validation_result.get("file_extension", ""),
                "method_used": "whisper_direct" if result.get("status") == "success" else "unknown"
            },
            "system_info": {
                "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                "transcription_service_initialized": True,
                "ffmpeg_available": False,  # سيتم تحديثه لاحقاً
                "pydub_available": True
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"خطأ في اختبار تحويل الفيديو: {str(e)}",
            "details": {
                "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
                "openai_api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "lesson_id": lesson_id if 'lesson_id' in locals() else None,
                "suggestions": [
                    "تأكد من أن الفيديو يحتوي على صوت",
                    "تحقق من صيغة الفيديو",
                    "جرب فيديو آخر للاختبار"
                ]
            }
        } 