-- =====================================================
-- قاعدة بيانات منصة سيان التعليمية - التصميم النهائي الشامل
-- =====================================================


SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1. جداول المستخدمين والحسابات
-- =====================================================

CREATE TABLE `users` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `fname` varchar(255) NOT NULL,
  `mname` varchar(255) DEFAULT NULL,
  `lname` varchar(255) NOT NULL,
  `phone_number` varchar(20) DEFAULT NULL UNIQUE,
  `email` varchar(100) NOT NULL UNIQUE,
  `password` varchar(255) DEFAULT NULL,
  `token` varchar(255) DEFAULT NULL,
  `status` enum('active','pending_verification','suspended','blocked') NOT NULL DEFAULT 'pending_verification',
  `user_type` enum('student','academy','admin') NOT NULL DEFAULT 'student',
  `account_type` enum('google','local') NOT NULL DEFAULT 'local',
  `google_id` varchar(255) DEFAULT NULL,
  `verified` tinyint(1) NOT NULL DEFAULT 0,
  `refere_id` bigint(20) UNSIGNED DEFAULT NULL,
  `banner` varchar(255) DEFAULT NULL,
  `avatar` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `users_refere_id_foreign` (`refere_id`),
  KEY `users_status_index` (`status`),
  KEY `users_user_type_index` (`user_type`),
  CONSTRAINT `users_refere_id_foreign` FOREIGN KEY (`refere_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `students` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) UNSIGNED NOT NULL UNIQUE,
  `birth_date` date DEFAULT NULL,
  `gender` enum('male','female','other') NOT NULL DEFAULT 'male',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  CONSTRAINT `students_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `admins` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) UNSIGNED NOT NULL UNIQUE,
  `permissions` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`permissions`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  CONSTRAINT `admins_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `otps` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `code` varchar(6) NOT NULL,
  `purpose` enum('login','password_reset','email_verification','transaction_confirmation') NOT NULL,
  `is_used` tinyint(1) NOT NULL DEFAULT 0,
  `attempts` int(11) NOT NULL DEFAULT 0,
  `expires_at` timestamp NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `otps_user_id_foreign` (`user_id`),
  KEY `otps_purpose_index` (`purpose`),
  KEY `otps_is_used_index` (`is_used`),
  CONSTRAINT `otps_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================
-- 2. نظام الأدوار والصلاحيات (RBAC)
-- =====================================================

CREATE TABLE `permissions` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL UNIQUE COMMENT 'مثل: courses.create, finance.view',
  `description` varchar(200) NOT NULL COMMENT 'وصف الصلاحية',
  `module` varchar(30) NOT NULL COMMENT 'الوحدة: courses, finance, users',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `permissions_module_index` (`module`)
) ENGINE=InnoDB;

CREATE TABLE `academy_roles` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `name` varchar(50) NOT NULL COMMENT 'اسم الدور: مدير مبيعات، محاسب',
  `description` text COMMENT 'وصف الدور ومسؤولياته',
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_academy_role` (`academy_id`, `name`),
  KEY `academy_roles_is_active_index` (`is_active`),
  CONSTRAINT `academy_roles_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `role_permissions` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `role_id` bigint(20) UNSIGNED NOT NULL,
  `permission_id` bigint(20) UNSIGNED NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_role_permission` (`role_id`, `permission_id`),
  CONSTRAINT `role_permissions_role_id_foreign` FOREIGN KEY (`role_id`) REFERENCES `academy_roles` (`id`) ON DELETE CASCADE,
  CONSTRAINT `role_permissions_permission_id_foreign` FOREIGN KEY (`permission_id`) REFERENCES `permissions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `system_users` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `system_role_id` bigint(20) UNSIGNED NULL,
  `assigned_by` bigint(20) UNSIGNED NOT NULL COMMENT 'من قام بالتعيين',
  `assigned_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_system_user` (`user_id`),
  CONSTRAINT `system_users_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `system_users_system_role_id_foreign` FOREIGN KEY (`system_role_id`) REFERENCES `academy_roles` (`id`) ON DELETE SET NULL,
  CONSTRAINT `system_users_assigned_by_foreign` FOREIGN KEY (`assigned_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB;

-- =====================================================
-- 3. جداول الأكاديميات والقوالب
-- =====================================================

CREATE TABLE `academies` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `license` varchar(255) DEFAULT NULL,
  `name` varchar(200) NOT NULL,
  `about` longtext DEFAULT NULL,
  `image` varchar(255) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `facebook` varchar(255) DEFAULT NULL,
  `twitter` varchar(255) DEFAULT NULL,
  `instagram` varchar(255) DEFAULT NULL,
  `snapchat` varchar(255) DEFAULT NULL,
  `status` enum('active','unactive','draft') NOT NULL DEFAULT 'active',
  `trial_status` enum('available','active','expired','used','not_eligible') NOT NULL DEFAULT 'available',
  `trial_start` date DEFAULT NULL,
  `trial_end` date DEFAULT NULL,
  `users_count` int(11) NOT NULL DEFAULT 0,
  `courses_count` int(11) NOT NULL DEFAULT 0,
  `package_id` bigint(20) UNSIGNED DEFAULT NULL,
  `slug` varchar(155) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `academies_status_index` (`status`)
) ENGINE=InnoDB;

