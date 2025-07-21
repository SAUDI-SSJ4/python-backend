from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.db.base import Base


class AIAnswer(Base):
    """
    AI Answer model for storing AI-generated responses to student questions.
    
    This model supports AI-powered Q&A functionality within lessons,
    allowing students to ask questions and receive intelligent responses.
    """
    __tablename__ = "ai_answers"

    # Primary identification
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    
    # Q&A content
    question = Column(String(255), nullable=False)
    answer = Column(Text, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships - معلق مؤقتاً لحل conflicts
    # lesson = relationship("Lesson", back_populates="ai_answers")
    # student = relationship("Student", back_populates="ai_answers")

    def __repr__(self):
        return f"<AIAnswer(id={self.id}, lesson_id='{self.lesson_id}', question='{self.question[:50]}...')>"
    
    @property
    def question_preview(self) -> str:
        """Get truncated question for preview"""
        return self.question[:100] + "..." if len(self.question) > 100 else self.question
    
    @property
    def answer_preview(self) -> str:
        """Get truncated answer for preview"""
        return self.answer[:200] + "..." if len(self.answer) > 200 else self.answer 