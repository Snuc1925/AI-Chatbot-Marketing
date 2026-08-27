from __future__ import annotations

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
from app.services.chat_service import ChatRequest, ChatResponse
from app.sessions.models import SessionState

router = APIRouter()
logger = logging.getLogger(__name__)


class SyncKnowledgeRequest(BaseModel):
    force_reset: bool = False


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request_body: ChatRequest, request: Request) -> ChatResponse:
    services = request.app.state.services
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



