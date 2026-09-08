from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any
from pydantic import BaseModel, Field

from app.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.paths import resolve_data_path
from app.vectorstores.base import VectorMatch, VectorRecord
from app.vectorstores.qdrant_store import QdrantVectorStore

logger = logging.getLogger(__name__)


def resolve_file_path(file_path: str) -> str:
    if os.path.isabs(file_path) and os.path.exists(file_path):
        return file_path
    return resolve_data_path(file_path)


class SqlExampleItem(BaseModel):
    id: int = Field(description="Index/ID of the SQL example")
    question: str = Field(description="Natural language question/intent")
    sql: str = Field(description="Verified ClickHouse SQL query template")
    score: float | None = Field(default=None, description="Similarity score in RAG mode")


class SqlExamplesService:
    """
    Manages Golden Few-Shot SQL Examples:
    - Vectorizes natural language question into Qdrant vector store.
    - Supports both RAG Mode (semantic top-k search) and Full Fetch Mode (all examples).
    """

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        embedding_provider: OpenAIEmbeddingProvider,
        sql_examples_file_path: str = "sql_examples.json",
        enable_sql_examples_rag: bool = True,
        similarity_threshold: float = 0.35,
        top_k: int = 3,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.sql_examples_file_path = sql_examples_file_path
        self.enable_sql_examples_rag = enable_sql_examples_rag
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k

    def _load_raw_json(self) -> list[dict[str, Any]]:
        resolved = resolve_file_path(self.sql_examples_file_path)
        if not os.path.exists(resolved):
            logger.warning("SQL Examples file not found at: %s", resolved)
            return []
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.error("Error reading SQL examples JSON file: %s", e)
        return []

    def get_all_examples(self) -> list[SqlExampleItem]:
        """Loads and returns all SQL examples directly from the JSON file."""
        raw_items = self._load_raw_json()
        result: list[SqlExampleItem] = []
        for idx, item in enumerate(raw_items):
            result.append(
                SqlExampleItem(
                    id=item.get("id", idx),
                    question=item.get("question", "").strip(),
                    sql=item.get("sql", "").strip(),
                    score=1.0,
                )
            )
        return result

    def sync_sql_examples(self, force_reset: bool = False) -> dict[str, Any]:
        """
        Embeds the 'question' of each SQL example and indexes into the Qdrant vector store.
        """
        logger.info("Syncing SQL examples from %s (force_reset=%s)...", self.sql_examples_file_path, force_reset)
        examples = self.get_all_examples()

        if not examples:
            logger.warning("No SQL examples found in %s", self.sql_examples_file_path)
            return {"status": "skipped", "synced_count": 0, "message": "File SQL examples rỗng."}

        if force_reset:
            logger.info("Resetting SQL examples collection in Qdrant...")
            self.vector_store.reset()
        else:
            self.vector_store.ensure_collection()

        # Embed only the question text for semantic matching
        questions_to_embed = [ex.question for ex in examples]
        try:
            embeddings = self.embedding_provider.embed_batch(questions_to_embed)
        except Exception as e:
            logger.error("Embedding generation failed during SQL examples sync: %s", e)
            return {"status": "error", "synced_count": 0, "error": str(e)}

        records_to_upsert: list[VectorRecord] = []
        for idx, (ex, emb) in enumerate(zip(examples, embeddings)):
            record_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"sql_example_{ex.id}_{ex.question[:30]}"))
            doc_content = f"Question: {ex.question}\nSQL:\n{ex.sql}"
            record = VectorRecord(
                id=record_id,
                document=doc_content,
                embedding=emb,
                metadata={
                    "example_id": ex.id,
                    "question": ex.question,
                    "sql": ex.sql,
                    "source_file": self.sql_examples_file_path,
                },
            )
            records_to_upsert.append(record)

        try:
            self.vector_store.upsert(records_to_upsert)
            count = self.vector_store.count()
            logger.info("Successfully indexed %d SQL examples into vector store. Total count: %d", len(records_to_upsert), count)
            return {
                "status": "success",
                "synced_count": len(records_to_upsert),
                "total_count": count,
            }
        except Exception as e:
            logger.error("Failed to upsert SQL examples into vector store: %s", e)
            return {"status": "error", "synced_count": 0, "error": str(e)}

    def retrieve_relevant_examples(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> list[SqlExampleItem]:
        """
        Retrieves relevant SQL examples:
        - If enable_sql_examples_rag is False: Returns ALL examples (Full Fetch Mode).
        - If enable_sql_examples_rag is True: Performs Qdrant vector semantic search on question embeddings (RAG Mode).
        """
        if not self.enable_sql_examples_rag:
            return self.get_all_examples()

        if not query or not query.strip():
            return []

        eff_top_k = top_k if top_k is not None else self.top_k
        eff_threshold = threshold if threshold is not None else self.similarity_threshold

        try:
            query_embedding = self.embedding_provider.embed_text(query.strip())
            matches: list[VectorMatch] = self.vector_store.query(embedding=query_embedding, top_k=eff_top_k)

            # Filter matches by threshold
            relevant: list[SqlExampleItem] = []
            for m in matches:
                if m.score >= eff_threshold:
                    ex_id = m.metadata.get("example_id", 0)
                    question = m.metadata.get("question", "")
                    sql = m.metadata.get("sql", "")
                    if not question or not sql:
                        # Fallback: parse document
                        doc_lines = m.document.split("\nSQL:\n")
                        if len(doc_lines) == 2:
                            question = doc_lines[0].replace("Question: ", "").strip()
                            sql = doc_lines[1].strip()
                    relevant.append(
                        SqlExampleItem(
                            id=int(ex_id),
                            question=question,
                            sql=sql,
                            score=round(m.score, 4),
                        )
                    )

            # If all below threshold, return top-1 if score >= 0.25
            if not relevant and matches and matches[0].score >= 0.25:
                top_m = matches[0]
                relevant.append(
                    SqlExampleItem(
                        id=int(top_m.metadata.get("example_id", 0)),
                        question=top_m.metadata.get("question", ""),
                        sql=top_m.metadata.get("sql", ""),
                        score=round(top_m.score, 4),
                    )
                )

            return relevant
        except Exception as e:
            logger.error("SQL Examples RAG retrieval failed: %s", e)
            return []

    def count(self) -> int:
        return self.vector_store.count()
