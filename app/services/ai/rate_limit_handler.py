"""
Rate limiting handler for AI services with support for minute and hour-based limits
"""
import time
from typing import List, Literal
from enum import Enum


class RateLimitUnit(str, Enum):
    """Rate limit time units"""
    MINUTE = "minute"
    HOUR = "hour"


class RateLimitHandler:
    """
    Advanced rate limiting handler with support for minute and hour-based limits
    """
    
    def __init__(self, 
                 requests_per_unit: int = 60,
                 time_unit: RateLimitUnit = RateLimitUnit.MINUTE):
        """
        Initialize rate limiter
        
        Args:
            requests_per_unit: Number of requests allowed per time unit
            time_unit: Time unit (minute or hour)
        """
        self.requests_per_unit = requests_per_unit
        self.time_unit = time_unit
        self.request_times: List[float] = []
        
        # Set time window in seconds
        self.time_window = 60 if time_unit == RateLimitUnit.MINUTE else 3600
    
    def can_make_request(self) -> bool:
        """Check if we can make a request without hitting rate limits"""
        current_time = time.time()
        
        # Remove requests older than time window
        self.request_times = [
            t for t in self.request_times 
            if current_time - t < self.time_window
        ]
        
        return len(self.request_times) < self.requests_per_unit
    
    def record_request(self):
        """Record that a request was made"""
        self.request_times.append(time.time())
    
    def get_wait_time(self) -> float:
        """Get time to wait before next request"""
        if not self.request_times:
            return 0
        
        # Find the oldest request
        oldest_request = min(self.request_times)
        time_since_oldest = time.time() - oldest_request
        
        # If oldest request is outside time window, no wait needed
        if time_since_oldest >= self.time_window:
            return 0
        
        # Calculate wait time until oldest request expires
        return self.time_window - time_since_oldest
    
    def get_remaining_requests(self) -> int:
        """Get number of requests remaining in current time window"""
        current_time = time.time()
        
        # Clean old requests
        self.request_times = [
            t for t in self.request_times 
            if current_time - t < self.time_window
        ]
        
        return max(0, self.requests_per_unit - len(self.request_times))
    
    def get_reset_time(self) -> float:
        """Get timestamp when rate limit resets"""
        if not self.request_times:
            return time.time()
        
        oldest_request = min(self.request_times)
        return oldest_request + self.time_window
    
    def get_status(self) -> dict:
        """Get current rate limit status"""
        current_time = time.time()
        
        # Clean old requests
        self.request_times = [
            t for t in self.request_times 
            if current_time - t < self.time_window
        ]
        
        remaining = self.get_remaining_requests()
        reset_time = self.get_reset_time()
        
        return {
            "requests_per_unit": self.requests_per_unit,
            "time_unit": self.time_unit.value,
            "time_window_seconds": self.time_window,
            "current_requests": len(self.request_times),
            "remaining_requests": remaining,
            "can_make_request": remaining > 0,
            "wait_time_seconds": self.get_wait_time(),
            "reset_timestamp": reset_time,
            "reset_in_seconds": max(0, reset_time - current_time)
        }


class HourlyRateLimitHandler(RateLimitHandler):
    """Convenience class for hourly rate limiting"""
    
    def __init__(self, requests_per_hour: int = 40):
        super().__init__(requests_per_hour, RateLimitUnit.HOUR)


class MinuteRateLimitHandler(RateLimitHandler):
    """Convenience class for minute rate limiting"""
    
    def __init__(self, requests_per_minute: int = 40):
        super().__init__(requests_per_minute, RateLimitUnit.MINUTE) 