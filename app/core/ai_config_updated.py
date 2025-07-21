"""
Updated AI Configuration with support for hourly rate limiting
"""
import os
from typing import Dict, Optional
from enum import Enum
from pydantic import BaseModel, Field

from app.services.ai.rate_limit_handler import RateLimitHandler, RateLimitUnit
from app.core.config import settings


class AIProvider(str, Enum):
    """Supported AI service providers"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    GOOGLE_AI = "google_ai"
    ANTHROPIC = "anthropic"


class AIServiceType(str, Enum):
    """Types of AI services"""
    TRANSCRIPTION = "transcription"
    CHAT_COMPLETION = "chat_completion"
    TEXT_GENERATION = "text_generation"
    EMBEDDING = "embedding"


class AIServiceConfig(BaseModel):
    """Configuration for a specific AI service with enhanced rate limiting"""
    provider: AIProvider
    service_type: AIServiceType
    api_key: str = Field(..., description="API key for the service")
    api_base: Optional[str] = Field(None, description="Custom API base URL")
    model_name: str = Field(..., description="Model name to use")
    max_tokens: int = Field(default=4000, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, description="Model temperature")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    
    # Enhanced rate limiting settings
    rate_limit_value: int = Field(default=40, description="Rate limit value")
    rate_limit_unit: RateLimitUnit = Field(default=RateLimitUnit.HOUR, description="Rate limit unit")
    
    # Backward compatibility
    rate_limit_per_minute: Optional[int] = Field(None, description="Rate limit per minute (deprecated)")
    rate_limit_per_hour: Optional[int] = Field(None, description="Rate limit per hour")
    
    is_active: bool = Field(default=True, description="Whether service is active")
    
    class Config:
        env_prefix = "AI_"
    
    def get_rate_limiter(self) -> RateLimitHandler:
        """Get a rate limiter instance based on configuration"""
        return RateLimitHandler(
            requests_per_unit=self.rate_limit_value,
            time_unit=self.rate_limit_unit
        )


class AIConfigManager:
    """
    Enhanced AI configuration manager with hourly rate limiting support
    """
    
    def __init__(self):
        self._configs: Dict[str, AIServiceConfig] = {}
        self._load_default_configs()
    
    def _load_default_configs(self):
        """Load default AI service configurations with hourly rate limiting"""
        
        # Get rate limiting settings from environment
        rate_limit_unit = getattr(settings, "OPENAI_RATE_LIMIT_UNIT", "hour")
        rate_limit_value = getattr(settings, "OPENAI_RATE_LIMIT_PER_HOUR", 40)
        
        # Support legacy minute-based config
        if rate_limit_unit == "minute":
            rate_limit_value = getattr(settings, "OPENAI_RATE_LIMIT", 40)
        
        # OpenAI Configuration for transcription
        if settings.OPENAI_API_KEY:
            self._configs["transcription"] = AIServiceConfig(
                provider=AIProvider.OPENAI,
                service_type=AIServiceType.TRANSCRIPTION,
                api_key=settings.OPENAI_API_KEY,
                model_name="whisper-1",
                max_tokens=0,  # Not applicable for transcription
                temperature=0.0,
                rate_limit_value=rate_limit_value,
                rate_limit_unit=RateLimitUnit(rate_limit_unit)
            )
        
        # OpenAI Configuration for chat completion
        if settings.OPENAI_API_KEY:
            self._configs["chat"] = AIServiceConfig(
                provider=AIProvider.OPENAI,
                service_type=AIServiceType.CHAT_COMPLETION,
                api_key=settings.OPENAI_API_KEY,
                model_name=settings.OPENAI_MODEL,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
                rate_limit_value=rate_limit_value,
                rate_limit_unit=RateLimitUnit(rate_limit_unit)
            )
        
        # Azure OpenAI Configuration (if available)
        if getattr(settings, "AZURE_OPENAI_API_KEY", None):
            azure_rate_limit_unit = getattr(settings, "AZURE_OPENAI_RATE_LIMIT_UNIT", "hour")
            azure_rate_limit_value = getattr(settings, "AZURE_OPENAI_RATE_LIMIT_PER_HOUR", 60)
            
            self._configs["azure_chat"] = AIServiceConfig(
                provider=AIProvider.AZURE_OPENAI,
                service_type=AIServiceType.CHAT_COMPLETION,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_base=getattr(settings, "AZURE_OPENAI_ENDPOINT", None),
                model_name=getattr(settings, "AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
                max_tokens=getattr(settings, "AZURE_OPENAI_MAX_TOKENS", 4000),
                temperature=getattr(settings, "AZURE_OPENAI_TEMPERATURE", 0.7),
                rate_limit_value=azure_rate_limit_value,
                rate_limit_unit=RateLimitUnit(azure_rate_limit_unit)
            )
    
    def get_config(self, service_name: str) -> Optional[AIServiceConfig]:
        """Get configuration for a specific service"""
        return self._configs.get(service_name)
    
    def add_config(self, service_name: str, config: AIServiceConfig):
        """Add a new service configuration"""
        self._configs[service_name] = config
    
    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available and active"""
        config = self.get_config(service_name)
        return config is not None and config.is_active
    
    def get_available_services(self) -> Dict[str, str]:
        """Get all available services with their types"""
        return {
            name: config.service_type.value
            for name, config in self._configs.items()
            if config.is_active
        }
    
    def get_rate_limit_status(self, service_name: str) -> Optional[Dict]:
        """Get rate limiting status for a service"""
        config = self.get_config(service_name)
        if not config:
            return None
        
        rate_limiter = config.get_rate_limiter()
        return rate_limiter.get_status()
    
    def update_rate_limit(self, service_name: str, value: int, unit: RateLimitUnit):
        """Update rate limiting for a service"""
        config = self.get_config(service_name)
        if config:
            config.rate_limit_value = value
            config.rate_limit_unit = unit


class AIServiceFactory:
    """Factory for creating AI service instances with updated rate limiting"""
    
    config_manager = AIConfigManager()
    
    @staticmethod
    def create_transcription_service():
        """Create transcription service with hourly rate limiting"""
        from app.services.ai.openai_service_updated import OpenAITranscriptionService
        
        config = AIServiceFactory.config_manager.get_config("transcription")
        if not config:
            raise ValueError("Transcription service not configured")
        
        return OpenAITranscriptionService(config)
    
    @staticmethod
    def create_chat_service(preferred_provider: Optional[str] = None):
        """Create chat service with hourly rate limiting"""
        from app.services.ai.openai_service_updated import OpenAIChatService
        
        # Try to get the preferred provider first
        config = None
        if preferred_provider:
            config = AIServiceFactory.config_manager.get_config(preferred_provider)
        
        # Fall back to default chat service
        if not config:
            config = AIServiceFactory.config_manager.get_config("chat")
        
        if not config:
            raise ValueError("Chat service not configured")
        
        return OpenAIChatService(config)
    
    @staticmethod
    def get_config_manager() -> AIConfigManager:
        """Get the configuration manager instance"""
        return AIServiceFactory.config_manager 