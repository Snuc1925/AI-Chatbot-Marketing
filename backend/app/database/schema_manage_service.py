from __future__ import annotations

import json
import logging
import os
from typing import Any
from app.database.schema_manager import ColumnMetadata, SchemaManager, TableSchemaMetadata

logger = logging.getLogger(__name__)


class SchemaManageService:
    def __init__(
        self,
        schema_manager: SchemaManager,
        schema_file_path: str = "schemas.json",
    ) -> None:
        self.schema_manager = schema_manager
        self.schema_file_path = schema_file_path

    def _resolve_full_path(self) -> str:
        if os.path.isabs(self.schema_file_path):
            return self.schema_file_path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, self.schema_file_path)

    def _save_to_file(self) -> bool:
        """Saves current in-memory schemas to the JSON file."""
        full_path = self._resolve_full_path()
        try:
            tables = [table.model_dump() for table in self.schema_manager.get_all_tables()]
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(tables, f, ensure_ascii=False, indent=2)
            logger.info("Saved %d table schemas to %s", len(tables), full_path)
            return True
        except Exception as e:
            logger.error("Failed to save schemas to %s: %s", full_path, e)
            return False

    def list_tables(self) -> list[dict[str, Any]]:
        """Lists all managed tables with summary information."""
        tables = self.schema_manager.get_all_tables()
        return [
            {
                "table_name": t.table_name,
                "table_alias": t.table_alias,
                "description": t.description,
                "column_count": len(t.columns),
                "columns": [c.model_dump() for c in t.columns],
            }
            for t in tables
        ]

    def get_table(self, table_name: str) -> dict[str, Any] | None:
        """Gets full metadata for a specific table."""
        table = self.schema_manager.get_table(table_name)
        if not table:
            return None
        return table.model_dump()

    def upsert_table(self, data: dict[str, Any]) -> dict[str, Any]:
        """Creates or updates metadata for a table and saves to file."""
        table_meta = TableSchemaMetadata(**data)
        self.schema_manager._schemas[table_meta.table_name] = table_meta
        self._save_to_file()
        return {
            "status": "success",
            "message": f"Cập nhật schema bảng '{table_meta.table_name}' thành công.",
            "table": table_meta.model_dump(),
        }

    def update_descriptions(
        self,
        table_name: str,
        table_description: str | None = None,
        column_descriptions: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Updates only the free-text `description` of a table and/or its columns.
        Table name, column names and column types are intentionally NOT editable
        here - those are tied 1:1 to the real ClickHouse DDL in backend/sql/init.sql,
        while descriptions are pure prompt-context metadata that is safe to edit
        without any risk of drifting from the actual database structure.
        """
        table = self.schema_manager.get_table(table_name)
        if not table:
            raise KeyError(f"Không tìm thấy bảng '{table_name}' trong schema metadata.")

        if table_description is not None:
            table.description = table_description.strip()

        if column_descriptions:
            column_by_name = {c.name: c for c in table.columns}
            unknown = [name for name in column_descriptions if name not in column_by_name]
            if unknown:
                raise ValueError(f"Cột không tồn tại trong bảng '{table_name}': {', '.join(unknown)}")
            for col_name, desc in column_descriptions.items():
                column_by_name[col_name].description = desc.strip()

        self._save_to_file()
        return {
            "status": "success",
            "message": f"Đã cập nhật mô tả cho bảng '{table_name}'.",
            "table": table.model_dump(),
        }

    def delete_table(self, table_name: str) -> dict[str, Any]:
        """Deletes a table from schema metadata and saves to file."""
        if table_name not in self.schema_manager._schemas:
            return {"status": "not_found", "message": f"Không tìm thấy bảng '{table_name}'."}
        
        del self.schema_manager._schemas[table_name]
        self._save_to_file()
        return {"status": "success", "message": f"Đã xóa bảng '{table_name}' khỏi schema metadata."}

    def reload(self) -> dict[str, Any]:
        """Reloads schemas directly from JSON file."""
        loaded = self.schema_manager.load_schemas()
        return {
            "status": "success",
            "message": f"Đã nạp lại {len(loaded)} bảng từ {self.schema_file_path}.",
            "table_count": len(loaded),
            "tables": list(loaded.keys()),
        }
