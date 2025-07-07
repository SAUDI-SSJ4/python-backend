"""
AI Models for SAYAN Academy Platform
=====================================

This module contains SQLAlchemy models for the AI Assistant system,
including video transcription, exam correction, lesson summarization,
and intelligent conversation features.
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.db.base import Base
import enum
import uuid


# --------------------------------------------------------
# ENUMS
# --------------------------------------------------------

class ProcessingStatus(str, enum.Enum):
    """Processing status for AI tasks"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AIAnswerType(str, enum.Enum):
    """AI answer types"""
    QUESTION = "question"
    EXAM_FEEDBACK = "exam_feedback"
    RECOMMENDATION = "recommendation"
    SUMMARY = "summary"


class ConversationType(str, enum.Enum):
    """AI conversation types"""
    LESSON_HELP = "lesson_help"
    EXAM_HELP = "exam_help"
    GENERAL_SUPPORT = "general_support"
    COURSE_QUESTION = "course_question"


class UserType(str, enum.Enum):
    """User types for AI system"""
    STUDENT = "student"
    ACADEMY = "academy"
    ADMIN = "admin"


class ContextType(str, enum.Enum):
    """Context types for AI conversations"""
    LESSON = "lesson"
    EXAM = "exam"
    COURSE = "course"
    GENERAL = "general"


class ConversationStatus(str, enum.Enum):
    """Conversation status"""
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class SenderType(str, enum.Enum):
    """Message sender types"""
    USER = "user"
    AI = "ai"


class MessageType(str, enum.Enum):
    """Message types"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"


class DifficultyLevel(str, enum.Enum):
    """Difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MIXED = "mixed"


class QuestionType(str, enum.Enum):
    """Question types for AI generation"""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"


class BloomTaxonomy(str, enum.Enum):
    """Bloom's taxonomy levels"""
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class ContentType(str, enum.Enum):
    """Knowledge base content types"""
    FAQ = "faq"
    TUTORIAL = "tutorial"
    EXPLANATION = "explanation"
    TROUBLESHOOTING = "troubleshooting"


class MetricType(str, enum.Enum):
    """AI performance metric types"""
    TRANSCRIPTION = "transcription"
    EXAM_CORRECTION = "exam_correction"
    QUESTION_GENERATION = "question_generation"
    CONVERSATION = "conversation"
    SUMMARIZATION = "summarization"


