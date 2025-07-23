from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.db.base import Base


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    logo = Column(String(255), nullable=True)
    favicon = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(255), nullable=True)
    address = Column(String(255), nullable=True)
    facebook = Column(String(255), nullable=True)
    twitter = Column(String(255), nullable=True)
    instagram = Column(String(255), nullable=True)
    youtube = Column(String(255), nullable=True)
    linkedin = Column(String(255), nullable=True)
    whatsapp = Column(String(255), nullable=True)
    snapchat = Column(String(255), nullable=True)
    tiktok = Column(String(255), nullable=True)
    telegram = Column(String(255), nullable=True)
    discord = Column(String(255), nullable=True)
    terms = Column(Text, nullable=True)
    privacy = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)
    subdomain = Column(String(255), nullable=True)
    domain = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Settings(id={self.id}, title='{self.title}')>" 
 
 
 