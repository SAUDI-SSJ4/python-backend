from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from app.db.base import Base


class BlacklistedToken(Base):
    """
    Blacklisted JWT tokens for secure logout functionality
    
    This model stores invalidated tokens to prevent their reuse
    even if they haven't expired yet.
    """
    __tablename__ = "blacklisted_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token_jti = Column(String(255), unique=True, index=True, nullable=False, comment="JWT Token ID (jti claim)")
    user_id = Column(Integer, nullable=False, index=True, comment="User ID who owns the token")
    user_type = Column(String(50), nullable=False, comment="Type of user (student/academy/admin)")
    token_type = Column(String(50), nullable=False, default="access", comment="Token type (access/refresh)")
    expires_at = Column(DateTime, nullable=False, comment="Original token expiration time")
    blacklisted_at = Column(DateTime, nullable=False, default=func.now(), comment="When token was blacklisted")
    reason = Column(String(100), default="logout", comment="Reason for blacklisting")
    ip_address = Column(String(45), comment="IP address when token was blacklisted")
    user_agent = Column(Text, comment="User agent when token was blacklisted")
    is_active = Column(Boolean, default=True, comment="Whether blacklist entry is active")
    
    def __repr__(self):
        return f"<BlacklistedToken(jti={self.token_jti}, user_id={self.user_id}, reason={self.reason})>"
    
    @classmethod
    def is_token_blacklisted(cls, db, token_jti: str) -> bool:
        """Check if a token is blacklisted"""
        return db.query(cls).filter(
            cls.token_jti == token_jti,
            cls.is_active == True,
            cls.expires_at > datetime.utcnow()
        ).first() is not None
    
    @classmethod
    def blacklist_token(cls, db, token_jti: str, user_id: int, user_type: str, 
                       expires_at: datetime, token_type: str = "access", 
                       reason: str = "logout", ip_address: str = None, 
                       user_agent: str = None):
        """Add a token to blacklist"""
        blacklisted_token = cls(
            token_jti=token_jti,
            user_id=user_id,
            user_type=user_type,
            token_type=token_type,
            expires_at=expires_at,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(blacklisted_token)
        db.commit()
        return blacklisted_token
    
    @classmethod
    def cleanup_expired_tokens(cls, db):
        """Remove expired blacklisted tokens to keep table clean"""
        expired_count = db.query(cls).filter(
            cls.expires_at < datetime.utcnow()
        ).delete()
        db.commit()
        return expired_count 