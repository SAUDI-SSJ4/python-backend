"""
AI Assistant API Endpoints
==========================

Main API endpoints for AI assistant functionality.
Includes video transcription, exam correction, chat, and content generation.
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import asyncio
import uuid
import json
import logging

from app.db.session import get_db
from app.deps.auth import get_current_active_user, get_current_academy_user
from app.models.user import User
from app.models.ai_assistant import (
    VideoTranscription, ExamCorrection, LessonSummary, 
    AIConversation, AIConversationMessage, AIGeneratedContent,
    ProcessingStatus, ConversationStatus, SenderType
)
from app.schemas.ai_assistant import (
    TranscriptionRequest, TranscriptionResponse,
    ExamCorrectionRequest, ExamCorrectionResponse,
    ChatRequest, ChatResponse,
    SummaryRequest, SummaryResponse,
    ContentGenerationRequest, ContentGenerationResponse
)
from app.services.ai.openai_service import (
    OpenAITranscriptionService, OpenAIChatService, OpenAIServiceError
)
from app.core.ai_config import AIServiceFactory, ai_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Assistant"])


# --------------------------------------------------------
# UTILITY FUNCTIONS
# --------------------------------------------------------

def get_standard_error_response(message: str, error_code: str = "AI_ERROR") -> JSONResponse:
    """Create standardized error response following system pattern"""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": message,
            "error_code": error_code,
            "data": None
        }
    )


def get_standard_success_response(data: Any, message: str = "تم التنفيذ بنجاح") -> JSONResponse:
    """Create standardized success response following system pattern"""
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": message,
            "data": data
        }
    )


async def process_transcription_task(
    lesson_id: str,
    audio_file: UploadFile,
    language: str,
    academy_id: int,
    db: Session
):
    """Background task for processing video transcription"""
    transcription_id = str(uuid.uuid4())
    
    try:
        # Create initial transcription record
        transcription = VideoTranscription(
            id=transcription_id,
            lesson_id=lesson_id,
            academy_id=academy_id,
            transcription_text="",
            language=language,
            status=ProcessingStatus.PROCESSING
        )
        db.add(transcription)
        db.commit()
        
        # Process transcription
        service = AIServiceFactory.create_transcription_service()
        result = await service.transcribe_audio(
            audio_file=audio_file.file,
            language=language,
            academy_id=academy_id
        )
        
        # Update transcription record
        transcription.transcription_text = result["text"]
        transcription.confidence_score = result.get("confidence", 0.0)
        transcription.segments = result.get("segments", [])
        transcription.status = ProcessingStatus.COMPLETED
        transcription.duration_seconds = int(result.get("duration", 0))
        transcription.file_size_bytes = audio_file.size or 0
        
        db.commit()
        logger.info(f"Transcription {transcription_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Transcription {transcription_id} failed: {str(e)}")
        
        # Update status to failed
        transcription = db.query(VideoTranscription).filter(
            VideoTranscription.id == transcription_id
        ).first()
        if transcription:
            transcription.status = ProcessingStatus.FAILED
            db.commit()


# --------------------------------------------------------
# VIDEO TRANSCRIPTION ENDPOINTS
# --------------------------------------------------------

@router.post("/transcribe-video", response_model=Dict[str, Any])
async def transcribe_video(
    background_tasks: BackgroundTasks,
    lesson_id: str,
    language: str = "ar",
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_academy_user),
    db: Session = Depends(get_db)
):
    """
    Transcribe video/audio file to text using AI
    
    This endpoint accepts an audio/video file and returns transcribed text
    with timestamps and confidence scores.
    """
    try:
        # Validate service availability
        if not ai_config.is_service_available("transcription"):
            return get_standard_error_response(
                "خدمة تحويل الصوت غير متاحة حالياً",
                "SERVICE_UNAVAILABLE"
            )
        
        # Validate file type
        allowed_types = ["audio/", "video/"]
        if not any(audio_file.content_type.startswith(t) for t in allowed_types):
            return get_standard_error_response(
                "نوع الملف غير مدعوم. يرجى رفع ملف صوتي أو فيديو",
                "INVALID_FILE_TYPE"
            )
        
        # Check file size (max 25MB)
        max_size = 25 * 1024 * 1024  # 25MB in bytes
        if audio_file.size and audio_file.size > max_size:
            return get_standard_error_response(
                "حجم الملف كبير جداً. الحد الأقصى 25 ميجابايت",
                "FILE_TOO_LARGE"
            )
        
        # Validate lesson exists and user has access
        from app.models.lesson import Lesson
        from app.models.course import Course
        
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return get_standard_error_response(
                "الدرس المحدد غير موجود",
                "LESSON_NOT_FOUND"
            )
        
        course = db.query(Course).filter(Course.id == lesson.course_id).first()
        if not course or course.academy_id != current_user.academy_id:
            return get_standard_error_response(
                "ليس لديك صلاحية للوصول إلى هذا الدرس",
                "ACCESS_DENIED"
            )
        
        # Check if transcription already exists
        existing = db.query(VideoTranscription).filter(
            VideoTranscription.lesson_id == lesson_id
        ).first()
        
        if existing:
            if existing.status == ProcessingStatus.PROCESSING:
                return get_standard_success_response(
                    {
                        "transcription_id": existing.id,
                        "status": "processing",
                        "message": "التحويل قيد المعالجة"
                    },
                    "التحويل قيد المعالجة بالفعل"
                )
            elif existing.status == ProcessingStatus.COMPLETED:
                return get_standard_success_response(
                    {
                        "transcription_id": existing.id,
                        "text": existing.transcription_text,
                        "language": existing.language,
                        "confidence_score": float(existing.confidence_score),
                        "segments": existing.segments,
                        "status": "completed"
                    },
                    "تم العثور على تحويل موجود"
                )
        
        # Start background transcription task
        transcription_id = str(uuid.uuid4())
        background_tasks.add_task(
            process_transcription_task,
            lesson_id,
            audio_file,
            language,
            current_user.academy_id,
            db
        )
        
        return get_standard_success_response(
            {
                "transcription_id": transcription_id,
                "status": "processing",
                "estimated_time": "5-10 دقائق"
            },
            "بدأ تحويل الملف الصوتي. ستتلقى النتيجة قريباً"
        )
        
    except OpenAIServiceError as e:
        logger.error(f"OpenAI service error: {str(e)}")
        return get_standard_error_response(
            f"خطأ في خدمة الذكاء الاصطناعي: {e.message}",
            e.error_code or "AI_SERVICE_ERROR"
        )
    except Exception as e:
        logger.error(f"Transcription endpoint error: {str(e)}")
        return get_standard_error_response(
            "حدث خطأ أثناء معالجة الطلب",
            "INTERNAL_ERROR"
        )


@router.get("/transcription/{transcription_id}", response_model=Dict[str, Any])
async def get_transcription(
    transcription_id: str,
    current_user: User = Depends(get_current_academy_user),
    db: Session = Depends(get_db)
):
    """Get transcription results by ID"""
    try:
        transcription = db.query(VideoTranscription).filter(
            VideoTranscription.id == transcription_id
        ).first()
        
        if not transcription:
            return get_standard_error_response(
                "التحويل المطلوب غير موجود",
                "TRANSCRIPTION_NOT_FOUND"
            )
        
        # Check access permissions
        if transcription.academy_id != current_user.academy_id:
            return get_standard_error_response(
                "ليس لديك صلاحية للوصول إلى هذا التحويل",
                "ACCESS_DENIED"
            )
        
        response_data = {
            "transcription_id": transcription.id,
            "lesson_id": transcription.lesson_id,
            "status": transcription.status.value,
            "language": transcription.language,
            "created_at": transcription.created_at.isoformat()
        }
        
        if transcription.status == ProcessingStatus.COMPLETED:
            response_data.update({
                "text": transcription.transcription_text,
                "confidence_score": float(transcription.confidence_score),
                "segments": transcription.segments,
                "duration_seconds": transcription.duration_seconds,
                "file_size_bytes": transcription.file_size_bytes
            })
        elif transcription.status == ProcessingStatus.FAILED:
            response_data["error"] = "فشل في تحويل الملف"
        
        return get_standard_success_response(
            response_data,
            "تم جلب بيانات التحويل بنجاح"
        )
        
    except Exception as e:
        logger.error(f"Get transcription error: {str(e)}")
        return get_standard_error_response(
            "حدث خطأ أثناء جلب بيانات التحويل",
            "INTERNAL_ERROR"
        )


# --------------------------------------------------------
# EXAM CORRECTION ENDPOINTS  
# --------------------------------------------------------

@router.post("/correct-exam", response_model=Dict[str, Any])
async def correct_exam(
    exam_id: str,
    student_answers: List[Dict[str, Any]],
    current_user: User = Depends(get_current_academy_user),
    db: Session = Depends(get_db)
):
    """
    Automatically correct exam and provide AI feedback
    
    This endpoint processes student answers and provides intelligent
    feedback, scoring, and study recommendations.
    """
    try:
        # Validate service availability
        if not ai_config.is_service_available("chat"):
            return get_standard_error_response(
                "خدمة تصحيح الامتحانات غير متاحة حالياً",
                "SERVICE_UNAVAILABLE"
            )
        
        # Validate exam exists and get questions
        from app.models.exam import Exam
        from app.models.question import Question
        
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            return get_standard_error_response(
                "الامتحان المحدد غير موجود",
                "EXAM_NOT_FOUND"
            )
        
        # Get exam questions and correct answers
        questions = db.query(Question).filter(Question.exam_id == exam_id).all()
        if not questions:
            return get_standard_error_response(
                "لا توجد أسئلة في هذا الامتحان",
                "NO_QUESTIONS_FOUND"
            )
        
        # Prepare exam data for AI analysis
        exam_data = {
            "title": exam.title,
            "questions": [
                {
                    "id": q.id,
                    "title": q.title,
                    "type": q.type,
                    "correct_answer": q.correct_answer,
                    "score": q.score
                }
                for q in questions
            ]
        }
        
        # Generate AI feedback
        service = AIServiceFactory.create_chat_service()
        feedback_result = await service.generate_exam_feedback(
            exam_data=exam_data,
            student_answers=student_answers,
            academy_id=current_user.academy_id
        )
        
        # Calculate scores
        total_score = 0
        max_score = sum(q.score for q in questions)
        
        # Process individual answers (simplified scoring)
        for answer in student_answers:
            question = next((q for q in questions if q.id == answer.get("question_id")), None)
            if question and answer.get("answer") == question.correct_answer:
                total_score += question.score
        
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        # Create correction record
        correction_id = str(uuid.uuid4())
        correction = ExamCorrection(
            id=correction_id,
            exam_id=exam_id,
            student_id=current_user.id,  # Assuming current user is student
            academy_id=current_user.academy_id,
            submission_data={"answers": student_answers},
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            ai_feedback=feedback_result.get("content", "")
        )
        
        db.add(correction)
        db.commit()
        
        return get_standard_success_response(
            {
                "correction_id": correction_id,
                "total_score": total_score,
                "max_score": max_score,
                "percentage": round(percentage, 2),
                "feedback": feedback_result.get("content", ""),
                "grade": "ممتاز" if percentage >= 90 else "جيد جداً" if percentage >= 80 else "جيد" if percentage >= 70 else "مقبول" if percentage >= 60 else "ضعيف"
            },
            "تم تصحيح الامتحان بنجاح"
        )
        
    except OpenAIServiceError as e:
        logger.error(f"OpenAI service error in exam correction: {str(e)}")
        return get_standard_error_response(
            f"خطأ في خدمة الذكاء الاصطناعي: {e.message}",
            e.error_code or "AI_SERVICE_ERROR"
        )
    except Exception as e:
        logger.error(f"Exam correction error: {str(e)}")
        return get_standard_error_response(
            "حدث خطأ أثناء تصحيح الامتحان",
            "INTERNAL_ERROR"
        )


# --------------------------------------------------------
# CHAT/Q&A ENDPOINTS
# --------------------------------------------------------

@router.post("/chat", response_model=Dict[str, Any])
async def chat_with_ai(
    message: str,
    context_type: str = "general",
    context_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Chat with AI assistant for questions and support
    
    This endpoint provides intelligent responses to user questions
    with context awareness for lessons, exams, and courses.
    """
    try:
        # Validate service availability
        if not ai_config.is_service_available("chat"):
            return get_standard_error_response(
                "خدمة المحادثة غير متاحة حالياً",
                "SERVICE_UNAVAILABLE"
            )
        
        # Get or create conversation
        conversation = None
        if conversation_id:
            conversation = db.query(AIConversation).filter(
                AIConversation.id == conversation_id,
                AIConversation.user_id == current_user.id
            ).first()
        
        if not conversation:
            conversation = AIConversation(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                academy_id=getattr(current_user, 'academy_id', None),
                context_type=context_type,
                context_id=context_id,
                status=ConversationStatus.ACTIVE
            )
            db.add(conversation)
            db.commit()
        
        # Add user message
        user_message = AIConversationMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            sender_type=SenderType.USER,
            message=message
        )
        db.add(user_message)
        
        # Generate AI response
        service = AIServiceFactory.create_chat_service()
        
        # Prepare context-aware system prompt
        system_prompt = """أنت مساعد تعليمي ذكي لمنصة سيان. مهمتك مساعدة الطلاب والأساتذة 
        بالإجابة على أسئلتهم التعليمية وتقديم الدعم المناسب. كن مفيداً ومهذباً ودقيقاً في إجاباتك."""
        
        # Get conversation history for context
        previous_messages = db.query(AIConversationMessage).filter(
            AIConversationMessage.conversation_id == conversation.id
        ).order_by(AIConversationMessage.created_at.desc()).limit(10).all()
        
        chat_messages = []
        for msg in reversed(previous_messages[-5:]):  # Last 5 messages for context
            chat_messages.append({
                "role": "user" if msg.sender_type == SenderType.USER else "assistant",
                "content": msg.message
            })
        
        chat_messages.append({"role": "user", "content": message})
        
        ai_response = await service.generate_completion(
            messages=chat_messages,
            system_prompt=system_prompt,
            academy_id=getattr(current_user, 'academy_id', None)
        )
        
        # Add AI response message
        ai_message = AIConversationMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            sender_type=SenderType.AI,
            message=ai_response["content"],
            ai_model_used=ai_response.get("model", "gpt-4"),
            processing_time_ms=ai_response.get("processing_time_ms", 0)
        )
        db.add(ai_message)
        db.commit()
        
        return get_standard_success_response(
            {
                "conversation_id": conversation.id,
                "message_id": ai_message.id,
                "response": ai_response["content"],
                "usage": ai_response.get("usage", {})
            },
            "تم الحصول على الرد بنجاح"
        )
        
    except OpenAIServiceError as e:
        logger.error(f"OpenAI service error in chat: {str(e)}")
        return get_standard_error_response(
            f"خطأ في خدمة الذكاء الاصطناعي: {e.message}",
            e.error_code or "AI_SERVICE_ERROR"
        )
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        return get_standard_error_response(
            "حدث خطأ أثناء معالجة المحادثة",
            "INTERNAL_ERROR"
        )


# --------------------------------------------------------
# STATUS AND HEALTH ENDPOINTS
# --------------------------------------------------------

@router.get("/status", response_model=Dict[str, Any])
async def get_ai_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get AI services status and availability"""
    try:
        available_services = ai_config.get_available_services()
        
        return get_standard_success_response(
            {
                "services": available_services,
                "total_services": len(available_services),
                "system_status": "operational" if available_services else "limited"
            },
            "تم جلب حالة الخدمات بنجاح"
        )
        
    except Exception as e:
        logger.error(f"Status endpoint error: {str(e)}")
        return get_standard_error_response(
            "حدث خطأ أثناء جلب حالة الخدمات",
            "INTERNAL_ERROR"
        ) 