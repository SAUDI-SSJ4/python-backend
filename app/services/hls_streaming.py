import os
import subprocess
import tempfile
import secrets
import hashlib
import jwt
from typing import List, Dict, Optional, Tuple
import m3u8
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
import re

from app.core.config import settings
from app.models.video import Video


class HLSStreamingService:
    """
    Advanced HLS Streaming Service with AES-128 encryption
    Similar to Stream Bunny's approach for maximum video protection
    """
    
    def __init__(self, ffmpeg_path: str = None):
        # Auto-detect ffmpeg path
        if ffmpeg_path is None:
            from app.core.ffmpeg_config import FFmpegConfig
            ffmpeg_path = FFmpegConfig.get_ffmpeg_path()
        
        self.ffmpeg_path = ffmpeg_path
        self.segment_duration = 6  # 6 seconds per segment for better security
        self.output_dir = "temp_hls"
        self.secret_key = settings.SECRET_KEY
        
        # Security settings
        self.key_expiry_hours = 24  # Key expires after 24 hours
        self.max_playlist_age = 3600  # Playlist cache for 1 hour
        
    def create_encrypted_hls_playlist(
        self, 
        video_path: str, 
        video_id: str,
        user_id: str,
        request: Request
    ) -> Dict[str, str]:
        """
        Create encrypted HLS playlist with dynamic key generation
        """
        try:
            # Generate unique output name
            output_name = f"{video_id}_{user_id}_{int(datetime.now().timestamp())}"
            output_path = Path(self.output_dir) / output_name
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate encryption key for this session
            encryption_key = self._generate_session_key(video_id, user_id, request)
            
            # Create keyinfo file for this session
            keyinfo_path = self._create_keyinfo_file(encryption_key, output_path)
            
            # Generate two quality levels only - جودتان فقط
            qualities = [
                {"name": "high", "height": 720, "bitrate": "2800k", "label": "جودة عالية"},
                {"name": "low", "height": 480, "bitrate": "1400k", "label": "جودة منخفضة"}
            ]
            
            playlist_files = {}
            
            for quality in qualities:
                quality_output = output_path / quality["name"]
                quality_output.mkdir(exist_ok=True)
                
                # FFmpeg command for encrypted HLS
                cmd = [
                    self.ffmpeg_path,
                    "-i", video_path,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-b:v", quality["bitrate"],
                    "-maxrate", quality["bitrate"],
                    "-bufsize", str(int(quality["bitrate"].replace("k", "")) * 2) + "k",
                    "-vf", f"scale=-2:{quality['height']}",
                    "-hls_time", str(self.segment_duration),
                    "-hls_list_size", "0",
                    "-hls_segment_filename", str(quality_output / "segment_%03d.ts"),
                    "-hls_key_info_file", str(keyinfo_path),
                    "-hls_playlist_type", "vod",
                    "-hls_flags", "independent_segments",
                    str(quality_output / "playlist.m3u8")
                ]
                
                subprocess.run(cmd, check=True, capture_output=True)
                playlist_files[quality["name"]] = str(quality_output / "playlist.m3u8")
            
            # Create master playlist with security headers
            master_playlist = self._create_secure_master_playlist(
                playlist_files, 
                output_path, 
                video_id, 
                user_id
            )
            
            return {
                "master_playlist": str(master_playlist),
                "qualities": playlist_files,
                "session_id": output_name,
                "key_id": encryption_key["key_id"]
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating HLS playlist: {str(e)}"
            )
    
    def _generate_session_key(
        self, 
        video_id: str, 
        user_id: str, 
        request: Request
    ) -> Dict[str, str]:
        """
        Generate unique encryption key for this streaming session
        """
        # Create session-specific key
        session_data = f"{video_id}:{user_id}:{request.client.host}:{datetime.now().isoformat()}"
        key_id = hashlib.sha256(session_data.encode()).hexdigest()[:16]
        
        # Generate random AES-128 key
        key_bytes = secrets.token_bytes(16)
        key_hex = key_bytes.hex()
        
        # Store key with expiry (in production, use Redis or database)
        key_data = {
            "key_id": key_id,
            "key": key_hex,
            "video_id": video_id,
            "user_id": user_id,
            "expires_at": datetime.now() + timedelta(hours=self.key_expiry_hours),
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent", "")
        }
        
        # In production, store in Redis with expiry
        # redis_client.setex(f"hls_key:{key_id}", self.key_expiry_hours * 3600, json.dumps(key_data))
        
        return key_data
    
    def _create_keyinfo_file(self, key_data: Dict, output_path: Path) -> Path:
        """
        Create keyinfo file for FFmpeg encryption
        """
        key_path = output_path / f"{key_data['key_id']}.key"
        keyinfo_path = output_path / f"{key_data['key_id']}.keyinfo"
        
        # Write key file
        with open(key_path, "wb") as f:
            f.write(bytes.fromhex(key_data["key"]))
        
        # Write keyinfo file
        keyinfo_content = f"{key_path.name}\n{key_path}\n"
        with open(keyinfo_path, "w") as f:
            f.write(keyinfo_content)
        
        return keyinfo_path
    
    def _create_secure_master_playlist(
        self, 
        playlists: Dict[str, str], 
        output_path: Path,
        video_id: str,
        user_id: str
    ) -> Path:
        """
        Create master playlist with security headers
        """
        master_content = "#EXTM3U\n"
        master_content += "#EXT-X-VERSION:3\n"
        master_content += f"#EXT-X-INDEPENDENT-SEGMENTS\n"
        master_content += f"# Generated for video: {video_id}\n"
        master_content += f"# User: {user_id}\n"
        master_content += f"# Generated: {datetime.now().isoformat()}\n"
        
        for quality_name, playlist_path in playlists.items():
            # Get stream info
            playlist = m3u8.load(playlist_path)
            duration = playlist.target_duration or self.segment_duration
            
            master_content += f"#EXT-X-STREAM-INF:BANDWIDTH={self._get_bandwidth(quality_name)},RESOLUTION={self._get_resolution(quality_name)}\n"
            master_content += f"{quality_name}/playlist.m3u8\n"
        
        master_file = output_path / "master.m3u8"
        with open(master_file, "w") as f:
            f.write(master_content)
        
        return master_file
    
    def serve_hls_playlist(
        self, 
        playlist_path: str, 
        request: Request,
        video_id: str,
        user_id: str
    ) -> StreamingResponse:
        """
        Serve HLS playlist with security headers
        """
        try:
            file_path = Path(playlist_path)
            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Playlist not found"
                )
            
            # Read playlist content
            with open(file_path, "r") as f:
                content = f.read()
            
            # Add security headers
            headers = {
                "Content-Type": "application/vnd.apple.mpegurl",
                "Cache-Control": "private, max-age=300",  # 5 minutes cache
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Content-Disposition": "inline",
                "X-Video-ID": video_id,
                "X-User-ID": user_id,
                "X-Playlist-Type": "HLS"
            }
            
            return Response(
                content=content,
                headers=headers,
                media_type="application/vnd.apple.mpegurl"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error serving playlist: {str(e)}"
            )
    
    def serve_hls_segment(
        self, 
        segment_path: str, 
        request: Request,
        video_id: str,
        user_id: str
    ) -> StreamingResponse:
        """
        Serve HLS segment with security headers
        """
        try:
            file_path = Path(segment_path)
            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Segment not found"
                )
            
            # Get file info
            file_size = file_path.stat().st_size
            
            # Handle range requests
            range_header = request.headers.get("range")
            start = 0
            end = file_size - 1
            
            if range_header:
                range_match = re.search(r"bytes=(\d+)-(\d*)", range_header)
                if range_match:
                    start = int(range_match.group(1))
                    if range_match.group(2):
                        end = min(int(range_match.group(2)), file_size - 1)
            
            # Read segment data
            with open(file_path, "rb") as f:
                f.seek(start)
                data = f.read(end - start + 1)
            
            # Security headers
            headers = {
                "Content-Type": "video/MP2T",
                "Content-Length": str(len(data)),
                "Accept-Ranges": "bytes",
                "Cache-Control": "private, max-age=3600",  # 1 hour cache
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Content-Disposition": "inline",
                "X-Video-ID": video_id,
                "X-User-ID": user_id,
                "X-Segment-Type": "HLS"
            }
            
            if range_header:
                headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
                status_code = 206
            else:
                status_code = 200
            
            return Response(
                content=data,
                status_code=status_code,
                headers=headers,
                media_type="video/MP2T"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error serving segment: {str(e)}"
            )
    
    def serve_encryption_key(
        self, 
        key_id: str, 
        request: Request,
        video_id: str,
        user_id: str
    ) -> Response:
        """
        Serve encryption key with verification
        """
        try:
            # Verify key access (in production, check Redis/database)
            # key_data = redis_client.get(f"hls_key:{key_id}")
            # if not key_data:
            #     raise HTTPException(status_code=404, detail="Key not found")
            
            # For now, use simple verification
            if not self._verify_key_access(key_id, video_id, user_id, request):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to encryption key"
                )
            
            # Get key file path
            key_path = Path(self.output_dir) / f"{key_id}.key"
            if not key_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Key file not found"
                )
            
            # Read key
            with open(key_path, "rb") as f:
                key_data = f.read()
            
            # Security headers
            headers = {
                "Content-Type": "application/octet-stream",
                "Cache-Control": "private, no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Content-Disposition": "inline",
                "X-Video-ID": video_id,
                "X-User-ID": user_id,
                "X-Key-Type": "AES-128"
            }
            
            return Response(
                content=key_data,
                headers=headers,
                media_type="application/octet-stream"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error serving key: {str(e)}"
            )
    
    def _verify_key_access(
        self, 
        key_id: str, 
        video_id: str, 
        user_id: str, 
        request: Request
    ) -> bool:
        """
        Verify user has access to this encryption key
        """
        # Basic verification - in production, check database/Redis
        expected_key_id = hashlib.sha256(f"{video_id}:{user_id}".encode()).hexdigest()[:16]
        return key_id == expected_key_id
    
    def _get_bandwidth(self, quality: str) -> str:
        """Get bandwidth for quality level - جودتان فقط"""
        bandwidths = {
            "high": "2800000",  # 2.8 Mbps
            "low": "1400000"    # 1.4 Mbps
        }
        return bandwidths.get(quality, "1400000")
    
    def _get_resolution(self, quality: str) -> str:
        """Get resolution for quality level - جودتان فقط"""
        resolutions = {
            "high": "1280x720",  # 720p
            "low": "854x480"     # 480p
        }
        return resolutions.get(quality, "854x480")
    
    def cleanup_session_files(self, session_id: str):
        """
        Clean up temporary HLS files for a session
        """
        try:
            session_path = Path(self.output_dir) / session_id
            if session_path.exists():
                import shutil
                shutil.rmtree(session_path)
        except Exception as e:
            # Log cleanup error but don't raise
            print(f"Error cleaning up session files: {e}")


# Global instance
hls_streaming_service = HLSStreamingService() 