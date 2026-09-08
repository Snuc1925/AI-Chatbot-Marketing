from __future__ import annotations

import json
import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from fastapi.responses import StreamingResponse

from app.knowledge.knowledge_manage_service import (
    KnowledgeRuleCreate,
    KnowledgeRuleItem,
    KnowledgeRuleUpdate,
)
from app.knowledge.sql_examples_manage_service import (
    SqlExampleCreate,
    SqlExampleUpdate,
)
from app.logging_utils import client_ip_var, get_or_create_request_id, get_or_create_session_id
from app.services.chat_service import ChatRequest, ChatResponse
from app.sessions.models import SessionState

router = APIRouter()
logger = logging.getLogger(__name__)


def _extract_client_ip(request: Request) -> str:
    """
    Resolves the real client IP. Prefers X-Forwarded-For / X-Real-IP (set by a
    reverse proxy such as nginx in front of the VPS deployment) over
    request.client.host, which would otherwise just be the proxy's own IP.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    return request.client.host if request.client else "unknown"


class SyncKnowledgeRequest(BaseModel):
    force_reset: bool = False


class SqlExampleModeRequest(BaseModel):
    enable_rag: bool


class SystemPromptUpdate(BaseModel):
    content: str


class SchemaDescriptionsUpdate(BaseModel):
    table_description: str | None = None
    column_descriptions: dict[str, str] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request_body: ChatRequest, request: Request) -> ChatResponse:
    services = request.app.state.services
    # Assign this request's ID, session ID and client IP up-front so every log
    # line from here down - this endpoint, chat_service, llm_client - lands in
    # the same per-session/per-request log file (logs/requests/<session_id>/<request_id>.log)
    # and carries the IP that made the request.
    get_or_create_request_id()
    request_body.session_id = get_or_create_session_id(request_body.session_id)
    client_ip_var.set(_extract_client_ip(request))
    logger.info(">>> [POST /api/chat] Received request | query='%s' | session_id=%s", request_body.query, request_body.session_id)
    try:
        response = services.chat_service.process_chat(request_body)
        logger.info("<<< [POST /api/chat] Success | response_type=%s | session_id=%s", response.response_type, response.session_id)
        return response
    except Exception as e:
        logger.exception("!!! [POST /api/chat] Error processing chat: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream_endpoint(request_body: ChatRequest, request: Request):
    """
    Streams realtime execution progress (SSE) including Qdrant RAG, ClickHouse SQL,
    LLM reasoning traces, and token metrics.
    """
    services = request.app.state.services
    get_or_create_request_id()
    request_body.session_id = get_or_create_session_id(request_body.session_id)
    client_ip_var.set(_extract_client_ip(request))
    logger.info(">>> [POST /api/chat/stream] SSE stream started | query='%s' | session_id=%s", request_body.query, request_body.session_id)
    generator = services.stream_chat_service.stream_chat(request_body)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/session/{session_id}", response_model=SessionState)
async def get_session(session_id: str, request: Request) -> SessionState:
    services = request.app.state.services
    try:
        return services.session_store.get(session_id)
    except Exception as e:
        logger.exception("Error getting session '%s': %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/session/{session_id}")
async def delete_session(session_id: str, request: Request) -> dict[str, Any]:
    services = request.app.state.services
    try:
        services.session_store.delete(session_id)
        return {"status": "success", "message": f"Session '{session_id}' deleted."}
    except Exception as e:
        logger.exception("Error deleting session '%s': %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# --- Business Knowledge Rules Management (CRUD) ---

@router.get("/knowledge/rules", response_model=list[KnowledgeRuleItem])
async def list_knowledge_rules(request: Request) -> list[KnowledgeRuleItem]:
    services = request.app.state.services
    return services.knowledge_manage_service.list_rules()


@router.post("/knowledge/rules")
async def create_knowledge_rule(rule: KnowledgeRuleCreate, request: Request) -> dict[str, Any]:
    services = request.app.state.services
    try:
        return services.knowledge_manage_service.create_rule(rule, auto_sync=True)
    except Exception as e:
        logger.exception("Error creating rule: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/knowledge/rules/{rule_id}")
async def update_knowledge_rule(rule_id: int, update_data: KnowledgeRuleUpdate, request: Request) -> dict[str, Any]:
    services = request.app.state.services
    try:
        return services.knowledge_manage_service.update_rule(rule_id, update_data, auto_sync=True)
    except IndexError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Error updating rule: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge/rules/{rule_id}")
async def delete_knowledge_rule(rule_id: int, request: Request) -> dict[str, Any]:
    services = request.app.state.services
    try:
        return services.knowledge_manage_service.delete_rule(rule_id, auto_sync=True)
    except IndexError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Error deleting rule: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# --- Knowledge Sync & Retrieval ---

@router.post("/knowledge/sync")
async def sync_knowledge_endpoint(request_body: SyncKnowledgeRequest, request: Request) -> dict[str, Any]:
    services = request.app.state.services
    try:
        result = services.knowledge_service.sync_knowledge(force_reset=request_body.force_reset)
        return result
    except Exception as e:
        logger.exception("Error syncing knowledge: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge")
async def list_knowledge_endpoint(request: Request) -> dict[str, Any]:
    services = request.app.state.services
    chunks = services.knowledge_service.get_all_knowledge()
    count = services.knowledge_service.count()
    return {
        "chunks_count": len(chunks),
        "vector_store_count": count,
        "chunks": chunks,
    }


# --- Few-Shot Golden SQL Examples Management & Sync ---

@router.get("/sql-examples")
async def list_sql_examples_endpoint(request: Request) -> dict[str, Any]:
    """Lists all golden SQL examples and current RAG/Direct mode status."""
    services = request.app.state.services
    examples = services.sql_examples_manage_service.list_examples()
    v_count = services.sql_examples_service.count()
    is_rag = services.sql_examples_service.enable_sql_examples_rag
    return {
        "total_examples": len(examples),
        "vector_store_count": v_count,
        "enable_sql_examples_rag": is_rag,
        "mode_label": "RAG Mode (Few-Shot Semantic Search)" if is_rag else "Full Fetch Mode (Direct Mode)",
        "examples": examples,
    }


@router.post("/sql-examples")
async def create_sql_example_endpoint(item: SqlExampleCreate, request: Request) -> dict[str, Any]:
    """Creates a new SQL example and auto-syncs into Qdrant."""
    services = request.app.state.services
    try:
        return services.sql_examples_manage_service.create_example(item, auto_sync=True)
    except Exception as e:
        logger.exception("Error creating SQL example: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sql-examples/{example_id}")
async def update_sql_example_endpoint(example_id: int, item: SqlExampleUpdate, request: Request) -> dict[str, Any]:
    """Updates an existing SQL example and auto-syncs into Qdrant."""
    services = request.app.state.services
    try:
        return services.sql_examples_manage_service.update_example(example_id, item, auto_sync=True)
    except IndexError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Error updating SQL example: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sql-examples/{example_id}")
async def delete_sql_example_endpoint(example_id: int, request: Request) -> dict[str, Any]:
    """Deletes an SQL example and auto-syncs into Qdrant."""
    services = request.app.state.services
    try:
        return services.sql_examples_manage_service.delete_example(example_id, auto_sync=True)
    except IndexError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Error deleting SQL example: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sql-examples/sync")
async def sync_sql_examples_endpoint(request_body: SyncKnowledgeRequest, request: Request) -> dict[str, Any]:
    """Force re-indexes all SQL examples into Qdrant."""
    services = request.app.state.services
    try:
        return services.sql_examples_service.sync_sql_examples(force_reset=request_body.force_reset)
    except Exception as e:
        logger.exception("Error syncing SQL examples: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sql-examples/mode")
async def set_sql_examples_mode_endpoint(mode_req: SqlExampleModeRequest, request: Request) -> dict[str, Any]:
    """Toggles between RAG mode (semantic search) and Full Fetch mode (all examples)."""
    services = request.app.state.services
    return services.sql_examples_manage_service.set_rag_mode(mode_req.enable_rag)



@router.get("/clickhouse/tables")
async def list_clickhouse_tables(request: Request) -> dict[str, Any]:
    services = request.app.state.services
    try:
        rows = services.clickhouse_client.query("SHOW TABLES;")
        tables = [list(r.values())[0] for r in rows] if rows else []
        return {
            "status": "connected",
            "database": services.clickhouse_client.database,
            "tables": tables,
        }
    except Exception as e:
        logger.warning("ClickHouse tables query failed: %s", e)
        return {
            "status": "unavailable",
            "error": str(e),
            "tables": [],
        }


@router.get("/clickhouse/schema")
async def get_clickhouse_schema(request: Request) -> dict[str, Any]:
    services = request.app.state.services
    schema_text = services.schema_manager.get_all_schemas_text()
    return {
        "schema_text": schema_text,
        "enable_schema_rag": services.schema_manager.enable_schema_rag,
    }


@router.get("/health")
async def health_check(request: Request) -> dict[str, Any]:
    services = request.app.state.services
    knowledge_count = services.knowledge_service.count()
    ch_healthy = services.clickhouse_client.ping()
    return {
        "status": "healthy",
        "knowledge_vector_store_connected": True,
        "indexed_knowledge_count": knowledge_count,
        "clickhouse_connected": ch_healthy,
    }


# --- Monitor & Execution Trace Endpoints ---

@router.get("/monitor/traces")
async def list_monitor_traces(request: Request) -> list[dict[str, Any]]:
    services = request.app.state.services
    return services.monitor_service.list_traces()


@router.get("/monitor/traces/{request_id}")
async def get_monitor_trace_detail(request_id: str, request: Request) -> dict[str, Any]:
    services = request.app.state.services
    detail = services.monitor_service.get_trace_detail(request_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Trace not found")
    return detail


# --- Schema & Metadata Management Endpoints ---

@router.get("/schema/tables")
async def list_schema_tables(request: Request) -> list[dict[str, Any]]:
    """Lists all managed ClickHouse tables and their metadata."""
    services = request.app.state.services
    return services.schema_manage_service.list_tables()


@router.get("/schema/tables/{table_name}")
async def get_schema_table(table_name: str, request: Request) -> dict[str, Any]:
    """Gets detailed schema metadata for a specific table."""
    services = request.app.state.services
    table_meta = services.schema_manage_service.get_table(table_name)
    if not table_meta:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in metadata.")
    return table_meta


@router.put("/schema/tables/{table_name}/descriptions")
async def update_schema_descriptions(table_name: str, payload: SchemaDescriptionsUpdate, request: Request) -> dict[str, Any]:
    """
    Updates only the free-text description of a table and/or its columns.
    Table/column names and column types stay fixed - they mirror the real
    ClickHouse DDL in backend/sql/init.sql and are not editable via this endpoint.
    """
    services = request.app.state.services
    try:
        return services.schema_manage_service.update_descriptions(
            table_name,
            table_description=payload.table_description,
            column_descriptions=payload.column_descriptions,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error updating schema descriptions for '%s': %s", table_name, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schema/tables")
async def upsert_schema_table(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """Creates or updates a table's schema metadata and persists to schemas.json."""
    services = request.app.state.services
    if not payload.get("table_name"):
        raise HTTPException(status_code=400, detail="Field 'table_name' is required.")
    return services.schema_manage_service.upsert_table(payload)


