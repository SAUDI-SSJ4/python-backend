from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), unique=True, nullable=False)
    theme_name = Column(String(100), default="default")
    primary_color = Column(String(7), default="#007bff")
    secondary_color = Column(String(7), default="#6c757d")
    font_family = Column(String(100), default="Arial")
    custom_css = Column(Text, nullable=True)
    custom_js = Column(Text, nullable=True)
    header_config = Column(JSON, nullable=True)
    footer_config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy", back_populates="templates")


class About(Base):
    __tablename__ = "abouts"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    mission = Column(Text, nullable=True)
    vision = Column(Text, nullable=True)
    values = Column(JSON, nullable=True)
    image = Column(String(255), nullable=True)
    video_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy")


class Slider(Base):
    __tablename__ = "sliders"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    title = Column(String(255), nullable=True)
    subtitle = Column(String(255), nullable=True)
    image = Column(String(255), nullable=False)
    link = Column(String(500), nullable=True)
    button_text = Column(String(100), nullable=True)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy")


class Faq(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy")


class Opinion(Base):
    __tablename__ = "opinions"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    rating = Column(Integer, default=5)  # 1-5
    image = Column(String(255), nullable=True)
    is_featured = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy")
    student = relationship("Student") 