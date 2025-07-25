"""
Simplified Exams and Questions API
=================================
Using direct IDs for cleaner API design
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
from sqlalchemy import text

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user, get_current_student, get_current_academy_user_optional
from app.models.exam import Exam, Question, QuestionOption, QuestionType
from app.models.lesson import Lesson
from app.models.course import Course
from app.models.user import User
from app.models.student import Student
from app.core.response_handler import SayanSuccessResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# =====================================
# SIMPLIFIED EXAM ENDPOINTS
# =====================================

@router.get("/{exam_id}")
async def get_exam_details(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_academy_user_optional)
) -> Any:
    """Get exam details with questions - works for both teachers and students"""
    
    try:
        # Get exam
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الامتحان غير موجود"
            )
        
        # Check if user is authenticated (teacher) or not (student)
        is_teacher = current_user is not None
        
        if is_teacher:
            # Verify ownership through lesson -> course for teachers
            lesson = db.query(Lesson).filter(Lesson.id == exam.lesson_id).first()
            if not lesson:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="الدرس المرتبط بالامتحان غير موجود"
                )
            
            course = db.query(Course).filter(
                Course.id == lesson.course_id,
                Course.academy_id == current_user.academy.id
            ).first()
            
            if not course:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="ليس لديك صلاحية لعرض هذا الامتحان"
                )
        
        # Get questions using raw SQL to avoid enum issues
        if is_teacher:
            # For teachers: include correct answers
            questions_result = db.execute(text("""
                SELECT id, title, description, type, score, correct_answer
                FROM questions
                WHERE exam_id = :exam_id
            """), {"exam_id": exam_id}).fetchall()
        else:
            # For students: exclude correct answers
            questions_result = db.execute(text("""
                SELECT id, title, description, type, score
                FROM questions
                WHERE exam_id = :exam_id
            """), {"exam_id": exam_id}).fetchall()

        # Prepare questions data
        questions_data = []
        for question_row in questions_result:
            question_data = {
                "id": question_row.id,
                "title": question_row.title,
                "description": question_row.description,
                "type": question_row.type.upper(), # Convert to uppercase for consistency
                "score": question_row.score,
                "options": []
            }
            
            # Add correct_answer only for teachers
            if is_teacher and hasattr(question_row, 'correct_answer'):
                question_data["correct_answer"] = question_row.correct_answer

            # Get options using raw SQL
            if is_teacher:
                # For teachers: include is_correct flag
                options_result = db.execute(text("""
                    SELECT id, text, is_correct
                    FROM question_options
                    WHERE question_id = :question_id
                """), {"question_id": question_row.id}).fetchall()
            else:
                # For students: exclude is_correct flag
                options_result = db.execute(text("""
                    SELECT id, text
                    FROM question_options
                    WHERE question_id = :question_id
                """), {"question_id": question_row.id}).fetchall()

            for option_row in options_result:
                option_data = {
                    "id": option_row.id,
                    "text": option_row.text
                }
                
                # Add is_correct only for teachers
                if is_teacher and hasattr(option_row, 'is_correct'):
                    option_data["is_correct"] = option_row.is_correct
                
                question_data["options"].append(option_data)

            questions_data.append(question_data)
        
        return SayanSuccessResponse(
            data={
                "exam": {
                    "id": exam.id,
                    "title": exam.title,
                    "duration": exam.duration,
                    "status": exam.status,
                    "questions_count": len(questions_data),
                    "created_at": exam.created_at.isoformat() if exam.created_at else None,
                    "updated_at": exam.updated_at.isoformat() if exam.updated_at else None
                },
                "questions": questions_data
            },
            message="تم جلب تفاصيل الامتحان وأسئلته بنجاح"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exam details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"حدث خطأ أثناء جلب تفاصيل الامتحان: {str(e)}"
        )


@router.put("/{exam_id}")
async def update_exam(
    exam_id: str,
    exam_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Update exam details"""
    
    try:
        # Get exam
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الامتحان غير موجود"
            )
        
        # Verify ownership through lesson -> course
        lesson = db.query(Lesson).filter(Lesson.id == exam.lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الدرس المرتبط بالامتحان غير موجود"
            )
        
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية لتعديل هذا الامتحان"
            )
        
        # Update exam fields - only allow specific fields
        allowed_fields = ['title', 'duration', 'status', 'order_number']
        
        for field, value in exam_data.items():
            if field in allowed_fields and hasattr(exam, field):
                setattr(exam, field, value)
        
        db.commit()
        db.refresh(exam)
        
        return SayanSuccessResponse(
            data={"exam": exam},
            message="تم تحديث الامتحان بنجاح"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"حدث خطأ أثناء تحديث الامتحان: {str(e)}"
        )


