-- ============================================================
-- 中医问诊系统 四诊知微 种子数据
-- 提示词版本(prompt_version)由后端启动时基于代码内默认模板幂等建仓，
-- 保证单一事实来源；此处仅落租户与运行时系统配置。
-- ============================================================

SET NAMES utf8mb4;

-- 默认租户（单租户直客模式恒为 0）
INSERT INTO `tenant` (`tenant_id`, `name`, `status`, `quota`) VALUES
    (0, 'default', 'active', '{"max_sessions_month": 200, "max_images_month": 500}');

-- 运行时系统配置
INSERT INTO `system_config` (`config_key`, `config_value`, `description`) VALUES
    ('disclaimer.text',
     '本结果由 AI 生成，仅供参考，不构成医疗诊断、治疗方案或处方建议，不能替代执业医师的当面诊断。若身体不适，请及时前往正规医疗机构就诊，切勿自行用药。',
     '输出强制附加的免责声明固定文案'),
    ('safety.image_confidence_threshold', '0.60', '多模态识别置信度阈值，低于则不强行下结论'),
    ('safety.red_flag_enabled', 'true', '急危重症识别开关'),
    ('retention.days', '365', '健康数据默认留存天数，超期自动清理'),
    ('syndrome.temperature', '0.3', '辨证论治生成温度（0.2-0.4）');