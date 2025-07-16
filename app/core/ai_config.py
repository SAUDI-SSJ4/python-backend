"""
AI Configuration Management System
==================================

This module handles AI service configurations and API keys management
for the SAYAN Academy Platform AI Assistant system.
"""

import os
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
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
    """Configuration for a specific AI service"""
    provider: AIProvider
    service_type: AIServiceType
    api_key: str = Field(..., description="API key for the service")
    api_base: Optional[str] = Field(None, description="Custom API base URL")
    model_name: str = Field(..., description="Model name to use")
    max_tokens: int = Field(default=4000, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, description="Model temperature")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute")
    is_active: bool = Field(default=True, description="Whether service is active")
    
    class Config:
        env_prefix = "AI_"


class AIConfigManager:
    """
    Manages AI service configurations and provides access to AI services.
    
    This class handles:
    - Loading configurations from environment variables
    - Managing API keys securely
    - Providing service instances
    - Rate limiting and error handling
    """
    
    def __init__(self):
        self._configs: Dict[str, AIServiceConfig] = {}
        self._load_default_configs()
    
    def _load_default_configs(self):
        """Load default AI service configurations"""
        
        # OpenAI Configuration for transcription
        if os.getenv("OPENAI_API_KEY"):
            self._configs["transcription"] = AIServiceConfig(
                provider=AIProvider.OPENAI,
                service_type=AIServiceType.TRANSCRIPTION,
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="whisper-1",
                max_tokens=0,  # Not applicable for transcription
                temperature=0.0,
                rate_limit_per_minute=50
            )
        
        # OpenAI Configuration for chat completion
        if os.getenv("OPENAI_API_KEY"):
            self._configs["chat"] = AIServiceConfig(
                provider=AIProvider.OPENAI,
                service_type=AIServiceType.CHAT_COMPLETION,
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name=os.getenv("OPENAI_MODEL", "gpt-4"),
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
                temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
                rate_limit_per_minute=int(os.getenv("OPENAI_RATE_LIMIT", "40"))
            )
        
        # Azure OpenAI Configuration (if available)
        if os.getenv("AZURE_OPENAI_API_KEY"):
            self._configs["azure_chat"] = AIServiceConfig(
                provider=AIProvider.AZURE_OPENAI,
                service_type=AIServiceType.CHAT_COMPLETION,
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_base=os.getenv("AZURE_OPENAI_ENDPOINT"),
                model_name=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
                max_tokens=int(os.getenv("AZURE_OPENAI_MAX_TOKENS", "4000")),
                temperature=float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.7"))
            )
    
    def get_config(self, service_name: str) -> Optional[AIServiceConfig]:
        """Get configuration for a specific service"""
        return self._configs.get(service_name)
    
    def add_config(self, service_name: str, config: AIServiceConfig):
        """Add or update a service configuration"""
        self._configs[service_name] = config
    
    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available and active"""
        config = self._configs.get(service_name)
        return config is not None and config.is_active
    
    def get_available_services(self) -> Dict[str, str]:
        """Get list of available services with their providers"""
        return {
            name: config.provider.value 
            for name, config in self._configs.items() 
            if config.is_active
        }


# Global AI configuration manager instance
ai_config = AIConfigManager()


class AIServiceFactory:
    """Factory class for creating AI service instances"""
    
    @staticmethod
    def create_transcription_service():
        """Create transcription service instance"""
        config = ai_config.get_config("transcription")
        if not config:
            raise ValueError("Transcription service not configured")
        
        if config.provider == AIProvider.OPENAI:
            from app.services.ai.openai_service import OpenAITranscriptionService
            return OpenAITranscriptionService(config)
        else:
            raise ValueError(f"Unsupported transcription provider: {config.provider}")
    
    @staticmethod
    def create_chat_service(preferred_provider: Optional[str] = None):
        """Create chat completion service instance"""
        service_name = preferred_provider or "chat"
        config = ai_config.get_config(service_name)
        
        if not config:
            # Try alternative providers
            for name in ["azure_chat", "chat"]:
                config = ai_config.get_config(name)
                if config:
                    break
        
        if not config:
            raise ValueError("No chat service configured")
        
        if config.provider in [AIProvider.OPENAI, AIProvider.AZURE_OPENAI]:
            from app.services.ai.openai_service import OpenAIChatService
            return OpenAIChatService(config)
        else:
            raise ValueError(f"Unsupported chat provider: {config.provider}")


# Environment variables guide for .env file:
"""
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.7
OPENAI_RATE_LIMIT=40

# Azure OpenAI Configuration (optional)
AZURE_OPENAI_API_KEY=your_azure_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_MAX_TOKENS=4000
AZURE_OPENAI_TEMPERATURE=0.7

# AI Features Toggle
AI_TRANSCRIPTION_ENABLED=true
AI_CHAT_ENABLED=true
AI_EXAM_CORRECTION_ENABLED=true
AI_QUESTION_GENERATION_ENABLED=true
AI_SUMMARIZATION_ENABLED=true
""" 