"""
AI API Endpoints for SAYAN Academy Platform
==========================================

This module provides REST API endpoints for AI functionality.
All endpoints follow the system's response pattern and include proper error handling.

Educational Notes:
- Uses FastAPI best practices for API design
- Implements proper request/response validation
- Maintains consistent error handling patterns
- Includes authentication and authorization checks
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.deps.database import get_db
from app.deps.auth import get_current_user
from app.services.ai_service import AIService
from app.models.ai_assistant import AIAnswerType, ConversationType, SenderType
from app.models.user import User


# Create router
router = APIRouter(prefix="/ai", tags=["AI Assistant"])


# ========================================
# REQUEST/RESPONSE MODELS
# ========================================

class AIQuestionRequest(BaseModel):
    """Request model for AI question"""
    lesson_id: str = Field(..., description="Lesson ID")
    question: str = Field(..., min_length=5, max_length=1000, description="Question text")
    answer_type: AIAnswerType = Field(default=AIAnswerType.QUESTION, description="Type of answer")


class AIQuestionResponse(BaseModel):
    """Response model for AI question"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ConversationRequest(BaseModel):
    """Request model for creating conversation"""
    conversation_type: ConversationType = Field(..., description="Type of conversation")
    context_id: Optional[str] = Field(None, description="Context ID (lesson, exam, etc.)")
    title: Optional[str] = Field(None, description="Conversation title")


class MessageRequest(BaseModel):
    """Request model for adding message to conversation"""
    message: str = Field(..., min_length=1, max_length=2000, description="Message content")


class TranscriptionRequest(BaseModel):
    """Request model for video transcription"""
    lesson_id: str = Field(..., description="Lesson ID")
    video_id: str = Field(..., description="Video ID")
    video_file_path: str = Field(..., description="Path to video file")


class ExamCorrectionRequest(BaseModel):
    """Request model for exam correction"""
    exam_id: str = Field(..., description="Exam ID")
    student_answers: List[Dict[str, Any]] = Field(..., description="Student answers")


# ========================================
# AI ANSWERS ENDPOINTS
# ========================================

@router.post("/questions/ask", response_model=AIQuestionResponse)
async def ask_ai_question(
    request: AIQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ask AI a question about a lesson.
    
    This endpoint allows students to ask questions about lesson content
    and receive AI-generated answers with confidence scores.
    """
    try:
        # Initialize AI service
        ai_service = AIService(db)
        
        # Get academy ID if user is a student
        academy_id = None
        student_id = None
        
        if current_user.user_type == "student" and current_user.student_profile:
            student_id = current_user.student_profile.id
            # Get academy from lesson context (you'd implement this logic)
            # academy_id = get_academy_from_lesson(request.lesson_id)
        
        # Create AI answer
        result = ai_service.create_ai_answer(
            lesson_id=request.lesson_id,
            question=request.question,
            student_id=student_id,
            academy_id=academy_id,
            answer_type=request.answer_type
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return AIQuestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ في معالجة السؤال"
        )


@router.get("/questions/lesson/{lesson_id}", response_model=AIQuestionResponse)
async def get_lesson_questions(
    lesson_id: str,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get AI questions and answers for a specific lesson.
    
    This endpoint retrieves previous AI answers for a lesson
    with pagination support.
    """
    try:
        ai_service = AIService(db)
        
        result = ai_service.get_lesson_ai_answers(
            lesson_id=lesson_id,
            limit=limit,
            offset=offset
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return AIQuestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ في جلب الأسئلة"
        )


# ========================================
# CONVERSATION ENDPOINTS
# ========================================

@router.post("/conversations", response_model=AIQuestionResponse)
async def create_conversation(
    request: ConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new AI conversation.
    
    This endpoint creates a new conversation session with the AI assistant
    for ongoing dialogue about specific topics.
    """
    try:
        ai_service = AIService(db)
        
        # Get academy ID if applicable
        academy_id = None
        if current_user.user_type == "academy":
            academy_id = current_user.academy.id if current_user.academy else None
        
        result = ai_service.create_conversation(
            user_id=current_user.id,
            conversation_type=request.conversation_type,
            academy_id=academy_id,
            context_id=request.context_id,
            title=request.title
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return AIQuestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ في إنشاء المحادثة"
        )


@router.post("/conversations/{conversation_id}/messages", response_model=AIQuestionResponse)
async def add_message_to_conversation(
    conversation_id: str,
    request: MessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a message to an existing conversation.
    
    This endpoint adds a user message to a conversation and
    automatically generates an AI response.
    """
    try:
        ai_service = AIService(db)
        
        result = ai_service.add_message_to_conversation(
            conversation_id=conversation_id,
            message=request.message,
            sender_type=SenderType.USER
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return AIQuestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ في إضافة الرسالة"
        )


# ========================================
# VIDEO TRANSCRIPTION ENDPOINTS
# ========================================

@router.post("/transcriptions", response_model=AIQuestionResponse)
async def create_video_transcription(
    request: TranscriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a video transcription request.
    
    This endpoint starts the process of converting video content to text
    with subtitle generation support.
    """
    try:
        # Check if user has permission to create transcriptions
        if current_user.user_type not in ["academy", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="غير مصرح لك بإنشاء نسخ نصية للفيديو"
            )
        
        ai_service = AIService(db)
        
        # Get academy ID
        academy_id = None
        if current_user.user_type == "academy":
            academy_id = current_user.academy.id if current_user.academy else None
        
        result = ai_service.create_video_transcription(
            lesson_id=request.lesson_id,
            video_id=request.video_id,
            academy_id=academy_id,
            video_file_path=request.video_file_path
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return AIQuestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ في إنشاء النسخة النصية"
        )


@router.get("/transcriptions/{transcription_id}", response_model=AIQuestionResponse)
async def get_transcription_status(
    transcription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of a video transcription.
    
    This endpoint returns the current status and results of a
    video transcription process.
    """
    try:
        ai_service = AIService(db)
        
        result = ai_service.get_transcription_status(transcription_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["message"]
            )
        
        return AIQuestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ في جلب حالة النسخة النصية"
        )


# ========================================
# EXAM CORRECTION ENDPOINTS
# ========================================

@router.post("/exams/{exam_id}/correct", response_model=AIQuestionResponse)
async def correct_exam(
    exam_id: str,
    request: ExamCorrectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Correct an exam using AI.
    
    This endpoint processes student answers and provides AI-powered
    grading with detailed feedback and recommendations.
    """
    try:
        # Check if user is a student
        if current_user.user_type != "student" or not current_user.student_profile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="هذه الخدمة متاحة للطلاب فقط"
            )
        
        ai_service = AIService(db)
        
        # Get academy ID from exam context (you'd implement this logic)
        academy_id = None  # get_academy_from_exam(exam_id)
        
        result = ai_service.correct_exam(
            exam_id=exam_id,
            student_id=current_user.student_profile.id,
            academy_id=academy_id,
            student_answers=request.student_answers
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return AIQuestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ في تصحيح الامتحان"
        )


# ========================================
# UTILITY ENDPOINTS
# ========================================

@router.get("/health", response_model=Dict[str, Any])
async def ai_health_check():
    """
    Health check for AI services.
    
    This endpoint provides status information about AI services
    and their availability.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "ai_answers": "available",
            "transcription": "available",
            "conversations": "available",
            "exam_correction": "available"
        }
    } 