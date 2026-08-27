from __future__ import annotations

import logging
import time
import uuid
from typing import Any
from pydantic import BaseModel, Field

from app.database.clickhouse_client import ClickHouseClient
from app.database.schema_manager import SchemaManager
from app.knowledge.knowledge_service import KnowledgeService
from app.llm.llm_client import LLMClient, LLMTrace, SqlQueryItem
from app.services.monitor_service import MonitorService
from app.sessions.models import SessionState, SessionStatus
from app.sessions.store import BaseSessionStore

logger = logging.getLogger(__name__)


def log_llm_interaction(logger_inst: logging.Logger, step_name: str, trace: LLMTrace | None) -> None:
    """Helper to log detailed LLM prompt input, raw response output, and token metrics."""
    if not trace:
        return
    logger_inst.info("  [%s] === LLM REQUEST (INPUT) ===", step_name)
    for msg in trace.input_messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        indented = "\n".join(f"      {line}" for line in content.strip().splitlines())
        logger_inst.info("    -> [%s MESSAGE]:\n%s", role, indented)

    logger_inst.info("  [%s] === LLM RESPONSE (OUTPUT) ===", step_name)
    raw_lines = trace.raw_output.strip().splitlines()
    indented_out = "\n".join(f"      {line}" for line in raw_lines)
    logger_inst.info("    -> Raw Output:\n%s", indented_out)

    logger_inst.info(
        "  [%s] === LLM METRICS ===: latency=%sms | prompt_tokens=%d | completion_tokens=%d | total_tokens=%d | model=%s",
        step_name,
        trace.latency_ms,
        trace.prompt_tokens,
        trace.completion_tokens,
        trace.total_tokens,
        trace.model,
    )


class CitationItem(BaseModel):
    id: str = Field(description="Unique ID matching <cite id='...'> in message, e.g. 'sql_1'")
    type: str = Field(default="sql", description="Type of citation: 'sql', 'knowledge', etc.")
    title: str = Field(default="Truy vấn ClickHouse", description="Title for tooltip")
    query: str = Field(description="SQL query string")
    raw_result: Any | None = Field(default=None, description="Result preview from ClickHouse")
    execution_time_ms: float | None = Field(default=None, description="Execution time in milliseconds")


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    reset_session: bool = False
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    top_k: int = 3
    similarity_threshold: float = 0.60


class ChatResponse(BaseModel):
    session_id: str = Field(description="Unique ID of the conversation session.")
    session_status: str = Field(description="'IDLE' or 'WAITING_CLARIFY'")
    response_type: str = Field(
        description="'clarify' if asking for missing info, 'answer' if providing response, 'fallback' if no intent matched."
    )
    message: str = Field(description="The response text sent to user.")
    collected_slots: dict[str, Any] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    suggested_options: list[str] = Field(default_factory=list, description="Dynamic quick reply options suggested by LLM for current question")
    relevant_knowledge: list[str] = Field(default_factory=list, description="Relevant business rules retrieved from knowledge base")
    generated_sql: str | None = None
    generated_sqls: list[SqlQueryItem] = Field(default_factory=list, description="All SQL queries generated for this question")
    citations: list[CitationItem] = Field(default_factory=list, description="List of SQL/Knowledge citations with execution metadata")
    matched_scenario: str | None = None
    similarity_score: float | None = None
    clarify_guideline: str | None = None
    raw_answer_template: str | None = None
    top_matches: list[dict[str, Any]] = Field(default_factory=list)


