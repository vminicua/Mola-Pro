CREATE TABLE IF NOT EXISTS `sl_late_interest_settings` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `period_type` VARCHAR(10) NOT NULL,
    `rate` DECIMAL(7,4) NOT NULL DEFAULT 0.0000,
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    UNIQUE KEY `sl_late_interest_settings_period_type_uniq` (`period_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `sl_late_interest_settings` (`period_type`, `rate`)
VALUES
    ('daily', 0.0000),
    ('monthly', 0.0000)
ON DUPLICATE KEY UPDATE `period_type` = VALUES(`period_type`);
