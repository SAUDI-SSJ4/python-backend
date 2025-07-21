import os
import subprocess
import platform
from pathlib import Path


class FFmpegConfig:
    """
    FFmpeg configuration and path detection
    """
    
    # Common FFmpeg paths for different operating systems
    COMMON_PATHS = {
        "Windows": [
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe",
            "ffmpeg.exe"  # If in PATH
        ],
        "Linux": [
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/opt/ffmpeg/bin/ffmpeg",
            "ffmpeg"  # If in PATH
        ],
        "Darwin": [  # macOS
            "/usr/local/bin/ffmpeg",
            "/opt/homebrew/bin/ffmpeg",
            "/usr/bin/ffmpeg",
            "ffmpeg"  # If in PATH
        ]
    }
    
    @classmethod
    def get_ffmpeg_path(cls) -> str:
        """
        Detect FFmpeg installation path
        """
        system = platform.system()
        common_paths = cls.COMMON_PATHS.get(system, cls.COMMON_PATHS["Linux"])
        
        # First, try to find ffmpeg in PATH
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            if result.returncode == 0:
                return "ffmpeg"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Check common installation paths
        for path in common_paths:
            if os.path.exists(path):
                try:
                    result = subprocess.run(
                        [path, "-version"], 
                        capture_output=True, 
                        text=True, 
                        timeout=5
                    )
                    if result.returncode == 0:
                        return path
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
        
        # If not found, raise error with installation instructions
        raise FileNotFoundError(
            f"FFmpeg not found. Please install FFmpeg:\n"
            f"Windows: Download from https://ffmpeg.org/download.html\n"
            f"Linux: sudo apt-get install ffmpeg (Ubuntu/Debian) or sudo yum install ffmpeg (CentOS/RHEL)\n"
            f"macOS: brew install ffmpeg"
        )
    
    @classmethod
    def verify_ffmpeg_installation(cls) -> bool:
        """
        Verify FFmpeg installation and capabilities
        """
        try:
            ffmpeg_path = cls.get_ffmpeg_path()
            
            # Check if FFmpeg supports HLS
            result = subprocess.run(
                [ffmpeg_path, "-hide_banner", "-formats"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout.lower()
                return "hls" in output and "mpegts" in output
            
            return False
            
        except Exception:
            return False
    
    @classmethod
    def get_ffmpeg_version(cls) -> str:
        """
        Get FFmpeg version information
        """
        try:
            ffmpeg_path = cls.get_ffmpeg_path()
            
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Extract version from first line
                lines = result.stdout.split('\n')
                if lines:
                    return lines[0].strip()
            
            return "Unknown"
            
        except Exception:
            return "Unknown"
    
    @classmethod
    def test_hls_encoding(cls, input_file: str, output_dir: str) -> bool:
        """
        Test HLS encoding capabilities
        """
        try:
            ffmpeg_path = cls.get_ffmpeg_path()
            
            # Create test command
            cmd = [
                ffmpeg_path,
                "-i", input_file,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-hls_time", "6",
                "-hls_list_size", "0",
                "-hls_segment_filename", f"{output_dir}/test_segment_%03d.ts",
                f"{output_dir}/test_playlist.m3u8"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0
            
        except Exception:
            return False 