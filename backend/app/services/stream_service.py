from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator

from app.database.clickhouse_client import ClickHouseClient
from app.database.schema_manager import SchemaManager
from app.knowledge.knowledge_service import KnowledgeService
from app.logging_utils import get_or_create_request_id
from app.knowledge.sql_examples_service import SqlExamplesService
from app.llm.llm_client import LLMClient, LLMTrace, SqlQueryItem
from app.services.chat_service import ChatRequest, ChatResponse, CitationItem, log_llm_interaction
from app.services.monitor_service import MonitorService
from app.sessions.models import SessionStatus
from app.sessions.store import BaseSessionStore

logger = logging.getLogger(__name__)


def sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Formats payload as standard Server-Sent Events (SSE) data string."""
    import math

    def _sanitize(obj: Any) -> Any:
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(x) for x in obj]
        return obj

    clean_data = _sanitize(data)
    json_str = json.dumps(clean_data, ensure_ascii=False, default=str)
    return f"event: {event_type}\ndata: {json_str}\n\n"


class StreamChatService:
    def __init__(
        self,
        llm_client: LLMClient,
        session_store: BaseSessionStore,
        knowledge_service: KnowledgeService | None = None,
        schema_manager: SchemaManager | None = None,
        clickhouse_client: ClickHouseClient | None = None,
        monitor_service: MonitorService | None = None,
        sql_examples_service: SqlExamplesService | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.session_store = session_store
        self.knowledge_service = knowledge_service
        self.schema_manager = schema_manager
        self.clickhouse_client = clickhouse_client
        self.monitor_service = monitor_service
        self.sql_examples_service = sql_examples_service

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        t_request_start = time.perf_counter()
        user_query = request.query.strip()
        session_id = request.session_id or str(uuid.uuid4())
        # Reuses the request_id already assigned by the endpoint (see app/logging_utils.py)
        # so this request's logs land in the same per-request log file.
        request_id = get_or_create_request_id()

        logger.info("================================================================================")
        logger.info("[STREAM REQUEST START] ID: %s | Session: %s", request_id, session_id)
        logger.info("  User Query: '%s'", user_query)
        logger.info("  Chat History: %d messages", len(request.chat_history))

        if self.monitor_service:
            self.monitor_service.start_trace(request_id, session_id, user_query)

        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        llm_traces: list[dict[str, Any]] = []

        # 0. Initial Pipeline Start
        yield sse_event("pipeline_start", {
            "request_id": request_id,
            "session_id": session_id,
            "query": user_query,
            "timestamp": time.time(),
        })

        # 1. Step: Session Load
        t_step = time.perf_counter()
        yield sse_event("step_start", {
            "step": "SESSION_LOAD",
            "title": "Nạp trạng thái phiên (Redis)",
            "status": "running",
        })

        session_state = self.session_store.get(session_id)
        if request.reset_session:
            logger.info("  Resetting session state as requested.")
            session_state.reset_to_idle()
            self.session_store.save(session_state)

        is_follow_up = session_state.status == SessionStatus.WAITING_CLARIFY
        existing_slots = session_state.collected_slots if is_follow_up else {}
        session_load_ms = round((time.perf_counter() - t_step) * 1000, 2)
        logger.info("  [Step 1: Session] Status=%s | is_follow_up=%s | existing_slots=%s (%sms)", session_state.status.value, is_follow_up, existing_slots, session_load_ms)
        step_session_data = {
            "step": "SESSION_LOAD",
            "title": "Nạp trạng thái phiên (Redis)",
            "status": "completed",
            "latency_ms": session_load_ms,
            "data": {
                "session_status": session_state.status.value,
                "is_follow_up": is_follow_up,
                "existing_slots": existing_slots,
            },
        }
        if self.monitor_service:
            self.monitor_service.record_step(request_id, step_session_data)
        yield sse_event("step_done", step_session_data)

        if not user_query:
            logger.info("  Empty query received in stream. Returning fallback prompt.")
            final_resp = ChatResponse(
                session_id=session_id,
                session_status=session_state.status.value,
                response_type="fallback",
                message="Bạn vui lòng nhập câu hỏi hoặc yêu cầu cần tra cứu.",
            )
            req_latency = round((time.perf_counter() - t_request_start) * 1000, 2)
            if self.monitor_service:
                self.monitor_service.finish_trace(request_id, final_response=final_resp.model_dump(), total_latency_ms=req_latency)
            yield sse_event("final_response", {
                "chat_response": final_resp.model_dump(),
                "total_tokens": 0,
                "total_latency_ms": req_latency,
            })
            return

        # 2. Step: Knowledge RAG Retrieval
        t_step = time.perf_counter()
        yield sse_event("step_start", {
            "step": "KNOWLEDGE_RAG",
            "title": "Truy vấn Tri thức Nghiệp vụ (Qdrant)",
            "status": "running",
        })

        relevant_knowledge: list[str] = []
        if self.knowledge_service:
            try:
                knowledge_matches = self.knowledge_service.retrieve_relevant_knowledge_matches(user_query, top_k=3)
                relevant_knowledge = [m.document for m in knowledge_matches]
                logger.info("  [Step 2: Knowledge RAG] Retrieved %d chunks", len(knowledge_matches))
                for idx, match in enumerate(knowledge_matches, 1):
                    logger.info("    -> Chunk %d (score=%.4f): %s", idx, match.score, match.document[:120].replace('\n', ' '))
            except Exception as e:
                logger.warning("  [Step 2: Knowledge RAG] Retrieval failed: %s", e)

        rag_latency_ms = round((time.perf_counter() - t_step) * 1000, 2)
        step_rag_data = {
            "step": "KNOWLEDGE_RAG",
            "title": "Truy vấn Tri thức Nghiệp vụ (Qdrant)",
            "status": "completed",
            "latency_ms": rag_latency_ms,
            "data": {
                "chunks_count": len(relevant_knowledge),
                "chunks": relevant_knowledge,
            },
        }
        if self.monitor_service:
            self.monitor_service.record_step(request_id, step_rag_data)
        yield sse_event("step_done", step_rag_data)

        # 2.5. Step: Few-Shot Golden SQL Examples (Qdrant / Full)
        # HIDDEN (not deleted): SQL Examples feature is intentionally disabled - its
        # content now overlaps with Business Knowledge, so this step is no longer
        # emitted to the prompt, logs, or the Monitor UI's realtime pipeline view.
        # The underlying service/API/data file are left untouched so this can be
        # re-enabled later by uncommenting.
        relevant_sql_examples: list[dict[str, Any]] = []
        # t_step = time.perf_counter()
        # yield sse_event("step_start", {
        #     "step": "SQL_EXAMPLES",
        #     "title": "Truy xuất Mẫu Truy Vấn Đã Kiểm Chứng (Few-Shot SQLs)",
        #     "status": "running",
        # })
        #
        # if self.sql_examples_service:
        #     try:
        #         sql_ex_items = self.sql_examples_service.retrieve_relevant_examples(user_query)
        #         relevant_sql_examples = [{"question": item.question, "sql": item.sql} for item in sql_ex_items]
        #         is_sql_rag = getattr(self.sql_examples_service, "enable_sql_examples_rag", True)
        #         if is_sql_rag:
        #             logger.info("  [Step 2.5: SQL Examples RAG] Retrieved %d relevant golden SQLs (RAG Mode)", len(sql_ex_items))
        #             for idx, item in enumerate(sql_ex_items, 1):
        #                 score_str = f"score={item.score:.4f}" if item.score is not None else "score=N/A"
        #                 logger.info("    -> Example %d (%s): '%s'", idx, score_str, item.question[:100])
        #         else:
        #             logger.info("  [Step 2.5: Full SQL Examples] Injected all %d golden SQL examples (Direct Mode)", len(relevant_sql_examples))
        #             for idx, item in enumerate(sql_ex_items, 1):
        #                 logger.info("    -> Example %d: '%s'", idx, item.question[:100])
        #     except Exception as e:
        #         logger.warning("  [Step 2.5: SQL Examples] SQL examples retrieval failed: %s", e)
        #
        # sql_ex_latency_ms = round((time.perf_counter() - t_step) * 1000, 2)
        # step_sql_ex_data = {
        #     "step": "SQL_EXAMPLES",
        #     "title": "Truy xuất Mẫu Truy Vấn Đã Kiểm Chứng (Few-Shot SQLs)",
        #     "status": "completed",
        #     "latency_ms": sql_ex_latency_ms,
        #     "data": {
        #         "examples_count": len(relevant_sql_examples),
        #         "examples": relevant_sql_examples,
        #     },
        # }
        # if self.monitor_service:
        #     self.monitor_service.record_step(request_id, step_sql_ex_data)
        # yield sse_event("step_done", step_sql_ex_data)

        # 3. Step: Schema Context
        t_step = time.perf_counter()
        yield sse_event("step_start", {
            "step": "SCHEMA_CONTEXT",
            "title": "Nạp Cấu trúc Bảng ClickHouse",
            "status": "running",
        })

        schema_context: str = ""
        if self.schema_manager:
            try:
                schema_context = self.schema_manager.get_schema_context(user_query)
                logger.info("  [Step 3: Schema Context] Loaded schema context (%d chars)", len(schema_context))
            except Exception as e:
                logger.warning("  [Step 3: Schema Context] Schema failed: %s", e)

        schema_latency_ms = round((time.perf_counter() - t_step) * 1000, 2)
        step_schema_data = {
            "step": "SCHEMA_CONTEXT",
            "title": "Nạp Cấu trúc Bảng ClickHouse",
            "status": "completed",
            "latency_ms": schema_latency_ms,
            "data": {
                "schema_preview": schema_context[:300] + "..." if len(schema_context) > 300 else schema_context,
            },
        }
        if self.monitor_service:
            self.monitor_service.record_step(request_id, step_schema_data)
        yield sse_event("step_done", step_schema_data)

        # 4. Step: LLM Analysis & Intent/Slot extraction
        t_step = time.perf_counter()
        yield sse_event("step_start", {
            "step": "LLM_ANALYSIS",
            "title": "Phân tích Ý định & Slot / Sinh SQL (LLM)",
            "status": "running",
        })

        logger.info("  [Step 4: LLM Analysis] Analyzing query, extracting slots & generating SQL...")
        try:
            analysis = self.llm_client.analyze_clarify_and_answer(
                user_query=user_query,
                existing_slots=existing_slots,
                business_knowledge=relevant_knowledge,
                sql_examples=relevant_sql_examples,
                schema_context=schema_context,
                chat_history=request.chat_history,
                is_follow_up=is_follow_up,
            )
        except Exception as e:
            logger.error("  [Step 4: LLM Analysis] LLM analysis failed: %s", e)
            yield sse_event("pipeline_error", {
                "step": "LLM_ANALYSIS",
                "error": f"Lỗi kết nối LLM API: {e}",
            })
            final_resp = ChatResponse(
                session_id=session_id,
                session_status=session_state.status.value,
                response_type="error",
                message=f"Lỗi kết nối LLM API: {e}",
            )
            req_latency = round((time.perf_counter() - t_request_start) * 1000, 2)
            if self.monitor_service:
                self.monitor_service.finish_trace(request_id, final_response=final_resp.model_dump(), total_latency_ms=req_latency, error=str(e))
            yield sse_event("final_response", {
                "chat_response": final_resp.model_dump(),
                "total_tokens": 0,
                "total_latency_ms": req_latency,
            })
            return

        if analysis.trace:
            log_llm_interaction(logger, "Step 4: LLM Analysis", analysis.trace)
            total_prompt_tokens += analysis.trace.prompt_tokens
            total_completion_tokens += analysis.trace.completion_tokens
            total_tokens += analysis.trace.total_tokens
            llm_traces.append(analysis.trace.model_dump())
            if self.monitor_service:
                self.monitor_service.record_llm_trace(request_id, analysis.trace.model_dump())

        analysis_latency_ms = round((time.perf_counter() - t_step) * 1000, 2)
        logger.info(
            "  [Step 4: LLM Analysis] Done in %sms | Tokens: (prompt=%d, completion=%d, total=%d) | Clarify Needed: %s | Extracted: %s | Missing: %s | SQLs: %d",
            analysis_latency_ms,
            analysis.trace.prompt_tokens if analysis.trace else 0,
            analysis.trace.completion_tokens if analysis.trace else 0,
            analysis.trace.total_tokens if analysis.trace else 0,
            analysis.is_clarification_needed,
            analysis.extracted_entities,
            analysis.missing_slots,
            len(analysis.generated_sqls),
        )
        for sql_item in analysis.generated_sqls:
            logger.info("    -> SQL [%s] (%s): %s", sql_item.id, sql_item.title, sql_item.sql)

        step_llm_data = {
            "step": "LLM_ANALYSIS",
            "title": "Phân tích Ý định & Slot / Sinh SQL (LLM)",
            "status": "completed",
            "latency_ms": analysis_latency_ms,
            "data": {
                "is_clarification_needed": analysis.is_clarification_needed,
                "clarifying_question": analysis.clarifying_question,
                "suggested_options": analysis.suggested_options,
                "extracted_entities": analysis.extracted_entities,
                "missing_slots": analysis.missing_slots,
                "generated_sqls": [s.model_dump() for s in analysis.generated_sqls],
                "llm_trace": analysis.trace.model_dump() if analysis.trace else None,
            },
        }
        if self.monitor_service:
            self.monitor_service.record_step(request_id, step_llm_data)
        yield sse_event("step_done", step_llm_data)

        if is_follow_up and analysis.is_intent_switched:
            logger.info("  Session %s detected intent switch.", session_id)
            session_state.reset_to_idle()

        # 5. Handle Clarification needed
        if analysis.is_clarification_needed:
            session_state.status = SessionStatus.WAITING_CLARIFY
            session_state.collected_slots = analysis.extracted_entities
            session_state.missing_slots = analysis.missing_slots
            self.session_store.save(session_state)

            bot_msg = analysis.clarifying_question or "Bạn vui lòng cung cấp thêm thông tin để hệ thống hỗ trợ tra cứu."
            logger.info("  [Response: CLARIFY] Question: '%s' | Options: %s", bot_msg, analysis.suggested_options)
            final_resp = ChatResponse(
                session_id=session_id,
                session_status=session_state.status.value,
                response_type="clarify",
                message=bot_msg,
                collected_slots=session_state.collected_slots,
                missing_slots=session_state.missing_slots,
                suggested_options=analysis.suggested_options,
                relevant_knowledge=relevant_knowledge,
                generated_sql=analysis.generated_sql,
                generated_sqls=analysis.generated_sqls,
            )

            total_req_time = round((time.perf_counter() - t_request_start) * 1000, 2)
            logger.info("[STREAM REQUEST FINISHED] ID: %s | Clarify required | Total: %sms", request_id, total_req_time)
            logger.info("================================================================================")
            if self.monitor_service:
                self.monitor_service.finish_trace(
                    request_id=request_id,
                    final_response=final_resp.model_dump(),
                    total_latency_ms=total_req_time,
                )

            yield sse_event("final_response", {
                "chat_response": final_resp.model_dump(),
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens,
                "total_latency_ms": total_req_time,
                "llm_traces": llm_traces,
            })
            return

        # 6. Step: Execute Multi-SQL on ClickHouse
        final_slots = dict(analysis.extracted_entities)
        session_state.reset_to_idle()
        self.session_store.save(session_state)

        citations: list[CitationItem] = []
        sql_query_results: list[dict[str, Any]] = []

        if analysis.generated_sqls:
            t_step = time.perf_counter()
            logger.info("  [Step 5: ClickHouse Execution] Executing %d SQL queries...", len(analysis.generated_sqls))
            yield sse_event("step_start", {
                "step": "SQL_EXECUTION",
                "title": f"Thực thi {len(analysis.generated_sqls)} câu lệnh ClickHouse SQL",
                "status": "running",
            })

            for item in analysis.generated_sqls:
                t_sql = time.perf_counter()
                raw_res: Any = []
                exec_time: float | None = None

                if self.clickhouse_client:
                    try:
                        raw_res = self.clickhouse_client.query(item.sql)
                        exec_time = round((time.perf_counter() - t_sql) * 1000, 2)
                        logger.info("    -> SQL [%s] OK in %sms (rows=%d): %s", item.id, exec_time, len(raw_res), item.sql)
                        if len(raw_res) > 0:
                            logger.info("       Sample result: %s", str(raw_res[0])[:120])
                    except Exception as e:
                        logger.error("    -> SQL [%s] FAILED (%s): %s", item.id, item.sql, e)
                        raw_res = [{"error": f"Lỗi truy vấn ClickHouse: {e}"}]
                else:
                    logger.warning("    -> SQL [%s] ClickHouse client not configured!", item.id)
                    raw_res = [{"warning": "ClickHouse client chưa được cấu hình"}]

                citation = CitationItem(
                    id=item.id,
                    type="sql",
                    title=item.title or "Truy vấn ClickHouse",
                    query=item.sql,
                    raw_result=raw_res,
                    execution_time_ms=exec_time,
                )
                citations.append(citation)

                sql_info = {
                    "id": item.id,
                    "title": item.title,
                    "sql": item.sql,
                    "result": raw_res,
                    "execution_time_ms": exec_time,
                }
                sql_query_results.append(sql_info)
                if self.monitor_service:
                    self.monitor_service.record_sql(request_id, sql_info)

            sql_exec_total_ms = round((time.perf_counter() - t_step) * 1000, 2)
            step_sql_data = {
                "step": "SQL_EXECUTION",
                "title": f"Thực thi {len(analysis.generated_sqls)} câu lệnh ClickHouse SQL",
                "status": "completed",
                "latency_ms": sql_exec_total_ms,
                "data": {
                    "sql_results": sql_query_results,
                },
            }
            if self.monitor_service:
                self.monitor_service.record_step(request_id, step_sql_data)
            yield sse_event("step_done", step_sql_data)

        # 7. Step: LLM Answer Synthesis & Citations
        t_step = time.perf_counter()
        yield sse_event("step_start", {
            "step": "ANSWER_SYNTHESIS",
            "title": "Tổng hợp câu trả lời & gắn thẻ trích dẫn Citations (LLM)",
            "status": "running",
        })

        if sql_query_results:
            logger.info("  [Step 6: LLM Synthesis] Synthesizing final answer with citations...")
            bot_msg, synth_trace = self.llm_client.synthesize_answer_with_citations(
                user_query=user_query,
                collected_slots=final_slots,
                sql_query_results=sql_query_results,
                business_knowledge=relevant_knowledge,
            )
            if synth_trace:
                log_llm_interaction(logger, "Step 6: LLM Synthesis", synth_trace)
            total_prompt_tokens += synth_trace.prompt_tokens
            total_completion_tokens += synth_trace.completion_tokens
            total_tokens += synth_trace.total_tokens
            llm_traces.append(synth_trace.model_dump())
            if self.monitor_service:
                self.monitor_service.record_llm_trace(request_id, synth_trace.model_dump())
            logger.info(
                "  [Step 6: LLM Synthesis] Done in %sms | Tokens: (prompt=%d, completion=%d, total=%d)",
                synth_trace.latency_ms,
                synth_trace.prompt_tokens,
                synth_trace.completion_tokens,
                synth_trace.total_tokens,
            )
        else:
            bot_msg = analysis.suggested_answer or "Đã ghi nhận yêu cầu của bạn."

        synthesis_latency_ms = round((time.perf_counter() - t_step) * 1000, 2)
        step_synth_data = {
            "step": "ANSWER_SYNTHESIS",
            "title": "Tổng hợp câu trả lời & gắn thẻ trích dẫn Citations (LLM)",
            "status": "completed",
            "latency_ms": synthesis_latency_ms,
            "data": {
                "bot_message_preview": bot_msg[:150] + "..." if len(bot_msg) > 150 else bot_msg,
                "citations_count": len(citations),
            },
        }
        if self.monitor_service:
            self.monitor_service.record_step(request_id, step_synth_data)
        yield sse_event("step_done", step_synth_data)

        # 8. Final Response Event
        final_resp = ChatResponse(
            session_id=session_id,
            session_status=session_state.status.value,
            response_type="answer",
            message=bot_msg,
            collected_slots=final_slots,
            missing_slots=[],
            suggested_options=[],
            relevant_knowledge=relevant_knowledge,
            generated_sql=analysis.generated_sql,
            generated_sqls=analysis.generated_sqls,
            citations=citations,
        )

        total_req_time = round((time.perf_counter() - t_request_start) * 1000, 2)
        logger.info("  [Response: ANSWER] Bot message: '%s...'", bot_msg[:120].replace('\n', ' '))
        logger.info("[STREAM REQUEST FINISHED] ID: %s | Citations: %d | Total: %sms", request_id, len(citations), total_req_time)
        logger.info("================================================================================")

        if self.monitor_service:
            self.monitor_service.finish_trace(
                request_id=request_id,
                final_response=final_resp.model_dump(),
                total_latency_ms=total_req_time,
            )

        yield sse_event("final_response", {
            "chat_response": final_resp.model_dump(),
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "total_latency_ms": total_req_time,
            "llm_traces": llm_traces,
        })


