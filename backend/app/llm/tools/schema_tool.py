from __future__ import annotations

import json
import logging
from typing import Any
from app.database.schema_manager import SchemaManager

logger = logging.getLogger(__name__)


class SchemaAgentTool:
    """
    On-Demand Schema Discovery Tool for LLMs.
    Designed for Agentic workflows when the data warehouse grows to dozens or hundreds of tables.
    Allows the LLM to inspect tables and columns dynamically on-demand instead of loading all DDLs into prompt.
    """

    def __init__(self, schema_manager: SchemaManager) -> None:
        self.schema_manager = schema_manager

    @property
    def tool_definitions(self) -> list[dict[str, Any]]:
        """OpenAI-compatible Function Calling tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_database_tables",
                    "description": "Liệt kê danh sách tất cả các bảng dữ liệu có sẵn trong Database ClickHouse kèm mô tả tóm tắt mục đích sử dụng của từng bảng.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_table_schema_detail",
                    "description": "Lấy chi tiết cấu trúc bảng (danh sách cột, kiểu dữ liệu, khóa JOIN, partition và mô tả nghiệp vụ) của một bảng cụ thể.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Tên bảng cần xem chi tiết (ví dụ: 'sms_log_v2', 'f023_mpre_vas', 'f_adpm_aimkt_campaign_customer_detail')",
                            }
                        },
                        "required": ["table_name"],
                    },
                },
            },
        ]

    def execute_tool(self, function_name: str, arguments: dict[str, Any]) -> str:
        """Executes the tool call requested by LLM and returns the formatted response."""
        logger.info("Executing Schema Tool Call: %s with args %s", function_name, arguments)

        if function_name == "list_database_tables":
            tables = self.schema_manager.get_all_tables()
            summary = [
                {
                    "table_name": t.table_name,
                    "table_alias": t.table_alias,
                    "description": t.description,
                    "column_count": len(t.columns),
                }
                for t in tables
            ]
            return json.dumps({"status": "success", "tables": summary}, ensure_ascii=False, indent=2)

        elif function_name == "get_table_schema_detail":
            table_name = arguments.get("table_name", "").strip()
            table_meta = self.schema_manager.get_table(table_name)
            if not table_meta:
                return json.dumps(
                    {"status": "error", "message": f"Bảng '{table_name}' không tồn tại trong metadata."},
                    ensure_ascii=False,
                )
            
            return json.dumps(
                {
                    "status": "success",
                    "table_name": table_meta.table_name,
                    "table_alias": table_meta.table_alias,
                    "description": table_meta.description,
                    "columns": [col.model_dump() for col in table_meta.columns],
                },
                ensure_ascii=False,
                indent=2,
            )

        return json.dumps({"status": "error", "message": f"Unknown tool: {function_name}"}, ensure_ascii=False)
