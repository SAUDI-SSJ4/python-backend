from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, SmallInteger, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.db.base import Base
import uuid
import enum


class ToolType(str, enum.Enum):
    """Interactive tool types enumeration"""
    COLORED_CARD = "colored_card"    # Colored card with title, description, color, and image
    TIMELINE = "timeline"            # Timeline events with order


class InteractiveTool(Base):
    """
    Interactive tool model for educational tools within lessons.
    
    Supports two types of interactive tools:
    - Colored cards: Display information with title, description, color, and image
    - Timeline: Display chronological events with order
    """
    __tablename__ = "interactive_tools"

    # Primary identification
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(CHAR(36), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    
    # Tool information
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    tool_type = Column(SQLEnum(ToolType), nullable=False, default=ToolType.COLORED_CARD)
    color = Column(String(10), nullable=False, default="#007bff")   # Color theme for the tool
    image = Column(String(255))  # Tool icon or preview image
    order_number = Column(SmallInteger, nullable=False, default=1)  # Display order within lesson
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    lesson = relationship("Lesson", back_populates="interactive_tools")

    def __repr__(self):
        return f"<InteractiveTool(id={self.id}, title='{self.title}', tool_type='{self.tool_type}')>"
    
    @property
    def display_color(self) -> str:
        """Get display color with fallback to default"""
        return self.color if self.color else "#007bff"
    
    @property
    def tool_url(self) -> str:
        """Generate URL for accessing the interactive tool"""
        return f"/api/v1/tools/{self.id}/interactive" 