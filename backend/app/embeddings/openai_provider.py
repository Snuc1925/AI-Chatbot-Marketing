from __future__ import annotations

import logging
from typing import Sequence
import openai
from openai import OpenAI

from app.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        base_url: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self.model = model
        self.dimensions = dimensions
        clean_base_url = base_url.strip() if (base_url and base_url.strip()) else None
        clean_api_key = api_key.strip() if (api_key and api_key.strip()) else None
        self.client = OpenAI(
            api_key=clean_api_key or "placeholder-key",
            base_url=clean_base_url,
        )

    def embed_text(self, text: str) -> list[float]:
        cleaned_text = text.replace("\n", " ").strip()
        kwargs = {"input": cleaned_text, "model": self.model}
        if self.dimensions and "text-embedding-3" in self.model:
            kwargs["dimensions"] = self.dimensions

        response = self.client.embeddings.create(**kwargs)
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        cleaned_texts = [t.replace("\n", " ").strip() for t in texts]
        kwargs = {"input": cleaned_texts, "model": self.model}
        if self.dimensions and "text-embedding-3" in self.model:
            kwargs["dimensions"] = self.dimensions

        response = self.client.embeddings.create(**kwargs)
        # Sort embeddings according to original index in case response is unordered
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]
