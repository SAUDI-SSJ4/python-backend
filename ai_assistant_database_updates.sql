-- SAYAN AI Assistant Database Updates
-- ===================================
-- This SQL file contains the necessary database modifications
-- to implement the AI Assistant system for SAYAN Academy Platform

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

-- --------------------------------------------------------
-- 1. VIDEO TRANSCRIPTION SYSTEM
-- --------------------------------------------------------

-- Table for storing video transcriptions
CREATE TABLE `video_transcriptions` (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `lesson_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `video_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transcription_text` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `subtitles_srt` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `subtitles_vtt` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `language` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'ar',
  `confidence_score` decimal(5,2) DEFAULT '0.00',
  `processing_status` ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
  `processing_time_seconds` int DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `video_transcriptions_lesson_id_foreign` (`lesson_id`),
  KEY `video_transcriptions_video_id_foreign` (`video_id`),
  KEY `video_transcriptions_status_index` (`processing_status`),
  CONSTRAINT `video_transcriptions_lesson_id_foreign` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`) ON DELETE CASCADE,
  CONSTRAINT `video_transcriptions_video_id_foreign` FOREIGN KEY (`video_id`) REFERENCES `videos` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing video content segments with timestamps
CREATE TABLE `video_segments` (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `transcription_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `start_time` int NOT NULL,
  `end_time` int NOT NULL,
  `text` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `keywords` json DEFAULT NULL,
  `confidence_score` decimal(5,2) DEFAULT '0.00',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `video_segments_transcription_id_foreign` (`transcription_id`),
  KEY `video_segments_start_time_index` (`start_time`),
  CONSTRAINT `video_segments_transcription_id_foreign` FOREIGN KEY (`transcription_id`) REFERENCES `video_transcriptions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 2. AI EXAM CORRECTION SYSTEM
-- --------------------------------------------------------

-- Enhanced AI Answers table (updating existing)
ALTER TABLE `ai_answers` 
ADD COLUMN `answer_type` ENUM('question', 'exam_feedback', 'recommendation', 'summary') DEFAULT 'question',
ADD COLUMN `context_data` json DEFAULT NULL,
ADD COLUMN `confidence_score` decimal(5,2) DEFAULT '0.00',
ADD COLUMN `source_content_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
ADD COLUMN `ai_model_used` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'gpt-4',
ADD COLUMN `processing_time_ms` int DEFAULT '0',
ADD COLUMN `feedback_score` tinyint DEFAULT NULL,
ADD COLUMN `is_helpful` boolean DEFAULT NULL;

-- Table for storing exam corrections and feedback
CREATE TABLE `exam_corrections` (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `exam_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `student_id` bigint UNSIGNED NOT NULL,
  `submission_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `total_score` decimal(5,2) NOT NULL DEFAULT '0.00',
  `max_score` decimal(5,2) NOT NULL DEFAULT '0.00',
  `percentage` decimal(5,2) NOT NULL DEFAULT '0.00',
  `auto_feedback` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `recommendations` json DEFAULT NULL,
  `improvement_areas` json DEFAULT NULL,
  `strengths` json DEFAULT NULL,
  `study_plan` json DEFAULT NULL,
  `corrected_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `exam_corrections_exam_id_foreign` (`exam_id`),
  KEY `exam_corrections_student_id_foreign` (`student_id`),
  KEY `exam_corrections_percentage_index` (`percentage`),
  CONSTRAINT `exam_corrections_exam_id_foreign` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`) ON DELETE CASCADE,
  CONSTRAINT `exam_corrections_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing individual question corrections
CREATE TABLE `question_corrections` (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `exam_correction_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `question_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `student_answer` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `correct_answer` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `is_correct` boolean NOT NULL DEFAULT false,
  `score_awarded` decimal(5,2) NOT NULL DEFAULT '0.00',
  `max_score` decimal(5,2) NOT NULL DEFAULT '0.00',
  `ai_feedback` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `difficulty_level` ENUM('easy', 'medium', 'hard') DEFAULT 'medium',
  `time_spent_seconds` int DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `question_corrections_exam_correction_id_foreign` (`exam_correction_id`),
  KEY `question_corrections_question_id_foreign` (`question_id`),
  KEY `question_corrections_is_correct_index` (`is_correct`),
  CONSTRAINT `question_corrections_exam_correction_id_foreign` FOREIGN KEY (`exam_correction_id`) REFERENCES `exam_corrections` (`id`) ON DELETE CASCADE,
  CONSTRAINT `question_corrections_question_id_foreign` FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 3. AI LESSON SUMMARIZATION SYSTEM
-- --------------------------------------------------------

-- Table for storing lesson summaries
CREATE TABLE `lesson_summaries` (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `lesson_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `short_summary` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `detailed_summary` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `key_points` json DEFAULT NULL,
  `learning_objectives` json DEFAULT NULL,
  `tags` json DEFAULT NULL,
  `difficulty_level` ENUM('beginner', 'intermediate', 'advanced') DEFAULT 'beginner',
  `estimated_study_time` int DEFAULT '0',
  `prerequisites` json DEFAULT NULL,
  `generated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `lesson_summaries_lesson_id_foreign` (`lesson_id`),
  KEY `lesson_summaries_difficulty_index` (`difficulty_level`),
  CONSTRAINT `lesson_summaries_lesson_id_foreign` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 4. AI EXAM GENERATION SYSTEM
-- --------------------------------------------------------

-- Table for storing AI-generated exam templates
CREATE TABLE `ai_exam_templates` (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `lesson_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `course_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `template_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `difficulty_level` ENUM('easy', 'medium', 'hard', 'mixed') DEFAULT 'medium',
  `question_count` int DEFAULT '10',
  `time_limit_minutes` int DEFAULT '30',
  `passing_score` decimal(5,2) DEFAULT '60.00',
  `question_types` json DEFAULT NULL,
  `content_focus` json DEFAULT NULL,
  `is_active` boolean DEFAULT true,
  `created_by` bigint UNSIGNED DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ai_exam_templates_lesson_id_foreign` (`lesson_id`),
  KEY `ai_exam_templates_course_id_foreign` (`course_id`),
  KEY `ai_exam_templates_difficulty_index` (`difficulty_level`),
  CONSTRAINT `ai_exam_templates_lesson_id_foreign` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`) ON DELETE CASCADE,
  CONSTRAINT `ai_exam_templates_course_id_foreign` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing AI-generated questions
CREATE TABLE `ai_generated_questions` (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `template_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `question_text` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `question_type` ENUM('multiple_choice', 'true_false', 'short_answer', 'essay') NOT NULL,
  `difficulty_level` ENUM('easy', 'medium', 'hard') DEFAULT 'medium',
  `options` json DEFAULT NULL,
  `correct_answer` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `explanation` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `points` int DEFAULT '1',
  `source_content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `bloom_taxonomy_level` ENUM('remember', 'understand', 'apply', 'analyze', 'evaluate', 'create') DEFAULT 'understand',
  `is_approved` boolean DEFAULT false,
  `quality_score` decimal(5,2) DEFAULT '0.00',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ai_generated_questions_template_id_foreign` (`template_id`),
  KEY `ai_generated_questions_type_index` (`question_type`),
  KEY `ai_generated_questions_difficulty_index` (`difficulty_level`),
  CONSTRAINT `ai_generated_questions_template_id_foreign` FOREIGN KEY (`template_id`) REFERENCES `ai_exam_templates` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 5. AI CONVERSATION SYSTEM
-- --------------------------------------------------------

-- Table for storing AI conversations
CREATE TABLE `ai_conversations` (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` bigint UNSIGNED NOT NULL,
  `user_type` ENUM('student', 'academy', 'admin') NOT NULL DEFAULT 'student',
  `conversation_type` ENUM('lesson_help', 'exam_help', 'general_support', 'course_question') NOT NULL,
  `context_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `context_type` ENUM('lesson', 'exam', 'course', 'general') DEFAULT 'general',
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` ENUM('active', 'closed', 'archived') DEFAULT 'active',
  `satisfaction_rating` tinyint DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ai_conversations_user_id_foreign` (`user_id`),
  KEY `ai_conversations_type_index` (`conversation_type`),
  KEY `ai_conversations_status_index` (`status`),
  CONSTRAINT `ai_conversations_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing conversation messages
CREATE TABLE `ai_conversation_messages` (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `conversation_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `sender_type` ENUM('user', 'ai') NOT NULL,
  `message` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `message_type` ENUM('text', 'image', 'video', 'audio', 'file') DEFAULT 'text',
  `attachments` json DEFAULT NULL,
  `ai_model_used` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `processing_time_ms` int DEFAULT '0',
  `confidence_score` decimal(5,2) DEFAULT '0.00',
  `is_helpful` boolean DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ai_conversation_messages_conversation_id_foreign` (`conversation_id`),
  KEY `ai_conversation_messages_sender_type_index` (`sender_type`),
  KEY `ai_conversation_messages_created_at_index` (`created_at`),
  CONSTRAINT `ai_conversation_messages_conversation_id_foreign` FOREIGN KEY (`conversation_id`) REFERENCES `ai_conversations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 6. AI KNOWLEDGE BASE SYSTEM
-- --------------------------------------------------------

-- Table for storing AI knowledge base content
CREATE TABLE `ai_knowledge_base` (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `academy_id` bigint UNSIGNED DEFAULT NULL,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type` ENUM('faq', 'tutorial', 'explanation', 'troubleshooting') NOT NULL,
  `category` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tags` json DEFAULT NULL,
  `search_keywords` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `priority` tinyint DEFAULT '1',
  `is_active` boolean DEFAULT true,
  `view_count` int DEFAULT '0',
  `helpful_count` int DEFAULT '0',
  `not_helpful_count` int DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ai_knowledge_base_academy_id_foreign` (`academy_id`),
  KEY `ai_knowledge_base_type_index` (`content_type`),
  KEY `ai_knowledge_base_category_index` (`category`),
  KEY `ai_knowledge_base_active_index` (`is_active`),
  CONSTRAINT `ai_knowledge_base_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 7. AI ANALYTICS AND PERFORMANCE TRACKING
-- --------------------------------------------------------

-- Table for tracking AI system performance
CREATE TABLE `ai_performance_metrics` (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `metric_type` ENUM('transcription', 'exam_correction', 'question_generation', 'conversation', 'summarization') NOT NULL,
  `academy_id` bigint UNSIGNED DEFAULT NULL,
  `user_id` bigint UNSIGNED DEFAULT NULL,
  `request_data` json DEFAULT NULL,
  `response_data` json DEFAULT NULL,
  `processing_time_ms` int DEFAULT '0',
  `accuracy_score` decimal(5,2) DEFAULT '0.00',
  `success` boolean DEFAULT true,
  `error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `tokens_used` int DEFAULT '0',
  `cost_usd` decimal(10,6) DEFAULT '0.000000',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ai_performance_metrics_type_index` (`metric_type`),
  KEY `ai_performance_metrics_academy_id_foreign` (`academy_id`),
  KEY `ai_performance_metrics_user_id_foreign` (`user_id`),
  KEY `ai_performance_metrics_created_at_index` (`created_at`),
  CONSTRAINT `ai_performance_metrics_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE SET NULL,
  CONSTRAINT `ai_performance_metrics_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 8. AI SETTINGS AND CONFIGURATION
-- --------------------------------------------------------

-- Table for AI system configuration
CREATE TABLE `ai_settings` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `academy_id` bigint UNSIGNED DEFAULT NULL,
  `setting_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `setting_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `setting_type` ENUM('string', 'number', 'boolean', 'json') DEFAULT 'string',
  `is_active` boolean DEFAULT true,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ai_settings_academy_setting_unique` (`academy_id`, `setting_key`),
  KEY `ai_settings_academy_id_foreign` (`academy_id`),
  CONSTRAINT `ai_settings_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default AI settings
INSERT INTO `ai_settings` (`academy_id`, `setting_key`, `setting_value`, `setting_type`) VALUES
(NULL, 'ai_enabled', 'true', 'boolean'),
(NULL, 'transcription_enabled', 'true', 'boolean'),
(NULL, 'exam_correction_enabled', 'true', 'boolean'),
(NULL, 'question_generation_enabled', 'true', 'boolean'),
(NULL, 'conversation_enabled', 'true', 'boolean'),
(NULL, 'summarization_enabled', 'true', 'boolean'),
(NULL, 'default_ai_model', 'gpt-4', 'string'),
(NULL, 'max_tokens_per_request', '4000', 'number'),
(NULL, 'confidence_threshold', '0.7', 'number'),
(NULL, 'auto_correction_enabled', 'true', 'boolean');

-- --------------------------------------------------------
-- 9. INDEXES FOR PERFORMANCE OPTIMIZATION
-- --------------------------------------------------------

-- Additional indexes for better performance
CREATE INDEX `idx_ai_answers_type_student` ON `ai_answers` (`answer_type`, `student_id`);
CREATE INDEX `idx_ai_answers_created_at` ON `ai_answers` (`created_at`);
CREATE INDEX `idx_exam_corrections_date` ON `exam_corrections` (`corrected_at`);
CREATE INDEX `idx_video_transcriptions_language` ON `video_transcriptions` (`language`);
CREATE INDEX `idx_ai_conversations_context` ON `ai_conversations` (`context_type`, `context_id`);

-- --------------------------------------------------------
-- 10. TRIGGERS FOR AUTOMATIC UPDATES
-- --------------------------------------------------------

-- Trigger to update lesson summary when lesson is updated
DELIMITER ;;
CREATE TRIGGER `update_lesson_summary_trigger` 
AFTER UPDATE ON `lessons` 
FOR EACH ROW 
BEGIN
    IF NEW.updated_at != OLD.updated_at AND NEW.status = 1 THEN
        INSERT INTO `ai_performance_metrics` (
            `id`, `metric_type`, `request_data`, `success`, `created_at`
        ) VALUES (
            UUID(), 'summarization', 
            JSON_OBJECT('lesson_id', NEW.id, 'action', 'auto_update_summary'),
            TRUE, NOW()
        );
    END IF;
END;;
DELIMITER ;

-- Trigger to track AI usage
DELIMITER ;;
CREATE TRIGGER `track_ai_usage_trigger` 
AFTER INSERT ON `ai_conversation_messages` 
FOR EACH ROW 
BEGIN
    IF NEW.sender_type = 'ai' THEN
        INSERT INTO `ai_performance_metrics` (
            `id`, `metric_type`, `processing_time_ms`, `tokens_used`, `success`, `created_at`
        ) VALUES (
            UUID(), 'conversation', 
            NEW.processing_time_ms, 
            LENGTH(NEW.message) / 4, -- Rough token estimation
            TRUE, NOW()
        );
    END IF;
END;;
DELIMITER ;

COMMIT;

-- --------------------------------------------------------
-- COMPLETION MESSAGE
-- --------------------------------------------------------

-- SELECT 'AI Assistant System Database Setup Complete!' as Status;
-- SELECT 'New Tables Created:' as Info;
-- SELECT '1. video_transcriptions - للتسجيلات الصوتية' as Table1;
-- SELECT '2. video_segments - لتقسيم الفيديو' as Table2;
-- SELECT '3. exam_corrections - لتصحيح الامتحانات' as Table3;
-- SELECT '4. question_corrections - لتصحيح الأسئلة' as Table4;
-- SELECT '5. lesson_summaries - لتلخيص الدروس' as Table5;
-- SELECT '6. ai_exam_templates - لقوالب الامتحانات' as Table6;
-- SELECT '7. ai_generated_questions - للأسئلة المُولدة' as Table7;
-- SELECT '8. ai_conversations - للمحادثات' as Table8;
-- SELECT '9. ai_conversation_messages - لرسائل المحادثة' as Table9;
-- SELECT '10. ai_knowledge_base - لقاعدة المعرفة' as Table10;
-- SELECT '11. ai_performance_metrics - لمتابعة الأداء' as Table11;
-- SELECT '12. ai_settings - للإعدادات' as Table12; 