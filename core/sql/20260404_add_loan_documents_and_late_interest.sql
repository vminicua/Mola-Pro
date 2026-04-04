ALTER TABLE `sl_loans`
    ADD COLUMN IF NOT EXISTS `late_interest_enabled` TINYINT(1) NOT NULL DEFAULT 0 AFTER `attachment`;

CREATE TABLE IF NOT EXISTS `sl_loan_documents` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `loan_id` BIGINT NOT NULL,
    `name` VARCHAR(180) NOT NULL,
    `document_type` VARCHAR(80) NULL,
    `file` VARCHAR(255) NOT NULL,
    `uploaded_by_id` INT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    KEY `sl_loan_documents_loan_id_idx` (`loan_id`),
    KEY `sl_loan_documents_uploaded_by_id_idx` (`uploaded_by_id`),
    CONSTRAINT `sl_loan_documents_loan_id_fk`
        FOREIGN KEY (`loan_id`) REFERENCES `sl_loans` (`id`),
    CONSTRAINT `sl_loan_documents_uploaded_by_id_fk`
        FOREIGN KEY (`uploaded_by_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
