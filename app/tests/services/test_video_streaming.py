"""
Tests for Video Streaming Service.

This module contains unit tests for the video streaming service including:
- Token generation and verification
- Access control validation
- Video file handling
- Security features
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from app.services.video_streaming import VideoStreamingService
from app.models.video import Video
from app.models.lesson import Lesson


@pytest.mark.services
class TestVideoStreamingService:
    """Test suite for Video Streaming Service"""
    
    def setup_method(self):
        """Setup test service instance"""
        self.service = VideoStreamingService()
    
    def test_generate_video_token(self):
        """Test JWT token generation for video access"""
        video_id = "test-video-123"
        student_id = 1
        
        token = self.service.generate_video_token(video_id, student_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_video_token(self):
        """Test JWT token verification"""
        video_id = "test-video-123"
        student_id = 1
        
        # Generate token
        token = self.service.generate_video_token(video_id, student_id)
        
        # Verify token
        payload = self.service.verify_video_token(token)
        
        assert payload["video_id"] == video_id
        assert payload["student_id"] == student_id
        assert payload["type"] == "video_access"
    
    def test_verify_expired_token(self):
        """Test verification of expired token"""
        video_id = "test-video-123"
        student_id = 1
        
        # Generate token with very short expiry
        past_time = timedelta(seconds=-1)
        token = self.service.generate_video_token(video_id, student_id, past_time)
        
        # Should raise exception for expired token
        with pytest.raises(Exception):
            self.service.verify_video_token(token)
    
    @patch('app.services.video_streaming.Path.exists')
    def test_get_video_file_path(self, mock_exists):
        """Test video file path resolution"""
        mock_exists.return_value = True
        
        video = Mock()
        video.video = "lessons/test-video.mp4"
        
        file_path = self.service.get_video_file_path(video)
        
        assert isinstance(file_path, Path)
        assert "test-video.mp4" in str(file_path)
    
    def test_generate_checksum(self):
        """Test security checksum generation"""
        video_id = "test-video-123"
        student_id = 1
        
        checksum1 = self.service._generate_checksum(video_id, student_id)
        checksum2 = self.service._generate_checksum(video_id, student_id)
        
        # Same inputs should generate same checksum
        assert checksum1 == checksum2
        
        # Different inputs should generate different checksums
        checksum3 = self.service._generate_checksum("different-video", student_id)
        assert checksum1 != checksum3 