CREATE TABLE `academy_users` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `user_role` enum('owner','admin','trainer') NOT NULL DEFAULT 'owner',
  `academy_role_id` bigint(20) UNSIGNED NULL COMMENT 'الدور المخصص للمستخدم',
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `joined_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `academy_users_academy_id_user_id_unique` (`academy_id`,`user_id`),
  KEY `academy_users_user_id_foreign` (`user_id`),
  KEY `academy_users_academy_role_id_foreign` (`academy_role_id`),
  KEY `academy_users_is_active_index` (`is_active`),
  CONSTRAINT `academy_users_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE,
  CONSTRAINT `academy_users_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `academy_users_academy_role_id_foreign` FOREIGN KEY (`academy_role_id`) REFERENCES `academy_roles` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `trainers` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `bio` text DEFAULT NULL,
  `specialization` varchar(255) DEFAULT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `trainers_user_id_academy_id_unique` (`user_id`,`academy_id`),
  KEY `trainers_academy_id_foreign` (`academy_id`),
  CONSTRAINT `trainers_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `trainers_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `abouts` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(255) DEFAULT NULL,
  `sub_title` varchar(255) DEFAULT NULL,
  `content` longtext DEFAULT NULL,
  `feature_one` longtext DEFAULT NULL,
  `feature_two` longtext DEFAULT NULL,
  `image` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `abouts_academy_id_foreign` (`academy_id`),
  CONSTRAINT `abouts_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `academyfaqs` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `question` varchar(200) NOT NULL,
  `answer` text NOT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `academyfaqs_academy_id_foreign` (`academy_id`),
  CONSTRAINT `academyfaqs_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `templates` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `name` varchar(200) NOT NULL,
  `primary_color` varchar(10) NOT NULL,
  `secondary_color` varchar(10) NOT NULL,
  `favicon` varchar(255) DEFAULT NULL,
  `logo` varchar(255) DEFAULT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `templates_academy_id_foreign` (`academy_id`),
  CONSTRAINT `templates_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `sliders` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(255) NOT NULL,
  `sub_title` varchar(255) NOT NULL,
  `first_button_title` varchar(100) DEFAULT NULL,
  `first_button_link` varchar(255) DEFAULT NULL,
  `second_button_title` varchar(100) DEFAULT NULL,
  `second_button_link` varchar(255) DEFAULT NULL,
  `content` text DEFAULT NULL,
  `image` varchar(255) DEFAULT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `sliders_academy_id_foreign` (`academy_id`),
  KEY `sliders_status_index` (`status`),
  CONSTRAINT `sliders_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `footers` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(255) NOT NULL,
  `content` varchar(255) NOT NULL,
  `image` varchar(255) DEFAULT NULL,
  `facebook` varchar(255) DEFAULT NULL,
  `twitter` varchar(255) DEFAULT NULL,
  `instagram` varchar(255) DEFAULT NULL,
  `linkedin` varchar(255) DEFAULT NULL,
  `youtube` varchar(255) DEFAULT NULL,
  `snapchat` varchar(255) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `phone` varchar(255) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `footers_academy_id_foreign` (`academy_id`),
  CONSTRAINT `footers_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================
-- 3. جداول المحافظ المستقلة
-- =====================================================

