from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
import os
import uuid
from pathlib import Path
import mimetypes
from typing import Optional
import re
import time
from collections import defaultdict, deque

from app.core.response_utils import create_success_response, create_error_response
from app.deps.auth import get_current_user
from app.models.user import User
from app.services.video_streaming import VideoStreamingService

router = APIRouter()

# Video streaming service instance
video_service = VideoStreamingService()

# Rate limiting for concurrent requests (in-memory)
user_request_tracker = defaultdict(lambda: deque(maxlen=20))  # Track last 20 requests per user
CONCURRENT_REQUEST_LIMIT = 8  # Max 8 concurrent requests per user (allows normal browsing)
REQUEST_WINDOW = 5  # 5 seconds window (shorter window for faster reset)

@router.get("/watch-direct/{video_id}")
async def watch_video_direct(
    video_id: str,
    request: Request,
    range_header: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Direct video streaming endpoint that works with files in upload folder
    Bypasses database lookup and streams files directly
    """
    try:
        # Validate video_id format (UUID)
        try:
            uuid.UUID(video_id)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content=create_error_response(
                    message="معرف الفيديو غير صحيح",
                    status_code=400,
                    error_type="Validation Error"
                )
            )
        
        # Enhanced Security check - Block download managers and suspicious patterns
        user_agent = request.headers.get("user-agent", "").lower()
        
        blocked_agents = [
            "wget", "curl", "download", "manager", "downloader", 
            "idm", "fdm", "jdownloader", "youtube-dl", "yt-dlp",
            "aria2", "axel", "httpie", "python-requests", "eagleget",
            "flashget", "internet download", "free download", "mass downloader"
        ]
        
        if any(agent in user_agent for agent in blocked_agents):
            return JSONResponse(
                status_code=403,
                content=create_error_response(
                    message="هذا النوع من البرامج غير مسموح لتشغيل الفيديوهات",
                    status_code=403,
                    error_type="Access Denied"
                )
            )
        
        # Additional security checks for download manager behavior
        suspicious_headers = []
        
        # Check for download manager specific headers
        if request.headers.get("if-range"):
            suspicious_headers.append("If-Range (Resume Download)")
        
        if request.headers.get("connection", "").lower() == "keep-alive" and request.headers.get("range"):
            suspicious_headers.append("Keep-Alive + Range Request")
        
        # Check for missing Referer (download managers often don't send referer)
        if not request.headers.get("referer") and request.headers.get("range"):
            suspicious_headers.append("Missing Referer with Range Request")
        
        # Check for suspicious Accept headers
        accept_header = request.headers.get("accept", "").lower()
        if accept_header == "*/*" and request.headers.get("range"):
            suspicious_headers.append("Wildcard Accept with Range Request")
        
        # If multiple suspicious patterns detected, block the request
        if len(suspicious_headers) >= 2:
            return JSONResponse(
                status_code=403,
                content=create_error_response(
                    message=f"سلوك مشبوه تم اكتشافه: {', '.join(suspicious_headers)}",
                    status_code=403,
                    error_type="Suspicious Behavior Detected"
                )
            )
        
        # Check if user is authenticated
        if not current_user:
            return JSONResponse(
                status_code=401,
                content=create_error_response(
                    message="يجب تسجيل الدخول لمشاهدة الفيديوهات",
                    status_code=401,
                    error_type="Unauthorized"
                )
            )
        
        # Smart rate limiting - stricter for suspicious patterns
        user_id = str(current_user.id)
        current_time = time.time()
        
        # Determine if this looks like a download manager based on headers
        is_suspicious_request = False
        suspicion_score = 0
        
        # Check for download manager patterns
        if request.headers.get("range") and not request.headers.get("referer"):
            suspicion_score += 2  # Range without referer is suspicious
        
        if user_agent in ["", "unknown"] or len(user_agent) < 10:
            suspicion_score += 1  # Very short or missing user agent
        
        if request.headers.get("accept") == "*/*" and request.headers.get("range"):
            suspicion_score += 1  # Wildcard accept with range
        
        # Apply different limits based on suspicion
        if suspicion_score >= 2:
            is_suspicious_request = True
            current_limit = 2  # Very strict for suspicious requests
            current_window = 15  # Longer window for suspicious requests
        else:
            current_limit = CONCURRENT_REQUEST_LIMIT  # Normal limit for regular browsers
            current_window = REQUEST_WINDOW
        
        # Clean old requests from tracker
        user_requests = user_request_tracker[user_id]
        while user_requests and current_time - user_requests[0] > current_window:
            user_requests.popleft()
        
        # Check if user has too many recent requests
        if len(user_requests) >= current_limit:
            error_message = "تم تجاوز الحد المسموح للطلبات المتوازية"
            if is_suspicious_request:
                error_message = "تم اكتشاف نشاط مشبوه - تم تقييد الوصول"
                
            return JSONResponse(
                status_code=429,
                content=create_error_response(
                    message=error_message,
                    status_code=429,
                    error_type="Too Many Requests"
                )
            )
        
        # Add current request to tracker
        user_requests.append(current_time)
        
        # Look for video file in upload directory
        upload_dir = Path("static/uploads/lessons")
        video_file = None
        
        # Search for file with video_id in filename
        if upload_dir.exists():
            for file_path in upload_dir.glob("*.mp4"):
                if video_id in file_path.name:
                    video_file = file_path
                    break
        
        # If not found by ID, try exact filename match
        if not video_file:
            possible_names = [
                f"{video_id}.mp4",
                f"video_{video_id}.mp4",
            ]
            
            for name in possible_names:
                possible_path = upload_dir / name
                if possible_path.exists():
                    video_file = possible_path
                    break
        
        if not video_file or not video_file.exists():
            return JSONResponse(
                status_code=404,
                content=create_error_response(
                    message="ملف الفيديو غير موجود",
                    status_code=404,
                    error_type="Not Found"
                )
            )
        
        # Check file size (skip empty or very small files)
        file_size = video_file.stat().st_size
        if file_size < 1000:  # Less than 1KB
            return JSONResponse(
                status_code=422,
                content=create_error_response(
                    message="ملف الفيديو تالف أو فارغ",
                    status_code=422,
                    error_type="Unprocessable Entity"
                )
            )
        
        # Get range header for streaming
        range_header = request.headers.get("range")
        
        # Security: Block suspicious range requests (Download Manager behavior)
        if range_header:
            # Block multiple concurrent range requests (typical download manager behavior)
            # Only allow single range requests from legitimate browsers
            if "bytes=" in range_header.lower():
                # Check if this looks like a download manager pattern
                range_parts = range_header.lower().replace("bytes=", "").strip()
                
                # Block if range is too specific (download manager pattern)
                if "-" in range_parts:
                    start_end = range_parts.split("-")
                    if len(start_end) == 2 and start_end[0].isdigit():
                        start_byte = int(start_end[0])
                        # Block if requesting from middle of file (resume download pattern)
                        if start_byte > 100000:  # More than 100KB into file
                            return JSONResponse(
                                status_code=403,
                                content=create_error_response(
                                    message="هذا النوع من طلبات التحميل غير مسموح",
                                    status_code=403,
                                    error_type="Range Request Blocked"
                                )
                            )
                
                # Block specific download manager range patterns
                suspicious_patterns = [
                    "bytes=0-262143",    # Common IDM chunk size
                    "bytes=0-1048575",   # Common 1MB chunk
                    "bytes=0-524287",    # Common 512KB chunk
                ]
                
                if range_header in suspicious_patterns:
                    return JSONResponse(
                        status_code=403,
                        content=create_error_response(
                            message="نمط طلب التحميل مشبوه ومحظور",
                            status_code=403,
                            error_type="Suspicious Range Pattern"
                        )
                    )
        
        # Stream the video file
        def generate_video_stream():
            chunk_size = 1024 * 1024  # 1MB chunks
            start = 0
            end = file_size - 1
            
            # Parse range header if present
            if range_header:
                range_match = re.search(r"bytes=(\d+)-(\d*)", range_header)
                if range_match:
                    start = int(range_match.group(1))
                    if range_match.group(2):
                        end = min(int(range_match.group(2)), file_size - 1)
            
            # Open file and stream content
            with open(video_file, "rb") as video_file_handle:
                video_file_handle.seek(start)
                remaining = end - start + 1
                
                while remaining > 0:
                    chunk_size = min(chunk_size, remaining)
                    chunk = video_file_handle.read(chunk_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(str(video_file))
        if not content_type:
            content_type = "video/mp4"
        
        # Prepare response headers
        headers = {
            "Content-Type": content_type,
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
            # Security headers to prevent download
            "Content-Disposition": "inline",
            "X-Frame-Options": "SAMEORIGIN",
        }
        
        # Handle range requests
        status_code = 200
        if range_header:
            range_match = re.search(r"bytes=(\d+)-(\d*)", range_header)
            if range_match:
                start = int(range_match.group(1))
                end = file_size - 1
                if range_match.group(2):
                    end = min(int(range_match.group(2)), file_size - 1)
                
                headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
                headers["Content-Length"] = str(end - start + 1)
                status_code = 206
        
        # Return streaming response
        return StreamingResponse(
            generate_video_stream(),
            status_code=status_code,
            headers=headers,
            media_type=content_type
        )
        
    except Exception as e:
        print(f"Error in watch_video_direct: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="حدث خطأ أثناء تشغيل الفيديو",
                status_code=500,
                error_type="Internal Server Error"
            )
        )

@router.get("/info-direct/{video_id}")
async def get_video_info_direct(
    video_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get video file information directly from filesystem
    """
    try:
        # Validate video_id format
        try:
            uuid.UUID(video_id)
        except ValueError:
            return SayanErrorResponse(
                message="معرف الفيديو غير صحيح",
                status_code=400
            )
        
        # Check authentication
        if not current_user:
            return SayanErrorResponse(
                message="يجب تسجيل الدخول للوصول لمعلومات الفيديو",
                status_code=401
            )
        
        # Look for video file
        upload_dir = Path("static/uploads/lessons")
        video_file = None
        
        if upload_dir.exists():
            for file_path in upload_dir.glob("*.mp4"):
                if video_id in file_path.name:
                    video_file = file_path
                    break
        
        if not video_file or not video_file.exists():
            return SayanErrorResponse(
                message="ملف الفيديو غير موجود",
                status_code=404
            )
        
        # Get file information
        file_stats = video_file.stat()
        file_info = {
            "video_id": video_id,
            "filename": video_file.name,
            "size_bytes": file_stats.st_size,
            "size_mb": round(file_stats.st_size / (1024 * 1024), 2),
            "created_at": file_stats.st_ctime,
            "modified_at": file_stats.st_mtime,
            "stream_url": f"/api/v1/videos/watch-direct/{video_id}",
            "status": "available" if file_stats.st_size > 1000 else "empty_or_corrupted"
        }
        
        return JSONResponse(
            status_code=200,
            content=create_success_response(
                data=file_info,
                message="تم جلب معلومات الفيديو بنجاح"
            )
        )
        
    except Exception as e:
        print(f"Error in get_video_info_direct: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="حدث خطأ أثناء جلب معلومات الفيديو",
                status_code=500,
                error_type="Internal Server Error"
            )
        )

