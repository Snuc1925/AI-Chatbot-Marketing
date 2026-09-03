from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from app.knowledge.sql_examples_service import SqlExamplesService

logger = logging.getLogger(__name__)


class SqlExampleCreate(BaseModel):
    question: str = Field(description="Natural language question/intent")
    sql: str = Field(description="Verified ClickHouse SQL query template")


class SqlExampleUpdate(BaseModel):
    question: str | None = Field(default=None, description="Updated natural language question")
    sql: str | None = Field(default=None, description="Updated ClickHouse SQL query")


class SqlExamplesManageService:
    """
    Service for CRUD management of SQL examples (sql_examples.json)
    with automatic vector store re-indexing and mode toggle.
    """

    def __init__(
        self,
        sql_examples_service: SqlExamplesService,
        sql_examples_file_path: str = "sql_examples.json",
    ) -> None:
        self.sql_examples_service = sql_examples_service
        self.sql_examples_file_path = sql_examples_file_path

    def _resolve_file_path(self) -> Path:
        if os.path.isabs(self.sql_examples_file_path):
            return Path(self.sql_examples_file_path)
        base_dir = Path(__file__).resolve().parent.parent.parent
        return base_dir / self.sql_examples_file_path

    def _load_raw_rules(self) -> list[dict[str, Any]]:
        file_path = self._resolve_file_path()
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error("Failed to load SQL examples file: %s", e)
            return []

    def _save_rules(self, rules: list[dict[str, Any]]) -> None:
        file_path = self._resolve_file_path()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Re-assign sequential IDs
        for idx, item in enumerate(rules):
            item["id"] = idx
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        logger.info("Saved %d SQL examples to %s", len(rules), file_path)

    def list_examples(self) -> list[dict[str, Any]]:
        raw = self._load_raw_rules()
        for idx, r in enumerate(raw):
            r["id"] = idx
        return raw

    def create_example(self, example: SqlExampleCreate, auto_sync: bool = True) -> dict[str, Any]:
        rules = self._load_raw_rules()
        new_item = {
            "id": len(rules),
            "question": example.question.strip(),
            "sql": example.sql.strip(),
        }
        rules.append(new_item)
        self._save_rules(rules)
        logger.info("Created new SQL example: '%s'", new_item["question"][:50])

        sync_result = None
        if auto_sync and self.sql_examples_service:
            try:
                sync_result = self.sql_examples_service.sync_sql_examples(force_reset=True)
            except Exception as e:
                logger.warning("Auto sync SQL examples failed: %s", e)

        return {
            "status": "success",
            "message": "Đã thêm câu lệnh SQL mẫu thành công.",
            "example": new_item,
            "total_examples": len(rules),
            "sync_result": sync_result,
        }

    def update_example(self, example_id: int, update_data: SqlExampleUpdate, auto_sync: bool = True) -> dict[str, Any]:
        rules = self._load_raw_rules()
        if example_id < 0 or example_id >= len(rules):
            raise IndexError(f"SQL example với ID {example_id} không tồn tại.")

        if update_data.question is not None:
            rules[example_id]["question"] = update_data.question.strip()
        if update_data.sql is not None:
            rules[example_id]["sql"] = update_data.sql.strip()

        self._save_rules(rules)
        logger.info("Updated SQL example ID %d", example_id)

        sync_result = None
        if auto_sync and self.sql_examples_service:
            try:
                sync_result = self.sql_examples_service.sync_sql_examples(force_reset=True)
            except Exception as e:
                logger.warning("Auto sync SQL examples failed after update: %s", e)

        return {
            "status": "success",
            "message": f"Đã cập nhật câu lệnh SQL mẫu #{example_id} thành công.",
            "example": rules[example_id],
            "sync_result": sync_result,
        }

    def delete_example(self, example_id: int, auto_sync: bool = True) -> dict[str, Any]:
        rules = self._load_raw_rules()
        if example_id < 0 or example_id >= len(rules):
            raise IndexError(f"SQL example với ID {example_id} không tồn tại.")

        deleted_item = rules.pop(example_id)
        self._save_rules(rules)
        logger.info("Deleted SQL example ID %d: '%s'", example_id, deleted_item.get("question", "")[:50])

        sync_result = None
        if auto_sync and self.sql_examples_service:
            try:
                sync_result = self.sql_examples_service.sync_sql_examples(force_reset=True)
            except Exception as e:
                logger.warning("Auto sync SQL examples failed after delete: %s", e)

        return {
            "status": "success",
            "message": f"Đã xóa câu lệnh SQL mẫu #{example_id} thành công.",
            "deleted_example": deleted_item,
            "total_examples": len(rules),
            "sync_result": sync_result,
        }

    def set_rag_mode(self, enable_rag: bool) -> dict[str, Any]:
        """Toggles between RAG mode (semantic search) and Full Fetch mode (all examples)."""
        self.sql_examples_service.enable_sql_examples_rag = enable_rag
        mode_str = "RAG Mode (Few-Shot Semantic Search)" if enable_rag else "Full Fetch Mode (Toàn bộ ví dụ mẫu)"
        logger.info("SQL Examples mode changed to: %s", mode_str)
        return {
            "status": "success",
            "enable_sql_examples_rag": enable_rag,
            "mode_label": mode_str,
        }
