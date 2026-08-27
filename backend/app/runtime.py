from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import Settings
from app.database.clickhouse_client import ClickHouseClient
from app.database.schema_manage_service import SchemaManageService
from app.database.schema_manager import SchemaManager
from app.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.knowledge.knowledge_manage_service import KnowledgeManageService
from app.knowledge.knowledge_service import KnowledgeService
from app.llm.llm_client import LLMClient
from app.llm.tools.schema_tool import SchemaAgentTool
from app.services.chat_service import ChatService
from app.services.monitor_service import MonitorService
from app.services.stream_service import StreamChatService
from app.sessions.store import BaseSessionStore, RedisSessionStore
from app.vectorstores.qdrant_store import QdrantVectorStore

logger = logging.getLogger(__name__)


@dataclass
class ApplicationServices:
    knowledge_vector_store: QdrantVectorStore
    embedding_provider: OpenAIEmbeddingProvider
    llm_client: LLMClient
    session_store: BaseSessionStore
    knowledge_service: KnowledgeService
    knowledge_manage_service: KnowledgeManageService
    schema_manager: SchemaManager
    schema_manage_service: SchemaManageService
    schema_tool: SchemaAgentTool
    clickhouse_client: ClickHouseClient
    chat_service: ChatService
    stream_chat_service: StreamChatService
    monitor_service: MonitorService

    @classmethod
    def build(cls, settings: Settings) -> ApplicationServices:
        logger.info("Initializing Application Services...")

        # 1. Embedding provider
        embedding_provider = OpenAIEmbeddingProvider(
            api_key=settings.embedding_api_key or settings.llm_api_key,
            model=settings.embedding_model,
            base_url=settings.embedding_base_url,
            dimensions=settings.embedding_size,
        )

        # 2. Vector store for Business Knowledge RAG
        knowledge_vector_store = QdrantVectorStore(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            grpc_port=settings.qdrant_grpc_port,
            api_key=settings.qdrant_api_key,
            collection_name=settings.knowledge_collection_name,
            vector_size=settings.embedding_size,
        )

        # 3. LLM Client
        llm_client = LLMClient(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )

        # 4. Redis Session Store
        session_store = RedisSessionStore(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            ttl_seconds=settings.session_ttl_seconds,
        )

        # 5. ClickHouse Client & Schema Manager
        clickhouse_client = ClickHouseClient(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_db,
        )

        schema_manager = SchemaManager(
            schema_file_path=settings.schema_file_path,
            enable_schema_rag=settings.enable_schema_rag,
        )

        schema_manage_service = SchemaManageService(
            schema_manager=schema_manager,
            schema_file_path=settings.schema_file_path,
        )

        schema_tool = SchemaAgentTool(
            schema_manager=schema_manager,
        )

        # 6. Knowledge Service & Knowledge Manage Service
        knowledge_service = KnowledgeService(
            vector_store=knowledge_vector_store,
            embedding_provider=embedding_provider,
            knowledge_file_path=settings.knowledge_file_path,
            enable_knowledge_rag=settings.enable_knowledge_rag,
        )

        knowledge_manage_service = KnowledgeManageService(
            knowledge_service=knowledge_service,
            knowledge_file_path=settings.knowledge_file_path,
        )

        # 7. Monitor Service
        monitor_service = MonitorService(max_traces=100)

        # 8. Chat service & Stream Chat Service
        chat_service = ChatService(
            llm_client=llm_client,
            session_store=session_store,
            knowledge_service=knowledge_service,
            schema_manager=schema_manager,
            clickhouse_client=clickhouse_client,
            default_similarity_threshold=settings.similarity_threshold,
        )

        stream_chat_service = StreamChatService(
            llm_client=llm_client,
            session_store=session_store,
            knowledge_service=knowledge_service,
            schema_manager=schema_manager,
            clickhouse_client=clickhouse_client,
            monitor_service=monitor_service,
        )

        # Connect Monitor to chat services
        chat_service.monitor_service = monitor_service
        stream_chat_service.monitor_service = monitor_service

        return cls(
            knowledge_vector_store=knowledge_vector_store,
            embedding_provider=embedding_provider,
            llm_client=llm_client,
            session_store=session_store,
            knowledge_service=knowledge_service,
            knowledge_manage_service=knowledge_manage_service,
            schema_manager=schema_manager,
            schema_manage_service=schema_manage_service,
            schema_tool=schema_tool,
            clickhouse_client=clickhouse_client,
            chat_service=chat_service,
            stream_chat_service=stream_chat_service,
            monitor_service=monitor_service,
        )
