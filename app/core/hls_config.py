from typing import Dict, List, Optional
from pydantic import BaseModel
from pathlib import Path


class HLSConfig(BaseModel):
    """
    HLS Configuration with advanced security settings
    """
    
    # Basic HLS settings
    segment_duration: int = 6  # seconds per segment
    playlist_type: str = "vod"  # video on demand
    independent_segments: bool = True
    
    # Quality levels configuration - جودتان فقط: عالية ومنخفضة
    quality_levels: List[Dict[str, str]] = [
        {"name": "high", "height": "720", "bitrate": "2800k", "resolution": "1280x720", "label": "جودة عالية"},
        {"name": "low", "height": "480", "bitrate": "1400k", "resolution": "854x480", "label": "جودة منخفضة"}
    ]
    
    # Encryption settings
    encryption_method: str = "AES-128"
    key_expiry_hours: int = 24
    key_rotation_enabled: bool = True
    
    # Security settings
    session_timeout_minutes: int = 120  # 2 hours
    max_concurrent_sessions: int = 3
    ip_whitelist_enabled: bool = False
    ip_whitelist: List[str] = []
    
    # Cache settings
    playlist_cache_seconds: int = 300  # 5 minutes
    segment_cache_seconds: int = 3600  # 1 hour
    key_cache_seconds: int = 60  # 1 minute
    
    # Rate limiting
    requests_per_minute: int = 60
    burst_limit: int = 10
    
    # File paths
    output_directory: str = "temp_hls"
    key_directory: str = "keys"
    
    # FFmpeg settings
    ffmpeg_preset: str = "medium"
    ffmpeg_crf: int = 23
    ffmpeg_threads: int = 0  # auto
    
    # Advanced security
    watermark_enabled: bool = True
    watermark_text: str = "SAYAN"
    watermark_opacity: float = 0.3
    
    # Monitoring
    access_logging: bool = True
    error_logging: bool = True
    analytics_enabled: bool = True
    
    class Config:
        env_prefix = "HLS_"


class SecurityConfig(BaseModel):
    """
    Security configuration for HLS streaming
    """
    
    # User agent blocking
    blocked_user_agents: List[str] = [
        "curl", "wget", "youtube-dl", "yt-dlp",
        "ffmpeg", "aria2", "idm", "fdm", "jdownloader",
        "download", "spider", "crawler", "bot"
    ]
    
    # Allowed user agents for development
    allowed_dev_agents: List[str] = [
        "python-requests", "postman", "insomnia", "httpie", "test"
    ]
    
    # Valid browser patterns
    valid_browsers: List[str] = [
        "chrome", "firefox", "safari", "edge", "opera", 
        "mozilla", "webkit", "thunder", "powershell", "webrequest"
    ]
    
    # Suspicious headers to check
    suspicious_headers: List[str] = [
        "x-forwarded-for", "x-real-ip", "x-forwarded-proto",
        "x-forwarded-host", "x-forwarded-port"
    ]
    
    # Rate limiting per IP
    rate_limit_per_ip: int = 100  # requests per minute
    rate_limit_burst: int = 20
    
    # Session security
    session_fingerprint_enabled: bool = True
    session_timeout_seconds: int = 7200  # 2 hours
    
    # Encryption
    key_rotation_interval_hours: int = 24
    key_verification_enabled: bool = True
    
    # Monitoring
    suspicious_activity_threshold: int = 10
    block_duration_minutes: int = 60
    
    class Config:
        env_prefix = "HLS_SECURITY_"


class QualityConfig(BaseModel):
    """
    Quality configuration for different scenarios
    """
    
    # Default quality for different connection types - جودتان فقط
    default_qualities: Dict[str, str] = {
        "mobile": "low",
        "tablet": "low", 
        "desktop": "high",
        "high_speed": "high"
    }
    
    # Adaptive bitrate settings
    adaptive_bitrate: bool = True
    bandwidth_buffer: float = 1.2  # 20% buffer
    
    # Quality switching thresholds
    switch_up_threshold: float = 0.8  # 80% of current level
    switch_down_threshold: float = 0.6  # 60% of current level
    
    # Minimum quality for different screen sizes - جودتان فقط
    min_quality_by_screen: Dict[str, str] = {
        "small": "low",    # < 480px
        "medium": "low",   # 480px - 768px
        "large": "high",   # 768px - 1024px
        "xlarge": "high"   # > 1024px
    }
    
    class Config:
        env_prefix = "HLS_QUALITY_"


# Global configuration instances
hls_config = HLSConfig()
security_config = SecurityConfig()
quality_config = QualityConfig()


def get_hls_config() -> HLSConfig:
    """Get HLS configuration"""
    return hls_config


def get_security_config() -> SecurityConfig:
    """Get security configuration"""
    return security_config


def get_quality_config() -> QualityConfig:
    """Get quality configuration"""
    return quality_config


def validate_hls_setup() -> Dict[str, bool]:
    """
    Validate HLS setup and return status
    """
    status = {
        "ffmpeg_available": False,
        "output_directory_writable": False,
        "key_directory_writable": False,
        "encryption_supported": False
    }
    
    try:
        # Check FFmpeg
        from app.core.ffmpeg_config import FFmpegConfig
        FFmpegConfig.get_ffmpeg_path()
        status["ffmpeg_available"] = True
    except:
        pass
    
    # Check directories
    output_dir = Path(hls_config.output_directory)
    key_dir = Path(hls_config.key_directory)
    
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        test_file = output_dir / "test.txt"
        test_file.write_text("test")
        test_file.unlink()
        status["output_directory_writable"] = True
    except:
        pass
    
    try:
        key_dir.mkdir(parents=True, exist_ok=True)
        test_file = key_dir / "test.txt"
        test_file.write_text("test")
        test_file.unlink()
        status["key_directory_writable"] = True
    except:
        pass
    
    # Check encryption support
    try:
        import secrets
        import hashlib
        status["encryption_supported"] = True
    except:
        pass
    
    return status


def get_quality_by_bandwidth(bandwidth_kbps: int) -> str:
    """
    Determine optimal quality based on bandwidth - جودتان فقط
    """
    if bandwidth_kbps >= 2800:
        return "high"
    else:
        return "low"


def get_quality_by_screen_size(width: int, height: int) -> str:
    """
    Determine optimal quality based on screen size - جودتان فقط
    """
    max_dimension = max(width, height)
    
    if max_dimension >= 1280:
        return "high"
    else:
        return "low" 