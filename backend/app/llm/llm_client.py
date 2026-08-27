from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from pydantic import BaseModel, Field
from openai import OpenAI

logger = logging.getLogger(__name__)



def safe_parse_json(raw_text: str) -> dict[str, Any]:
    """
    Safely extract and parse JSON from model output, handling potential markdown code blocks
    or trailing formatting.
    """
    if not raw_text or not raw_text.strip():
        return {}

    cleaned = raw_text.strip()

    # If wrapped in markdown code blocks, strip them
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as e:
                logger.warning("Regex json substring parsing also failed: %s", e)
        logger.error("Failed to parse JSON from response: %s", raw_text)
        return {}



class LLMTrace(BaseModel):
    call_type: str = Field(description="Call type name, e.g. 'analyze_clarify_and_answer'")
    model: str = Field(description="Model name used for completion")
    input_messages: list[dict[str, str]] = Field(default_factory=list, description="Exact messages payload sent to LLM")
    raw_output: str = Field(default="", description="Raw string output from LLM before parsing")
    prompt_tokens: int = Field(default=0, description="Tokens used for prompt")
    completion_tokens: int = Field(default=0, description="Tokens used for completion")
    total_tokens: int = Field(default=0, description="Total tokens used for this call")
    latency_ms: float = Field(default=0.0, description="Execution time in milliseconds")


class SqlQueryItem(BaseModel):
    id: str = Field(description="Unique ID for citation reference, e.g. 'sql_1', 'sql_2'")
    title: str = Field(default="Truy vấn ClickHouse", description="Short title or description of this query")
    sql: str = Field(description="Valid ClickHouse SQL SELECT query")