CREATE TABLE `wallets` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `balance` decimal(12,2) NOT NULL DEFAULT 0.00,
  `currency` varchar(3) NOT NULL DEFAULT 'SAR',
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `wallets_user_id_unique` (`user_id`),
  KEY `wallets_is_active_index` (`is_active`),
  CONSTRAINT `wallets_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `wallet_transactions` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `wallet_id` bigint(20) UNSIGNED NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  `direction` enum('in','out') NOT NULL,
  `source_type` enum('referral','withdrawal','admin','adjustment','refund','payout') NOT NULL,
  `source_id` bigint(20) UNSIGNED DEFAULT NULL,
  `balance_before` decimal(12,2) NOT NULL,
  `balance_after` decimal(12,2) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `wallet_transactions_wallet_id_foreign` (`wallet_id`),
  CONSTRAINT `wallet_transactions_wallet_id_foreign` FOREIGN KEY (`wallet_id`) REFERENCES `wallets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `bank_accounts` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `owner_id` bigint(20) UNSIGNED NOT NULL,
  `owner_type` enum('student','academy') NOT NULL,
  `bank_name` varchar(100) NOT NULL,
  `account_holder_name` varchar(100) NOT NULL,
  `account_number` varchar(64) NOT NULL,
  `iban` varchar(64) DEFAULT NULL,
  `swift_code` varchar(64) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `is_default` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `bank_accounts_owner_id_type_index` (`owner_id`, `owner_type`),
  CONSTRAINT `bank_accounts_student_owner_foreign` 
    FOREIGN KEY (`owner_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `bank_accounts_academy_owner_foreign` 
    FOREIGN KEY (`owner_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `withdrawal_requests` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `wallet_id` bigint(20) UNSIGNED NOT NULL,
  `requester_id` bigint(20) UNSIGNED NOT NULL,
  `requester_type` enum('student','academy') NOT NULL,
  `payout_account_id` bigint(20) UNSIGNED NOT NULL,
  `payout_request_id` varchar(64) DEFAULT NULL,
  `amount` decimal(10,2) NOT NULL,
  `status` enum('pending','approved','rejected','processing','completed','failed') NOT NULL DEFAULT 'pending',
  `reason_for_failure` varchar(255) DEFAULT NULL,
  `processed_by` varchar(100) DEFAULT NULL,
  `approved_at` timestamp NULL DEFAULT NULL,
  `rejected_at` timestamp NULL DEFAULT NULL,
  `processed_at` timestamp NULL DEFAULT NULL,
  `completed_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `withdrawal_requests_wallet_id_foreign` (`wallet_id`),
  KEY `withdrawal_requests_payout_account_id_foreign` (`payout_account_id`),
  KEY `withdrawal_requests_status_index` (`status`),
  CONSTRAINT `withdrawal_requests_wallet_id_foreign` FOREIGN KEY (`wallet_id`) REFERENCES `wallets` (`id`) ON DELETE CASCADE,
  CONSTRAINT `withdrawal_requests_payout_account_id_foreign` FOREIGN KEY (`payout_account_id`) REFERENCES `bank_accounts` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE `payout_logs` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `withdrawal_request_id` bigint(20) UNSIGNED NOT NULL,
  `payout_request_id` varchar(64) NOT NULL,
  `status` varchar(50) NOT NULL,
  `message` text DEFAULT NULL,
  `response` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `payout_logs_withdrawal_request_id_foreign` (`withdrawal_request_id`),
  CONSTRAINT `payout_logs_withdrawal_request_id_foreign` FOREIGN KEY (`withdrawal_request_id`) REFERENCES `withdrawal_requests` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `referral_rewards` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `referrer_user_id` bigint(20) UNSIGNED NOT NULL COMMENT 'المستخدم الذي أحال',
  `referred_user_id` bigint(20) UNSIGNED NOT NULL COMMENT 'المستخدم المُحال',
  `coupon_id` bigint(20) UNSIGNED DEFAULT NULL COMMENT 'الكوبون المستخدم',
  `payment_id` bigint(20) UNSIGNED DEFAULT NULL COMMENT 'الدفعة التي أدت للمكافأة',
  `amount` decimal(10,2) NOT NULL,
  `reward_type` enum('sign_up','first_purchase','course_completed') DEFAULT 'sign_up',
  `status` enum('pending','paid','expired') DEFAULT 'pending',
  `description` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `paid_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `referral_rewards_referrer_user_id_foreign` (`referrer_user_id`),
  KEY `referral_rewards_referred_user_id_foreign` (`referred_user_id`),
  KEY `referral_rewards_coupon_id_foreign` (`coupon_id`),
  KEY `referral_rewards_payment_id_foreign` (`payment_id`),
  KEY `referral_rewards_status_index` (`status`),
  CONSTRAINT `referral_rewards_referrer_user_id_foreign` FOREIGN KEY (`referrer_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `referral_rewards_referred_user_id_foreign` FOREIGN KEY (`referred_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `referral_rewards_coupon_id_foreign` FOREIGN KEY (`coupon_id`) REFERENCES `coupons` (`id`) ON DELETE SET NULL,
  CONSTRAINT `referral_rewards_payment_id_foreign` FOREIGN KEY (`payment_id`) REFERENCES `payments` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

-- =====================================================
-- 4. جداول المنتجات والكورسات
-- =====================================================

CREATE TABLE `products` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `price` decimal(10,2) NOT NULL DEFAULT 0.00,
  `discount_price` decimal(10,2) DEFAULT NULL,
  `currency` varchar(3) NOT NULL DEFAULT 'SAR',
  `status` enum('draft','published','archived') NOT NULL DEFAULT 'draft',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `products_academy_id_foreign` (`academy_id`),
  KEY `products_status_index` (`status`),
  CONSTRAINT `products_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `categories` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `parent_id` bigint(20) UNSIGNED DEFAULT NULL,
  `title` varchar(255) NOT NULL,
  `slug` varchar(255) NOT NULL UNIQUE,
  `image` varchar(255) DEFAULT NULL,
  `content` text DEFAULT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `categories_parent_id_foreign` (`parent_id`),
  KEY `categories_status_index` (`status`),
  CONSTRAINT `categories_parent_id_foreign` FOREIGN KEY (`parent_id`) REFERENCES `categories` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `courses` (
  `id` char(36) NOT NULL,
  `product_id` bigint(20) UNSIGNED NOT NULL,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `category_id` bigint(20) UNSIGNED NOT NULL,
  `trainer_id` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(255) NOT NULL,
  `slug` varchar(255) NOT NULL UNIQUE,
  `image` varchar(255) NOT NULL,
  `content` longtext NOT NULL,
  `short_content` text NOT NULL,
  `preparations` longtext DEFAULT NULL,
  `requirements` longtext DEFAULT NULL,
  `learning_outcomes` longtext DEFAULT NULL,
  `gallery` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`gallery`)),
  `preview_video` varchar(255) DEFAULT NULL,
  `status` enum('draft','published','archived') NOT NULL DEFAULT 'draft',
  `featured` tinyint(1) NOT NULL DEFAULT 0,
  `type` enum('live','recorded','attend') NOT NULL DEFAULT 'recorded',
  `url` varchar(255) DEFAULT NULL,
  `price` decimal(10,2) NOT NULL DEFAULT 0.00,
  `discount_price` decimal(10,2) DEFAULT NULL,
  `discount_ends_at` timestamp NULL DEFAULT NULL,
  `level` enum('beginner','intermediate','advanced') NOT NULL DEFAULT 'beginner',
  `avg_rating` decimal(3,2) NOT NULL DEFAULT 0.00,
  `ratings_count` int(11) NOT NULL DEFAULT 0,
  `students_count` int(11) NOT NULL DEFAULT 0,
  `lessons_count` int(11) NOT NULL DEFAULT 0,
  `duration_seconds` int(11) NOT NULL DEFAULT 0,
  `completion_rate` decimal(5,2) NOT NULL DEFAULT 0.00,
  `platform_fee_percentage` decimal(5,2) NOT NULL DEFAULT 0.00,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `courses_product_id_foreign` (`product_id`),
  KEY `courses_academy_id_foreign` (`academy_id`),
  KEY `courses_category_id_foreign` (`category_id`),
  KEY `courses_trainer_id_foreign` (`trainer_id`),
  KEY `courses_status_index` (`status`),
  KEY `courses_featured_index` (`featured`),
  CONSTRAINT `courses_product_id_foreign` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE,
  CONSTRAINT `courses_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE,
  CONSTRAINT `courses_category_id_foreign` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE CASCADE,
  CONSTRAINT `courses_trainer_id_foreign` FOREIGN KEY (`trainer_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `digital_products` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `product_id` bigint(20) UNSIGNED NOT NULL,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(255) NOT NULL,
  `slug` varchar(255) NOT NULL UNIQUE,
  `description` text DEFAULT NULL,
  `excerpt` varchar(255) DEFAULT NULL,
  `price` decimal(10,2) NOT NULL DEFAULT 0.00,
  `discount_price` decimal(10,2) DEFAULT NULL,
  `discount_ends_at` timestamp NULL DEFAULT NULL,
  `file` varchar(255) DEFAULT NULL,
  `file_type` varchar(50) DEFAULT NULL,
  `file_size_bytes` bigint(20) DEFAULT 0,
  `preview_image` varchar(255) DEFAULT NULL,
  `status` enum('draft','published','archived') NOT NULL DEFAULT 'draft',
  `downloads_count` int(11) NOT NULL DEFAULT 0,
  `avg_rating` decimal(3,2) NOT NULL DEFAULT 0.00,
  `ratings_count` int(11) NOT NULL DEFAULT 0,
  `platform_fee_percentage` decimal(5,2) NOT NULL DEFAULT 0.00,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `digital_products_product_id_foreign` (`product_id`),
  KEY `digital_products_academy_id_foreign` (`academy_id`),
  KEY `digital_products_status_index` (`status`),
  CONSTRAINT `digital_products_product_id_foreign` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE,
  CONSTRAINT `digital_products_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `packages` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `product_id` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(255) NOT NULL,
  `price` decimal(10,2) NOT NULL DEFAULT 0.00,
  `duration_days` int(11) NOT NULL DEFAULT 0,
  `max_courses` int(11) NOT NULL DEFAULT 0,
  `max_users` int(11) NOT NULL DEFAULT 0,
  `status` tinyint(1) NOT NULL DEFAULT 0,
  `template_id` int(11) NOT NULL DEFAULT 0,
  `features` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`features`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `packages_product_id_foreign` (`product_id`),
  KEY `packages_status_index` (`status`),
  CONSTRAINT `packages_product_id_foreign` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================
-- 5. جداول الفواتير والمدفوعات 
-- =====================================================

CREATE TABLE `coupons` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `owner_id` bigint(20) UNSIGNED DEFAULT NULL COMMENT 'صاحب الكوبون (user_id)',
  `owner_type` enum('student','academy','system') NOT NULL DEFAULT 'system' COMMENT 'نوع صاحب الكوبون',
  `code` varchar(100) NOT NULL UNIQUE,
  `type` enum('flat_discount','percentage') NOT NULL,
  `flat_discount` decimal(10,2) DEFAULT NULL,
  `percentage` decimal(5,2) DEFAULT NULL,
  `min_amount` decimal(10,2) DEFAULT NULL,
  `max_discount` decimal(10,2) DEFAULT NULL,
  `usage_limit` int(11) DEFAULT NULL,
  `used_count` int(11) NOT NULL DEFAULT 0,
  `starts_at` timestamp NULL DEFAULT NULL,
  `expires_at` timestamp NULL DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `coupons_owner_id_type_index` (`owner_id`, `owner_type`),
  KEY `coupons_is_active_index` (`is_active`),
  KEY `coupons_type_index` (`type`),
  CONSTRAINT `coupons_owner_foreign` FOREIGN KEY (`owner_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `coupon_usage` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `coupon_id` bigint(20) UNSIGNED NOT NULL,
  `user_id` bigint(20) UNSIGNED NOT NULL COMMENT 'المستخدم الذي استخدم الكوبون',
  `payment_id` bigint(20) UNSIGNED DEFAULT NULL COMMENT 'الدفعة المرتبطة',
  `discount_amount` decimal(10,2) NOT NULL,
  `used_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `coupon_usage_coupon_id_foreign` (`coupon_id`),
  KEY `coupon_usage_user_id_foreign` (`user_id`),
  KEY `coupon_usage_payment_id_foreign` (`payment_id`),
  CONSTRAINT `coupon_usage_coupon_id_foreign` FOREIGN KEY (`coupon_id`) REFERENCES `coupons` (`id`) ON DELETE CASCADE,
  CONSTRAINT `coupon_usage_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `coupon_usage_payment_id_foreign` FOREIGN KEY (`payment_id`) REFERENCES `payments` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `invoices` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `customer_type` enum('student','academy') NOT NULL,
  `customer_id` bigint(20) UNSIGNED NOT NULL,
  `wallet_transaction_id` bigint(20) UNSIGNED DEFAULT NULL,
  `total` decimal(10,2) NOT NULL DEFAULT 0.00,
  `total_after_discount` decimal(10,2) NOT NULL DEFAULT 0.00,
  `vat_percentage` decimal(4,2) DEFAULT NULL,
  `vat_amount` decimal(10,2) NOT NULL DEFAULT 0.00,
  `grand_total` decimal(10,2) NOT NULL DEFAULT 0.00,
  `status` enum('pending','completed','failed','refunded') NOT NULL DEFAULT 'pending',
  `currency` varchar(3) NOT NULL DEFAULT 'SAR',
  `coupon_code` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `invoices_wallet_transaction_id_foreign` (`wallet_transaction_id`),
  KEY `invoices_status_index` (`status`),
  CONSTRAINT `invoices_wallet_transaction_id_foreign` FOREIGN KEY (`wallet_transaction_id`) REFERENCES `wallet_transactions` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `invoice_products` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `invoice_id` bigint(20) UNSIGNED NOT NULL,
  `product_id` bigint(20) UNSIGNED NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `discount` decimal(10,2) NOT NULL DEFAULT 0.00,
  `price_after_discount` decimal(10,2) GENERATED ALWAYS AS (`price` - `discount`) STORED,
  `quantity` int(11) NOT NULL DEFAULT 1,
  `vat_percentage` decimal(4,2) DEFAULT NULL,
  `vat_amount` decimal(10,2) NOT NULL DEFAULT 0.00,
  `total` decimal(10,2) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `invoice_products_invoice_id_foreign` (`invoice_id`),
  KEY `invoice_products_product_id_foreign` (`product_id`),
  CONSTRAINT `invoice_products_invoice_id_foreign` FOREIGN KEY (`invoice_id`) REFERENCES `invoices` (`id`) ON DELETE CASCADE,
  CONSTRAINT `invoice_products_product_id_foreign` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================
-- 6. جداول الدفع وبوابات الدفع
-- =====================================================

CREATE TABLE `payments` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `invoice_id` bigint(20) UNSIGNED NOT NULL,
  `student_id` bigint(20) UNSIGNED NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `currency` varchar(3) NOT NULL DEFAULT 'SAR',
  `payment_method` enum('credit_card','debit_card','bank_transfer','wallet','cash','tap','myfatoorah','tabby','tamara') NOT NULL,
  `payment_status` enum('pending','processing','completed','failed','cancelled','refunded','expired') NOT NULL DEFAULT 'pending',
  `transaction_reference` varchar(255) DEFAULT NULL,
  `gateway_transaction_id` varchar(255) DEFAULT NULL,
  `gateway_response` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`gateway_response`)),
  `fees` decimal(10,2) DEFAULT 0.00,
  `net_amount` decimal(10,2) DEFAULT NULL,
  `processed_at` timestamp NULL DEFAULT NULL,
  `expired_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `payments_invoice_id_foreign` (`invoice_id`),
  KEY `payments_student_id_foreign` (`student_id`),
  KEY `payments_payment_status_index` (`payment_status`),
  CONSTRAINT `payments_invoice_id_foreign` FOREIGN KEY (`invoice_id`) REFERENCES `invoices` (`id`) ON DELETE CASCADE,
  CONSTRAINT `payments_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `payment_gateway_logs` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `payment_id` bigint(20) UNSIGNED DEFAULT NULL,
  `gateway_name` varchar(50) NOT NULL,
  `transaction_reference` varchar(255) DEFAULT NULL,
  `request_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`request_data`)),
  `response_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`response_data`)),
  `status` enum('pending','success','failed','cancelled','timeout') NOT NULL DEFAULT 'pending',
  `error_message` text DEFAULT NULL,
  `processed_at` timestamp NULL DEFAULT NULL,
  `webhook_received_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `payment_gateway_logs_payment_id_foreign` (`payment_id`),
  KEY `payment_gateway_logs_gateway_name_index` (`gateway_name`),
  CONSTRAINT `payment_gateway_logs_payment_id_foreign` FOREIGN KEY (`payment_id`) REFERENCES `payments` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `videos` (
  `id` char(36) NOT NULL,
  `lesson_id` char(36) NOT NULL,
  `title` varchar(255) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `video` varchar(255) DEFAULT NULL,
  `order_number` int(11) NOT NULL DEFAULT 0,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `duration` int(11) NOT NULL DEFAULT 0,
  `deleted_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `videos_lesson_id_foreign` (`lesson_id`),
  KEY `videos_order_number_index` (`order_number`),
  CONSTRAINT `videos_lesson_id_foreign` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `exams` (
  `id` char(36) NOT NULL,
  `lesson_id` char(36) NOT NULL,
  `title` varchar(255) DEFAULT NULL,
  `question` varchar(300) DEFAULT NULL,
  `answers` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`answers`)),
  `correct_answer` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`correct_answer`)),
  `order_number` int(11) NOT NULL DEFAULT 0,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `duration` int(11) NOT NULL DEFAULT 0,
  `question_type` enum('single','choose','boolean') NOT NULL DEFAULT 'single',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `exams_lesson_id_foreign` (`lesson_id`),
  KEY `exams_order_number_index` (`order_number`),
  CONSTRAINT `exams_lesson_id_foreign` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `questions` (
  `id` char(36) NOT NULL,
  `exam_id` char(36) NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `type` enum('multiple_choice','true_false','text') NOT NULL,
  `score` int(11) NOT NULL,
  `correct_answer` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `questions_exam_id_foreign` (`exam_id`),
  CONSTRAINT `questions_exam_id_foreign` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `question_options` (
  `id` char(70) NOT NULL,
  `question_id` char(70) NOT NULL,
  `text` varchar(255) NOT NULL,
  `is_correct` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `question_options_question_id_foreign` (`question_id`),
  CONSTRAINT `question_options_question_id_foreign` FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `interactive_tools` (
  `id` char(36) NOT NULL,
  `lesson_id` char(36) NOT NULL,
  `title` varchar(200) NOT NULL,
  `description` text NOT NULL,
  `image` varchar(255) DEFAULT NULL,
  `color` varchar(10) DEFAULT NULL,
  `order_number` smallint(5) UNSIGNED DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `interactive_tools_lesson_id_foreign` (`lesson_id`),
  KEY `interactive_tools_title_index` (`title`),
  CONSTRAINT `interactive_tools_lesson_id_foreign` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `ai_answers` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `lesson_id` char(36) NOT NULL,
  `student_id` bigint(20) UNSIGNED DEFAULT NULL,
  `question` varchar(255) NOT NULL,
  `answer` longtext NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `ai_answers_lesson_id_foreign` (`lesson_id`),
  KEY `ai_answers_student_id_foreign` (`student_id`),
  CONSTRAINT `ai_answers_lesson_id_foreign` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`) ON DELETE CASCADE,
  CONSTRAINT `ai_answers_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `coursecategories` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `course_id` char(36) NOT NULL,
  `parent_id` bigint(20) UNSIGNED DEFAULT NULL,
  `title` varchar(255) NOT NULL,
  `image` varchar(255) DEFAULT NULL,
  `content` text DEFAULT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `coursecategories_course_id_foreign` (`course_id`),
  KEY `coursecategories_parent_id_foreign` (`parent_id`),
  KEY `coursecategories_status_index` (`status`),
  CONSTRAINT `coursecategories_course_id_foreign` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE,
  CONSTRAINT `coursecategories_parent_id_foreign` FOREIGN KEY (`parent_id`) REFERENCES `coursecategories` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================
-- 7. جداول المحتوى التعليمي
-- =====================================================

CREATE TABLE `chapters` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `course_id` char(36) NOT NULL,
  `title` varchar(200) NOT NULL,
  `description` text DEFAULT NULL,
  `order_number` int(11) NOT NULL DEFAULT 0,
  `is_published` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `chapters_course_id_foreign` (`course_id`),
  CONSTRAINT `chapters_course_id_foreign` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `lessons` (
  `id` char(36) NOT NULL,
  `chapter_id` bigint(20) UNSIGNED NOT NULL,
  `course_id` char(36) NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `video` varchar(255) DEFAULT NULL,
  `video_type` enum('upload','embed','youtube','vimeo') DEFAULT 'upload',
  `video_provider` varchar(20) DEFAULT NULL,
  `video_duration` int(11) DEFAULT 0,
  `views_count` int(11) DEFAULT 0,
  `size_bytes` bigint(20) DEFAULT 0,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `order_number` int(11) DEFAULT 0,
  `type` enum('video','exam','tool','text') NOT NULL DEFAULT 'video',
  `is_free_preview` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `lessons_chapter_id_foreign` (`chapter_id`),
  KEY `lessons_course_id_foreign` (`course_id`),
  CONSTRAINT `lessons_chapter_id_foreign` FOREIGN KEY (`chapter_id`) REFERENCES `chapters` (`id`) ON DELETE CASCADE,
  CONSTRAINT `lessons_course_id_foreign` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `student_digital_products` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` bigint(20) UNSIGNED NOT NULL,
  `digital_product_id` bigint(20) UNSIGNED NOT NULL,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `payment_id` bigint(20) UNSIGNED NOT NULL,
  `download_count` int(11) NOT NULL DEFAULT 0,
  `purchased_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `student_digital_products_student_id_product_id_unique` (`student_id`,`digital_product_id`),
  KEY `student_digital_products_digital_product_id_foreign` (`digital_product_id`),
  KEY `student_digital_products_academy_id_foreign` (`academy_id`),
  KEY `student_digital_products_payment_id_foreign` (`payment_id`),
  CONSTRAINT `student_digital_products_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `student_digital_products_digital_product_id_foreign` FOREIGN KEY (`digital_product_id`) REFERENCES `digital_products` (`id`) ON DELETE CASCADE,
  CONSTRAINT `student_digital_products_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE,
  CONSTRAINT `student_digital_products_payment_id_foreign` FOREIGN KEY (`payment_id`) REFERENCES `payments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `carts` (
  `id` char(36) NOT NULL,
  `cookie_id` char(36) DEFAULT NULL,
  `student_id` bigint(20) UNSIGNED DEFAULT NULL,
  `course_id` char(36) DEFAULT NULL,
  `digital_product_id` bigint(20) UNSIGNED DEFAULT NULL,
  `quantity` int(11) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `carts_student_id_foreign` (`student_id`),
  KEY `carts_course_id_foreign` (`course_id`),
  KEY `carts_digital_product_id_foreign` (`digital_product_id`),
  CONSTRAINT `carts_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `carts_course_id_foreign` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE,
  CONSTRAINT `carts_digital_product_id_foreign` FOREIGN KEY (`digital_product_id`) REFERENCES `digital_products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `rates` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` bigint(20) UNSIGNED DEFAULT NULL,
  `ratable_type` varchar(255) NOT NULL,
  `ratable_id` bigint(20) UNSIGNED NOT NULL,
  `rating` tinyint(3) UNSIGNED NOT NULL DEFAULT 5,
  `comment` text DEFAULT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `course_id` char(36) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `rates_student_id_foreign` (`student_id`),
  KEY `rates_ratable_type_ratable_id_index` (`ratable_type`,`ratable_id`),
  KEY `rates_course_id_foreign` (`course_id`),
  CONSTRAINT `rates_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `rates_course_id_foreign` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `digital_product_ratings` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `digital_product_id` bigint(20) UNSIGNED NOT NULL,
  `student_id` bigint(20) UNSIGNED NOT NULL,
  `rating` tinyint(3) UNSIGNED NOT NULL,
  `comment` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `digital_product_ratings_product_id_student_id_unique` (`digital_product_id`,`student_id`),
  KEY `digital_product_ratings_student_id_foreign` (`student_id`),
  CONSTRAINT `digital_product_ratings_product_id_foreign` FOREIGN KEY (`digital_product_id`) REFERENCES `digital_products` (`id`) ON DELETE CASCADE,
  CONSTRAINT `digital_product_ratings_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `opinions` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` bigint(20) UNSIGNED DEFAULT NULL,
  `student_name` varchar(255) NOT NULL,
  `student_image` varchar(255) DEFAULT NULL,
  `rating` tinyint(3) UNSIGNED NOT NULL,
  `comment` text NOT NULL,
  `is_approved` tinyint(1) NOT NULL DEFAULT 0,
  `is_featured` tinyint(1) NOT NULL DEFAULT 0,
  `course_id` bigint(20) UNSIGNED DEFAULT NULL,
  `product_id` bigint(20) UNSIGNED DEFAULT NULL,
  `academy_id` bigint(20) UNSIGNED DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `opinions_student_id_foreign` (`student_id`),
  KEY `opinions_course_id_foreign` (`course_id`),
  KEY `opinions_product_id_foreign` (`product_id`),
  KEY `opinions_academy_id_foreign` (`academy_id`),
  KEY `opinions_is_approved_index` (`is_approved`),
  KEY `opinions_is_featured_index` (`is_featured`),
  CONSTRAINT `opinions_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `opinions_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `student_opinions` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `student_name` varchar(200) DEFAULT NULL,
  `student_email` varchar(200) DEFAULT NULL,
  `student_avatar` varchar(300) DEFAULT NULL,
  `rate` int(11) NOT NULL DEFAULT 5,
  `opinion` varchar(300) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `student_opinions_academy_id_foreign` (`academy_id`),
  CONSTRAINT `student_opinions_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `favourites` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` bigint(20) UNSIGNED NOT NULL,
  `course_id` char(36) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `favourites_student_id_course_id_unique` (`student_id`,`course_id`),
  KEY `favourites_course_id_foreign` (`course_id`),
  CONSTRAINT `favourites_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `favourites_course_id_foreign` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================
-- 8. جداول التتبع والتقدم
-- =====================================================

CREATE TABLE `student_courses` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` bigint(20) UNSIGNED NOT NULL,
  `course_id` char(36) NOT NULL,
  `invoice_id` bigint(20) UNSIGNED DEFAULT NULL,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `status` enum('active','expired','suspended') NOT NULL DEFAULT 'active',
  `started_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `expires_at` timestamp NULL DEFAULT NULL,
  `completion_percentage` decimal(5,2) NOT NULL DEFAULT 0.00,
  `price_paid` decimal(10,2) NOT NULL DEFAULT 0.00,
  `last_accessed_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `student_courses_student_id_course_id_unique` (`student_id`,`course_id`),
  KEY `student_courses_course_id_foreign` (`course_id`),
  KEY `student_courses_academy_id_foreign` (`academy_id`),
  KEY `student_courses_invoice_id_foreign` (`invoice_id`),
  CONSTRAINT `student_courses_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `student_courses_course_id_foreign` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE,
  CONSTRAINT `student_courses_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE,
  CONSTRAINT `student_courses_invoice_id_foreign` FOREIGN KEY (`invoice_id`) REFERENCES `invoices` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `lesson_progress` (
  `id` char(36) NOT NULL,
  `student_id` bigint(20) UNSIGNED NOT NULL,
  `lesson_id` char(36) NOT NULL,
  `course_id` char(36) NOT NULL,
  `progress_percentage` int(11) NOT NULL DEFAULT 0,
  `completed` tinyint(1) NOT NULL DEFAULT 0,
  `current_position_seconds` int(11) DEFAULT 0,
  `last_watched_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `lesson_progress_student_id_lesson_id_unique` (`student_id`,`lesson_id`),
  KEY `lesson_progress_lesson_id_foreign` (`lesson_id`),
  KEY `lesson_progress_course_id_foreign` (`course_id`),
  CONSTRAINT `lesson_progress_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `lesson_progress_lesson_id_foreign` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`) ON DELETE CASCADE,
  CONSTRAINT `lesson_progress_course_id_foreign` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `blogs` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `academy_id` bigint(20) UNSIGNED DEFAULT NULL,
  `title` varchar(255) NOT NULL,
  `slug` varchar(255) NOT NULL UNIQUE,
  `content` longtext DEFAULT NULL,
  `image` varchar(255) DEFAULT NULL,
  `video` varchar(255) DEFAULT NULL,
  `cover` varchar(255) DEFAULT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `views` int(11) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `blogs_academy_id_foreign` (`academy_id`),
  KEY `blogs_status_index` (`status`),
  CONSTRAINT `blogs_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `blog_categories` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `parent_id` bigint(20) UNSIGNED DEFAULT NULL,
  `title` varchar(255) NOT NULL,
  `slug` varchar(255) NOT NULL UNIQUE,
  `image` varchar(255) DEFAULT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `blog_categories_parent_id_foreign` (`parent_id`),
  KEY `blog_categories_status_index` (`status`),
  CONSTRAINT `blog_categories_parent_id_foreign` FOREIGN KEY (`parent_id`) REFERENCES `blog_categories` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `blog_posts` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `blog_id` bigint(20) UNSIGNED NOT NULL,
  `category_id` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(255) NOT NULL,
  `slug` varchar(255) NOT NULL UNIQUE,
  `excerpt` text DEFAULT NULL,
  `content` longtext NOT NULL,
  `meta_description` varchar(255) DEFAULT NULL,
  `author_name` varchar(255) DEFAULT NULL,
  `image` varchar(255) DEFAULT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `views` int(11) NOT NULL DEFAULT 0,
  `average_rating` decimal(3,2) NOT NULL DEFAULT 0.00,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `blog_posts_blog_id_foreign` (`blog_id`),
  KEY `blog_posts_category_id_foreign` (`category_id`),
  KEY `blog_posts_title_index` (`title`),
  KEY `blog_posts_created_at_index` (`created_at`),
  CONSTRAINT `blog_posts_blog_id_foreign` FOREIGN KEY (`blog_id`) REFERENCES `blogs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `blog_posts_category_id_foreign` FOREIGN KEY (`category_id`) REFERENCES `blog_categories` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `blog_keywords` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL UNIQUE,
  `slug` varchar(255) NOT NULL UNIQUE,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB;

CREATE TABLE `blog_post_keyword` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `blog_post_id` bigint(20) UNSIGNED NOT NULL,
  `blog_keyword_id` bigint(20) UNSIGNED NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `blog_post_keyword_post_keyword_unique` (`blog_post_id`,`blog_keyword_id`),
  KEY `blog_post_keyword_blog_keyword_id_foreign` (`blog_keyword_id`),
  CONSTRAINT `blog_post_keyword_blog_post_id_foreign` FOREIGN KEY (`blog_post_id`) REFERENCES `blog_posts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `blog_post_keyword_blog_keyword_id_foreign` FOREIGN KEY (`blog_keyword_id`) REFERENCES `blog_keywords` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `blog_comments` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `post_id` bigint(20) UNSIGNED NOT NULL,
  `student_id` bigint(20) UNSIGNED NOT NULL,
  `content` text NOT NULL,
  `rating` tinyint(3) UNSIGNED DEFAULT NULL,
  `is_approved` tinyint(1) NOT NULL DEFAULT 0,
  `status` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `blog_comments_post_id_foreign` (`post_id`),
  KEY `blog_comments_student_id_foreign` (`student_id`),
  KEY `blog_comments_is_approved_index` (`is_approved`),
  CONSTRAINT `blog_comments_post_id_foreign` FOREIGN KEY (`post_id`) REFERENCES `blog_posts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `blog_comments_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `subscriptions` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `academy_id` bigint(20) UNSIGNED NOT NULL,
  `package_id` bigint(20) UNSIGNED NOT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 0,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `payment_method` varchar(255) NOT NULL DEFAULT 'cash',
  `payment_status` enum('pending','completed','failed','refunded') NOT NULL DEFAULT 'pending',
  `package_type` enum('monthly','yearly','lifetime') NOT NULL DEFAULT 'monthly',
  `package_price` decimal(10,2) NOT NULL DEFAULT 0.00,
  `max_users` int(11) NOT NULL DEFAULT 0,
  `max_courses` int(11) NOT NULL DEFAULT 0,
  `transaction_id` varchar(255) DEFAULT NULL,
  `invoice_id` varchar(255) DEFAULT NULL,
  `payment_response` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`payment_response`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `subscriptions_academy_id_foreign` (`academy_id`),
  KEY `subscriptions_package_id_foreign` (`package_id`),
  KEY `subscriptions_status_index` (`status`),
  KEY `subscriptions_payment_status_index` (`payment_status`),
  CONSTRAINT `subscriptions_academy_id_foreign` FOREIGN KEY (`academy_id`) REFERENCES `academies` (`id`) ON DELETE CASCADE,
  CONSTRAINT `subscriptions_package_id_foreign` FOREIGN KEY (`package_id`) REFERENCES `packages` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `transactions` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` bigint(20) UNSIGNED NOT NULL,
  `wallet_transaction_id` bigint(20) UNSIGNED DEFAULT NULL,
  `total_amount` decimal(10,2) DEFAULT NULL,
  `currency` varchar(3) NOT NULL DEFAULT 'SAR',
  `status` enum('pending','completed','failed','refunded') NOT NULL DEFAULT 'pending',
  `payment_details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`payment_details`)),
  `coupon_code` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `transactions_student_id_foreign` (`student_id`),
  KEY `transactions_status_index` (`status`),
  KEY `transactions_wallet_transaction_id_foreign` (`wallet_transaction_id`),
  CONSTRAINT `transactions_student_id_foreign` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `transactions_wallet_transaction_id_foreign` FOREIGN KEY (`wallet_transaction_id`) REFERENCES `wallet_transactions` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `faqs` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `content` longtext NOT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `faqs_status_index` (`status`)
) ENGINE=InnoDB;

-- =====================================================
-- 9. جداول إضافية
-- =====================================================

CREATE TABLE `notifications` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `type` varchar(100) NOT NULL,
  `title` varchar(255) NOT NULL,
  `message` text NOT NULL,
  `data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`data`)),
  `read_at` timestamp NULL DEFAULT NULL,
  `action_url` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `notifications_user_id_foreign` (`user_id`),
  KEY `notifications_read_at_index` (`read_at`),
  CONSTRAINT `notifications_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `settings` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `key` varchar(255) NOT NULL UNIQUE,
  `value` longtext DEFAULT NULL,
  `type` enum('string','number','boolean','json') NOT NULL DEFAULT 'string',
  `is_public` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB;

-- =====================================================
-- 10. فيوهات للحسابات التلقائية 
-- =====================================================

-- فيو لعرض المنتجات مع تفاصيلها من الجداول المرتبطة
-- الغرض: توحيد عرض جميع المنتجات (دورات، منتجات رقمية، باقات) في استعلام واحد
-- الفائدة: بدلاً من 3 استعلامات منفصلة، استعلام موحد واحد للكتالوج
-- الاستخدام: SELECT * FROM products_with_details WHERE academy_id = 1;
CREATE VIEW `products_with_details` AS
SELECT 
    p.id,
    p.academy_id,
    p.title,
    p.description,
    p.price,
    p.discount_price,
    p.status,
    'course' as product_type,
    c.id as item_id,
    c.slug,
    c.image,
    c.level,
    c.duration_seconds
FROM products p
INNER JOIN courses c ON c.product_id = p.id

UNION ALL

SELECT 
    p.id,
    p.academy_id,
    p.title,
    p.description,
    p.price,
    p.discount_price,
    p.status,
    'digital_product' as product_type,
    dp.id as item_id,
    dp.slug,
    dp.preview_image as image,
    'general' as level,
    0 as duration_seconds
FROM products p
INNER JOIN digital_products dp ON dp.product_id = p.id

UNION ALL

SELECT 
    p.id,
    p.academy_id,
    p.title,
    p.description,
    p.price,
    p.discount_price,
    p.status,
    'package' as product_type,
    pkg.id as item_id,
    NULL as slug,
    NULL as image,
    'package' as level,
    pkg.duration_days * 24 * 3600 as duration_seconds
FROM products p
INNER JOIN packages pkg ON pkg.product_id = p.id;

-- فيو لعرض صلاحيات المستخدمين في الأكاديميات
CREATE VIEW `user_permissions` AS
SELECT 
    au.user_id,
    au.academy_id,
    u.fname,
    u.lname,
    u.email,
    au.user_role as basic_role,
    ar.name as custom_role,
    p.name as permission,
    p.description as permission_description,
    p.module
FROM academy_users au
JOIN users u ON au.user_id = u.id
LEFT JOIN academy_roles ar ON au.academy_role_id = ar.id
LEFT JOIN role_permissions rp ON ar.id = rp.role_id
LEFT JOIN permissions p ON rp.permission_id = p.id
WHERE au.user_role != 'owner'; -- المالك له كل الصلاحيات

-- فيو لعرض فريق الأكاديمية مع الأدوار
CREATE VIEW `academy_team` AS
SELECT 
    au.academy_id,
    ac.name as academy_name,
    u.id as user_id,
    u.fname, 
    u.lname, 
    u.email,
    au.user_role,
    ar.name as custom_role,
    ar.description as role_description,
    au.is_active,
    au.joined_at,
    au.created_at
FROM academy_users au
JOIN users u ON au.user_id = u.id
JOIN academies ac ON au.academy_id = ac.id
LEFT JOIN academy_roles ar ON au.academy_role_id = ar.id
WHERE au.is_active = 1;

-- فيو للأكاديميات مع بيانات المالك
CREATE VIEW `academies_with_owner` AS
SELECT 
    a.*,
    u.fname as owner_fname,
    u.lname as owner_lname,
    u.email as owner_email,
    u.phone_number as owner_phone,
    u.status as owner_status,
    au.joined_at as owner_joined_at
FROM academies a
JOIN academy_users au ON a.id = au.academy_id
JOIN users u ON au.user_id = u.id
WHERE au.user_role = 'owner';

-- فيو موحد لجميع صلاحيات المستخدمين (أكاديميات + نظام)
CREATE VIEW `all_user_permissions` AS
-- صلاحيات الأكاديميات
SELECT 
    au.user_id,
    'academy' as context_type,
    au.academy_id as context_id,
    p.name as permission,
    p.description,
    p.module,
    'academy_role' as permission_source
FROM academy_users au
JOIN academy_roles ar ON au.academy_role_id = ar.id
JOIN role_permissions rp ON ar.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
WHERE au.is_active = 1

UNION ALL

-- صلاحيات النظام
SELECT 
    su.user_id,
    'system' as context_type,
    NULL as context_id,
    p.name as permission,
    p.description,
    p.module,
    'system_role' as permission_source
FROM system_users su
JOIN academy_roles r ON su.system_role_id = r.id
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id;

-- =====================================================
-- 11. إدراج بيانات أساسية
-- =====================================================

INSERT INTO `settings` (`key`, `value`, `type`, `is_public`) VALUES
('platform_name', 'منصة سيان التعليمية', 'string', 1),
('default_currency', 'SAR', 'string', 1),
('vat_percentage', '15.00', 'number', 1),
('platform_fee_percentage', '10.00', 'number', 0),
('max_withdrawal_amount', '50000.00', 'number', 0),
('min_withdrawal_amount', '100.00', 'number', 0);

INSERT INTO `categories` (`id`, `title`, `slug`, `status`) VALUES
(1, 'تقنية المعلومات', 'information-technology', 1),
(2, 'التصميم والفنون', 'design-arts', 1),
(3, 'إدارة الأعمال', 'business-management', 1),
(4, 'التسويق الرقمي', 'digital-marketing', 1),
(5, 'اللغات', 'languages', 1);

-- إدراج الصلاحيات الأساسية
INSERT INTO `permissions` (`name`, `description`, `module`) VALUES
-- صلاحيات الدورات
('courses.create', 'إنشاء دورات جديدة', 'courses'),
('courses.edit', 'تعديل الدورات الموجودة', 'courses'),
('courses.delete', 'حذف الدورات', 'courses'),
('courses.view', 'عرض الدورات والإحصائيات', 'courses'),
('courses.publish', 'نشر وإخفاء الدورات', 'courses'),

-- صلاحيات الطلاب
('students.view', 'عرض قائمة الطلاب', 'students'),
('students.manage', 'إدارة حسابات الطلاب', 'students'),
('students.export', 'تصدير بيانات الطلاب', 'students'),
('students.communication', 'التواصل مع الطلاب', 'students'),

-- صلاحيات المالية
('finance.view', 'عرض التقارير المالية', 'finance'),
('finance.manage', 'إدارة العمليات المالية', 'finance'),
('finance.export', 'تصدير البيانات المالية', 'finance'),
('finance.withdrawals', 'معالجة طلبات السحب', 'finance'),

-- صلاحيات المحتوى
('content.create', 'إنشاء محتوى جديد', 'content'),
('content.edit', 'تعديل المحتوى الموجود', 'content'),
('content.delete', 'حذف المحتوى', 'content'),
('content.moderate', 'مراجعة وإشراف المحتوى', 'content'),

-- صلاحيات المستخدمين
('users.invite', 'دعوة مستخدمين جدد', 'users'),
('users.manage', 'إدارة المستخدمين', 'users'),
('users.roles', 'إدارة الأدوار والصلاحيات', 'users'),

-- صلاحيات التقارير
('reports.view', 'عرض التقارير', 'reports'),
('reports.export', 'تصدير التقارير', 'reports'),
('reports.analytics', 'الوصول للتحليلات المتقدمة', 'reports'),

-- صلاحيات الإعدادات
('settings.manage', 'إدارة إعدادات الأكاديمية', 'settings'),
('settings.template', 'تخصيص القوالب والمظهر', 'settings'),

-- صلاحيات المدونة
('blog.create', 'إنشاء مقالات جديدة', 'blog'),
('blog.edit', 'تعديل المقالات', 'blog'),
('blog.publish', 'نشر المقالات', 'blog'),
('blog.moderate', 'مراجعة التعليقات', 'blog'),

-- صلاحيات النظام العامة
('system.backup', 'إنشاء نسخ احتياطية', 'system'),
('system.maintenance', 'صيانة النظام', 'system'),
('system.logs', 'الوصول لسجلات النظام', 'system');

-- =====================================================
-- فهارس إضافية لتحسين الأداء
-- =====================================================

-- فهرس مركب للبحث السريع في المنتجات
CREATE INDEX idx_products_academy_status ON products(academy_id, status);

-- فهرس للمدفوعات حسب التاريخ والحالة  
CREATE INDEX idx_payments_date_status ON payments(created_at, payment_status);

-- فهرس لمعاملات المحافظ حسب التاريخ
CREATE INDEX idx_wallet_transactions_date ON wallet_transactions(created_at);

-- فهرس لتقدم الطلاب
CREATE INDEX idx_lesson_progress_student_completed ON lesson_progress(student_id, completed);

-- =====================================================
-- قيود إضافية لضمان سلامة البيانات
-- =====================================================

-- التأكد من صحة أسعار المنتجات
ALTER TABLE products ADD CONSTRAINT chk_products_price 
CHECK (price >= 0 AND (discount_price IS NULL OR discount_price < price));

-- التأكد من صحة رصيد المحافظ
ALTER TABLE wallets ADD CONSTRAINT chk_wallets_balance 
CHECK (balance >= 0);

-- التأكد من صحة نسب الخصم
ALTER TABLE coupons ADD CONSTRAINT chk_coupons_percentage 
CHECK (percentage IS NULL OR (percentage > 0 AND percentage <= 100));

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================
--   نظام RBAC 
-- =====================================================
--  جداول نظام الأدوار والصلاحيات:
-- - permissions: 29 صلاحية أساسية في 9 وحدات
-- - academy_roles: أدوار مخصصة لكل أكاديمية
-- - role_permissions: ربط الأدوار بالصلاحيات
-- - system_users: مستخدمو النظام العام
-- - تحديث academy_users: إضافة academy_role_id
--
--  Views مساعدة:
-- - user_permissions: صلاحيات المستخدمين
-- - academy_team: فريق الأكاديمية
-- - academies_with_owner: الأكاديميات مع المالكين
-- - all_user_permissions: جميع الصلاحيات موحدة
--
--
--  تحسين هيكلي مهم:
-- - تم حذف الاتصال المباشر بين academies و users
-- - جميع العلاقات تتم عبر academy_users فقط
-- - تصميم أنظف وأكثر مرونة ووضوحاً 