@router.delete("/{exam_id}")
async def delete_exam(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Delete exam and all its questions"""
    
    try:
        # Get exam
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الامتحان غير موجود"
            )
        
        # Verify ownership through lesson -> course
        lesson = db.query(Lesson).filter(Lesson.id == exam.lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الدرس المرتبط بالامتحان غير موجود"
            )
        
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية لحذف هذا الامتحان"
            )
        
        # Delete exam and all related data
        try:
            # Delete questions and options first
            for question in exam.questions:
                for option in question.options:
                    db.delete(option)
                db.delete(question)
            
            # Delete the exam
            db.delete(exam)
            db.commit()
            
            return SayanSuccessResponse(
                message="تم حذف الامتحان بنجاح"
            )
        except Exception as delete_error:
            db.rollback()
            logger.error(f"Error during exam deletion: {str(delete_error)}")
            # Handle enum conversion error
            if "is not among the defined enum values" in str(delete_error):
                # Try to delete without enum validation
                try:
                    db.execute(text("DELETE FROM question_options WHERE question_id IN (SELECT id FROM questions WHERE exam_id = :exam_id)"), {"exam_id": exam_id})
                    db.execute(text("DELETE FROM questions WHERE exam_id = :exam_id"), {"exam_id": exam_id})
                    db.execute(text("DELETE FROM exams WHERE id = :exam_id"), {"exam_id": exam_id})
                    db.commit()
                    return SayanSuccessResponse(
                        message="تم حذف الامتحان بنجاح"
                    )
                except Exception as raw_delete_error:
                    db.rollback()
                    logger.error(f"Raw delete error: {str(raw_delete_error)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"حدث خطأ أثناء حذف الامتحان: {str(raw_delete_error)}"
                    )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"حدث خطأ أثناء حذف الامتحان: {str(delete_error)}"
                )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"حدث خطأ أثناء حذف الامتحان: {str(e)}"
        )


# =====================================
# SIMPLIFIED QUESTION ENDPOINTS
# =====================================

@router.get("/questions/{question_id}")
async def get_question_details(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Get question details with options"""
    
    # Get question
    question = db.query(Question).filter(Question.id == question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="السؤال غير موجود"
        )
    
    # Verify ownership through exam -> lesson -> course
    exam = db.query(Exam).filter(Exam.id == question.exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الامتحان المرتبط بالسؤال غير موجود"
        )
    
    lesson = db.query(Lesson).filter(Lesson.id == exam.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدرس المرتبط بالسؤال غير موجود"
        )
    
    course = db.query(Course).filter(
        Course.id == lesson.course_id,
        Course.academy_id == current_user.academy.id
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحية لعرض هذا السؤال"
        )
    
    return SayanSuccessResponse(
        data={
            "question": question,
            "options": question.options,
            "total_options": len(question.options) if question.options else 0
        },
        message="تم جلب تفاصيل السؤال بنجاح"
    )


@router.put("/questions/{question_id}")
async def update_question(
    question_id: str,
    question_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Update question details"""
    
    try:
        # Get question
        question = db.query(Question).filter(Question.id == question_id).first()
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="السؤال غير موجود"
            )
        
        # Verify ownership through exam -> lesson -> course
        exam = db.query(Exam).filter(Exam.id == question.exam_id).first()
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الامتحان المرتبط بالسؤال غير موجود"
            )
        
        lesson = db.query(Lesson).filter(Lesson.id == exam.lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الدرس المرتبط بالسؤال غير موجود"
            )
        
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية لتعديل هذا السؤال"
            )
        
        # Update question fields
        for field, value in question_data.items():
            if hasattr(question, field):
                setattr(question, field, value)
        
        db.commit()
        db.refresh(question)
        
        return SayanSuccessResponse(
            data={"question": question},
            message="تم تحديث السؤال بنجاح"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"حدث خطأ أثناء تحديث السؤال: {str(e)}"
        )


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Delete question and all its options"""
    
    try:
        # Get question
        question = db.query(Question).filter(Question.id == question_id).first()
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="السؤال غير موجود"
            )
        
        # Verify ownership through exam -> lesson -> course
        exam = db.query(Exam).filter(Exam.id == question.exam_id).first()
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الامتحان المرتبط بالسؤال غير موجود"
            )
        
        lesson = db.query(Lesson).filter(Lesson.id == exam.lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="الدرس المرتبط بالسؤال غير موجود"
            )
        
        course = db.query(Course).filter(
            Course.id == lesson.course_id,
            Course.academy_id == current_user.academy.id
        ).first()
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية لحذف هذا السؤال"
            )
        
        db.delete(question)
        db.commit()
        
        return SayanSuccessResponse(
            message="تم حذف السؤال بنجاح"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"حدث خطأ أثناء حذف السؤال: {str(e)}"
        )


# =====================================
# STUDENT EXAM ENDPOINTS
# =====================================




@router.post("/public/{exam_id}/submit")
async def submit_exam_answers(
    exam_id: str,
    answers: dict,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Submit exam answers and get results"""
    
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الامتحان غير موجود"
        )
    
    return SayanSuccessResponse(
        data={
            "results": {
                "score": 0,
                "total_marks": exam.total_marks,
                "passed": False,
                "percentage": 0
            }
        },
        message="تم تسليم الامتحان بنجاح"
    ) 

 