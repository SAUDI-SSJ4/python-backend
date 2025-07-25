"""
Text Quality Enhancement Service

This service provides tools for improving transcription quality,
validating accuracy, and enhancing text readability.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class TextQualityService:
    """
    Service for enhancing transcription text quality and accuracy
    """
    
    def __init__(self):
        self.arabic_punctuation = {
            '،': ',',
            '؛': ';',
            '؟': '?',
            '!': '!',
            '...': '...',
            '..': '..',
            '.': '.'
        }
        
        self.common_arabic_fixes = {
            'اللغة العربية': 'اللغة العربية',
            'البرمجة': 'البرمجة',
            'التطوير': 'التطوير',
            'الويب': 'الويب',
            'المواقع': 'المواقع',
            'التطبيقات': 'التطبيقات',
            'قاعدة البيانات': 'قاعدة البيانات',
            'الخوارزميات': 'الخوارزميات',
            'الذكاء الاصطناعي': 'الذكاء الاصطناعي',
            'التعلم الآلي': 'التعلم الآلي'
        }
    
    def enhance_transcription_quality(
        self, 
        text: str, 
        language: str = "ar",
        confidence_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Enhance transcription text quality with multiple improvements
        
        Process Flow:
        1. Clean and normalize text
        2. Fix common transcription errors
        3. Improve punctuation and formatting
        4. Calculate quality metrics
        5. Apply confidence-based corrections
        6. Return enhanced text with quality report
        """
        try:
            original_text = text
            enhanced_text = text
            
            # Step 1: Basic text cleaning
            enhanced_text = self._clean_text(enhanced_text)
            
            # Step 2: Language-specific enhancements
            if language == "ar":
                enhanced_text = self._enhance_arabic_text(enhanced_text)
            else:
                enhanced_text = self._enhance_english_text(enhanced_text)
            
            # Step 3: Fix common transcription errors
            enhanced_text = self._fix_common_errors(enhanced_text, language)
            
            # Step 4: Improve punctuation and formatting
            enhanced_text = self._improve_punctuation(enhanced_text, language)
            
            # Step 5: Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(
                original_text, 
                enhanced_text, 
                confidence_score
            )
            
            # Step 6: Apply confidence-based corrections
            if confidence_score < 0.7:
                enhanced_text = self._apply_low_confidence_fixes(enhanced_text, language)
            
            return {
                "original_text": original_text,
                "enhanced_text": enhanced_text,
                "quality_metrics": quality_metrics,
                "improvements_applied": self._get_applied_improvements(original_text, enhanced_text),
                "confidence_score": confidence_score,
                "language": language
            }
            
        except Exception as e:
            logger.error(f"Error enhancing transcription quality: {e}")
            return {
                "original_text": text,
                "enhanced_text": text,
                "quality_metrics": {"error": str(e)},
                "improvements_applied": [],
                "confidence_score": confidence_score,
                "language": language
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return text
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normalize line breaks
        text = re.sub(r'\n+', '\n', text)
        
        return text
    
    def _enhance_arabic_text(self, text: str) -> str:
        """Enhance Arabic text specifically"""
        if not text:
            return text
        
        # Fix common Arabic transcription issues
        for wrong, correct in self.common_arabic_fixes.items():
            text = text.replace(wrong, correct)
        
        # Fix Arabic numbers
        text = self._fix_arabic_numbers(text)
        
        # Fix Arabic punctuation
        text = self._fix_arabic_punctuation(text)
        
        # Fix common Arabic word combinations
        text = self._fix_arabic_word_combinations(text)
        
        return text
    
    def _enhance_english_text(self, text: str) -> str:
        """Enhance English text specifically"""
        if not text:
            return text
        
        # Fix common English transcription issues
        text = self._fix_english_common_errors(text)
        
        # Improve capitalization
        text = self._improve_english_capitalization(text)
        
        return text
    
    def _fix_arabic_numbers(self, text: str) -> str:
        """Fix Arabic number transcription"""
        # Common number fixes
        number_fixes = {
            'صفر': '0',
            'واحد': '1',
            'اثنين': '2',
            'ثلاثة': '3',
            'أربعة': '4',
            'خمسة': '5',
            'ستة': '6',
            'سبعة': '7',
            'ثمانية': '8',
            'تسعة': '9',
            'عشرة': '10'
        }
        
        for arabic, number in number_fixes.items():
            text = re.sub(rf'\b{arabic}\b', number, text)
        
        return text
    
    def _fix_arabic_punctuation(self, text: str) -> str:
        """Fix Arabic punctuation marks"""
        # Fix spacing around punctuation
        text = re.sub(r'\s*([،؛؟!])\s*', r'\1 ', text)
        
        # Fix multiple punctuation marks
        text = re.sub(r'([،؛؟!])\1+', r'\1', text)
        
        return text
    
    def _fix_arabic_word_combinations(self, text: str) -> str:
        """Fix common Arabic word combination errors"""
        # Fix common word separations
        word_fixes = {
            'في هذا': 'في هذا',
            'من أجل': 'من أجل',
            'على سبيل': 'على سبيل',
            'بالإضافة إلى': 'بالإضافة إلى',
            'على الرغم من': 'على الرغم من'
        }
        
        for wrong, correct in word_fixes.items():
            text = text.replace(wrong, correct)
        
        return text
    
    def _fix_english_common_errors(self, text: str) -> str:
        """Fix common English transcription errors"""
        # Common English fixes
        english_fixes = {
            'programming': 'programming',
            'development': 'development',
            'application': 'application',
            'database': 'database',
            'algorithm': 'algorithm',
            'artificial intelligence': 'artificial intelligence',
            'machine learning': 'machine learning'
        }
        
        for wrong, correct in english_fixes.items():
            text = text.replace(wrong, correct)
        
        return text
    
    def _improve_english_capitalization(self, text: str) -> str:
        """Improve English text capitalization"""
        # Capitalize first letter of sentences
        sentences = text.split('. ')
        capitalized_sentences = []
        
        for sentence in sentences:
            if sentence:
                sentence = sentence.strip()
                if sentence and sentence[0].isalpha():
                    sentence = sentence[0].upper() + sentence[1:]
                capitalized_sentences.append(sentence)
        
        return '. '.join(capitalized_sentences)
    
    def _fix_common_errors(self, text: str, language: str) -> str:
        """Fix common transcription errors"""
        if language == "ar":
            # Arabic-specific fixes
            text = re.sub(r'\b(هذا|هذه|هؤلاء)\s+(هذا|هذه|هؤلاء)\b', r'\1', text)
            text = re.sub(r'\b(في|من|إلى|على)\s+(في|من|إلى|على)\b', r'\1', text)
        else:
            # English-specific fixes
            text = re.sub(r'\b(the|a|an)\s+(the|a|an)\b', r'\1', text, flags=re.IGNORECASE)
            text = re.sub(r'\b(is|are|was|were)\s+(is|are|was|were)\b', r'\1', text, flags=re.IGNORECASE)
        
        return text
    
    def _improve_punctuation(self, text: str, language: str) -> str:
        """Improve punctuation and formatting"""
        # Fix spacing around punctuation
        if language == "ar":
            text = re.sub(r'\s*([،؛؟!])\s*', r'\1 ', text)
        else:
            text = re.sub(r'\s*([,.!?;:])\s*', r'\1 ', text)
        
        # Fix multiple punctuation marks
        text = re.sub(r'([،؛؟!.,!?;:])\1+', r'\1', text)
        
        # Fix sentence endings
        text = re.sub(r'([^.!?])\s*$', r'\1.', text)
        
        return text
    
    def _calculate_quality_metrics(
        self, 
        original_text: str, 
        enhanced_text: str, 
        confidence_score: float
    ) -> Dict[str, Any]:
        """Calculate text quality metrics"""
        try:
            # Basic metrics
            original_length = len(original_text)
            enhanced_length = len(enhanced_text)
            
            # Word count
            original_words = len(original_text.split())
            enhanced_words = len(enhanced_text.split())
            
            # Character-level similarity
            similarity = self._calculate_similarity(original_text, enhanced_text)
            
            # Readability score (simple implementation)
            readability_score = self._calculate_readability(enhanced_text)
            
            # Quality indicators
            has_punctuation = bool(re.search(r'[،؛؟!.,!?;:]', enhanced_text))
            has_proper_spacing = not bool(re.search(r'\s{2,}', enhanced_text))
            has_proper_capitalization = bool(re.search(r'[A-Z]', enhanced_text)) if enhanced_text else False
            
            return {
                "original_length": original_length,
                "enhanced_length": enhanced_length,
                "original_words": original_words,
                "enhanced_words": enhanced_words,
                "similarity_score": similarity,
                "readability_score": readability_score,
                "confidence_score": confidence_score,
                "quality_indicators": {
                    "has_punctuation": has_punctuation,
                    "has_proper_spacing": has_proper_spacing,
                    "has_proper_capitalization": has_proper_capitalization
                },
                "improvement_percentage": self._calculate_improvement_percentage(
                    original_text, enhanced_text
                )
            }
            
        except Exception as e:
            logger.error(f"Error calculating quality metrics: {e}")
            return {"error": str(e)}
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        # Simple character-based similarity
        set1 = set(text1.lower())
        set2 = set(text2.lower())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_readability(self, text: str) -> float:
        """Calculate simple readability score"""
        if not text:
            return 0.0
        
        # Simple readability based on sentence and word length
        sentences = text.split('.')
        words = text.split()
        
        if not sentences or not words:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Higher score for moderate sentence and word lengths
        sentence_score = max(0, 1 - abs(avg_sentence_length - 15) / 15)
        word_score = max(0, 1 - abs(avg_word_length - 5) / 5)
        
        return (sentence_score + word_score) / 2
    
    def _calculate_improvement_percentage(self, original: str, enhanced: str) -> float:
        """Calculate improvement percentage"""
        if not original:
            return 0.0
        
        # Simple improvement calculation
        original_quality = len(original.strip()) / max(len(original), 1)
        enhanced_quality = len(enhanced.strip()) / max(len(enhanced), 1)
        
        if original_quality == 0:
            return 100.0
        
        improvement = ((enhanced_quality - original_quality) / original_quality) * 100
        return max(0, min(100, improvement))
    
    def _apply_low_confidence_fixes(self, text: str, language: str) -> str:
        """Apply additional fixes for low confidence transcriptions"""
        # More aggressive cleaning for low confidence
        text = re.sub(r'\b\w{1,2}\b', '', text)  # Remove very short words
        text = re.sub(r'\s+', ' ', text)  # Normalize spaces
        
        return text.strip()
    
    def _get_applied_improvements(self, original: str, enhanced: str) -> List[str]:
        """Get list of applied improvements"""
        improvements = []
        
        if len(enhanced.strip()) > len(original.strip()):
            improvements.append("Text length increased")
        
        if re.search(r'[،؛؟!.,!?;:]', enhanced) and not re.search(r'[،؛؟!.,!?;:]', original):
            improvements.append("Punctuation added")
        
        if not re.search(r'\s{2,}', enhanced) and re.search(r'\s{2,}', original):
            improvements.append("Spacing normalized")
        
        if len(enhanced.split()) > len(original.split()):
            improvements.append("Word count increased")
        
        return improvements
    
    def validate_transcription_accuracy(
        self, 
        transcription_text: str, 
        expected_keywords: List[str] = None,
        language: str = "ar"
    ) -> Dict[str, Any]:
        """
        Validate transcription accuracy against expected content
        
        Args:
            transcription_text: The transcribed text
            expected_keywords: List of expected keywords
            language: Language of the text
            
        Returns:
            Dictionary with accuracy metrics and suggestions
        """
        try:
            validation_result = {
                "overall_accuracy": 0.0,
                "keyword_matches": [],
                "missing_keywords": [],
                "unexpected_content": [],
                "suggestions": [],
                "confidence_level": "low"
            }
            
            if not transcription_text:
                validation_result["suggestions"].append("Transcription text is empty")
                return validation_result
            
            # Check for expected keywords
            if expected_keywords:
                found_keywords = []
                missing_keywords = []
                
                for keyword in expected_keywords:
                    if keyword.lower() in transcription_text.lower():
                        found_keywords.append(keyword)
                    else:
                        missing_keywords.append(keyword)
                
                validation_result["keyword_matches"] = found_keywords
                validation_result["missing_keywords"] = missing_keywords
                
                # Calculate accuracy based on keyword matches
                if expected_keywords:
                    accuracy = len(found_keywords) / len(expected_keywords)
                    validation_result["overall_accuracy"] = accuracy
                    
                    if accuracy >= 0.8:
                        validation_result["confidence_level"] = "high"
                    elif accuracy >= 0.6:
                        validation_result["confidence_level"] = "medium"
                    else:
                        validation_result["confidence_level"] = "low"
            
            # Check for common transcription issues
            issues = self._detect_transcription_issues(transcription_text, language)
            validation_result["unexpected_content"] = issues
            
            # Generate suggestions
            suggestions = self._generate_accuracy_suggestions(validation_result, language)
            validation_result["suggestions"] = suggestions
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating transcription accuracy: {e}")
            return {
                "overall_accuracy": 0.0,
                "error": str(e),
                "confidence_level": "unknown"
            }
    
    def _detect_transcription_issues(self, text: str, language: str) -> List[str]:
        """Detect common transcription issues"""
        issues = []
        
        # Check for repeated words
        words = text.split()
        for i in range(len(words) - 1):
            if words[i] == words[i + 1]:
                issues.append(f"Repeated word: {words[i]}")
        
        # Check for very short sentences
        sentences = text.split('.')
        for sentence in sentences:
            if len(sentence.strip().split()) < 3:
                issues.append(f"Very short sentence: {sentence.strip()}")
        
        # Check for missing punctuation
        if not re.search(r'[،؛؟!.,!?;:]', text):
            issues.append("Missing punctuation")
        
        return issues
    
    def _generate_accuracy_suggestions(
        self, 
        validation_result: Dict[str, Any], 
        language: str
    ) -> List[str]:
        """Generate suggestions for improving accuracy"""
        suggestions = []
        
        if validation_result["overall_accuracy"] < 0.6:
            suggestions.append("Consider re-transcribing with better audio quality")
        
        if validation_result["missing_keywords"]:
            suggestions.append(f"Missing expected keywords: {', '.join(validation_result['missing_keywords'])}")
        
        if validation_result["unexpected_content"]:
            suggestions.append("Review transcription for accuracy issues")
        
        if validation_result["confidence_level"] == "low":
            suggestions.append("Low confidence transcription - manual review recommended")
        
        return suggestions 