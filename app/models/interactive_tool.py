from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, SmallInteger
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class InteractiveTool(Base):
    """
    Interactive tool model for educational tools and widgets within lessons.
    
    These tools provide interactive learning experiences such as calculators,
    simulations, diagrams, or other educational utilities.
    """
    __tablename__ = "interactive_tools"

    # Primary identification
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    
    # Tool information
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    image = Column(String(255))  # Tool icon or preview image
    color = Column(String(10))   # Color theme for the tool
    order_number = Column(SmallInteger)  # Display order within lesson
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    lesson = relationship("Lesson", back_populates="interactive_tools")

    def __repr__(self):
        return f"<InteractiveTool(id={self.id}, title='{self.title}', lesson_id='{self.lesson_id}')>"
    
    @property
    def display_color(self) -> str:
        """Get display color with fallback to default"""
        return self.color if self.color else "#007bff"
    
    @property
    def tool_url(self) -> str:
        """Generate URL for accessing the interactive tool"""
        return f"/api/v1/tools/{self.id}/interactive" 