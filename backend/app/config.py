from __future__ import annotations

import json
from typing import Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="AI Marketing Chatbot Backend", alias="APP_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str | list[str] = Field(default="*", alias="CORS_ORIGINS")

    # Qdrant settings
    qdrant_host: str = Field(default="qdrant", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_grpc_port: int = Field(default=6334, alias="QDRANT_GRPC_PORT")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    collection_name: str = Field(default="ai_mkt_data", alias="COLLECTION_NAME")

    # Redis settings
    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")
    session_ttl_seconds: int = Field(default=1800, alias="SESSION_TTL_SECONDS")

    # ClickHouse settings
    clickhouse_host: str = Field(default="clickhouse", alias="CLICKHOUSE_HOST")
    clickhouse_port: int = Field(default=8123, alias="CLICKHOUSE_PORT")
    clickhouse_user: str = Field(default="default", alias="CLICKHOUSE_USER")
    clickhouse_password: str | None = Field(default=None, alias="CLICKHOUSE_PASSWORD")
    clickhouse_db: str = Field(default="default", alias="CLICKHOUSE_DB")

    # Embedding settings
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_size: int = Field(default=1536, alias="EMBEDDING_SIZE")
    embedding_api_key: str | None = Field(default=None, alias="EMBEDDING_API_KEY")
    embedding_base_url: str | None = Field(default=None, alias="EMBEDDING_BASE_URL")

    # LLM settings
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")

    # Knowledge & RAG settings
    knowledge_collection_name: str = Field(default="business_knowledge", alias="KNOWLEDGE_COLLECTION_NAME")
    knowledge_file_path: str = Field(default="business_knowledge.json", alias="KNOWLEDGE_FILE_PATH")
    enable_knowledge_rag: bool = Field(default=True, alias="ENABLE_KNOWLEDGE_RAG")
    enable_schema_rag: bool = Field(default=False, alias="ENABLE_SCHEMA_RAG")
    similarity_threshold: float = Field(default=0.65, alias="SIMILARITY_THRESHOLD")
    top_k: int = Field(default=3, alias="TOP_K")

    @field_validator(
        "embedding_base_url",
        "llm_base_url",
        "embedding_api_key",
        "llm_api_key",
        "redis_password",
        "qdrant_api_key",
        "clickhouse_password",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        if isinstance(self.cors_origins, list):
            return self.cors_origins
        if self.cors_origins == "*":
            return ["*"]
        try:
            parsed = json.loads(self.cors_origins)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
