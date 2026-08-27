from __future__ import annotations

import logging
import uuid
from typing import Any
from app.embeddings.base import BaseEmbeddingProvider
from app.knowledge.knowledge_loader import load_knowledge_chunks
from app.vectorstores.base import BaseVectorStore, VectorMatch, VectorRecord

logger = logging.getLogger(__name__)


class KnowledgeService:
    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_provider: BaseEmbeddingProvider,
        knowledge_file_path: str = "business_knowledge.json",
    ) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.knowledge_file_path = knowledge_file_path

    def sync_knowledge(self, force_reset: bool = False) -> dict[str, Any]:
        """
        Loads natural language business rule chunks from JSON or Markdown file, generates vector embeddings,
        and indexes them into Qdrant vector store.
        """
        logger.info("Syncing business knowledge from %s (force_reset=%s)...", self.knowledge_file_path, force_reset)

        chunks = load_knowledge_chunks(self.knowledge_file_path)

        if not chunks:
            logger.warning("No knowledge chunks found in %s", self.knowledge_file_path)
            return {"status": "skipped", "synced_count": 0, "message": "File tri thức rỗng."}

        if force_reset:
            logger.info("Resetting knowledge collection in Qdrant...")
            self.vector_store.reset()
        else:
            self.vector_store.ensure_collection()

        try:
            embeddings = self.embedding_provider.embed_batch(chunks)
        except Exception as e:
            logger.error("Embedding generation failed during knowledge sync: %s", e)
            return {"status": "error", "synced_count": 0, "error": str(e)}

        records_to_upsert: list[VectorRecord] = []
        for idx, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
            record_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"knowledge_chunk_{idx}_{chunk_text[:30]}"))
            record = VectorRecord(
                id=record_id,
                document=chunk_text,
                embedding=emb,
                metadata={
                    "chunk_index": idx,
                    "source_file": self.knowledge_file_path,
                    "preview": chunk_text[:100],
                },
            )
            records_to_upsert.append(record)

        try:
            self.vector_store.upsert(records_to_upsert)
            count = self.vector_store.count()
            logger.info("Successfully indexed %d knowledge chunks into vector store. Total count: %d", len(records_to_upsert), count)
            return {
                "status": "success",
                "synced_count": len(records_to_upsert),
                "total_count": count,
                "chunks_preview": [c[:80] + "..." if len(c) > 80 else c for c in chunks],
            }
        except Exception as e:
            logger.error("Failed to upsert knowledge records into vector store: %s", e)
            return {"status": "error", "synced_count": 0, "error": str(e)}

    def retrieve_relevant_knowledge(self, query: str, top_k: int = 3, threshold: float = 0.35) -> list[str]:
        """
        Embeds user query and retrieves the top-k most relevant natural language business rule chunks.
        """
        if not query or not query.strip():
            return []

        try:
            query_embedding = self.embedding_provider.embed_text(query.strip())
            matches: list[VectorMatch] = self.vector_store.query(embedding=query_embedding, top_k=top_k)
            # Filter matches by threshold
            relevant_chunks = [m.document for m in matches if m.score >= threshold]
            if not relevant_chunks and matches:
                # If all below threshold, still return top-1 chunk if score is reasonable (> 0.25)
                if matches[0].score >= 0.25:
                    relevant_chunks = [matches[0].document]
            return relevant_chunks
        except Exception as e:
            logger.error("Knowledge retrieval failed: %s", e)
            return []

    def get_all_knowledge(self) -> list[str]:
        """Loads and returns all knowledge chunks directly from file."""
        try:
            return load_knowledge_chunks(self.knowledge_file_path)
        except Exception as e:
            logger.warning("Could not read knowledge file: %s", e)
            return []

    def count(self) -> int:
        return self.vector_store.count()

