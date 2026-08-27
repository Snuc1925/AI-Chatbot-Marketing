from __future__ import annotations

import logging
from typing import Any
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.vectorstores.base import BaseVectorStore, VectorMatch, VectorRecord

logger = logging.getLogger(__name__)    


class QdrantVectorStore(BaseVectorStore):
    def __init__(
        self,
        host: str = "qdrant",
        port: int = 6333,
        grpc_port: int = 6334,
        api_key: str | None = None,
        collection_name: str = "ai_mkt_data",
        vector_size: int = 1536,
        distance: models.Distance = models.Distance.COSINE,
    ) -> None:
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        self.client = QdrantClient(
            host=host,
            port=port,
            grpc_port=grpc_port,
            api_key=api_key,
            timeout=10.0,
            check_compatibility=False,
        )
        self.ensure_collection()

    def ensure_collection(self) -> None:
        """Create collection if it does not exist."""
        try:
            exists = self.client.collection_exists(collection_name=self.collection_name)
            if not exists:
                logger.info(
                    "Creating Qdrant collection '%s' with vector size %d and distance %s",
                    self.collection_name,
                    self.vector_size,
                    self.distance,
                )
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=self.distance,
                    ),
                )
        except Exception as e:
            logger.warning("Could not auto-create/verify Qdrant collection: %s", e)

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return

        points = []
        for record in records:
            payload = {
                "document": record.document,
                **record.metadata,
            }
            points.append(
                models.PointStruct(
                    id=record.id,
                    vector=record.embedding,
                    payload=payload,
                )
            )

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
            logger.info("Upserted %d records into collection '%s'", len(records), self.collection_name)
        except Exception as e:
            logger.error("Failed to upsert %d records into Qdrant collection '%s': %s", len(records), self.collection_name, e)
            raise e

    def query(self, embedding: list[float], top_k: int = 3) -> list[VectorMatch]:
        try:
            # Query using search or query_points
            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=embedding,
                limit=top_k,
                with_payload=True,
            )
            points = search_result.points
        except Exception as e:
            # Fallback to search
            logger.debug("query_points failed, fallback to search: %s", e)
            points = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=top_k,
                with_payload=True,
            )

        matches: list[VectorMatch] = []
        for p in points:
            payload = dict(p.payload or {})
            document = payload.pop("document", "")
            matches.append(
                VectorMatch(
                    id=str(p.id),
                    document=str(document),
                    metadata=payload,
                    score=float(p.score),
                )
            )
        return matches

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=ids),
            wait=True,
        )

    def reset(self) -> None:
        try:
            self.client.delete_collection(collection_name=self.collection_name)
        except Exception as e:
            logger.debug("Reset collection ignored: %s", e)
        self.ensure_collection()

    def count(self) -> int:
        try:
            result = self.client.count(collection_name=self.collection_name, exact=True)
            return result.count
        except Exception as e:
            logger.warning("Failed to get count from Qdrant: %s", e)
            return 0

    def list_ids(self) -> list[str]:
        try:
            scroll_result, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                with_payload=False,
                with_vectors=False,
            )
            return [str(p.id) for p in scroll_result]
        except Exception:
            return []