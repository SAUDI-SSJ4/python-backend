"""
AI Assistant Models for SAYAN Academy Platform
==============================================

This module provides comprehensive AI functionality for the SAYAN platform.
It includes models for video transcription, exam correction, lesson summarization,
intelligent conversations, and performance monitoring.

Educational Note:
- Each model follows SQLAlchemy best practices
- Proper indexing for query performance
- Comprehensive error handling support
- Clear relationships between entities
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON, DECIMAL, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.db.base import Base
import enum
import uuid
from datetime import datetime


# --------------------------------------------------------
# ENUMS - Define all possible states and types
# --------------------------------------------------------

class ProcessingStatus(str, enum.Enum):
    """Status tracking for AI processing tasks"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AIAnswerType(str, enum.Enum):
    """Types of AI-generated answers and responses"""
    QUESTION = "question"
    EXAM_FEEDBACK = "exam_feedback"
    RECOMMENDATION = "recommendation"
    SUMMARY = "summary"
    CORRECTION = "correction"


class ConversationType(str, enum.Enum):
    """Categories of AI conversations"""
    LESSON_HELP = "lesson_help"
    EXAM_HELP = "exam_help"
    GENERAL_SUPPORT = "general_support"
    COURSE_QUESTION = "course_question"
    TECHNICAL_SUPPORT = "technical_support"


class ContextType(str, enum.Enum):
    """Context types for AI conversations"""
    LESSON = "lesson"
    EXAM = "exam"
    COURSE = "course"
    CHAPTER = "chapter"
    GENERAL = "general"


class ConversationStatus(str, enum.Enum):
    """Status of AI conversations"""
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class SenderType(str, enum.Enum):
    """Message sender identification"""
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class MessageType(str, enum.Enum):
    """Types of messages in conversations"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    CODE = "code"


class DifficultyLevel(str, enum.Enum):
    """Academic difficulty levels"""
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
    FILL_BLANK = "fill_blank"


class ContentType(str, enum.Enum):
    """Knowledge base content categories"""
    FAQ = "faq"
    TUTORIAL = "tutorial"
    EXPLANATION = "explanation"
    TROUBLESHOOTING = "troubleshooting"
    GUIDE = "guide"


class MetricType(str, enum.Enum):
    """Performance metric categories"""
    TRANSCRIPTION = "transcription"
    EXAM_CORRECTION = "exam_correction"
    QUESTION_GENERATION = "question_generation"
    CONVERSATION = "conversation"
    SUMMARIZATION = "summarization"


class SettingType(str, enum.Enum):
    """Configuration setting data types"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"


# --------------------------------------------------------
# CORE AI MODELS
# --------------------------------------------------------

