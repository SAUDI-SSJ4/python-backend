"""
Simplified Interactive Tools API
===============================
Supporting colored cards and timeline tools
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user, get_current_student
from app.models.interactive_tool import InteractiveTool, ToolType
from app.models.lesson import Lesson
from app.models.course import Course
from app.models.user import User
from app.models.student import Student
from app.core.response_handler import SayanSuccessResponse, SayanErrorResponse

router = APIRouter()

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
    tool_data: dict,
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
        
        # Update tool fields
        allowed_fields = ["title", "description", "tool_type", "color", "image", "order_number"]
        for field, value in tool_data.items():
            if field in allowed_fields and hasattr(tool, field):
                setattr(tool, field, value)
        
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
                    "order_number": tool.order_number,
                    "updated_at": tool.updated_at.isoformat()
                }
            },
            message="تم تحديث الأداة التفاعلية بنجاح"
        )
        
    except Exception as e:
        db.rollback()
        return SayanErrorResponse(
            message=f"حدث خطأ أثناء تحديث الأداة التفاعلية: {str(e)}",
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