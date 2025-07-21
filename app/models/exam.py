from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.db.base import Base
import enum
import uuid


class QuestionType(str, enum.Enum):
    """Question type enumeration for different assessment formats"""
    MULTIPLE_CHOICE = "multiple_choice"  # Traditional multiple choice
    TRUE_FALSE = "true_false"   # True/False questions
    TEXT = "text"              # Text input questions


class Exam(Base):
    """
    Exam model representing quizzes and assessments within lessons.
    
    Exams can contain multiple questions of different types and provide
    interactive assessment capabilities for student evaluation.
    """
    __tablename__ = "exams"

    # Primary identification
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    
    # Exam information
    title = Column(String(255))
    question = Column(String(300))  # Main question text (legacy field)
    answers = Column(JSON)  # JSON array of possible answers (legacy field)
    correct_answer = Column(JSON)  # JSON array of correct answers (legacy field)
    order_number = Column(Integer, default=0, index=True)
    status = Column(Boolean, default=True, nullable=False)
    duration = Column(Integer, default=0)  # Duration in seconds
    question_type = Column(SQLEnum(QuestionType), default=QuestionType.MULTIPLE_CHOICE, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    lesson = relationship("Lesson", back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    
    # AI Assistant relationships
    ai_corrections = relationship("ExamCorrection", back_populates="exam", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Exam(id={self.id}, title='{self.title}', type='{self.question_type}')>"
    
    @property
    def questions_count(self) -> int:
        """Get total number of questions in this exam"""
        return len(self.questions) if self.questions else 0
    
    @property
    def total_score(self) -> int:
        """Calculate total possible score for this exam"""
        if not self.questions:
            return 0
        return sum(question.score for question in self.questions)
    
    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string"""
        if not self.duration:
            return "No limit"
        
        minutes = self.duration // 60
        seconds = self.duration % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"
        else:
            return f"{seconds}s"


class Question(Base):
    """
    Question model representing individual questions within an exam.
    
    Each question has a type, score value, and can have multiple options
    for choice-based questions.
    """
    __tablename__ = "questions"

    # Primary identification
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id = Column(CHAR(36), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    
    # Question information
    title = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(SQLEnum(QuestionType), nullable=False)
    score = Column(Integer, nullable=False)
    correct_answer = Column(String(255))  # For text and simple questions
    
    # Indicates whether the question was generated automatically by AI
    is_ai_generated = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    exam = relationship("Exam", back_populates="questions")
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")
    
    # AI Assistant relationships
    ai_corrections = relationship("QuestionCorrection", back_populates="question", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Question(id={self.id}, title='{self.title}', type='{self.type}')>"
    
    @property
    def is_choice_question(self) -> bool:
        """Check if question requires choice options"""
        return self.type in [QuestionType.MULTIPLE_CHOICE, QuestionType.TEXT, QuestionType.TRUE_FALSE]
    
    @property
    def is_text_question(self) -> bool:
        """Check if question requires text input"""
        return self.type == QuestionType.TEXT
    
    @property
    def is_boolean_question(self) -> bool:
        """Check if question is true/false type"""
        return self.type == QuestionType.TRUE_FALSE


class QuestionOption(Base):
    """
    Question option model representing possible answers for choice-based questions.
    
    Each option belongs to a question and can be marked as correct or incorrect.
    """
    __tablename__ = "question_options"

    # Primary identification
    id = Column(CHAR(70), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(CHAR(70), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    
    # Option information
    text = Column(String(255), nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    question = relationship("Question", back_populates="options")

    def __repr__(self):
        return f"<QuestionOption(id={self.id}, text='{self.text}', correct={self.is_correct})>" 