class SettingType(str, enum.Enum):
    """AI setting types"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"


# --------------------------------------------------------
# VIDEO TRANSCRIPTION MODELS
# --------------------------------------------------------

class VideoTranscription(Base):
    """Video transcription model for storing AI-generated text from videos"""
    __tablename__ = "video_transcriptions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(CHAR(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=True)
    transcription_text = Column(Text, nullable=False)
    subtitles_srt = Column(Text)
    subtitles_vtt = Column(Text)
    language = Column(String(10), default="ar")
    confidence_score = Column(DECIMAL(5,2), default=0.00)
    processing_status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING)
    processing_time_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    lesson = relationship("Lesson", back_populates="transcriptions")
    video = relationship("Video", back_populates="transcriptions")
    segments = relationship("VideoSegment", back_populates="transcription", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<VideoTranscription(id={self.id}, lesson_id={self.lesson_id}, status={self.processing_status})>"


class VideoSegment(Base):
    """Video segment model for timestamped transcription segments"""
    __tablename__ = "video_segments"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transcription_id = Column(CHAR(36), ForeignKey("video_transcriptions.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    keywords = Column(JSON)
    confidence_score = Column(DECIMAL(5,2), default=0.00)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    transcription = relationship("VideoTranscription", back_populates="segments")

    def __repr__(self):
        return f"<VideoSegment(id={self.id}, start_time={self.start_time}, end_time={self.end_time})>"


# --------------------------------------------------------
# EXAM CORRECTION MODELS
# --------------------------------------------------------

class ExamCorrection(Base):
    """Exam correction model for AI-powered exam grading"""
    __tablename__ = "exam_corrections"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id = Column(CHAR(36), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    submission_id = Column(CHAR(36), nullable=False)
    total_score = Column(DECIMAL(5,2), nullable=False, default=0.00)
    max_score = Column(DECIMAL(5,2), nullable=False, default=0.00)
    percentage = Column(DECIMAL(5,2), nullable=False, default=0.00)
    auto_feedback = Column(Text)
    recommendations = Column(JSON)
    improvement_areas = Column(JSON)
    strengths = Column(JSON)
    study_plan = Column(JSON)
    corrected_at = Column(DateTime, default=func.now(), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    exam = relationship("Exam", back_populates="corrections")
    student = relationship("Student", back_populates="exam_corrections")
    question_corrections = relationship("QuestionCorrection", back_populates="exam_correction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ExamCorrection(id={self.id}, exam_id={self.exam_id}, score={self.total_score})>"


class QuestionCorrection(Base):
    """Question correction model for individual question grading"""
    __tablename__ = "question_corrections"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_correction_id = Column(CHAR(36), ForeignKey("exam_corrections.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(CHAR(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    student_answer = Column(Text)
    correct_answer = Column(Text)
    is_correct = Column(Boolean, nullable=False, default=False)
    score_awarded = Column(DECIMAL(5,2), nullable=False, default=0.00)
    max_score = Column(DECIMAL(5,2), nullable=False, default=0.00)
    ai_feedback = Column(Text)
    difficulty_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    time_spent_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    exam_correction = relationship("ExamCorrection", back_populates="question_corrections")
    question = relationship("Question", back_populates="corrections")

    def __repr__(self):
        return f"<QuestionCorrection(id={self.id}, question_id={self.question_id}, correct={self.is_correct})>"


# --------------------------------------------------------
# LESSON SUMMARIZATION MODELS
# --------------------------------------------------------

class LessonSummary(Base):
    """Lesson summary model for AI-generated lesson summaries"""
    __tablename__ = "lesson_summaries"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    short_summary = Column(Text, nullable=False)
    detailed_summary = Column(Text, nullable=False)
    key_points = Column(JSON)
    learning_objectives = Column(JSON)
    tags = Column(JSON)
    difficulty_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    estimated_study_time = Column(Integer, default=0)
    prerequisites = Column(JSON)
    generated_at = Column(DateTime, default=func.now(), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    lesson = relationship("Lesson", back_populates="summaries")

    def __repr__(self):
        return f"<LessonSummary(id={self.id}, lesson_id={self.lesson_id})>"


# --------------------------------------------------------
# AI EXAM GENERATION MODELS
# --------------------------------------------------------

class AIExamTemplate(Base):
    """AI exam template model for generating exam templates"""
    __tablename__ = "ai_exam_templates"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    template_name = Column(String(255), nullable=False)
    difficulty_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    question_count = Column(Integer, default=10)
    time_limit_minutes = Column(Integer, default=30)
    passing_score = Column(DECIMAL(5,2), default=60.00)
    question_types = Column(JSON)
    content_focus = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    lesson = relationship("Lesson", back_populates="exam_templates")
    course = relationship("Course", back_populates="exam_templates")
    generated_questions = relationship("AIGeneratedQuestion", back_populates="template", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AIExamTemplate(id={self.id}, name={self.template_name})>"


class AIGeneratedQuestion(Base):
    """AI generated question model for storing AI-created questions"""
    __tablename__ = "ai_generated_questions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = Column(CHAR(36), ForeignKey("ai_exam_templates.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(SQLEnum(QuestionType), nullable=False)
    difficulty_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    options = Column(JSON)
    correct_answer = Column(Text)
    explanation = Column(Text)
    points = Column(Integer, default=1)
    source_content = Column(Text)
    bloom_taxonomy_level = Column(SQLEnum(BloomTaxonomy), default=BloomTaxonomy.UNDERSTAND)
    is_approved = Column(Boolean, default=False)
    quality_score = Column(DECIMAL(5,2), default=0.00)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    template = relationship("AIExamTemplate", back_populates="generated_questions")

    def __repr__(self):
        return f"<AIGeneratedQuestion(id={self.id}, type={self.question_type})>"


# --------------------------------------------------------
# AI CONVERSATION MODELS
# --------------------------------------------------------

class AIConversation(Base):
    """AI conversation model for storing intelligent conversations"""
    __tablename__ = "ai_conversations"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_type = Column(SQLEnum(UserType), default=UserType.STUDENT, nullable=False)
    conversation_type = Column(SQLEnum(ConversationType), nullable=False)
    context_id = Column(CHAR(36))
    context_type = Column(SQLEnum(ContextType), default=ContextType.GENERAL)
    title = Column(String(255))
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE)
    satisfaction_rating = Column(Integer)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="ai_conversations")
    messages = relationship("AIConversationMessage", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AIConversation(id={self.id}, user_id={self.user_id}, type={self.conversation_type})>"


class AIConversationMessage(Base):
    """AI conversation message model for storing chat messages"""
    __tablename__ = "ai_conversation_messages"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(CHAR(36), ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False)
    sender_type = Column(SQLEnum(SenderType), nullable=False)
    message = Column(Text, nullable=False)
    message_type = Column(SQLEnum(MessageType), default=MessageType.TEXT)
    attachments = Column(JSON)
    ai_model_used = Column(String(50))
    processing_time_ms = Column(Integer, default=0)
    confidence_score = Column(DECIMAL(5,2), default=0.00)
    is_helpful = Column(Boolean)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    conversation = relationship("AIConversation", back_populates="messages")

    def __repr__(self):
        return f"<AIConversationMessage(id={self.id}, sender={self.sender_type})>"


# --------------------------------------------------------
# AI KNOWLEDGE BASE MODELS
# --------------------------------------------------------

class AIKnowledgeBase(Base):
    """AI knowledge base model for storing AI knowledge content"""
    __tablename__ = "ai_knowledge_base"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(SQLEnum(ContentType), nullable=False)
    category = Column(String(100))
    tags = Column(JSON)
    search_keywords = Column(Text)
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    academy = relationship("Academy", back_populates="knowledge_base")

    def __repr__(self):
        return f"<AIKnowledgeBase(id={self.id}, title={self.title})>"


# --------------------------------------------------------
# AI PERFORMANCE TRACKING MODELS
# --------------------------------------------------------

class AIPerformanceMetric(Base):
    """AI performance metric model for tracking AI system performance"""
    __tablename__ = "ai_performance_metrics"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_type = Column(SQLEnum(MetricType), nullable=False)
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    request_data = Column(JSON)
    response_data = Column(JSON)
    processing_time_ms = Column(Integer, default=0)
    accuracy_score = Column(DECIMAL(5,2), default=0.00)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(DECIMAL(10,6), default=0.000000)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    academy = relationship("Academy", back_populates="ai_metrics")
    user = relationship("User", back_populates="ai_metrics")

    def __repr__(self):
        return f"<AIPerformanceMetric(id={self.id}, type={self.metric_type}, success={self.success})>"


# --------------------------------------------------------
# AI SETTINGS MODEL
# --------------------------------------------------------

class AISetting(Base):
    """AI setting model for storing AI system configuration"""
    __tablename__ = "ai_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=True)
    setting_key = Column(String(100), nullable=False)
    setting_value = Column(Text)
    setting_type = Column(SQLEnum(SettingType), default=SettingType.STRING)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    academy = relationship("Academy", back_populates="ai_settings")

    def __repr__(self):
        return f"<AISetting(id={self.id}, key={self.setting_key}, value={self.setting_value})>" 