@router.delete("/schema/tables/{table_name}")
async def delete_schema_table(table_name: str, request: Request) -> dict[str, Any]:
    """Deletes a table from schema metadata and updates schemas.json."""
    services = request.app.state.services
    res = services.schema_manage_service.delete_table(table_name)
    if res.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res


@router.post("/schema/reload")
async def reload_schema_metadata(request: Request) -> dict[str, Any]:
    """Reloads schema metadata from schemas.json file directly."""
    services = request.app.state.services
    return services.schema_manage_service.reload()


@router.get("/schema/tools/definitions")
async def get_schema_tool_definitions(request: Request) -> list[dict[str, Any]]:
    """Returns tool schemas for LLM Function Calling (Agentic schema on-demand discovery)."""
    services = request.app.state.services
    return services.schema_tool.tool_definitions


@router.post("/schema/tools/call")
async def call_schema_tool(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """Tests executing a Schema Tool Call directly."""
    services = request.app.state.services
    tool_name = payload.get("tool_name", "")
    args = payload.get("arguments", {})
    raw_res = services.schema_tool.execute_tool(tool_name, args)
    return {"status": "success", "result": json.loads(raw_res)}


# --- System Prompts Management (editable at runtime, no restart needed) ---

@router.get("/prompts")
async def list_system_prompts(request: Request) -> list[dict[str, Any]]:
    """Lists all editable LLM system prompts currently in effect."""
    services = request.app.state.services
    return services.prompt_manage_service.list_prompts()


@router.put("/prompts/{key}")
async def update_system_prompt(key: str, payload: SystemPromptUpdate, request: Request) -> dict[str, Any]:
    """Updates a system prompt's content. Takes effect on the very next LLM call."""
    services = request.app.state.services
    try:
        return services.prompt_manage_service.update_prompt(key, payload.content)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/prompts/{key}/reset")
async def reset_system_prompt(key: str, request: Request) -> dict[str, Any]:
    """Resets a system prompt back to its built-in default content."""
    services = request.app.state.services
    try:
        return services.prompt_manage_service.reset_prompt(key)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/monitor/live")
async def monitor_live_stream(request: Request):
    """
    Subscribes to global realtime pipeline events across all users for Admin Live Dashboard.
    """
    services = request.app.state.services
    generator = services.monitor_service.subscribe()
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
