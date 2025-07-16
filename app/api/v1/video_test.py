from fastapi import APIRouter, Request, Query, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from app.deps.database import get_db
from app.models.video import Video
import os

router = APIRouter()

@router.get("/test-stream/{video_id}")
async def test_video_stream(
    video_id: str,
    request: Request,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Simplified video streaming test endpoint
    No complex authentication - just basic checks
    """
    
    print(f"🎬 TEST: Video ID: {video_id}")
    print(f"🎬 TEST: Token: {token[:50]}...")
    print(f"🎬 TEST: User Agent: {request.headers.get('user-agent', 'N/A')}")
    
    try:
        # Basic video lookup
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            print(f"❌ TEST: Video not found")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Video not found",
                    "video_id": video_id
                }
            )
        
        print(f"✅ TEST: Video found: {video.title}")
        print(f"✅ TEST: Video file: {video.video}")
        
        # Check if file exists
        if video.video:
            file_path = os.path.join("static", video.video)
            print(f"✅ TEST: Looking for file at: {file_path}")
            
            if os.path.exists(file_path):
                print(f"✅ TEST: File exists! Size: {os.path.getsize(file_path)} bytes")
                
                # Return file directly
                return FileResponse(
                    path=file_path,
                    media_type="video/mp4",
                    headers={
                        "Content-Disposition": "inline",
                        "Cache-Control": "no-cache"
                    }
                )
            else:
                print(f"❌ TEST: File not found at: {file_path}")
                return JSONResponse(
                    status_code=404,
                    content={
                        "status": "error", 
                        "message": "Video file not found on disk",
                        "file_path": file_path
                    }
                )
        else:
            print(f"❌ TEST: No video file path in database")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "No video file path in database"
                }
            )
            
    except Exception as e:
        print(f"❌ TEST ERROR: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Test error: {str(e)}"
            }
        )


@router.get("/debug-info/{video_id}")
async def debug_video_info(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to check video information
    """
    
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            return {"status": "error", "message": "Video not found"}
        
        file_path = os.path.join("static", video.video) if video.video else None
        file_exists = os.path.exists(file_path) if file_path else False
        file_size = os.path.getsize(file_path) if file_exists else 0
        
        return {
            "status": "success",
            "video_info": {
                "id": video.id,
                "title": video.title,
                "video_path": video.video,
                "full_path": file_path,
                "file_exists": file_exists,
                "file_size": file_size,
                "lesson_id": video.lesson_id
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)} 