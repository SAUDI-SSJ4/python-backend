"""
OpenAI Service Implementation
=============================

Core OpenAI services for transcription and chat completion.
Includes comprehensive error handling and rate limiting.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, List
import openai
from openai import OpenAI, AsyncOpenAI
from openai.types.audio import Transcription
from openai.types.chat import ChatCompletion

from app.core.ai_config import AIServiceConfig, AIServiceType
from app.models.ai_assistant import AIPerformanceMetric, MetricType
from app.db.session import SessionLocal


logger = logging.getLogger(__name__)


class OpenAIServiceError(Exception):
    """Custom exception for OpenAI service errors"""
    def __init__(self, message: str, error_code: Optional[str] = None, original_error: Optional[Exception] = None):
        self.message = message
        self.error_code = error_code
        self.original_error = original_error
        super().__init__(self.message)


class RateLimitHandler:
    """Simple rate limiting handler"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_times: List[float] = []
    
    def can_make_request(self) -> bool:
        """Check if we can make a request without hitting rate limits"""
        current_time = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        return len(self.request_times) < self.requests_per_minute
    
    def record_request(self):
        """Record that a request was made"""
        self.request_times.append(time.time())
    
    def get_wait_time(self) -> float:
        """Get time to wait before next request"""
        if not self.request_times:
            return 0
        
        oldest_request = min(self.request_times)
        time_since_oldest = time.time() - oldest_request
        
        if time_since_oldest >= 60:
            return 0
        
        return 60 - time_since_oldest


