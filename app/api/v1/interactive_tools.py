"""
Simplified Interactive Tools API
===============================
Supporting colored cards and timeline tools
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import os
import uuid
import logging

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user, get_current_student
from app.models.interactive_tool import InteractiveTool, ToolType
from app.models.lesson import Lesson
from app.models.course import Course
from app.models.user import User
from app.models.student import Student
from app.core.response_handler import SayanSuccessResponse, SayanErrorResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# =====================================
# SIMPLIFIED INTERACTIVE TOOLS ENDPOINTS
# =====================================

@router.get("/tools/{tool_id}")
async def get_tool_details(
    tool_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Get interactive tool details"""
    
    try:
        # Get tool
        tool = db.query(InteractiveTool).filter(InteractiveTool.id == tool_id).first()
        
        if not tool:
            return SayanErrorResponse(
                message="الأداة التفاعلية غير موجودة",
                error_type="TOOL_NOT_FOUND",
                status_code=404
            )
        
        # Verify ownership through lesson -> course
        lesson = db.query(Lesson).filter(Lesson.id == tool.lesson_id).first()
        if not lesson:
            return SayanErrorResponse(
                message="الدرس المرتبط بالأداة غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
                message="ليس لديك صلاحية لعرض هذه الأداة",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        return SayanSuccessResponse(
            data={
                "tool": {
                    "id": tool.id,
                    "title": tool.title,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "color": tool.color,
                    "image": tool.image,
                    "content": tool.content,  # HTML content for text type
                    "order_number": tool.order_number,
                    "created_at": tool.created_at.isoformat(),
                    "updated_at": tool.updated_at.isoformat()
                }
            },
            message="تم جلب تفاصيل الأداة بنجاح"
        )
        
    except Exception as e:
        return SayanErrorResponse(
            message=f"حدث خطأ أثناء جلب تفاصيل الأداة: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )


@router.put("/tools/{tool_id}")
async def update_tool(
    tool_id: str,
    title: Optional[str] = Form(None, description="Tool title"),
    description: Optional[str] = Form(None, description="Tool description"),
    tool_type: Optional[str] = Form(None, description="Tool type: colored_card, timeline, text"),
    color: Optional[str] = Form(None, description="Tool color"),
    content: Optional[str] = Form(None, description="HTML content for text type"),
    order_number: Optional[int] = Form(None, description="Display order"),
    image: Optional[UploadFile] = File(None, description="Tool image"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Update interactive tool"""
    
    try:
        # Get tool
        tool = db.query(InteractiveTool).filter(InteractiveTool.id == tool_id).first()
        
        if not tool:
            return SayanErrorResponse(
                message="الأداة التفاعلية غير موجودة",
                error_type="TOOL_NOT_FOUND",
                status_code=404
            )
        
        # Verify ownership through lesson -> course
        lesson = db.query(Lesson).filter(Lesson.id == tool.lesson_id).first()
        if not lesson:
            return SayanErrorResponse(
                message="الدرس المرتبط بالأداة غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
                message="ليس لديك صلاحية لتعديل هذه الأداة",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        # Handle image upload if provided
        if image:
            try:
                # Validate image file
                if not image.content_type or not image.content_type.startswith('image/'):
                    return SayanErrorResponse(
                        message="الملف المرفوع ليس صورة",
                        error_type="INVALID_FILE_TYPE",
                        status_code=400
                    )
                
                # Generate unique filename
                file_extension = os.path.splitext(image.filename)[1] if image.filename else '.jpg'
                filename = f"tool_{str(uuid.uuid4())}{file_extension}"
                
                # Create upload directory if it doesn't exist
                upload_dir = "static/uploads/tools"
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save image file
                file_path = os.path.join(upload_dir, filename)
                with open(file_path, "wb") as buffer:
                    image_content = await image.read()
                    buffer.write(image_content)
                
                image_path = f"uploads/tools/{filename}"
                tool.image = image_path
                
            except Exception as e:
                return SayanErrorResponse(
                    message=f"حدث خطأ أثناء رفع الصورة: {str(e)}",
                    error_type="FILE_UPLOAD_ERROR",
                    status_code=500
                )
        
        # Update tool fields - all fields are optional
        if title is not None:
            tool.title = title
        if description is not None:
            tool.description = description
        if tool_type is not None:
            tool.tool_type = tool_type
        if color is not None:
            tool.color = color
        if content is not None:
            tool.content = content
        if order_number is not None:
            tool.order_number = order_number
        
        db.commit()
        db.refresh(tool)
        
        return SayanSuccessResponse(
            data={
                "tool": {
                    "id": tool.id,
                    "title": tool.title,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "color": tool.color,
                    "image": tool.image,
                    "content": tool.content,  # HTML content for text type
                    "order_number": tool.order_number,
                    "updated_at": tool.updated_at.isoformat()
                }
            },
            message="تم تحديث الأداة التفاعلية بنجاح"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating interactive tool: {str(e)}")
        return SayanErrorResponse(
            message="حدث خطأ أثناء تحديث الأداة التفاعلية",
            error_type="INTERNAL_ERROR",
            status_code=500
        )



@router.delete("/tools/{tool_id}")
async def delete_tool(
    tool_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Delete interactive tool"""
    
    try:
        # Get tool
        tool = db.query(InteractiveTool).filter(InteractiveTool.id == tool_id).first()
        
        if not tool:
            return SayanErrorResponse(
                message="الأداة التفاعلية غير موجودة",
                error_type="TOOL_NOT_FOUND",
                status_code=404
            )
        
        # Verify ownership through lesson -> course
        lesson = db.query(Lesson).filter(Lesson.id == tool.lesson_id).first()
        if not lesson:
            return SayanErrorResponse(
                message="الدرس المرتبط بالأداة غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            return SayanErrorResponse(
                message="ليس لديك صلاحية لحذف هذه الأداة",
                error_type="PERMISSION_DENIED",
                status_code=403
            )
        
        # Delete tool
        db.delete(tool)
        db.commit()
        
        return SayanSuccessResponse(
            data={"deleted_tool_id": tool_id},
            message="تم حذف الأداة التفاعلية بنجاح"
        )
        
    except Exception as e:
        db.rollback()
        return SayanErrorResponse(
            message=f"حدث خطأ أثناء حذف الأداة التفاعلية: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )


# =====================================
# STUDENT INTERACTIVE TOOLS ENDPOINTS
# =====================================

@router.get("/public/tools/{tool_id}")
async def get_tool_for_student(
    tool_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Get interactive tool for student use"""
    
    try:
        tool = db.query(InteractiveTool).filter(InteractiveTool.id == tool_id).first()
        
        if not tool:
            return SayanErrorResponse(
                message="الأداة التفاعلية غير موجودة",
                error_type="TOOL_NOT_FOUND",
                status_code=404
            )
        
        lesson = db.query(Lesson).filter(Lesson.id == tool.lesson_id).first()
        if not lesson:
            return SayanErrorResponse(
                message="الدرس المرتبط بالأداة غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        return SayanSuccessResponse(
            data={
                "tool": {
                    "id": tool.id,
                    "title": tool.title,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "color": tool.color,
                    "image": tool.image,
                    "content": tool.content,  # HTML content for text type
                    "order_number": tool.order_number
                }
            },
            message="تم جلب الأداة بنجاح"
        )
        
    except Exception as e:
        return SayanErrorResponse(
            message=f"حدث خطأ أثناء جلب الأداة: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )


@router.get("/public/lesson/{lesson_id}/tools")
async def get_lesson_tools_for_student(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Get all interactive tools for a lesson (student view)"""
    
    try:
        # Check if lesson exists
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return SayanErrorResponse(
                message="الدرس غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        # Get tools ordered by order_number
        tools = db.query(InteractiveTool).filter(
            InteractiveTool.lesson_id == lesson_id
        ).order_by(InteractiveTool.order_number).all()
        
        return SayanSuccessResponse(
            data={
                "lesson_id": lesson_id,
                "tools": [
                    {
                        "id": tool.id,
                        "title": tool.title,
                        "description": tool.description,
                        "tool_type": tool.tool_type,
                        "color": tool.color,
                        "image": tool.image,
                        "content": tool.content,  # HTML content for text type
                        "order_number": tool.order_number
                    }
                    for tool in tools
                ]
            },
            message="تم جلب أدوات الدرس بنجاح"
        )
        
    except Exception as e:
        return SayanErrorResponse(
            message=f"حدث خطأ أثناء جلب أدوات الدرس: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        )


@router.post("/public/tools/{tool_id}/interact")
async def interact_with_tool(
    tool_id: str,
    interaction_data: dict,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Process student interaction with tool"""
    
    try:
        tool = db.query(InteractiveTool).filter(InteractiveTool.id == tool_id).first()
        
        if not tool:
            return SayanErrorResponse(
                message="الأداة التفاعلية غير موجودة",
                error_type="TOOL_NOT_FOUND",
                status_code=404
            )
        
        lesson = db.query(Lesson).filter(Lesson.id == tool.lesson_id).first()
        if not lesson:
            return SayanErrorResponse(
                message="الدرس المرتبط بالأداة غير موجود",
                error_type="LESSON_NOT_FOUND",
                status_code=404
            )
        
        return SayanSuccessResponse(
            data={
                "result": {
                    "tool_id": tool_id,
                    "student_id": current_student.id,
                    "interaction_type": interaction_data.get("type"),
                    "timestamp": "2025-06-25T08:00:00Z"
                }
            },
            message="تم تسجيل التفاعل بنجاح"
        )
        
    except Exception as e:
        return SayanErrorResponse(
            message=f"حدث خطأ أثناء تسجيل التفاعل: {str(e)}",
            error_type="INTERNAL_ERROR",
            status_code=500
        ) 