"""
AI Service for SAYAN Academy Platform
====================================

This service provides AI functionality including video transcription,
exam correction, lesson summarization, and intelligent conversations.

Educational Notes:
- Uses proper exception handling with try/catch blocks
- Implements human-readable patterns without AI-specific terminology
- Maintains consistent response patterns from the system
- Includes proper database transaction management
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func
from datetime import datetime, timedelta
import json
import uuid
from decimal import Decimal

from app.models.ai_assistant import (
    AIAnswer, VideoTranscription, ExamCorrection, QuestionCorrection,
    LessonSummary, AIConversation, AIConversationMessage, AIKnowledgeBase,
    AIPerformanceMetric, AISetting, ProcessingStatus, AIAnswerType,
    ConversationType, SenderType, MessageType, MetricType
)
from app.models.lesson import Lesson
from app.models.exam import Exam
from app.models.student import Student
from app.models.academy import Academy
from app.core.config import settings


class AIService:
    """
    Main AI service class for handling all AI-related operations.
    
    This class provides methods for:
    - Creating AI answers for student questions
    - Processing video transcriptions
    - Managing AI conversations
    - Generating lesson summaries
    - Correcting exams with AI assistance
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================
    # AI ANSWERS MANAGEMENT
    # ========================================
    
    def create_ai_answer(
        self, 
        lesson_id: str, 
        question: str, 
        student_id: Optional[int] = None,
        academy_id: Optional[int] = None,
        answer_type: AIAnswerType = AIAnswerType.QUESTION
    ) -> Dict[str, Any]:
        """
        Create a new AI answer for a student question.
        
        Args:
            lesson_id: The lesson ID where the question was asked
            question: The question text
            student_id: Optional student ID
            academy_id: Optional academy ID
            answer_type: Type of AI answer
            
        Returns:
            Dictionary containing the result and answer data
        """
        try:
            # Validate lesson exists
            lesson = self.db.query(Lesson).filter(Lesson.id == lesson_id).first()
            if not lesson:
                return {
                    "success": False,
                    "message": "لم يتم العثور على الدرس المطلوب",
                    "data": None
                }
            
            # Here you would integrate with your AI API (like OpenAI)
            # For now, we'll simulate an AI response
            ai_response = self._generate_ai_response(question, lesson)
            
            # Create AI answer record
            ai_answer = AIAnswer(
                lesson_id=lesson_id,
                student_id=student_id,
                academy_id=academy_id,
                question=question,
                answer=ai_response["answer"],
                answer_type=answer_type,
                confidence_score=ai_response["confidence"],
                ai_model_used="gpt-4",
                processing_time_ms=ai_response["processing_time"],
                context_data=ai_response["context"]
            )
            
            self.db.add(ai_answer)
            self.db.commit()
            self.db.refresh(ai_answer)
            
            # Log performance metrics
            self._log_ai_performance(
                MetricType.CONVERSATION,
                academy_id,
                student_id,
                {"question": question},
                ai_response,
                success=True
            )
            
            return {
                "success": True,
                "message": "تم إنشاء الإجابة بنجاح",
                "data": {
                    "id": ai_answer.id,
                    "answer": ai_answer.answer,
                    "confidence_score": float(ai_answer.confidence_score),
                    "created_at": ai_answer.created_at
                }
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "message": "حدث خطأ في إنشاء الإجابة",
                "error": str(e)
            }
    
    def get_lesson_ai_answers(
        self, 
        lesson_id: str, 
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get AI answers for a specific lesson.
        
        Args:
            lesson_id: The lesson ID
            limit: Number of answers to return
            offset: Number of answers to skip
            
        Returns:
            Dictionary containing answers list and pagination info
        """
        try:
            # Get answers with pagination
            answers = self.db.query(AIAnswer).filter(
                AIAnswer.lesson_id == lesson_id
            ).order_by(desc(AIAnswer.created_at)).limit(limit).offset(offset).all()
            
            # Get total count
            total_count = self.db.query(AIAnswer).filter(
                AIAnswer.lesson_id == lesson_id
            ).count()
            
            # Format response
            answer_list = []
            for answer in answers:
                answer_list.append({
                    "id": answer.id,
                    "question": answer.question,
                    "answer": answer.answer,
                    "answer_type": answer.answer_type,
                    "confidence_score": float(answer.confidence_score) if answer.confidence_score else 0.0,
                    "is_helpful": answer.is_helpful,
                    "created_at": answer.created_at
                })
            
            return {
                "success": True,
                "message": "تم جلب الإجابات بنجاح",
                "data": {
                    "answers": answer_list,
                    "total_count": total_count,
                    "has_more": (offset + limit) < total_count
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": "حدث خطأ في جلب الإجابات",
                "error": str(e)
            }
    
    # ========================================
    # VIDEO TRANSCRIPTION
    # ========================================
    
    def create_video_transcription(
        self, 
        lesson_id: str, 
        video_id: str,
        academy_id: int,
        video_file_path: str
    ) -> Dict[str, Any]:
        """
        Create a video transcription request.
        
        Args:
            lesson_id: The lesson ID
            video_id: The video ID
            academy_id: Academy ID
            video_file_path: Path to video file
            
        Returns:
            Dictionary containing transcription result
        """
        try:
            # Create transcription record
            transcription = VideoTranscription(
                lesson_id=lesson_id,
                video_id=video_id,
                academy_id=academy_id,
                transcription_text="",  # Will be filled by background job
                processing_status=ProcessingStatus.PENDING,
                language="ar"
            )
            
            self.db.add(transcription)
            self.db.commit()
            self.db.refresh(transcription)
            
            # Here you would queue a background job to process the video
            # For now, we'll simulate processing
            processing_result = self._process_video_transcription(
                transcription.id, 
                video_file_path
            )
            
            return {
                "success": True,
                "message": "تم بدء عملية تحويل الفيديو إلى نص",
                "data": {
                    "transcription_id": transcription.id,
                    "status": transcription.processing_status,
                    "estimated_completion": "5-10 دقائق"
                }
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "message": "حدث خطأ في بدء عملية التحويل",
                "error": str(e)
            }
    
    def get_transcription_status(self, transcription_id: str) -> Dict[str, Any]:
        """
        Get the status of a video transcription.
        
        Args:
            transcription_id: The transcription ID
            
        Returns:
            Dictionary containing transcription status and data
        """
        try:
            transcription = self.db.query(VideoTranscription).filter(
                VideoTranscription.id == transcription_id
            ).first()
            
            if not transcription:
                return {
                    "success": False,
                    "message": "لم يتم العثور على عملية التحويل",
                    "data": None
                }
            
            return {
                "success": True,
                "message": "تم جلب حالة التحويل بنجاح",
                "data": {
                    "id": transcription.id,
                    "status": transcription.processing_status,
                    "confidence_score": float(transcription.confidence_score) if transcription.confidence_score else 0.0,
                    "transcription_text": transcription.transcription_text,
                    "subtitles_srt": transcription.subtitles_srt,
                    "subtitles_vtt": transcription.subtitles_vtt,
                    "processing_time": transcription.processing_time_seconds,
                    "created_at": transcription.created_at,
                    "updated_at": transcription.updated_at
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": "حدث خطأ في جلب حالة التحويل",
                "error": str(e)
            }
    
    # ========================================
    # CONVERSATION MANAGEMENT
    # ========================================
    
    def create_conversation(
        self, 
        user_id: int,
        conversation_type: ConversationType,
        academy_id: Optional[int] = None,
        context_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new AI conversation.
        
        Args:
            user_id: User ID
            conversation_type: Type of conversation
            academy_id: Optional academy ID
            context_id: Optional context ID (lesson, exam, etc.)
            title: Optional conversation title
            
        Returns:
            Dictionary containing conversation data
        """
        try:
            conversation = AIConversation(
                user_id=user_id,
                academy_id=academy_id,
                conversation_type=conversation_type,
                context_id=context_id,
                title=title or f"محادثة جديدة - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            
            return {
                "success": True,
                "message": "تم إنشاء المحادثة بنجاح",
                "data": {
                    "id": conversation.id,
                    "title": conversation.title,
                    "type": conversation.conversation_type,
                    "status": conversation.status,
                    "created_at": conversation.created_at
                }
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "message": "حدث خطأ في إنشاء المحادثة",
                "error": str(e)
            }
    
    def add_message_to_conversation(
        self, 
        conversation_id: str,
        message: str,
        sender_type: SenderType,
        message_type: MessageType = MessageType.TEXT
    ) -> Dict[str, Any]:
        """
        Add a message to an existing conversation.
        
        Args:
            conversation_id: Conversation ID
            message: Message content
            sender_type: Who sent the message
            message_type: Type of message
            
        Returns:
            Dictionary containing message data and AI response if applicable
        """
        try:
            # Validate conversation exists
            conversation = self.db.query(AIConversation).filter(
                AIConversation.id == conversation_id
            ).first()
            
            if not conversation:
                return {
                    "success": False,
                    "message": "لم يتم العثور على المحادثة",
                    "data": None
                }
            
            # Create user message
            user_message = AIConversationMessage(
                conversation_id=conversation_id,
                sender_type=sender_type,
                message=message,
                message_type=message_type
            )
            
            self.db.add(user_message)
            self.db.flush()  # Get the ID without committing
            
            response_data = {
                "user_message": {
                    "id": user_message.id,
                    "message": user_message.message,
                    "sender_type": user_message.sender_type,
                    "created_at": user_message.created_at
                }
            }
            
            # If user message, generate AI response
            if sender_type == SenderType.USER:
                ai_response = self._generate_conversation_response(
                    conversation, 
                    message
                )
                
                ai_message = AIConversationMessage(
                    conversation_id=conversation_id,
                    sender_type=SenderType.AI,
                    message=ai_response["message"],
                    message_type=MessageType.TEXT,
                    ai_model_used="gpt-4",
                    processing_time_ms=ai_response["processing_time"],
                    confidence_score=ai_response["confidence"]
                )
                
                self.db.add(ai_message)
                self.db.flush()
                
                response_data["ai_message"] = {
                    "id": ai_message.id,
                    "message": ai_message.message,
                    "sender_type": ai_message.sender_type,
                    "confidence_score": float(ai_message.confidence_score) if ai_message.confidence_score else 0.0,
                    "created_at": ai_message.created_at
                }
            
            # Update conversation timestamp
            conversation.updated_at = datetime.now()
            self.db.commit()
            
            return {
                "success": True,
                "message": "تم إضافة الرسالة بنجاح",
                "data": response_data
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "message": "حدث خطأ في إضافة الرسالة",
                "error": str(e)
            }
    
    # ========================================
    # EXAM CORRECTION
    # ========================================
    
    def correct_exam(
        self, 
        exam_id: str,
        student_id: int,
        academy_id: int,
        student_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Correct an exam using AI.
        
        Args:
            exam_id: Exam ID
            student_id: Student ID
            academy_id: Academy ID
            student_answers: List of student answers
            
        Returns:
            Dictionary containing correction results
        """
        try:
            # Validate exam exists
            exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
            if not exam:
                return {
                    "success": False,
                    "message": "لم يتم العثور على الامتحان",
                    "data": None
                }
            
            # Process answers and calculate scores
            correction_results = self._process_exam_answers(exam, student_answers)
            
            # Create exam correction record
            exam_correction = ExamCorrection(
                exam_id=exam_id,
                student_id=student_id,
                academy_id=academy_id,
                submission_id=str(uuid.uuid4()),
                total_score=correction_results["total_score"],
                max_score=correction_results["max_score"],
                percentage=correction_results["percentage"],
                auto_feedback=correction_results["feedback"],
                recommendations=correction_results["recommendations"],
                improvement_areas=correction_results["improvement_areas"],
                strengths=correction_results["strengths"],
                study_plan=correction_results["study_plan"],
                correction_time_ms=correction_results["processing_time"]
            )
            
            self.db.add(exam_correction)
            self.db.flush()
            
            # Create individual question corrections
            for question_result in correction_results["questions"]:
                question_correction = QuestionCorrection(
                    exam_correction_id=exam_correction.id,
                    question_id=question_result["question_id"],
                    student_answer=question_result["student_answer"],
                    correct_answer=question_result["correct_answer"],
                    is_correct=question_result["is_correct"],
                    score_awarded=question_result["score_awarded"],
                    max_score=question_result["max_score"],
                    ai_feedback=question_result["feedback"]
                )
                
                self.db.add(question_correction)
            
            self.db.commit()
            self.db.refresh(exam_correction)
            
            return {
                "success": True,
                "message": "تم تصحيح الامتحان بنجاح",
                "data": {
                    "correction_id": exam_correction.id,
                    "total_score": float(exam_correction.total_score),
                    "max_score": float(exam_correction.max_score),
                    "percentage": float(exam_correction.percentage),
                    "feedback": exam_correction.auto_feedback,
                    "recommendations": exam_correction.recommendations,
                    "passed": exam_correction.percentage >= 60.0,
                    "corrected_at": exam_correction.corrected_at
                }
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "message": "حدث خطأ في تصحيح الامتحان",
                "error": str(e)
            }
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _generate_ai_response(self, question: str, lesson: Lesson) -> Dict[str, Any]:
        """
        Generate AI response for a question.
        This would integrate with actual AI service like OpenAI.
        """
        # Simulate AI processing
        return {
            "answer": f"هذا رد تلقائي للسؤال: {question}\n\nبناءً على محتوى الدرس '{lesson.title}', يمكنني مساعدتك في فهم هذا الموضوع.",
            "confidence": Decimal("0.85"),
            "processing_time": 1250,
            "context": {
                "lesson_title": lesson.title,
                "lesson_type": lesson.type,
                "question_length": len(question)
            }
        }
    
    def _process_video_transcription(self, transcription_id: str, video_path: str) -> Dict[str, Any]:
        """
        Process video transcription.
        This would integrate with actual transcription service.
        """
        # Simulate transcription processing
        return {
            "transcription_text": "نص تجريبي للتحويل الصوتي",
            "confidence": 0.92,
            "processing_time": 45,
            "segments": [
                {"start": 0, "end": 5, "text": "مرحباً بكم في هذا الدرس"},
                {"start": 5, "end": 10, "text": "سنتعلم اليوم عن..."}
            ]
        }
    
    def _generate_conversation_response(self, conversation: AIConversation, message: str) -> Dict[str, Any]:
        """
        Generate AI response for conversation.
        This would integrate with actual AI service.
        """
        # Simulate AI conversation response
        return {
            "message": f"شكراً لك على سؤالك. بناءً على محتوى المحادثة، يمكنني مساعدتك في: {message}",
            "confidence": Decimal("0.88"),
            "processing_time": 950
        }
    
    def _process_exam_answers(self, exam: Exam, student_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process exam answers and calculate scores.
        This would integrate with actual AI grading service.
        """
        # Simulate exam correction
        total_score = 0
        max_score = 100
        questions = []
        
        for answer in student_answers:
            # Simulate question correction
            is_correct = answer.get("answer") == "correct_answer"  # Simplified
            score = 10 if is_correct else 0
            total_score += score
            
            questions.append({
                "question_id": answer["question_id"],
                "student_answer": answer["answer"],
                "correct_answer": "correct_answer",
                "is_correct": is_correct,
                "score_awarded": score,
                "max_score": 10,
                "feedback": "إجابة صحيحة، أحسنت!" if is_correct else "إجابة خاطئة، يرجى المراجعة"
            })
        
        percentage = (total_score / max_score) * 100
        
        return {
            "total_score": total_score,
            "max_score": max_score,
            "percentage": percentage,
            "feedback": f"حصلت على {percentage}% في هذا الامتحان",
            "recommendations": ["راجع المواضيع التي لم تجب عليها بشكل صحيح"],
            "improvement_areas": ["الفهم القرائي", "التحليل"],
            "strengths": ["الحفظ", "الفهم الأساسي"],
            "study_plan": {"week_1": "راجع الدرس الأول", "week_2": "حل تمارين إضافية"},
            "processing_time": 2500,
            "questions": questions
        }
    
    def _log_ai_performance(
        self, 
        metric_type: MetricType,
        academy_id: Optional[int],
        user_id: Optional[int],
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Log AI performance metrics.
        """
        try:
            metric = AIPerformanceMetric(
                metric_type=metric_type,
                academy_id=academy_id,
                user_id=user_id,
                request_data=request_data,
                response_data=response_data,
                processing_time_ms=response_data.get("processing_time", 0),
                success=success,
                error_message=error_message,
                tokens_used=response_data.get("tokens_used", 0),
                cost_usd=response_data.get("cost_usd", 0.0)
            )
            
            self.db.add(metric)
            self.db.commit()
            
        except Exception as e:
            # Log error but don't fail the main operation
            print(f"Failed to log AI performance: {str(e)}")
            self.db.rollback() 