class BaseOpenAIService:
    """Base class for OpenAI services with common functionality"""
    
    def __init__(self, config: AIServiceConfig):
        self.config = config
        self.rate_limiter = RateLimitHandler(config.rate_limit_per_minute)
        
        # Initialize OpenAI clients
        self._init_clients()
    
    def _init_clients(self):
        """Initialize OpenAI clients"""
        try:
            if self.config.api_base:
                # Azure OpenAI configuration
                self.client = OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.api_base
                )
                self.async_client = AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.api_base
                )
            else:
                # Standard OpenAI configuration
                self.client = OpenAI(api_key=self.config.api_key)
                self.async_client = AsyncOpenAI(api_key=self.config.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI clients: {str(e)}")
            raise OpenAIServiceError("Failed to initialize OpenAI service", original_error=e)
    
    def _check_rate_limit(self):
        """Check and handle rate limiting"""
        if not self.rate_limiter.can_make_request():
            wait_time = self.rate_limiter.get_wait_time()
            raise OpenAIServiceError(
                f"Rate limit exceeded. Wait {wait_time:.1f} seconds.",
                error_code="RATE_LIMIT_EXCEEDED"
            )
        
        self.rate_limiter.record_request()
    
    def _log_metric(self, service_type: MetricType, request_data: Dict[str, Any], 
                   response_data: Optional[Dict[str, Any]] = None, 
                   processing_time_ms: int = 0, tokens_used: int = 0, 
                   success: bool = True, error_message: Optional[str] = None,
                   academy_id: Optional[int] = None):
        """Log performance metrics to database"""
        try:
            with SessionLocal() as db:
                metric = AIPerformanceMetric(
                    academy_id=academy_id,
                    metric_type=service_type,
                    request_data=request_data,
                    response_data=response_data,
                    processing_time_ms=processing_time_ms,
                    tokens_used=tokens_used,
                    success=success,
                    error_message=error_message
                )
                db.add(metric)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to log AI metric: {str(e)}")


class OpenAITranscriptionService(BaseOpenAIService):
    """OpenAI Whisper transcription service"""
    
    async def transcribe_audio(
        self, 
        audio_file: Any, 
        language: str = "ar",
        academy_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using OpenAI Whisper API
        
        Args:
            audio_file: Audio file to transcribe
            language: Language code (default: 'ar' for Arabic)
            academy_id: Academy ID for metrics
            
        Returns:
            Dictionary containing transcription results
            
        Raises:
            OpenAIServiceError: If transcription fails
        """
        start_time = time.time()
        request_data = {
            "model": self.config.model_name,
            "language": language,
            "response_format": "verbose_json"
        }
        
        try:
            # Check rate limits
            self._check_rate_limit()
            
            logger.info(f"Starting transcription with model {self.config.model_name}")
            
            # Make transcription request
            response: Transcription = await self.async_client.audio.transcriptions.create(
                model=self.config.model_name,
                file=audio_file,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Process response
            result = {
                "text": response.text,
                "language": response.language,
                "duration": getattr(response, 'duration', 0),
                "segments": []
            }
            
            # Extract segments if available
            if hasattr(response, 'segments') and response.segments:
                result["segments"] = [
                    {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text,
                        "confidence": getattr(segment, 'avg_logprob', 0.0)
                    }
                    for segment in response.segments
                ]
            
            # Log success metric
            self._log_metric(
                service_type=MetricType.TRANSCRIPTION,
                request_data=request_data,
                response_data={"duration": result["duration"], "segments_count": len(result["segments"])},
                processing_time_ms=processing_time_ms,
                success=True,
                academy_id=academy_id
            )
            
            logger.info(f"Transcription completed successfully in {processing_time_ms}ms")
            return result
            
        except openai.RateLimitError as e:
            error_msg = f"OpenAI rate limit exceeded: {str(e)}"
            logger.error(error_msg)
            
            self._log_metric(
                service_type=MetricType.TRANSCRIPTION,
                request_data=request_data,
                processing_time_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=error_msg,
                academy_id=academy_id
            )
            
            raise OpenAIServiceError(error_msg, error_code="RATE_LIMIT", original_error=e)
            
        except openai.AuthenticationError as e:
            error_msg = f"OpenAI authentication failed: {str(e)}"
            logger.error(error_msg)
            
            self._log_metric(
                service_type=MetricType.TRANSCRIPTION,
                request_data=request_data,
                processing_time_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=error_msg,
                academy_id=academy_id
            )
            
            raise OpenAIServiceError(error_msg, error_code="AUTH_ERROR", original_error=e)
            
        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            logger.error(error_msg)
            
            self._log_metric(
                service_type=MetricType.TRANSCRIPTION,
                request_data=request_data,
                processing_time_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=error_msg,
                academy_id=academy_id
            )
            
            raise OpenAIServiceError(error_msg, original_error=e)


class OpenAIChatService(BaseOpenAIService):
    """OpenAI Chat Completion service"""
    
    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        academy_id: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate chat completion using OpenAI API
        
        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            academy_id: Academy ID for metrics
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing completion results
            
        Raises:
            OpenAIServiceError: If completion fails
        """
        start_time = time.time()
        
        # Prepare messages
        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend(messages)
        
        request_data = {
            "model": self.config.model_name,
            "messages": chat_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature)
        }
        
        try:
            # Check rate limits
            self._check_rate_limit()
            
            logger.info(f"Starting chat completion with model {self.config.model_name}")
            
            # Make completion request
            response: ChatCompletion = await self.async_client.chat.completions.create(
                model=self.config.model_name,
                messages=chat_messages,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                timeout=self.config.timeout
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract response data
            choice = response.choices[0]
            result = {
                "content": choice.message.content,
                "role": choice.message.role,
                "finish_reason": choice.finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                }
            }
            
            # Log success metric
            self._log_metric(
                service_type=MetricType.CONVERSATION,
                request_data=request_data,
                response_data={"finish_reason": result["finish_reason"]},
                processing_time_ms=processing_time_ms,
                tokens_used=result["usage"]["total_tokens"],
                success=True,
                academy_id=academy_id
            )
            
            logger.info(f"Chat completion completed successfully in {processing_time_ms}ms")
            return result
            
        except openai.RateLimitError as e:
            error_msg = f"OpenAI rate limit exceeded: {str(e)}"
            logger.error(error_msg)
            
            self._log_metric(
                service_type=MetricType.CONVERSATION,
                request_data=request_data,
                processing_time_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=error_msg,
                academy_id=academy_id
            )
            
            raise OpenAIServiceError(error_msg, error_code="RATE_LIMIT", original_error=e)
            
        except openai.AuthenticationError as e:
            error_msg = f"OpenAI authentication failed: {str(e)}"
            logger.error(error_msg)
            
            self._log_metric(
                service_type=MetricType.CONVERSATION,
                request_data=request_data,
                processing_time_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=error_msg,
                academy_id=academy_id
            )
            
            raise OpenAIServiceError(error_msg, error_code="AUTH_ERROR", original_error=e)
            
        except Exception as e:
            error_msg = f"Chat completion failed: {str(e)}"
            logger.error(error_msg)
            
            self._log_metric(
                service_type=MetricType.CONVERSATION,
                request_data=request_data,
                processing_time_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=error_msg,
                academy_id=academy_id
            )
            
            raise OpenAIServiceError(error_msg, original_error=e)
    
    async def generate_exam_feedback(
        self,
        exam_data: Dict[str, Any],
        student_answers: List[Dict[str, Any]],
        academy_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate personalized exam feedback using AI
        
        Args:
            exam_data: Exam questions and correct answers
            student_answers: Student's submitted answers
            academy_id: Academy ID for metrics
            
        Returns:
            Dictionary containing feedback and recommendations
        """
        system_prompt = """أنت مساعد تعليمي ذكي متخصص في تقييم أداء الطلاب وتقديم التوجيه المناسب.
        مهمتك هي تحليل إجابات الطالب وتقديم ملاحظات بناءة وتوصيات للتحسين.
        اجعل ردودك إيجابية ومحفزة ومفيدة للطالب."""
        
        # Prepare analysis prompt
        analysis_prompt = f"""
        تحليل نتائج الامتحان:
        
        بيانات الامتحان: {exam_data}
        
        إجابات الطالب: {student_answers}
        
        يرجى تقديم:
        1. تقييم شامل لأداء الطالب
        2. نقاط القوة والضعف
        3. توصيات محددة للتحسين
        4. خطة دراسية مقترحة
        5. كلمات تشجيعية للطالب
        
        قدم الرد في صيغة JSON مع المفاتيح التالية:
        - overall_feedback
        - strengths
        - weaknesses
        - recommendations
        - study_plan
        - encouragement_message
        """
        
        messages = [{"role": "user", "content": analysis_prompt}]
        
        return await self.generate_completion(
            messages=messages,
            system_prompt=system_prompt,
            academy_id=academy_id,
            temperature=0.7
        ) 