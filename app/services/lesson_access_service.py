from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.lesson import Lesson
from app.models.chapter import Chapter
from app.models.course import Course
from app.models.lesson_progress import LessonProgress
from app.models.student_course import StudentCourse
from app.models.student import Student


class LessonAccessService:
    """Service to handle lesson access control and progression logic"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def can_access_lesson(self, student_id: int, lesson_id: int) -> Dict[str, Any]:
        """
        Check if a student can access a specific lesson based on progression rules
        
        Args:
            student_id: ID of the student
            lesson_id: ID of the lesson to check access for
            
        Returns:
            Dict containing access status and reason
        """
        try:
            # Get lesson details
            lesson = self.db.query(Lesson).filter(Lesson.id == lesson_id).first()
            if not lesson:
                return {
                    "is_accessible": False,
                    "access_reason": "Lesson not found",
                    "error": "LESSON_NOT_FOUND"
                }
            
            # Check if student is enrolled in the course
            enrollment = self.db.query(StudentCourse).filter(
                StudentCourse.student_id == student_id,
                StudentCourse.course_id == lesson.course_id
            ).first()
            
            if not enrollment:
                return {
                    "is_accessible": False,
                    "access_reason": "Student not enrolled in course",
                    "error": "NOT_ENROLLED"
                }
            
            # Check if lesson is marked as free preview
            if lesson.is_free_preview:
                return {
                    "is_accessible": True,
                    "access_reason": "Free preview lesson",
                    "lesson_type": lesson.lesson_type
                }
            
            # Check chapter access
            chapter_access = self._can_access_chapter(student_id, lesson.chapter_id)
            if not chapter_access["is_accessible"]:
                return chapter_access
            
            # Check previous lessons in the same chapter
            previous_lessons = self.db.query(Lesson).filter(
                Lesson.chapter_id == lesson.chapter_id,
                Lesson.order_number < lesson.order_number
            ).order_by(Lesson.order_number).all()
            
            # Check if all previous lessons are sufficiently completed
            for prev_lesson in previous_lessons:
                if not self._is_lesson_sufficiently_completed(student_id, prev_lesson.id, prev_lesson.lesson_type):
                    return {
                        "is_accessible": False,
                        "access_reason": f"Previous lesson '{prev_lesson.title}' must be completed first",
                        "error": "PREVIOUS_LESSON_INCOMPLETE",
                        "required_lesson_id": prev_lesson.id,
                        "required_lesson_title": prev_lesson.title
                    }
            
            return {
                "is_accessible": True,
                "access_reason": "All prerequisites met",
                "lesson_type": lesson.lesson_type
            }
            
        except Exception as e:
            return {
                "is_accessible": False,
                "access_reason": f"Error checking access: {str(e)}",
                "error": "SYSTEM_ERROR"
            }
    
    def _can_access_chapter(self, student_id: int, chapter_id: int) -> Dict[str, Any]:
        """
        Check if student can access a specific chapter
        
        Args:
            student_id: ID of the student
            chapter_id: ID of the chapter to check
            
        Returns:
            Dict containing access status and reason
        """
        try:
            # Get chapter details
            chapter = self.db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if not chapter:
                return {
                    "is_accessible": False,
                    "access_reason": "Chapter not found",
                    "error": "CHAPTER_NOT_FOUND"
                }
            
            # Get all chapters in the course ordered by order_number
            previous_chapters = self.db.query(Chapter).filter(
                Chapter.course_id == chapter.course_id,
                Chapter.order_number < chapter.order_number
            ).order_by(Chapter.order_number).all()
            
            # Check if all previous chapters are completed
            for prev_chapter in previous_chapters:
                completion_info = self.get_chapter_completion(student_id, prev_chapter.id)
                if completion_info["completion_percentage"] < 100:
                    return {
                        "is_accessible": False,
                        "access_reason": f"Previous chapter '{prev_chapter.title}' must be completed first",
                        "error": "PREVIOUS_CHAPTER_INCOMPLETE",
                        "required_chapter_id": prev_chapter.id,
                        "required_chapter_title": prev_chapter.title,
                        "current_completion": completion_info["completion_percentage"]
                    }
            
            return {
                "is_accessible": True,
                "access_reason": "All previous chapters completed"
            }
            
        except Exception as e:
            return {
                "is_accessible": False,
                "access_reason": f"Error checking chapter access: {str(e)}",
                "error": "SYSTEM_ERROR"
            }
    
    def _is_lesson_sufficiently_completed(self, student_id: int, lesson_id: int, lesson_type: str) -> bool:
        """
        Check if a lesson meets completion requirements based on its type
        
        Args:
            student_id: ID of the student
            lesson_id: ID of the lesson
            lesson_type: Type of lesson (video, exam, tool, text)
            
        Returns:
            Boolean indicating if lesson is sufficiently completed
        """
        try:
            progress = self.db.query(LessonProgress).filter(
                LessonProgress.student_id == student_id,
                LessonProgress.lesson_id == lesson_id
            ).first()
            
            if not progress:
                return False
            
            # Different completion rules based on lesson type
            if lesson_type == "video":
                # Video lessons require 50% completion
                return progress.progress_percentage >= 50
            elif lesson_type in ["exam", "tool"]:
                # Exam and tool lessons require 100% completion
                return progress.completed and progress.progress_percentage >= 100
            elif lesson_type == "text":
                # Text lessons require 100% completion
                return progress.completed and progress.progress_percentage >= 100
            else:
                # Default: require 100% completion
                return progress.completed and progress.progress_percentage >= 100
                
        except Exception:
            return False
    
    def get_chapter_completion(self, student_id: int, chapter_id: int) -> Dict[str, Any]:
        """
        Calculate completion percentage for a specific chapter
        
        Args:
            student_id: ID of the student
            chapter_id: ID of the chapter
            
        Returns:
            Dict containing completion information
        """
        try:
            # Get all lessons in the chapter
            lessons = self.db.query(Lesson).filter(
                Lesson.chapter_id == chapter_id
            ).all()
            
            if not lessons:
                return {
                    "completion_percentage": 0,
                    "completed_lessons": 0,
                    "total_lessons": 0,
                    "accessible_lessons": 0
                }
            
            completed_count = 0
            accessible_count = 0
            
            for lesson in lessons:
                # Check if lesson is accessible
                access_result = self.can_access_lesson(student_id, lesson.id)
                if access_result["is_accessible"]:
                    accessible_count += 1
                
                # Check if lesson is sufficiently completed
                if self._is_lesson_sufficiently_completed(student_id, lesson.id, lesson.lesson_type):
                    completed_count += 1
            
            completion_percentage = (completed_count / len(lessons)) * 100 if lessons else 0
            
            return {
                "completion_percentage": round(completion_percentage, 2),
                "completed_lessons": completed_count,
                "total_lessons": len(lessons),
                "accessible_lessons": accessible_count
            }
            
        except Exception as e:
            return {
                "completion_percentage": 0,
                "completed_lessons": 0,
                "total_lessons": 0,
                "accessible_lessons": 0,
                "error": str(e)
            }
    
    def get_course_progression(self, student_id: int, course_id: int) -> Dict[str, Any]:
        """
        Get comprehensive course progression information
        
        Args:
            student_id: ID of the student
            course_id: ID of the course
            
        Returns:
            Dict containing full progression information
        """
        try:
            # Check enrollment
            enrollment = self.db.query(StudentCourse).filter(
                StudentCourse.student_id == student_id,
                StudentCourse.course_id == course_id
            ).first()
            
            if not enrollment:
                return {
                    "error": "Student not enrolled in course",
                    "is_enrolled": False
                }
            
            # Get all chapters in order
            chapters = self.db.query(Chapter).filter(
                Chapter.course_id == course_id
            ).order_by(Chapter.order_number).all()
            
            chapters_info = []
            total_course_lessons = 0
            total_completed_lessons = 0
            
            for chapter in chapters:
                chapter_completion = self.get_chapter_completion(student_id, chapter.id)
                
                # Get lessons in this chapter
                lessons = self.db.query(Lesson).filter(
                    Lesson.chapter_id == chapter.id
                ).order_by(Lesson.order_number).all()
                
                lessons_info = []
                for lesson in lessons:
                    access_result = self.can_access_lesson(student_id, lesson.id)
                    
                    # Get lesson progress
                    progress = self.db.query(LessonProgress).filter(
                        LessonProgress.student_id == student_id,
                        LessonProgress.lesson_id == lesson.id
                    ).first()
                    
                    lesson_info = {
                        "lesson_id": lesson.id,
                        "title": lesson.title,
                        "lesson_type": lesson.lesson_type,
                        "order_number": lesson.order_number,
                        "is_accessible": access_result["is_accessible"],
                        "access_reason": access_result["access_reason"],
                        "is_free_preview": lesson.is_free_preview,
                        "progress_percentage": progress.progress_percentage if progress else 0,
                        "is_completed": self._is_lesson_sufficiently_completed(student_id, lesson.id, lesson.lesson_type)
                    }
                    
                    lessons_info.append(lesson_info)
                    total_course_lessons += 1
                    if lesson_info["is_completed"]:
                        total_completed_lessons += 1
                
                chapter_access = self._can_access_chapter(student_id, chapter.id)
                chapters_info.append({
                    "chapter_id": chapter.id,
                    "title": chapter.title,
                    "order_number": chapter.order_number,
                    "is_accessible": chapter_access["is_accessible"],
                    "completion_percentage": chapter_completion["completion_percentage"],
                    "lessons": lessons_info
                })
            
            # Calculate overall course completion
            course_completion = (total_completed_lessons / total_course_lessons) * 100 if total_course_lessons > 0 else 0
            
            # Find next accessible lesson
            next_lesson = None
            for chapter_info in chapters_info:
                for lesson_info in chapter_info["lessons"]:
                    if lesson_info["is_accessible"] and not lesson_info["is_completed"]:
                        next_lesson = {
                            "lesson_id": lesson_info["lesson_id"],
                            "title": lesson_info["title"],
                            "chapter_title": chapter_info["title"]
                        }
                        break
                if next_lesson:
                    break
            
            return {
                "is_enrolled": True,
                "course_completion_percentage": round(course_completion, 2),
                "total_lessons": total_course_lessons,
                "completed_lessons": total_completed_lessons,
                "next_lesson": next_lesson,
                "chapters": chapters_info
            }
            
        except Exception as e:
            return {
                "error": f"Error getting course progression: {str(e)}",
                "is_enrolled": False
            }
    
    def get_next_accessible_lesson(self, student_id: int, course_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the next accessible lesson for a student in a course
        
        Args:
            student_id: ID of the student
            course_id: ID of the course
            
        Returns:
            Dict containing next lesson information or None
        """
        try:
            progression = self.get_course_progression(student_id, course_id)
            return progression.get("next_lesson")
        except Exception:
            return None 