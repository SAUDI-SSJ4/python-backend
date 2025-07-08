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
from app.core.response_handler import SayanSuccessResponse

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
    
    return SayanSuccessResponse(
        data={"tool": tool},
        message="تم جلب تفاصيل الأداة بنجاح"
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
        
        return SayanSuccessResponse(
            data={"tool": tool},
            message="تم تحديث الأداة التفاعلية بنجاح"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"حدث خطأ أثناء تحديث الأداة التفاعلية: {str(e)}"
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
        
        return SayanSuccessResponse(
            message="تم حذف الأداة التفاعلية بنجاح"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"حدث خطأ أثناء حذف الأداة التفاعلية: {str(e)}"
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
    
    tool = db.query(InteractiveTool).filter(InteractiveTool.id == tool_id).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الأداة التفاعلية غير موجودة"
        )
    
    lesson = db.query(Lesson).filter(Lesson.id == tool.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدرس المرتبط بالأداة غير موجود"
        )
    
    return SayanSuccessResponse(
        data={"tool": tool},
        message="تم جلب الأداة بنجاح"
    )


@router.post("/public/tools/{tool_id}/interact")
async def interact_with_tool(
    tool_id: str,
    interaction_data: dict,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Process student interaction with tool"""
    
    tool = db.query(InteractiveTool).filter(InteractiveTool.id == tool_id).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الأداة التفاعلية غير موجودة"
        )
    
    lesson = db.query(Lesson).filter(Lesson.id == tool.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدرس المرتبط بالأداة غير موجود"
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