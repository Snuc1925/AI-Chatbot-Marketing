from __future__ import annotations

import json
import logging
import os
from typing import Any
from pydantic import BaseModel, Field
from app.vectorstores.base import BaseVectorStore

logger = logging.getLogger(__name__)


class ColumnMetadata(BaseModel):
    name: str
    type: str
    description: str = ""



class TableSchemaMetadata(BaseModel):
    table_name: str
    table_alias: str | None = None
    description: str = ""
    columns: list[ColumnMetadata] = Field(default_factory=list)


class SchemaManager:
    def __init__(
        self,
        schema_file_path: str = "schemas.json",
        enable_schema_rag: bool = False,
        schema_vector_store: BaseVectorStore | None = None,
    ) -> None:
        self.schema_file_path = schema_file_path
        self.enable_schema_rag = enable_schema_rag
        self.schema_vector_store = schema_vector_store
        self._schemas: dict[str, TableSchemaMetadata] = {}
        self.load_schemas()

    def load_schemas(self) -> dict[str, TableSchemaMetadata]:
        """
        Loads table metadata, column descriptions, and join hints from schemas.json.
        """
        if not os.path.isabs(self.schema_file_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            full_path = os.path.join(base_dir, self.schema_file_path)
            if not os.path.exists(full_path):
                full_path = self.schema_file_path
        else:
            full_path = self.schema_file_path

        if not os.path.exists(full_path):
            logger.warning("Schema metadata file not found at %s. Initializing empty schema manager.", full_path)
            self._schemas = {}
            return self._schemas

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            loaded: dict[str, TableSchemaMetadata] = {}
            if isinstance(data, list):
                for item in data:
                    table_meta = TableSchemaMetadata(**item)
                    loaded[table_meta.table_name] = table_meta
            elif isinstance(data, dict):
                for tbl_name, item in data.items():
                    if isinstance(item, dict):
                        item.setdefault("table_name", tbl_name)
                        table_meta = TableSchemaMetadata(**item)
                        loaded[tbl_name] = table_meta

            self._schemas = loaded
            logger.info("Loaded %d table schemas from %s", len(self._schemas), full_path)
            return self._schemas
        except Exception as e:
            logger.error("Failed to load schema metadata from %s: %s", full_path, e)
            return self._schemas

    def get_all_tables(self) -> list[TableSchemaMetadata]:
        return list(self._schemas.values())

    def get_table(self, table_name: str) -> TableSchemaMetadata | None:
        return self._schemas.get(table_name)

    def format_table_context(self, table_meta: TableSchemaMetadata) -> str:
        """Formats a single table's metadata and columns for LLM prompt context."""
        parts = [f"### BẢNG: {table_meta.table_name}"]
        if table_meta.description:
            parts.append(f"Mô tả nghiệp vụ: {table_meta.description}")

        if table_meta.columns:
            col_lines = []
            for col in table_meta.columns:
                desc_str = f" - {col.description}" if col.description else ""
                col_lines.append(f"  - `{col.name}` ({col.type}){desc_str}")
            parts.append("Các cột chính:\n" + "\n".join(col_lines))

        # if table_meta.join_hints:
        #     hints = "\n".join(f"  * {hint}" for hint in table_meta.join_hints)
        #     parts.append("Gợi ý liên kết JOIN:\n" + hints)

        # if table_meta.ddl:
        #     parts.append(f"DDL:\n```sql\n{table_meta.ddl}\n```")

        return "\n".join(parts) + "\n"

    def get_all_schemas_text(self) -> str:
        """Returns formatted schemas and column comments of all available tables."""
        if not self._schemas:
            self.load_schemas()
        return "\n".join(self.format_table_context(meta) for meta in self._schemas.values())

    def get_schema_context(self, user_query: str = "", top_k: int = 4) -> str:
        """
        Pluggable Schema Context Provider:
        - Default (Direct): Returns all active table schemas from schemas.json into Prompt.
        - Schema RAG Mode: Performs semantic search over indexed table descriptions if enabled.
        """
        if not self.enable_schema_rag or not self.schema_vector_store:
            return self.get_all_schemas_text()

        try:
            matches = self.schema_vector_store.search(user_query, top_k=top_k)
            if not matches:
                return self.get_all_schemas_text()

            relevant_tables = []
            for match in matches:
                table_name = match.metadata.get("table_name")
                if table_name and table_name in self._schemas:
                    relevant_tables.append(self.format_table_context(self._schemas[table_name]))

            if not relevant_tables:
                return self.get_all_schemas_text()

            return "\n".join(relevant_tables)
        except Exception as e:
            logger.warning("Schema RAG search failed, falling back to full schemas: %s", e)
            return self.get_all_schemas_text()
