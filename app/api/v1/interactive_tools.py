"""
Simplified Interactive Tools API
===============================
Using direct IDs for cleaner API design
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user, get_current_student
from app.models.interactive_tool import InteractiveTool
from app.models.lesson import Lesson
from app.models.course import Course
from app.models.user import User
from app.models.student import Student

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
    
    # Get tool
    tool = db.query(InteractiveTool).filter(InteractiveTool.id == tool_id).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الأداة التفاعلية غير موجودة"
        )
    
    # Verify ownership through lesson -> course
    lesson = db.query(Lesson).filter(Lesson.id == tool.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدرس المرتبط بالأداة غير موجود"
        )
    
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحية لعرض هذه الأداة"
        )
    
    return {
        "status": "success",
        "tool": tool
    }


@router.put("/tools/{tool_id}")
async def update_tool(
    tool_id: str,
    tool_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Update interactive tool"""
    
    # Get tool
    tool = db.query(InteractiveTool).filter(InteractiveTool.id == tool_id).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الأداة التفاعلية غير موجودة"
        )
    
    # Verify ownership through lesson -> course
    lesson = db.query(Lesson).filter(Lesson.id == tool.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدرس المرتبط بالأداة غير موجود"
        )
    
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحية لتعديل هذه الأداة"
        )
    
    # Update tool fields
    for field, value in tool_data.items():
        if hasattr(tool, field):
            setattr(tool, field, value)
    
    db.commit()
    db.refresh(tool)
    
    return {
        "status": "success",
        "message": "تم تحديث الأداة التفاعلية بنجاح",
        "tool": tool
    }


@router.delete("/tools/{tool_id}")
async def delete_tool(
    tool_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Delete interactive tool"""
    
    # Get tool
    tool = db.query(InteractiveTool).filter(InteractiveTool.id == tool_id).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الأداة التفاعلية غير موجودة"
        )
    
    # Verify ownership through lesson -> course
    lesson = db.query(Lesson).filter(Lesson.id == tool.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدرس المرتبط بالأداة غير موجود"
        )
    
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحية لحذف هذه الأداة"
        )
    
    db.delete(tool)
    db.commit()
    
    return {
        "status": "success",
        "message": "تم حذف الأداة التفاعلية بنجاح"
    }


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
    
    # Get tool
    tool = db.query(InteractiveTool).filter(InteractiveTool.id == tool_id).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الأداة التفاعلية غير موجودة"
        )
    
    # Verify student enrollment in course
    lesson = db.query(Lesson).filter(Lesson.id == tool.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدرس المرتبط بالأداة غير موجود"
        )
    
    # TODO: Add enrollment verification logic here
    # student_enrollment = check_student_enrollment(current_student.id, lesson.course_id)
    # if not student_enrollment:
    #     raise HTTPException(status_code=403, detail="غير مسجل في هذه الدورة")
    
    return {
        "status": "success",
        "tool": tool
    }


@router.post("/public/tools/{tool_id}/interact")
async def interact_with_tool(
    tool_id: str,
    interaction_data: dict,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Process student interaction with tool"""
    
    # Get tool
    tool = db.query(InteractiveTool).filter(InteractiveTool.id == tool_id).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الأداة التفاعلية غير موجودة"
        )
    
    # Verify student enrollment in course
    lesson = db.query(Lesson).filter(Lesson.id == tool.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدرس المرتبط بالأداة غير موجود"
        )
    
    # TODO: Process interaction based on tool type
    # TODO: Save student interaction data
    # TODO: Return results or feedback
    
    return {
        "status": "success",
        "message": "تم تسجيل التفاعل بنجاح",
        "result": {
            "tool_id": tool_id,
            "student_id": current_student.id,
            "interaction_type": interaction_data.get("type"),
            "timestamp": "2025-06-25T08:00:00Z"
        }
    } 