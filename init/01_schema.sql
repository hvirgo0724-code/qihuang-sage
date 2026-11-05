-- ============================================================
-- 中医问诊系统 四诊知微 (Fourfold Clarity) 业务数据库 DDL
-- MySQL 8.0 / utf8mb4 / InnoDB
-- 通过 /docker-entrypoint-initdb.d/ 首次自动初始化，按文件名顺序执行
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------- 租户域（单租户恒为 0，字段保留便于切换 SaaS） ----------
DROP TABLE IF EXISTS `tenant`;
CREATE TABLE `tenant` (
    `tenant_id`   BIGINT       NOT NULL AUTO_INCREMENT,
    `name`        VARCHAR(128) NOT NULL,
    `status`      VARCHAR(16)  NOT NULL DEFAULT 'active',  -- active/disabled
    `quota`       JSON         NULL,                       -- 用量配额
    `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`tenant_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='多租户';

-- ---------- 用户域 ----------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
    `user_id`         BIGINT       NOT NULL AUTO_INCREMENT,
    `tenant_id`       BIGINT       NOT NULL DEFAULT 0,
    `username`        VARCHAR(64)  NOT NULL,
    `password_hash`   VARCHAR(255) NOT NULL,
    `phone`           TEXT         NULL,    -- AES-256-GCM 加密(base64, enc: 前缀)
    `nickname`        VARCHAR(64)  NULL,
    `avatar`          VARCHAR(512) NULL,
    `gender`          VARCHAR(8)   NULL,    -- male/female/unknown
    `age`             INT          NULL,
    `role`            VARCHAR(16)  NOT NULL DEFAULT 'USER', -- USER/ADMIN
    `status`          VARCHAR(16)  NOT NULL DEFAULT 'active', -- active/disabled/deleted
    `data_consent_at` DATETIME     NULL,    -- 健康数据单独授权时间
    `create_time`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`user_id`),
    UNIQUE KEY `uk_user_username` (`username`),
    KEY `idx_user_tenant` (`tenant_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='用户';

DROP TABLE IF EXISTS `user_profile`;
CREATE TABLE `user_profile` (
    `user_id`            BIGINT NOT NULL,
    `height`             FLOAT  NULL,
    `weight`             FLOAT  NULL,
    `allergies`          TEXT   NULL, -- 加密
    `chronic_diseases`   TEXT   NULL, -- 加密
    `medication_history` TEXT   NULL, -- 加密
    `remark`             TEXT   NULL, -- 加密
    PRIMARY KEY (`user_id`),
    CONSTRAINT `fk_profile_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='健康画像';

-- ---------- 问诊域 ----------
DROP TABLE IF EXISTS `consultation_session`;
CREATE TABLE `consultation_session` (
    `session_id`  BIGINT       NOT NULL AUTO_INCREMENT,
    `tenant_id`   BIGINT       NOT NULL DEFAULT 0,
    `user_id`     BIGINT       NOT NULL,
    `start_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `end_time`    DATETIME     NULL,
    `status`      VARCHAR(16)  NOT NULL DEFAULT 'ongoing', -- ongoing/completed/aborted
    `complaint`   TEXT         NULL,    -- 主诉，最终落库（敏感可加密）
    `risk_level`  VARCHAR(16)  NULL,    -- low/medium/high/emergency
    `trace_id`    VARCHAR(64)  NULL,
    PRIMARY KEY (`session_id`),
    KEY `idx_session_user` (`user_id`),
    KEY `idx_session_tenant` (`tenant_id`),
    CONSTRAINT `fk_session_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='问诊会话';

DROP TABLE IF EXISTS `consultation_record`;
CREATE TABLE `consultation_record` (
    `record_id`   BIGINT      NOT NULL AUTO_INCREMENT,
    `session_id`  BIGINT      NOT NULL,
    `role`        VARCHAR(16) NOT NULL,  -- user/assistant/system
    `type`        VARCHAR(16) NOT NULL DEFAULT 'text', -- text/image/result
    `content`     TEXT        NULL,    -- 敏感内容可加密
    `meta`        JSON        NULL,    -- 症状槽位、结构化片段
    `create_time` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`record_id`),
    KEY `idx_record_session` (`session_id`),
    CONSTRAINT `fk_record_session` FOREIGN KEY (`session_id`) REFERENCES `consultation_session` (`session_id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='问诊轮次/消息';

DROP TABLE IF EXISTS `tcm_image`;
CREATE TABLE `tcm_image` (
    `image_id`        BIGINT      NOT NULL AUTO_INCREMENT,
    `session_id`      BIGINT      NOT NULL,
    `image_type`      VARCHAR(16) NOT NULL, -- tongue/face
    `file_path`       VARCHAR(512) NOT NULL,
    `quality_pass`    TINYINT(1)  NOT NULL DEFAULT 0,
    `analysis_result` JSON        NULL,
    `create_time`     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`image_id`),
    KEY `idx_image_session` (`session_id`),
    CONSTRAINT `fk_image_session` FOREIGN KEY (`session_id`) REFERENCES `consultation_session` (`session_id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='上传图片';

-- ---------- 辨证结果域 ----------
DROP TABLE IF EXISTS `syndrome_analysis`;
CREATE TABLE `syndrome_analysis` (
    `analysis_id`      BIGINT      NOT NULL AUTO_INCREMENT,
    `session_id`       BIGINT      NOT NULL,
    `syndrome`         VARCHAR(128) NULL,
    `evidence`         JSON        NULL, -- 逐条依据，标注来源
    `differential`     JSON        NULL,
    `confidence`       FLOAT       NULL,
    `treatment_principle` VARCHAR(512) NULL,
    `formula_suggestions` JSON     NULL, -- 附出处与图谱引用
    `diet_advice`      JSON        NULL,
    `acupoint_advice`  JSON        NULL,
    `lifestyle_advice` JSON        NULL,
    `risk_level`       VARCHAR(16) NULL, -- low/medium/high/emergency
    `emergency_flag`   TINYINT(1)  NOT NULL DEFAULT 0,
    `disclaimer`       TEXT        NULL,
    `graph_refs`       JSON        NULL,
    `model_name`       VARCHAR(64) NULL,
    `prompt_version`   VARCHAR(32) NULL,
    `latency_ms`       INT         NULL,
    `create_time`      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`analysis_id`),
    KEY `idx_analysis_session` (`session_id`),
    CONSTRAINT `fk_analysis_session` FOREIGN KEY (`session_id`) REFERENCES `consultation_session` (`session_id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='辨证结果快照';

-- ---------- 安全与审计域 ----------
DROP TABLE IF EXISTS `safety_audit_log`;
CREATE TABLE `safety_audit_log` (
    `log_id`       BIGINT      NOT NULL AUTO_INCREMENT,
    `session_id`   BIGINT      NULL,
    `stage`        VARCHAR(16) NOT NULL, -- input/output/image
    `check_result` VARCHAR(16) NOT NULL, -- pass/block/escalate
    `hit_rule`     VARCHAR(128) NULL,
    `raw_text`     TEXT        NULL,  -- 已脱敏
    `action`       VARCHAR(64) NULL,
    `create_time`  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`log_id`),
    KEY `idx_safety_session` (`session_id`),
    KEY `idx_safety_result` (`check_result`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='安全护栏审计';

DROP TABLE IF EXISTS `operation_log`;
CREATE TABLE `operation_log` (
    `op_id`         BIGINT      NOT NULL AUTO_INCREMENT,
    `user_id`       BIGINT      NULL,
    `tenant_id`     BIGINT      NOT NULL DEFAULT 0,
    `action`        VARCHAR(64) NOT NULL, -- query/create/update/delete/export
    `resource_type` VARCHAR(64) NOT NULL,
    `resource_id`   VARCHAR(64) NULL,
    `result`        VARCHAR(16) NULL,
    `ip`            VARCHAR(64) NULL,
    `trace_id`      VARCHAR(64) NULL,
    `create_time`   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`op_id`),
    KEY `idx_op_user` (`user_id`),
    KEY `idx_op_tenant` (`tenant_id`),
    KEY `idx_op_time` (`create_time`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='操作审计';

DROP TABLE IF EXISTS `feedback`;
CREATE TABLE `feedback` (
    `feedback_id` BIGINT      NOT NULL AUTO_INCREMENT,
    `user_id`     BIGINT      NOT NULL,
    `analysis_id` BIGINT      NULL,
    `rating`      TINYINT     NOT NULL, -- 1-5
    `comment`     TEXT        NULL,
    `correct`     TINYINT(1)  NULL,     -- 医学正确性打标
    `create_time` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`feedback_id`),
    KEY `idx_feedback_user` (`user_id`),
    KEY `idx_feedback_analysis` (`analysis_id`),
    CONSTRAINT `fk_feedback_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='用户反馈';

-- ---------- 企业级平台域 ----------
DROP TABLE IF EXISTS `async_job`;
CREATE TABLE `async_job` (
    `job_id`      VARCHAR(64) NOT NULL,
    `job_type`    VARCHAR(32) NOT NULL, -- image_analysis/graph_import/vector_rebuild/export
    `status`      VARCHAR(16) NOT NULL DEFAULT 'pending', -- pending/running/success/failed
    `progress`    INT         NOT NULL DEFAULT 0,
    `params`      JSON        NULL,
    `result`      JSON        NULL,
    `error`       TEXT        NULL,
    `trace_id`    VARCHAR(64) NULL,
    `create_time` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `finish_time` DATETIME    NULL,
    PRIMARY KEY (`job_id`),
    KEY `idx_job_status` (`status`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='异步任务';

DROP TABLE IF EXISTS `prompt_version`;
CREATE TABLE `prompt_version` (
    `version_id`  BIGINT      NOT NULL AUTO_INCREMENT,
    `scene`       VARCHAR(32) NOT NULL, -- inspection/inquiry/syndrome/treatment/safety
    `version`     VARCHAR(32) NOT NULL,
    `content`     TEXT        NOT NULL,
    `status`      VARCHAR(16) NOT NULL DEFAULT 'draft', -- draft/active/retired
    `changelog`   TEXT        NULL,
    `operator_id` BIGINT      NULL,
    `create_time` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`version_id`),
    KEY `idx_prompt_scene` (`scene`, `status`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='提示词版本';

DROP TABLE IF EXISTS `eval_dataset`;
CREATE TABLE `eval_dataset` (
    `dataset_id`  BIGINT      NOT NULL AUTO_INCREMENT,
    `name`        VARCHAR(128) NOT NULL,
    `scene`       VARCHAR(32) NULL,
    `samples`     JSON        NOT NULL,
    `create_time` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`dataset_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='评测集';

DROP TABLE IF EXISTS `eval_run`;
CREATE TABLE `eval_run` (
    `run_id`         BIGINT      NOT NULL AUTO_INCREMENT,
    `dataset_id`     BIGINT      NOT NULL,
    `prompt_version` VARCHAR(32) NULL,
    `metrics`        JSON        NULL,
    `create_time`    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`run_id`),
    KEY `idx_eval_dataset` (`dataset_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='评测记录';

-- ---------- 运行时系统配置（免责声明/阈值等可配置项） ----------
DROP TABLE IF EXISTS `system_config`;
CREATE TABLE `system_config` (
    `config_key`   VARCHAR(64)  NOT NULL,
    `config_value` TEXT         NULL,
    `description`  VARCHAR(255) NULL,
    `update_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`config_key`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='运行时系统配置';

-- ---------- 人工接诊域 ----------
DROP TABLE IF EXISTS `clinical_encounter`;
CREATE TABLE `clinical_encounter` (
    `session_id`  BIGINT      NOT NULL,
    `tenant_id`   BIGINT      NOT NULL DEFAULT 0,
    `patient_id`  BIGINT      NOT NULL,
    `doctor_id`   BIGINT      NOT NULL,
    `status`      VARCHAR(16) NOT NULL DEFAULT 'requested', -- requested/active/closed/cancelled
    `consent_at`  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `accepted_at` DATETIME    NULL,
    `closed_at`   DATETIME    NULL,
    `review`      TEXT        NULL,
    `reviewed_at` DATETIME    NULL,
    PRIMARY KEY (`session_id`),
    KEY `idx_clinical_tenant` (`tenant_id`),
    KEY `idx_clinical_doctor` (`doctor_id`),
    CONSTRAINT `fk_clinical_session` FOREIGN KEY (`session_id`) REFERENCES `consultation_session` (`session_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_clinical_patient` FOREIGN KEY (`patient_id`) REFERENCES `user` (`user_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_clinical_doctor` FOREIGN KEY (`doctor_id`) REFERENCES `user` (`user_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='人工接诊';

DROP TABLE IF EXISTS `clinical_message`;
CREATE TABLE `clinical_message` (
    `message_id`  BIGINT      NOT NULL AUTO_INCREMENT,
    `session_id`  BIGINT      NOT NULL,
    `author_id`   BIGINT      NOT NULL,
    `author_role` VARCHAR(16) NOT NULL, -- DOCTOR/USER
    `content`     TEXT        NOT NULL,
    `created_at`  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`message_id`),
    KEY `idx_clinical_msg_session` (`session_id`),
    CONSTRAINT `fk_clinical_msg_session` FOREIGN KEY (`session_id`) REFERENCES `clinical_encounter` (`session_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_clinical_msg_author` FOREIGN KEY (`author_id`) REFERENCES `user` (`user_id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='接诊消息';

CREATE TABLE IF NOT EXISTS `report_review` (
    `analysis_id` BIGINT NOT NULL,
    `status` VARCHAR(16) NOT NULL DEFAULT 'pending',
    `revision` INT NOT NULL DEFAULT 1,
    `report` JSON NOT NULL,
    `confirmed_by` BIGINT NULL,
    `confirmed_at` DATETIME NULL,
    PRIMARY KEY (`analysis_id`),
    CONSTRAINT `fk_review_analysis` FOREIGN KEY (`analysis_id`) REFERENCES `syndrome_analysis` (`analysis_id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT ='医生审核报告快照';

SET FOREIGN_KEY_CHECKS = 1;