class AIAnswer(Base):
    """
    Enhanced AI Answers Model
    
    This model has been updated from the original to include comprehensive
    AI functionality. It stores all types of AI-generated responses with
    proper metadata and feedback tracking.
    
    Educational Note:
    - Uses DECIMAL for precise confidence scoring
    - JSON fields for flexible metadata storage
    - Proper indexing on frequently queried fields
    """
    __tablename__ = "ai_answers"

    # Primary key and foreign key relationships
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Core content fields
    question = Column(String(255), nullable=False)
    answer = Column(Text, nullable=False)
    answer_type = Column(SQLEnum(AIAnswerType), default=AIAnswerType.QUESTION, nullable=False, index=True)
    
    # AI enhancement fields - new additions to original model
    context_data = Column(JSON, comment="Contextual information used for AI processing")
    confidence_score = Column(DECIMAL(5, 2), default=0.00, comment="AI confidence level (0.00-1.00)")
    source_content_id = Column(CHAR(36), comment="Reference to source content")
    ai_model_used = Column(String(50), default="gpt-4", comment="AI model identifier")
    processing_time_ms = Column(Integer, default=0, comment="Processing time in milliseconds")
    
    # Additional AI metadata
    ai_evaluation_score = Column(DECIMAL(3, 2), default=0.00, comment="AI evaluation score for answer quality")
    is_correct = Column(Boolean, default=None, comment="Whether the answer is correct (for exam answers)")
    feedback_summary = Column(Text, comment="AI-generated feedback summary")
    improvement_suggestions = Column(JSON, comment="Suggestions for improvement")
    related_topics = Column(JSON, comment="Related topics and concepts")
    
    # Subtitle support for video content
    subtitles_srt = Column(Text, comment="SRT format subtitles")
    subtitles_vtt = Column(Text, comment="VTT format subtitles")
    
    # User feedback tracking
    feedback_score = Column(Integer, comment="User feedback score (1-5)")
    is_helpful = Column(Boolean, comment="User helpfulness rating")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    lesson = relationship("Lesson", back_populates="ai_answers")
    student = relationship("Student", back_populates="ai_answers")
    academy = relationship("Academy", back_populates="ai_answers")

    # Database indexes for performance
    __table_args__ = (
        Index('ix_ai_answers_lesson_student', 'lesson_id', 'student_id'),
        Index('ix_ai_answers_academy_type', 'academy_id', 'answer_type'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<AIAnswer(id={self.id}, type={self.answer_type}, lesson_id={self.lesson_id})>"


class VideoTranscription(Base):
    """
    Video Transcription Model
    
    Handles conversion of video/audio content to text with AI processing.
    Supports multiple languages and provides confidence scoring.
    
    Educational Note:
    - Stores both full transcription and time-segmented data
    - Uses JSON for flexible segment storage
    - Tracks processing metrics for optimization
    """
    __tablename__ = "video_transcriptions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id = Column(CHAR(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Transcription content
    transcription_text = Column(Text, nullable=False, comment="Full transcription text")
    subtitles_srt = Column(Text, comment="SRT format subtitles")
    subtitles_vtt = Column(Text, comment="VTT format subtitles")
    language = Column(String(10), default="ar", nullable=False, comment="Language code (ar, en, etc.)")
    
    # Quality and processing metrics
    confidence_score = Column(DECIMAL(5, 2), default=0.00, comment="Overall transcription confidence")
    processing_status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False, index=True)
    processing_time_seconds = Column(Integer, default=0, comment="Time taken for processing")
    
    # File metadata
    file_size_bytes = Column(Integer, default=0, comment="Original file size")
    duration_seconds = Column(Integer, default=0, comment="Video duration in seconds")
    
    # Segmented transcription data stored as JSON
    segments = Column(JSON, comment="Time-segmented transcription with timestamps")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    lesson = relationship("Lesson", back_populates="video_transcriptions")
    video = relationship("Video", back_populates="transcriptions")
    academy = relationship("Academy", back_populates="video_transcriptions")

    # Indexes for performance
    __table_args__ = (
        Index('ix_video_transcriptions_status', 'processing_status'),
        Index('ix_video_transcriptions_lesson_academy', 'lesson_id', 'academy_id'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<VideoTranscription(id={self.id}, lesson_id={self.lesson_id}, status={self.processing_status})>"


class ExamCorrection(Base):
    """
    Exam Correction Model
    
    Provides AI-powered exam grading with detailed feedback.
    Supports multiple question types and generates improvement recommendations.
    
    Educational Note:
    - Stores both individual question corrections and overall exam feedback
    - Uses JSON for flexible data storage
    - Provides detailed analytics for learning improvement
    """
    __tablename__ = "exam_corrections"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id = Column(CHAR(36), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Unique submission identifier
    submission_id = Column(CHAR(36), nullable=False, unique=True, index=True)
    
    # Scoring information
    total_score = Column(DECIMAL(5, 2), nullable=False, default=0.00, comment="Total score achieved")
    max_score = Column(DECIMAL(5, 2), nullable=False, default=0.00, comment="Maximum possible score")
    percentage = Column(DECIMAL(5, 2), nullable=False, default=0.00, comment="Percentage score")
    
    # AI-generated feedback
    auto_feedback = Column(Text, comment="AI-generated overall feedback")
    recommendations = Column(JSON, comment="Personalized learning recommendations")
    improvement_areas = Column(JSON, comment="Areas needing improvement")
    strengths = Column(JSON, comment="Student strengths identified")
    study_plan = Column(JSON, comment="Suggested study plan")
    
    # Processing metrics
    correction_time_ms = Column(Integer, default=0, comment="Time taken for AI correction")
    
    # Timestamps
    corrected_at = Column(DateTime, default=func.now(), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    exam = relationship("Exam", back_populates="ai_corrections")
    student = relationship("Student", back_populates="exam_corrections")
    academy = relationship("Academy", back_populates="exam_corrections")
    question_corrections = relationship("QuestionCorrection", back_populates="exam_correction", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('ix_exam_corrections_student_exam', 'student_id', 'exam_id'),
        Index('ix_exam_corrections_academy_date', 'academy_id', 'corrected_at'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<ExamCorrection(id={self.id}, exam_id={self.exam_id}, student_id={self.student_id})>"


class QuestionCorrection(Base):
    """
    Individual Question Correction Model
    
    Stores detailed correction information for each question in an exam.
    Provides question-level feedback and scoring.
    
    Educational Note:
    - Links to both exam correction and individual question
    - Supports different question types with flexible answer storage
    - Provides detailed feedback for each question
    """
    __tablename__ = "question_corrections"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_correction_id = Column(CHAR(36), ForeignKey("exam_corrections.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(CHAR(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Answer information
    student_answer = Column(Text, comment="Student's submitted answer")
    correct_answer = Column(Text, comment="The correct answer")
    is_correct = Column(Boolean, nullable=False, default=False, comment="Whether the answer is correct")
    
    # Scoring
    score_awarded = Column(DECIMAL(5, 2), nullable=False, default=0.00, comment="Points awarded")
    max_score = Column(DECIMAL(5, 2), nullable=False, default=0.00, comment="Maximum possible points")
    
    # AI feedback
    ai_feedback = Column(Text, comment="AI-generated feedback for this question")
    
    # Question metadata
    difficulty_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM, comment="Question difficulty")
    time_spent_seconds = Column(Integer, default=0, comment="Time spent on this question")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    exam_correction = relationship("ExamCorrection", back_populates="question_corrections")
    question = relationship("Question", back_populates="ai_corrections")

    # Indexes for performance
    __table_args__ = (
        Index('ix_question_corrections_exam_question', 'exam_correction_id', 'question_id'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<QuestionCorrection(id={self.id}, question_id={self.question_id}, is_correct={self.is_correct})>"


class LessonSummary(Base):
    """
    Lesson Summary Model
    
    Stores AI-generated summaries of lessons in different formats.
    Supports various summary types and learning analytics.
    
    Educational Note:
    - Provides multiple summary formats for different learning styles
    - Includes learning objectives and key points
    - Supports difficulty assessment and prerequisite tracking
    """
    __tablename__ = "lesson_summaries"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Summary content
    short_summary = Column(Text, nullable=False, comment="Brief lesson summary")
    detailed_summary = Column(Text, nullable=False, comment="Comprehensive lesson summary")
    
    # Structured learning data
    key_points = Column(JSON, comment="Main learning points")
    learning_objectives = Column(JSON, comment="Learning objectives covered")
    tags = Column(JSON, comment="Topic tags and keywords")
    
    # Difficulty and prerequisites
    difficulty_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM, comment="Lesson difficulty")
    estimated_study_time = Column(Integer, default=0, comment="Estimated study time in minutes")
    prerequisites = Column(JSON, comment="Required prior knowledge")
    
    # Language and generation info
    language = Column(String(10), default="ar", comment="Summary language")
    generated_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    lesson = relationship("Lesson", back_populates="ai_summaries")
    academy = relationship("Academy", back_populates="lesson_summaries")

    # Indexes for performance
    __table_args__ = (
        Index('ix_lesson_summaries_lesson_academy', 'lesson_id', 'academy_id'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<LessonSummary(id={self.id}, lesson_id={self.lesson_id})>"


class AIExamTemplate(Base):
    """
    AI Exam Template Model
    
    Stores templates for AI-generated exams with configurable parameters.
    Supports different exam types and difficulty levels.
    
    Educational Note:
    - Provides reusable exam templates
    - Configurable question types and difficulty distribution
    - Supports Bloom's taxonomy for educational alignment
    """
    __tablename__ = "ai_exam_templates"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Template configuration
    template_name = Column(String(255), nullable=False, comment="Template name")
    difficulty_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM, comment="Overall difficulty")
    question_count = Column(Integer, default=10, comment="Number of questions")
    time_limit_minutes = Column(Integer, default=30, comment="Time limit in minutes")
    passing_score = Column(DECIMAL(5, 2), default=60.00, comment="Passing score percentage")
    
    # Question configuration
    question_types = Column(JSON, comment="Distribution of question types")
    content_focus = Column(JSON, comment="Content areas to focus on")
    
    # Template status
    is_active = Column(Boolean, default=True, comment="Whether template is active")
    
    # Creation info
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Template creator")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    lesson = relationship("Lesson", back_populates="ai_exam_templates")
    course = relationship("Course", back_populates="ai_exam_templates")
    academy = relationship("Academy", back_populates="ai_exam_templates")
    creator = relationship("User", back_populates="ai_exam_templates")
    generated_questions = relationship("AIGeneratedQuestion", back_populates="template", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('ix_ai_exam_templates_lesson_course', 'lesson_id', 'course_id'),
        Index('ix_ai_exam_templates_academy_active', 'academy_id', 'is_active'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<AIExamTemplate(id={self.id}, name={self.template_name})>"


class AIGeneratedQuestion(Base):
    """
    AI Generated Question Model
    
    Stores individual questions generated by AI for exams and quizzes.
    Supports multiple question types with quality control.
    
    Educational Note:
    - Comprehensive question storage with options and explanations
    - Quality scoring for question assessment
    - Bloom's taxonomy alignment for educational standards
    """
    __tablename__ = "ai_generated_questions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = Column(CHAR(36), ForeignKey("ai_exam_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Question content
    question_text = Column(Text, nullable=False, comment="The question text")
    question_type = Column(SQLEnum(QuestionType), nullable=False, comment="Type of question")
    
    # Question configuration
    difficulty_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM, comment="Question difficulty")
    options = Column(JSON, comment="Answer options for multiple choice questions")
    correct_answer = Column(Text, comment="The correct answer")
    explanation = Column(Text, comment="Explanation of the correct answer")
    points = Column(Integer, default=1, comment="Points awarded for correct answer")
    
    # Educational metadata
    source_content = Column(Text, comment="Source content used for question generation")
    bloom_taxonomy_level = Column(String(20), comment="Bloom's taxonomy level")
    
    # Quality control
    is_approved = Column(Boolean, default=False, comment="Whether question is approved for use")
    quality_score = Column(DECIMAL(5, 2), default=0.00, comment="AI-assessed quality score")
    usage_count = Column(Integer, default=0, comment="Number of times question has been used")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    template = relationship("AIExamTemplate", back_populates="generated_questions")

    # Indexes for performance
    __table_args__ = (
        Index('ix_ai_generated_questions_template_approved', 'template_id', 'is_approved'),
        Index('ix_ai_generated_questions_type_difficulty', 'question_type', 'difficulty_level'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<AIGeneratedQuestion(id={self.id}, type={self.question_type})>"


# --------------------------------------------------------
# CONVERSATION MODELS
# --------------------------------------------------------

class AIConversation(Base):
    """
    AI Conversation Model
    
    Manages intelligent conversations between users and AI assistant.
    Supports different conversation types and contexts.
    
    Educational Note:
    - Tracks conversation context for personalized responses
    - Supports multiple conversation types (lesson help, exam support, etc.)
    - Provides conversation status management
    """
    __tablename__ = "ai_conversations"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Conversation configuration
    conversation_type = Column(SQLEnum(ConversationType), nullable=False, comment="Type of conversation")
    context_type = Column(SQLEnum(ContextType), default=ContextType.GENERAL, comment="Context category")
    context_id = Column(CHAR(36), comment="ID of related lesson/exam/course")
    
    # Conversation metadata
    title = Column(String(255), comment="Conversation title")
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE, nullable=False, index=True)
    context_metadata = Column(JSON, comment="Additional context and configuration")
    
    # User satisfaction
    satisfaction_rating = Column(Integer, comment="User satisfaction rating (1-5)")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="ai_conversations")
    academy = relationship("Academy", back_populates="ai_conversations")
    messages = relationship("AIConversationMessage", back_populates="conversation", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('ix_ai_conversations_user_status', 'user_id', 'status'),
        Index('ix_ai_conversations_academy_type', 'academy_id', 'conversation_type'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<AIConversation(id={self.id}, user_id={self.user_id}, type={self.conversation_type})>"


class AIConversationMessage(Base):
    """
    AI Conversation Message Model
    
    Stores individual messages within AI conversations.
    Supports different message types and AI metadata.
    
    Educational Note:
    - Tracks message metadata for AI performance analysis
    - Supports various message types (text, image, file, etc.)
    - Provides user feedback tracking for AI improvement
    """
    __tablename__ = "ai_conversation_messages"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(CHAR(36), ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Message content
    sender_type = Column(SQLEnum(SenderType), nullable=False, comment="Who sent the message")
    message = Column(Text, nullable=False, comment="Message content")
    message_type = Column(SQLEnum(MessageType), default=MessageType.TEXT, comment="Type of message")
    attachments = Column(JSON, comment="File attachments and media")
    
    # AI-specific metadata (for AI messages)
    ai_model_used = Column(String(50), comment="AI model used for response")
    processing_time_ms = Column(Integer, default=0, comment="Time taken to generate response")
    confidence_score = Column(DECIMAL(5, 2), default=0.00, comment="AI confidence in response")
    
    # User feedback
    is_helpful = Column(Boolean, comment="User feedback on message helpfulness")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    conversation = relationship("AIConversation", back_populates="messages")

    # Indexes for performance
    __table_args__ = (
        Index('ix_ai_conversation_messages_conversation_sender', 'conversation_id', 'sender_type'),
        Index('ix_ai_conversation_messages_created_at', 'created_at'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<AIConversationMessage(id={self.id}, sender={self.sender_type})>"


# --------------------------------------------------------
# KNOWLEDGE BASE AND SETTINGS
# --------------------------------------------------------

class AIKnowledgeBase(Base):
    """
    AI Knowledge Base Model
    
    Stores structured knowledge content for AI to reference.
    Supports different content types and search functionality.
    
    Educational Note:
    - Provides structured knowledge storage for AI responses
    - Supports content categorization and tagging
    - Tracks usage metrics for content optimization
    """
    __tablename__ = "ai_knowledge_base"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Content information
    title = Column(String(255), nullable=False, comment="Knowledge item title")
    content = Column(Text, nullable=False, comment="Knowledge content")
    content_type = Column(SQLEnum(ContentType), nullable=False, comment="Type of content")
    
    # Organization and search
    category = Column(String(100), comment="Content category")
    tags = Column(JSON, comment="Search tags")
    search_keywords = Column(Text, comment="Keywords for search optimization")
    
    # Priority and status
    priority = Column(Integer, default=1, comment="Content priority (1-10)")
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Usage metrics
    view_count = Column(Integer, default=0, comment="Number of times viewed")
    helpful_count = Column(Integer, default=0, comment="Number of helpful votes")
    not_helpful_count = Column(Integer, default=0, comment="Number of not helpful votes")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    academy = relationship("Academy", back_populates="ai_knowledge_base")

    # Indexes for performance
    __table_args__ = (
        Index('ix_ai_knowledge_base_academy_active', 'academy_id', 'is_active'),
        Index('ix_ai_knowledge_base_content_type', 'content_type'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<AIKnowledgeBase(id={self.id}, title={self.title})>"


class AIPerformanceMetric(Base):
    """
    AI Performance Metrics Model
    
    Tracks AI system performance and usage statistics.
    Provides insights for system optimization.
    
    Educational Note:
    - Comprehensive performance tracking for AI services
    - Cost tracking for AI API usage
    - Error monitoring and success rate tracking
    """
    __tablename__ = "ai_performance_metrics"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_type = Column(SQLEnum(MetricType), nullable=False, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Request and response data
    request_data = Column(JSON, comment="Request parameters and input data")
    response_data = Column(JSON, comment="Response metadata and output")
    
    # Performance metrics
    processing_time_ms = Column(Integer, default=0, comment="Processing time in milliseconds")
    accuracy_score = Column(DECIMAL(5, 2), default=0.00, comment="Accuracy score if applicable")
    
    # Status and error tracking
    success = Column(Boolean, default=True, nullable=False, index=True)
    error_message = Column(Text, comment="Error message if request failed")
    
    # Cost tracking
    tokens_used = Column(Integer, default=0, comment="Number of tokens consumed")
    cost_usd = Column(DECIMAL(10, 6), default=0.000000, comment="Cost in USD")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    academy = relationship("Academy", back_populates="ai_performance_metrics")
    user = relationship("User", back_populates="ai_performance_metrics")

    # Indexes for performance
    __table_args__ = (
        Index('ix_ai_performance_metrics_type_success', 'metric_type', 'success'),
        Index('ix_ai_performance_metrics_academy_created', 'academy_id', 'created_at'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<AIPerformanceMetric(id={self.id}, type={self.metric_type}, success={self.success})>"


class AISetting(Base):
    """
    AI Settings Model
    
    Stores configuration settings for AI system functionality.
    Supports different setting types and academy-specific configurations.
    
    Educational Note:
    - Flexible configuration system for AI parameters
    - Support for different data types (string, number, boolean, JSON)
    - Academy-specific settings for customization
    """
    __tablename__ = "ai_settings"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Setting configuration
    setting_key = Column(String(100), nullable=False, comment="Setting identifier")
    setting_value = Column(Text, comment="Setting value")
    setting_type = Column(SQLEnum(SettingType), default=SettingType.STRING, comment="Data type of setting")
    
    # Setting metadata
    description = Column(Text, comment="Setting description")
    default_value = Column(Text, comment="Default value")
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    academy = relationship("Academy", back_populates="ai_settings")

    # Indexes for performance
    __table_args__ = (
        Index('ix_ai_settings_academy_key', 'academy_id', 'setting_key'),
        Index('ix_ai_settings_key_active', 'setting_key', 'is_active'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )

    def __repr__(self):
        return f"<AISetting(id={self.id}, key={self.setting_key})>" 