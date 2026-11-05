"""应用配置：全部外部化，通过环境变量注入（.env）。"""
from functools import lru_cache
from urllib.parse import quote_plus
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 运行环境
    app_env: str = "dev"
    multi_tenant: bool = False
    cors_origins: list[str] = ["http://localhost", "http://localhost:5173"]

    # 安全
    jwt_secret_key: str = "change-me-to-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 14
    encryption_key: str = "change-me-32-byte-base64-key-please-generate"
    data_retention_days: int = 365

    # MySQL
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_database: str = "tcm"
    mysql_user: str = "tcm"
    mysql_password: str = "tcm-password"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # PostgreSQL（智能体记忆）
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "tcm"
    postgres_password: str = "tcm-pg-password"
    postgres_db: str = "tcm_memory"
    memory_short_ttl_hours: int = Field(default=24, ge=1, le=720)
    memory_long_ttl_days: int = Field(default=365, ge=1, le=3650)
    memory_max_items: int = Field(default=20, ge=1, le=100)
    agent_max_tool_calls: int = Field(default=16, ge=4, le=64)

    # Neo4j
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "tcm-neo4j-password"

    # Milvus
    milvus_host: str = "milvus"
    milvus_port: int = 19530

    # LLM / Embedding（DashScope 兼容 OpenAI 协议）
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_api_key: str = ""
    text_model: str = "qwen-plus"
    text_model_fallback: str = "qwen-plus"
    vision_model: str = "qwen-vl-max"
    vision_model_fallback: str = "qwen-vl-plus"
    vision_timeout_seconds: int = Field(default=120, ge=1, le=600)
    embedding_model: str = "text-embedding-v3"
    embedding_dim: int = 1024
    llm_timeout_seconds: int = 10
    llm_max_retries: int = 2

    # 观测
    otel_exporter_otlp_endpoint: str = "http://jaeger:4317"
    otel_sample_ratio: float = Field(default=0.1, ge=0, le=1)
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "qihuang-sage"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    # 免责声明（可被 system_config.disclaimer.text 覆盖）
    disclaimer_text: str = (
        "本结果由 AI 生成，仅供参考，不构成医疗诊断、治疗方案或处方建议，"
        "不能替代执业医师的当面诊断。若身体不适，请及时前往正规医疗机构就诊，切勿自行用药。"
    )

    @model_validator(mode="after")
    def _check_placeholder_secrets(self):
        """非测试环境对占位密钥给出明确告警；生产环境直接启动失败，避免带占位值上线。"""
        if self.app_env == "test":
            return self
        import logging

        log = logging.getLogger("app.config")
        placeholders = {
            "llm_api_key": "",
            "jwt_secret_key": "change-me-to-a-long-random-secret",
            "encryption_key": "change-me-32-byte-base64-key-please-generate",
        }
        for field_name, placeholder_value in placeholders.items():
            if getattr(self, field_name) == placeholder_value:
                message = (
                    f"占位密钥未替换：{field_name} 仍为默认占位值，"
                    "请通过 .env 配置真实密钥后再上线"
                )
                if self.app_env == "production":
                    raise ValueError(message)
                log.warning(message)
        return self

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+psycopg2://{quote_plus(self.postgres_user)}:{quote_plus(self.postgres_password)}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