class ChatService:
    def __init__(
        self,
        llm_client: LLMClient,
        session_store: BaseSessionStore,
        knowledge_service: KnowledgeService | None = None,
        schema_manager: SchemaManager | None = None,
        clickhouse_client: ClickHouseClient | None = None,
        default_similarity_threshold: float = 0.60,
        monitor_service: MonitorService | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.session_store = session_store
        self.knowledge_service = knowledge_service
        self.schema_manager = schema_manager
        self.clickhouse_client = clickhouse_client
        self.default_similarity_threshold = default_similarity_threshold
        self.monitor_service = monitor_service

    def process_chat(self, request: ChatRequest) -> ChatResponse:
        t_start = time.perf_counter()
        user_query = request.query.strip()
        session_id = request.session_id or str(uuid.uuid4())
        request_id = f"req-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"

        logger.info("================================================================================")
        logger.info("[REQUEST START] ID: %s | Session: %s", request_id, session_id)
        logger.info("  User Query: '%s'", user_query)
        logger.info("  Chat History: %d messages", len(request.chat_history))

        if self.monitor_service:
            self.monitor_service.start_trace(request_id, session_id, user_query)

        # 1. Fetch Session State from Redis
        session_state = self.session_store.get(session_id)

        # Handle explicit session reset request
        if request.reset_session:
            logger.info("  Resetting session state as requested.")
            session_state.reset_to_idle()
            self.session_store.save(session_state)

        is_follow_up = session_state.status == SessionStatus.WAITING_CLARIFY
        existing_slots = session_state.collected_slots if is_follow_up else {}
        logger.info("  [Step 1: Session] Status=%s | is_follow_up=%s | existing_slots=%s", session_state.status.value, is_follow_up, existing_slots)

        if not user_query:
            logger.info("  Empty query received. Returning fallback prompt.")
            resp = ChatResponse(
                session_id=session_id,
                session_status=session_state.status.value,
                response_type="fallback",
                message="Bạn vui lòng nhập câu hỏi hoặc yêu cầu cần tra cứu.",
                collected_slots=session_state.collected_slots,
                missing_slots=session_state.missing_slots,
            )
            if self.monitor_service:
                self.monitor_service.finish_trace(request_id, final_response=resp.model_dump(), total_latency_ms=round((time.perf_counter()-t_start)*1000, 2))
            return resp

        # 2. Retrieve relevant business rules from Business Knowledge
        relevant_knowledge: list[str] = []
        if self.knowledge_service:
            try:
                knowledge_matches = self.knowledge_service.retrieve_relevant_knowledge_matches(user_query, top_k=3)
                relevant_knowledge = [m.document for m in knowledge_matches]
                is_k_rag = getattr(self.knowledge_service, "enable_knowledge_rag", True)
                if is_k_rag:
                    logger.info("  [Step 2: Knowledge RAG] Retrieved %d relevant chunks (RAG Mode)", len(knowledge_matches))
                    for idx, match in enumerate(knowledge_matches, 1):
                        logger.info("    -> Chunk %d (score=%.4f): %s", idx, match.score, match.document[:120].replace('\n', ' '))
                else:
                    logger.info("  [Step 2: Full Knowledge] Injected all %d business knowledge rules into prompt (Direct Mode)", len(relevant_knowledge))
                    for idx, match in enumerate(knowledge_matches, 1):
                        logger.info("    -> Rule %d: %s", idx, match.document[:120].replace('\n', ' '))
            except Exception as e:
                logger.warning("  [Step 2: Knowledge] Knowledge retrieval failed: %s", e)

        # 3. Retrieve schema context
        schema_context: str = ""
        if self.schema_manager:
            try:
                schema_context = self.schema_manager.get_schema_context(user_query)
                is_s_rag = getattr(self.schema_manager, "enable_schema_rag", False)
                mode_str = "Schema RAG Mode" if is_s_rag else "Direct Full Schema Mode"
                logger.info("  [Step 3: Schema Context] Schema retrieved (%d chars, %s)", len(schema_context), mode_str)
            except Exception as e:
                logger.warning("  [Step 3: Schema Context] Schema retrieval failed: %s", e)

        # 4. LLM Analysis (Check Clarification, Extract Slots, Generate SQL)
        logger.info("  [Step 4: LLM Analysis] Analyzing query, extracting slots & generating SQL...")
        t_llm = time.perf_counter()
        try:
            analysis = self.llm_client.analyze_clarify_and_answer(
                user_query=user_query,
                existing_slots=existing_slots,
                business_knowledge=relevant_knowledge,
                schema_context=schema_context,
                chat_history=request.chat_history,
                is_follow_up=is_follow_up,
            )
            llm_time_ms = round((time.perf_counter() - t_llm) * 1000, 2)
            if analysis.trace:
                log_llm_interaction(logger, "Step 4: LLM Analysis", analysis.trace)
            logger.info(
                "  [Step 4: LLM Analysis] Done in %sms | Tokens: (prompt=%d, completion=%d, total=%d) | Clarify Needed: %s | Extracted: %s | Missing: %s | SQLs: %d",
                llm_time_ms,
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
        except Exception as e:
            logger.error("  [Step 4: LLM Analysis] LLM analysis failed: %s", e)
            err_resp = ChatResponse(
                session_id=session_id,
                session_status=session_state.status.value,
                response_type="error",
                message=f"Lỗi kết nối LLM API khi xử lý yêu cầu: {e}",
                collected_slots=session_state.collected_slots,
                missing_slots=session_state.missing_slots,
                relevant_knowledge=relevant_knowledge,
            )
            if self.monitor_service:
                self.monitor_service.finish_trace(request_id, final_response=err_resp.model_dump(), total_latency_ms=round((time.perf_counter()-t_start)*1000, 2), error=str(e))
            return err_resp

        if analysis.trace and self.monitor_service:
            self.monitor_service.record_llm_trace(request_id, analysis.trace.model_dump())

        # If user switched intent during follow-up, reset slots
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
            logger.info("  [Response: CLARIFY] Question: '%s' | Suggested options: %s", bot_msg, analysis.suggested_options)
            clarify_resp = ChatResponse(
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
            total_time = round((time.perf_counter() - t_start) * 1000, 2)
            logger.info("[REQUEST FINISHED] ID: %s | Clarify required | Total: %sms", request_id, total_time)
            logger.info("================================================================================")
            if self.monitor_service:
                self.monitor_service.finish_trace(request_id, final_response=clarify_resp.model_dump(), total_latency_ms=total_time)
            return clarify_resp

        # 6. Information is complete -> Execute SQL & synthesize answer
        final_slots = dict(analysis.extracted_entities)
        session_state.reset_to_idle()
        self.session_store.save(session_state)

        bot_msg, citations = self._execute_sqls_and_synthesize(
            user_query=user_query,
            collected_slots=final_slots,
            generated_sqls=analysis.generated_sqls,
            relevant_knowledge=relevant_knowledge,
            default_answer=analysis.suggested_answer or "Đã ghi nhận yêu cầu của bạn.",
            request_id=request_id,
        )

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

        total_time = round((time.perf_counter() - t_start) * 1000, 2)
        logger.info("  [Response: ANSWER] Bot message:\n%s", bot_msg)
        logger.info("[REQUEST FINISHED] ID: %s | Citations: %d | Total: %sms", request_id, len(citations), total_time)
        logger.info("================================================================================")

        if self.monitor_service:
            self.monitor_service.finish_trace(
                request_id=request_id,
                final_response=final_resp.model_dump(),
                total_latency_ms=total_time,
            )

        return final_resp

    def _execute_sqls_and_synthesize(
        self,
        user_query: str,
        collected_slots: dict[str, Any],
        generated_sqls: list[SqlQueryItem],
        relevant_knowledge: list[str],
        default_answer: str,
        request_id: str | None = None,
    ) -> tuple[str, list[CitationItem]]:
        """
        Executes generated ClickHouse SQL queries (if any), collects results and execution timing,
        and synthesizes a coherent final answer with inline <cite id="..."> tags.
        """
        if not generated_sqls:
            logger.info("  [Step 5: SQL Execution] No SQL generated, using default answer.")
            return default_answer, []

        citations: list[CitationItem] = []
        sql_query_results: list[dict[str, Any]] = []

        logger.info("  [Step 5: ClickHouse Execution] Executing %d SQL queries...", len(generated_sqls))
        for item in generated_sqls:
            exec_time: float | None = None
            raw_res: Any = []

            if self.clickhouse_client:
                try:
                    t_start = time.perf_counter()
                    raw_res = self.clickhouse_client.query(item.sql)
                    exec_time = round((time.perf_counter() - t_start) * 1000, 2)
                    logger.info("    -> SQL [%s] OK in %sms (rows=%d): %s", item.id, exec_time, len(raw_res), item.sql)
                    if len(raw_res) > 0:
                        logger.info("       Sample result: %s", str(raw_res[0])[:120])
                except Exception as e:
                    logger.error("    -> SQL [%s] FAILED (%s): %s", item.id, item.sql, e)
                    raw_res = [{"error": f"Lỗi truy vấn ClickHouse: {e}"}]
            else:
                logger.warning("    -> SQL [%s] ClickHouse client not configured!", item.id)
                raw_res = [{"warning": "ClickHouse client chưa được cấu hình"}]

            citations.append(
                CitationItem(
                    id=item.id,
                    type="sql",
                    title=item.title or "Truy vấn ClickHouse",
                    query=item.sql,
                    raw_result=raw_res,
                    execution_time_ms=exec_time,
                )
            )

            sql_info = {
                "id": item.id,
                "title": item.title,
                "sql": item.sql,
                "result": raw_res,
                "execution_time_ms": exec_time,
            }
            sql_query_results.append(sql_info)
            if self.monitor_service and request_id:
                self.monitor_service.record_sql(request_id, sql_info)

        # Synthesize response via LLM
        logger.info("  [Step 6: LLM Synthesis] Synthesizing final answer with citations...")
        t_synth = time.perf_counter()
        try:
            bot_msg, synth_trace = self.llm_client.synthesize_answer_with_citations(
                user_query=user_query,
                collected_slots=collected_slots,
                sql_query_results=sql_query_results,
                business_knowledge=relevant_knowledge,
            )
            if synth_trace:
                log_llm_interaction(logger, "Step 6: LLM Synthesis", synth_trace)
            synth_time_ms = round((time.perf_counter() - t_synth) * 1000, 2)
            logger.info(
                "  [Step 6: LLM Synthesis] Done in %sms | Tokens: (prompt=%d, completion=%d, total=%d)",
                synth_time_ms,
                synth_trace.prompt_tokens,
                synth_trace.completion_tokens,
                synth_trace.total_tokens,
            )
            if self.monitor_service and request_id:
                self.monitor_service.record_llm_trace(request_id, synth_trace.model_dump())
        except Exception as e:
            logger.error("  [Step 6: LLM Synthesis] Failed to synthesize answer: %s", e)
            bot_msg = default_answer

        return bot_msg, citations




