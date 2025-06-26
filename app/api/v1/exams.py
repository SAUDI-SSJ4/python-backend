"""
Simplified Exams and Questions API
=================================
Using direct IDs for cleaner API design
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps.database import get_db
from app.deps.auth import get_current_academy_user, get_current_student
from app.models.exam import Exam, Question, QuestionOption, QuestionType
from app.models.lesson import Lesson
from app.models.course import Course
from app.models.user import User
from app.models.student import Student

router = APIRouter()

# =====================================
# SIMPLIFIED EXAM ENDPOINTS
# =====================================

@router.get("/exams/{exam_id}")
async def get_exam_details(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Get exam details with questions"""
    
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
            detail="ليس لديك صلاحية لعرض هذا الامتحان"
        )
    
    return {
        "status": "success",
        "exam": exam,
        "questions": exam.questions,
        "total_questions": len(exam.questions) if exam.questions else 0
    }


@router.put("/exams/{exam_id}")
async def update_exam(
    exam_id: str,
    exam_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Update exam details"""
    
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
    
    # Update exam fields
    for field, value in exam_data.items():
        if hasattr(exam, field):
            setattr(exam, field, value)
    
    db.commit()
    db.refresh(exam)
    
    return {
        "status": "success",
        "message": "تم تحديث الامتحان بنجاح",
        "exam": exam
    }


@router.delete("/exams/{exam_id}")
async def delete_exam(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Delete exam and all its questions"""
    
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
    
    db.delete(exam)
    db.commit()
    
    return {
        "status": "success",
        "message": "تم حذف الامتحان بنجاح"
    }


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
    
    return {
        "status": "success",
        "question": question,
        "options": question.options,
        "total_options": len(question.options) if question.options else 0
    }


@router.put("/questions/{question_id}")
async def update_question(
    question_id: str,
    question_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Update question details"""
    
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
    
    return {
        "status": "success",
        "message": "تم تحديث السؤال بنجاح",
        "question": question
    }


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_academy_user)
) -> Any:
    """Delete question and all its options"""
    
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
    
    return {
        "status": "success",
        "message": "تم حذف السؤال بنجاح"
    }


# =====================================
# STUDENT EXAM ENDPOINTS
# =====================================

@router.get("/public/exams/{exam_id}")
async def get_exam_for_student(
    exam_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Get exam for student to take"""
    
    # Get exam
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الامتحان غير موجود"
        )
    
    # Verify student enrollment in course
    lesson = db.query(Lesson).filter(Lesson.id == exam.lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الدرس المرتبط بالامتحان غير موجود"
        )
    
    # TODO: Add enrollment verification logic here
    # student_enrollment = check_student_enrollment(current_student.id, lesson.course_id)
    # if not student_enrollment:
    #     raise HTTPException(status_code=403, detail="غير مسجل في هذه الدورة")
    
    # Return exam without showing correct answers
    exam_data = {
        "id": exam.id,
        "title": exam.title,
        "description": exam.description,
        "time_limit_minutes": exam.time_limit_minutes,
        "total_marks": exam.total_marks,
        "passing_marks": exam.passing_marks,
        "questions": []
    }
    
    # Add questions without correct answers
    for question in exam.questions:
        question_data = {
            "id": question.id,
            "text": question.text,
            "type": question.type,
            "marks": question.marks,
            "options": []
        }
        
        # Add options without showing which is correct
        for option in question.options:
            option_data = {
                "id": option.id,
                "text": option.text,
                "option_key": option.option_key
                # Don't include 'is_correct' for students
            }
            question_data["options"].append(option_data)
        
        exam_data["questions"].append(question_data)
    
    return {
        "status": "success",
        "exam": exam_data
    }


@router.post("/public/exams/{exam_id}/submit")
async def submit_exam_answers(
    exam_id: str,
    answers: dict,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
) -> Any:
    """Submit exam answers and get results"""
    
    # Get exam
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الامتحان غير موجود"
        )
    
    # TODO: Calculate score based on answers
    # TODO: Save student exam attempt
    # TODO: Return results
    
    return {
        "status": "success",
        "message": "تم تسليم الامتحان بنجاح",
        "results": {
            "score": 0,  # Calculate based on answers
            "total_marks": exam.total_marks,
            "passed": False,  # Based on passing_marks
            "percentage": 0
        }
    } 