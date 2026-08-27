from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from app.knowledge.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)


class KnowledgeRuleItem(BaseModel):
    id: int = Field(description="0-based index or unique ID in JSON list")
    topic: str = Field(description="Topic title of the business rule")
    description: str = Field(description="Natural language description of the rule")


class KnowledgeRuleCreate(BaseModel):
    topic: str = Field(description="Topic title")
    description: str = Field(description="Natural language description of the rule")


class KnowledgeRuleUpdate(BaseModel):
    topic: str | None = None
    description: str | None = None


class KnowledgeManageService:
    def __init__(
        self,
        knowledge_service: KnowledgeService,
        knowledge_file_path: str = "business_knowledge.json",
    ) -> None:
        self.knowledge_service = knowledge_service
        self.knowledge_file_path = knowledge_file_path

    def _resolve_file_path(self) -> Path:
        file_path = Path(self.knowledge_file_path)
        if not file_path.exists():
            alt_paths = [
                Path("business_knowledge.json"),
                Path("backend/business_knowledge.json"),
                Path(__file__).resolve().parent.parent.parent / "business_knowledge.json",
            ]
            for p in alt_paths:
                if p.exists():
                    return p
        return file_path

    def list_rules(self) -> list[KnowledgeRuleItem]:
        """Reads and returns all business rules from business_knowledge.json."""
        file_path = self._resolve_file_path()
        if not file_path.exists():
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []

            rules = []
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    rules.append(
                        KnowledgeRuleItem(
                            id=idx,
                            topic=str(item.get("topic", "")),
                            description=str(item.get("description", "")),
                        )
                    )
            return rules
        except Exception as e:
            logger.error("Failed to read knowledge file %s: %s", file_path, e)
            return []

    def _save_rules(self, rules: list[dict[str, str]]) -> None:
        file_path = self._resolve_file_path()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)

    def create_rule(self, rule: KnowledgeRuleCreate, auto_sync: bool = True) -> dict[str, Any]:
        """Appends a new business rule and saves to JSON."""
        file_path = self._resolve_file_path()
        current_rules = []
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                current_rules = json.load(f)
                if not isinstance(current_rules, list):
                    current_rules = []

        new_entry = {
            "topic": rule.topic.strip(),
            "description": rule.description.strip(),
        }
        current_rules.append(new_entry)
        self._save_rules(current_rules)
        logger.info("Added new knowledge rule: '%s'", rule.topic)

        sync_result = None
        if auto_sync and self.knowledge_service:
            try:
                sync_result = self.knowledge_service.sync_knowledge(force_reset=True)
            except Exception as e:
                logger.warning("Auto sync knowledge failed after create: %s", e)

        return {
            "status": "success",
            "message": f"Đã thêm quy tắc '{rule.topic}' thành công.",
            "total_rules": len(current_rules),
            "sync_result": sync_result,
        }

    def update_rule(self, rule_id: int, update_data: KnowledgeRuleUpdate, auto_sync: bool = True) -> dict[str, Any]:
        """Updates an existing business rule by index and saves to JSON."""
        file_path = self._resolve_file_path()
        if not file_path.exists():
            raise FileNotFoundError("Knowledge file not found")

        with open(file_path, "r", encoding="utf-8") as f:
            current_rules = json.load(f)

        if not isinstance(current_rules, list) or rule_id < 0 or rule_id >= len(current_rules):
            raise IndexError(f"Quy tắc với ID {rule_id} không tồn tại.")

        if update_data.topic is not None:
            current_rules[rule_id]["topic"] = update_data.topic.strip()
        if update_data.description is not None:
            current_rules[rule_id]["description"] = update_data.description.strip()

        self._save_rules(current_rules)
        logger.info("Updated knowledge rule ID %d", rule_id)

        sync_result = None
        if auto_sync and self.knowledge_service:
            try:
                sync_result = self.knowledge_service.sync_knowledge(force_reset=True)
            except Exception as e:
                logger.warning("Auto sync knowledge failed after update: %s", e)

        return {
            "status": "success",
            "message": f"Đã cập nhật quy tắc #{rule_id} thành công.",
            "rule": current_rules[rule_id],
            "sync_result": sync_result,
        }

    def delete_rule(self, rule_id: int, auto_sync: bool = True) -> dict[str, Any]:
        """Deletes a business rule by index and saves to JSON."""
        file_path = self._resolve_file_path()
        if not file_path.exists():
            raise FileNotFoundError("Knowledge file not found")

        with open(file_path, "r", encoding="utf-8") as f:
            current_rules = json.load(f)

        if not isinstance(current_rules, list) or rule_id < 0 or rule_id >= len(current_rules):
            raise IndexError(f"Quy tắc với ID {rule_id} không tồn tại.")

        deleted_item = current_rules.pop(rule_id)
        self._save_rules(current_rules)
        logger.info("Deleted knowledge rule ID %d: '%s'", rule_id, deleted_item.get("topic"))

        sync_result = None
        if auto_sync and self.knowledge_service:
            try:
                sync_result = self.knowledge_service.sync_knowledge(force_reset=True)
            except Exception as e:
                logger.warning("Auto sync knowledge failed after delete: %s", e)

        return {
            "status": "success",
            "message": f"Đã xóa quy tắc '{deleted_item.get('topic')}' thành công.",
            "total_rules": len(current_rules),
            "sync_result": sync_result,
        }
