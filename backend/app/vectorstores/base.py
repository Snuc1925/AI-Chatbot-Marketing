from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class VectorRecord:
    id: str
    document: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class VectorMatch:
    id: str
    document: str
    metadata: dict[str, Any]
    score: float

class BaseVectorStore(ABC):
    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    @abstractmethod
    def query(self, embedding: list[float], top_k: int) -> list[VectorMatch]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_ids(self) -> list[str]:
        raise NotImplementedError