class ClarifyAnalysisResult(BaseModel):
    is_clarification_needed: bool = Field(
        default=False,
        description="True if the user query is missing required parameters, False otherwise."
    )
    clarifying_question: str | None = Field(
        default="",
        description="The exact clarification question to ask the user if needed."
    )
    suggested_options: list[str] = Field(
        default_factory=list,
        description="Dynamic list of quick reply choices (options 1, 2, 3...) corresponding specifically to the current clarifying question. Do NOT include 'Other/Khác' as UI adds it automatically."
    )
    extracted_entities: dict[str, Any] = Field(
        default_factory=dict,
        description="Entities/parameters extracted from the user query (e.g., campaign_name, time_range, channel, age_group, etc.)"
    )
    missing_slots: list[str] = Field(
        default_factory=list,
        description="List of required parameter names that are still missing (e.g., ['time_range', 'campaign_name'])."
    )
    suggested_answer: str | None = Field(
        default="",
        description="Answer if clarification is not needed and no DB query is required."
    )
    generated_sql: str | None = Field(
        default=None,
        description="Optional single valid ClickHouse SQL query if applicable to answer the question."
    )
    generated_sqls: list[SqlQueryItem] = Field(
        default_factory=list,
        description="List of valid ClickHouse SQL queries needed to answer the question, each with unique ID (e.g., 'sql_1', 'sql_2')."
    )
    is_intent_switched: bool = Field(
        default=False,
        description="True if user is asking a completely different new question instead of answering the clarify question."
    )
    trace: LLMTrace | None = Field(
        default=None,
        description="Detailed trace of input prompt, raw response, tokens, and latency"
    )


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ) -> None:
        self.model = model
        clean_base_url = base_url.strip() if (base_url and base_url.strip()) else None
        clean_api_key = api_key.strip() if (api_key and api_key.strip()) else None
        self.client = OpenAI(
            api_key=clean_api_key or "placeholder-key",
            base_url=clean_base_url,
        )

    def analyze_clarify_and_answer(
        self,
        user_query: str,
        existing_slots: dict[str, Any] | None = None,
        business_knowledge: list[str] | None = None,
        schema_context: str | None = None,
        chat_history: list[dict[str, str]] | None = None,
        is_follow_up: bool = False,
    ) -> ClarifyAnalysisResult:
        """
        Analyzes the user's query against Business Knowledge and ClickHouse Schema.
        Returns extracted slots, clarification requirements, ClickHouse SQL queries (if ready),
        and full LLM execution trace with token metrics.
        """
        system_prompt = (
            "Bạn là một Trợ lý AI Marketing Analytics chuyên nghiệp cho hệ thống Marketing của Viettel.\n"
            "Nhiệm vụ của bạn là dựa vào quy tắc Tri thức Nghiệp vụ (Business Knowledge) và Cấu trúc cơ sở dữ liệu ClickHouse (Schema Context) "
            "để phân tích câu hỏi của người dùng và sinh dữ liệu định dạng JSON chuẩn.\n\n"
            "CÁC QUY TẮC BẮT BUỘC:\n"
            "1. Xác định ý định người dùng và trích xuất các thực thể (slots) như: tên chiến dịch (`campaign_name` hoặc `program_code`), "
            "khoảng thời gian (`time_range`), kênh truyền thông (`channel` như SMS, MYVIETTEL, CALLBOT), nhóm độ tuổi (`age_group`), tỉnh thành (`province`).\n"
            "2. Nếu câu hỏi của người dùng còn THIẾU thông tin quan trọng cần thiết để truy vấn dữ liệu chính xác (ví dụ: người dùng hỏi 'Tỷ lệ nhắn tin thành công của chiến dịch tháng này' nhưng chưa nói rõ chiến dịch nào): "
            "   - Đặt `is_clarification_needed`: true\n"
            "   - Điền câu hỏi làm rõ tự nhiên, lịch sự vào `clarifying_question`.\n"
            "   - Điền danh sách 3-4 lựa chọn gợi ý cụ thể vào `suggested_options` (ví dụ: ['Chiến dịch 5G', 'Chiến dịch DATA', 'Chiến dịch Mua gói']).\n"
            "   - Liệt kê các slot còn thiếu vào `missing_slots` (ví dụ: ['campaign_name']).\n"
            "   - Để `generated_sqls`: [] (chưa sinh SQL khi thiếu thông tin).\n"
            "3. Nếu câu hỏi ĐÃ ĐỦ thông tin để truy vấn:\n"
            "   - Đặt `is_clarification_needed`: false\n"
            "   - `clarifying_question`: null\n"
            "   - `suggested_options`: []\n"
            "   - `missing_slots`: []\n"
            "   - Sinh danh sách các câu lệnh ClickHouse SQL SELECT tương ứng trong `generated_sqls` (mỗi câu lệnh có `id` như 'sql_1', 'sql_2', `title` mô tả ngắn, và `sql` là câu truy vấn ClickHouse hợp lệ, không chứa ký tự escape sai).\n"
            "4. ĐỊNH DẠNG JSON ĐẦU RA BẮT BUỘC:\n"
            "{\n"
            '  "is_clarification_needed": true/false,\n'
            '  "clarifying_question": "Câu hỏi làm rõ nếu cần hoặc null",\n'
            '  "suggested_options": ["Lựa chọn 1", "Lựa chọn 2"],\n'
            '  "extracted_entities": {"slot_name": "value"},\n'
            '  "missing_slots": ["slot_name"],\n'
            '  "suggested_answer": "Câu trả lời trực tiếp nếu không cần truy vấn DB hoặc null",\n'
            '  "generated_sqls": [\n'
            '     {"id": "sql_1", "title": "Mô tả câu truy vấn", "sql": "SELECT ... FROM ..."}\n'
            '  ],\n'
            '  "is_intent_switched": false\n'
            "}"
        )

        user_content = f"--- CÂU HỎI NGƯỜI DÙNG ---\n{user_query}\n\n"

        if is_follow_up and existing_slots:
            user_content += f"--- CÁC THÔNG TIN ĐÃ THU THẬP TRƯỚC ĐÓ ---\n{json.dumps(existing_slots, ensure_ascii=False)}\n\n"

        if business_knowledge:
            bk_text = "\n".join(f"- {k}" for k in business_knowledge)
            user_content += f"--- TRI THỨC NGHIỆP VỤ LIÊN QUAN (BUSINESS KNOWLEDGE RAG) ---\n{bk_text}\n\n"

        if schema_context:
            user_content += f"--- CẤU TRÚC BẢNG DỮ LIỆU CLICKHOUSE (SCHEMA CONTEXT) ---\n{schema_context}\n\n"

        if chat_history:
            history_text = "\n".join(
                f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in chat_history[-4:]
            )
            user_content += f"\n--- LỊCH SỬ CHAT ---\n{history_text}\n"

        input_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        t_start = time.perf_counter()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=input_messages,
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
            raw_text = response.choices[0].message.content or "{}"
            data = safe_parse_json(raw_text)

            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            total_tokens = getattr(usage, "total_tokens", 0) if usage else (prompt_tokens + completion_tokens)

            trace = LLMTrace(
                call_type="analyze_clarify_and_answer",
                model=self.model,
                input_messages=input_messages,
                raw_output=raw_text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
            )

            # Ensure existing slots are merged if LLM omitted them
            merged_slots = {**(existing_slots or {}), **data.get("extracted_entities", {})}
            data["extracted_entities"] = merged_slots

            # Ensure all required fields exist
            if "is_clarification_needed" not in data:
                data["is_clarification_needed"] = bool(data.get("clarifying_question"))
            if "suggested_options" not in data:
                data["suggested_options"] = []
            if "missing_slots" not in data:
                data["missing_slots"] = []
            if "suggested_answer" not in data or data.get("suggested_answer") is None:
                data["suggested_answer"] = ""
            if "clarifying_question" in data and data.get("clarifying_question") is None:
                data["clarifying_question"] = ""
            if "generated_sqls" not in data:
                data["generated_sqls"] = []

            # Handle backward compatibility for single generated_sql
            if not data["generated_sqls"] and data.get("generated_sql"):
                data["generated_sqls"] = [{"id": "sql_1", "title": "Truy vấn dữ liệu ClickHouse", "sql": data["generated_sql"]}]
            elif data["generated_sqls"] and not data.get("generated_sql"):
                data["generated_sql"] = data["generated_sqls"][0].get("sql")

            data["trace"] = trace
            return ClarifyAnalysisResult(**data)
        except Exception as e:
            logger.error("LLM call failed or returned invalid response: %s", e)
            raise RuntimeError(f"Lỗi gọi LLM API ({self.model}): {e}") from e

    def synthesize_answer_with_citations(
        self,
        user_query: str,
        collected_slots: dict[str, Any],
        sql_query_results: list[dict[str, Any]],
        business_knowledge: list[str] | None = None,
    ) -> tuple[str, LLMTrace]:
        """
        Takes raw SQL query results and formats the final answer, wrapping cited numbers/metrics
        with <cite id="sql_X">metric_value</cite> tags.
        Returns the formatted string and the LLMTrace with token metrics.
        """
        system_prompt = (
            "Bạn là một trợ lý AI Marketing Analytics chuyên nghiệp của Viettel.\n"
            "Nhiệm vụ của bạn là dựa vào kết quả truy vấn SQL thực tế từ Database ClickHouse và quy tắc Tri thức Nghiệp vụ "
            "để soạn thảo câu trả lời hoàn chỉnh, chính xác, tự nhiên, chuyên nghiệp cho người dùng.\n\n"
            "QUY TẮC BẮT BUỘC VỀ TRÍCH DẪN SỐ LIỆU (CITATIONS):\n"
            "1. Bất kỳ khi nào bạn trích dẫn một số liệu, tỉ lệ phần trăm, doanh thu, số lượng bản ghi hoặc dữ liệu tính toán từ câu truy vấn có mã `sql_X`, "
            "bạn PHẢI bọc chính xác cụm từ/số liệu đó trong thẻ `<cite id=\"sql_X\">số liệu</cite>`.\n"
            "   - Ví dụ: 'Doanh thu chiến dịch đạt <cite id=\"sql_1\">3.500.000.000 VNĐ</cite> với tỷ lệ gửi thành công là <cite id=\"sql_2\">98.7%</cite>.'\n"
            "   - Ví dụ: 'Tổng số <cite id=\"sql_1\">15.420</cite> thuê bao đã mua gói cước thành công.'\n"
            "2. Trình bày số liệu rõ ràng, dễ hiểu, format số hàng nghìn bằng dấu chấm (ví dụ: 1.000.000) và giữ giọng điệu chuyên nghiệp.\n"
            "3. Không tự bịa số liệu nếu trong kết quả query không có. Nếu query không có dữ liệu (kết quả rỗng), hãy thông báo rõ ràng là chưa ghi nhận số liệu trong khoảng thời gian này.\n"
            "4. Trả về trực tiếp nội dung văn bản câu trả lời (Markdown), KHÔNG bọc trong JSON."
        )

        results_formatted = []
        for item in sql_query_results:
            sql_id = item.get("id", "sql_1")
            sql_title = item.get("title", "Truy vấn")
            sql_code = item.get("sql", "")
            raw_res = item.get("result", [])
            results_formatted.append(
                f"### Nguồn [{sql_id}] - {sql_title}:\n"
                f"SQL: {sql_code}\n"
                f"Kết quả trả về từ DB: {json.dumps(raw_res, ensure_ascii=False, default=str)}\n"
            )

        results_str = "\n".join(results_formatted)
        slots_str = json.dumps(collected_slots or {}, ensure_ascii=False)

        user_content = (
            f"--- YÊU CẦU NGƯỜI DÙNG ---\n"
            f"User Query: {user_query}\n"
            f"Collected Slots: {slots_str}\n\n"
            f"--- KẾT QUẢ TRUY VẤN TỪ DATABASE CLICKHOUSE ---\n"
            f"{results_str}\n"
        )

        if business_knowledge:
            bk_text = "\n".join(f"- {k}" for k in business_knowledge)
            user_content += f"\n--- QUY TẮC NGHIỆP VỤ ---\n{bk_text}\n"

        input_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        t_start = time.perf_counter()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=input_messages,
                temperature=0.2,
            )
            latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
            raw_text = (response.choices[0].message.content or "").strip()

            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            total_tokens = getattr(usage, "total_tokens", 0) if usage else (prompt_tokens + completion_tokens)

            trace = LLMTrace(
                call_type="synthesize_answer_with_citations",
                model=self.model,
                input_messages=input_messages,
                raw_output=raw_text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
            )

            return raw_text, trace
        except Exception as e:
            latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
            logger.error("Failed to synthesize answer with citations: %s", e)
            fallback_text = "Đã ghi nhận dữ liệu truy vấn từ hệ thống."
            trace = LLMTrace(
                call_type="synthesize_answer_with_citations",
                model=self.model,
                input_messages=input_messages,
                raw_output=f"Error: {e}",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                latency_ms=latency_ms,
            )
            return fallback_text, trace