@router.get("/list-available")
async def list_available_videos(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    List all available video files in the upload directory
    """
    try:
        # Check authentication
        if not current_user:
            return SayanErrorResponse(
                message="يجب تسجيل الدخول لعرض قائمة الفيديوهات",
                status_code=401
            )
        
        # Scan upload directory
        upload_dir = Path("static/uploads/lessons")
        videos_list = []
        
        if upload_dir.exists():
            for file_path in upload_dir.glob("*.mp4"):
                file_stats = file_path.stat()
                
                # Extract video ID from filename
                video_id = None
                filename_parts = file_path.stem.split("_")
                if len(filename_parts) >= 3:
                    potential_id = filename_parts[2]
                    try:
                        uuid.UUID(potential_id)
                        video_id = potential_id
                    except ValueError:
                        video_id = file_path.stem
                else:
                    video_id = file_path.stem
                
                video_info = {
                    "video_id": video_id,
                    "filename": file_path.name,
                    "size_bytes": file_stats.st_size,
                    "size_mb": round(file_stats.st_size / (1024 * 1024), 2),
                    "status": "available" if file_stats.st_size > 1000 else "empty_or_corrupted",
                    "stream_url": f"/api/v1/videos/watch-direct/{video_id}"
                }
                
                videos_list.append(video_info)
        
        # Sort by filename
        videos_list.sort(key=lambda x: x["filename"])
        
        return JSONResponse(
            status_code=200,
            content=create_success_response(
                data={
                    "videos": videos_list,
                    "total_count": len(videos_list),
                    "available_count": len([v for v in videos_list if v["status"] == "available"])
                },
                message=f"تم العثور على {len(videos_list)} فيديو"
            )
        )
        
    except Exception as e:
        print(f"Error in list_available_videos: {e}")
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="حدث خطأ أثناء جلب قائمة الفيديوهات",
                status_code=500,
                error_type="Internal Server Error"
            )
        ) 