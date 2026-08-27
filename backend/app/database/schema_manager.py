from __future__ import annotations

import logging
from typing import Any
from app.vectorstores.base import BaseVectorStore

logger = logging.getLogger(__name__)

# Complete schema descriptions for the 4 core marketing tables
TABLE_SCHEMAS: dict[str, dict[str, Any]] = {
    "f023_mpre_vas_manh": {
        "description": "Bảng log mua gói cước VAS của thuê bao.",
        "ddl": """CREATE TABLE f023_mpre_vas_manh (
    topic_kafka Nullable(String),
    filename Nullable(String),
    prd_id Nullable(UInt32),
    hour_id Nullable(String),
    import_date Nullable(Date),
    headnum_no Nullable(String),
    isdn String, -- Số điện thoại thuê bao mua gói (bỏ số 0 đầu, ví dụ 8498xxxxxxx hoặc 98xxxxxxx)
    vas_type Nullable(String), -- Loại VAS (VIETTEL, DK_OTHER, VTFREE, 2G3G,...)
    vas_service Nullable(String), -- Dịch vụ VAS (HUY T15K, DK_OTHER, SMARTMOTO,...)
    sub_service Nullable(String), -- Tên gói cước chi tiết (HGG100, CT50, DT50, 5G150, SD30S,...)
    action_no Nullable(String), -- Hành động: DK (Đăng ký), KT (Kiểm tra)
    action_no2 Nullable(String),
    vas_status Nullable(String),
    command Nullable(String), -- Cú pháp nhắn tin (KTS5, FT5, VT100,...)
    command2 Nullable(String),
    charge_type Nullable(String),
    sta_datetime Nullable(DateTime), -- Thời điểm mua / đăng ký gói
    org_charge Nullable(Float64), -- Giá gốc
    prom_charge Nullable(Float64), -- Giá khuyến mại
    tot_charge Nullable(Float64), -- Tổng cước phí thực tế
    party_code Nullable(String),
    description Nullable(String), -- Mô tả (S5, VT100, Trừ phí gia hạn gói 5G10,...)
    source_name Nullable(String),
    direction_id Nullable(Float64),
    insert_date Nullable(DateTime),
    mm_charge Nullable(Float64),
    mon Nullable(String),
    partition UInt32 -- Partition ngày dạng YYYYMMDD (vd: 20260801)
) ENGINE = MergeTree()
PARTITION BY partition
ORDER BY (partition, isdn);""",
    },
    "webservice_log_v2_manh": {
        "description": "Bảng ghi log truyền thông các kênh webservice (MyViettel, Callbot).",
        "ddl": """CREATE TABLE webservice_log_v2_manh (
    isdn String, -- Số điện thoại thuê bao nhận truyền thông
    campaign_action_id Nullable(UInt64),
    webservice Nullable(String),
    url Nullable(String),
    request_time String, -- Thời gian gửi tin (định dạng YYYYMMDDHHMMSS)
    request Nullable(String), -- Nội dung bản tin gửi (XML/JSON body)
    response_time Nullable(String), -- Thời gian phản hồi webservice
    response Nullable(String),
    status Nullable(String), -- Trạng thái gửi: status = '1' đối với kênh MYVIETTEL thành công, status = '200' đối với CALLBOT thành công
    campaign_id Nullable(UInt64), -- Mã chiến dịch Marketing
    filed1 Nullable(String),
    mode Nullable(String),
    partition UInt32 -- Partition ngày dạng YYYYMMDD
) ENGINE = MergeTree()
PARTITION BY partition
ORDER BY (partition, isdn, request_time);""",
    },
    "sms_log_v2": {
        "description": "Bảng ghi log truyền thông kênh tin nhắn SMS.",
        "ddl": """CREATE TABLE sms_log_v2 (
    msisdn String, -- Số điện thoại thuê bao nhận SMS (tương đương isdn)
    action_id Nullable(UInt64),
    sender Nullable(String), -- Đầu số / Brandname gửi (vd: VIETTEL_KM)
    send_time String, -- Thời gian gửi tin nhắn (định dạng YYYYMMDDHHMMSS)
    status Nullable(String), -- Trạng thái gửi: status = '0' là gửi tin nhắn SMS thành công
    gateway Nullable(Int64),
    duration Nullable(Int64),
    transaction_id Nullable(String),
    campaign_id Nullable(UInt64), -- Mã chiến dịch Marketing
    history_id Nullable(String),
    type Nullable(String),
    partition UInt32 -- Partition ngày dạng YYYYMMDD
) ENGINE = MergeTree()
PARTITION BY partition
ORDER BY (partition, msisdn, send_time);""",
    },
    "f_adpm_aimkt_campaign_customer_detail": {
        "description": "Bảng chi tiết danh sách khách hàng mục tiêu và cấu hình chiến dịch Marketing.",
        "ddl": """CREATE TABLE f_adpm_aimkt_campaign_customer_detail (
    msisdn String, -- Số điện thoại thuê bao (tương đương isdn)
    program_code Nullable(String), -- Mã chương trình / campaign
    vas_name Nullable(String), -- Tên gói cước khuyến nghị (5G50, MT7Z, 5GMAX, 5G70,...)
    channel Nullable(String), -- Kênh truyền thông khuyến nghị: SMS, MYVIETTEL, CALLBOT
    event_time Nullable(String), -- Khung giờ truyền thông (10h, 16h, 21h,...)
    cdr_name Nullable(String),
    group_flag Nullable(String), -- Nhóm thử nghiệm: TG (Target Group), CONTROL (Nhóm đối chứng)
    cust_age Nullable(String), -- Nhóm độ tuổi khách hàng: hoc sinh, sinh vien, lao dong tre, trung nien, cao tuoi
    province_code_home Nullable(String), -- Mã tỉnh thành: HCM, CTO, SLA, QNI, HUE, CMU, HNI,...
    trangthai_truyenthong Nullable(String), -- Trạng thái: tttc (truyền thông thành công), ko_tttc
    promo_label Nullable(String),
    chu_ky_goi Nullable(String),
    price Nullable(Float64),
    tieu_dung_chinh Nullable(String),
    ten_usecase Nullable(String), -- Tên usecase chiến dịch
    partition UInt32 -- Partition ngày dạng YYYYMMDD
) ENGINE = MergeTree()
PARTITION BY partition
ORDER BY (partition, msisdn);""",
    },
}


class SchemaManager:
    def __init__(
        self,
        enable_schema_rag: bool = False,
        schema_vector_store: BaseVectorStore | None = None,
    ) -> None:
        self.enable_schema_rag = enable_schema_rag
        self.schema_vector_store = schema_vector_store

    def get_all_schemas_text(self) -> str:
        """Returns full DDL and comments of all available tables."""
        parts = []
        for table_name, data in TABLE_SCHEMAS.items():
            parts.append(f"-- Table: {table_name}\n-- Mô tả: {data['description']}\n{data['ddl']}\n")
        return "\n".join(parts)

    def get_schema_context(self, user_query: str = "", top_k: int = 4) -> str:
        """
        Pluggable Schema Context Provider:
        - Default (Direct): Returns all active table schemas into Prompt.
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
                if table_name and table_name in TABLE_SCHEMAS:
                    data = TABLE_SCHEMAS[table_name]
                    relevant_tables.append(f"-- Table: {table_name}\n-- Mô tả: {data['description']}\n{data['ddl']}\n")

            if not relevant_tables:
                return self.get_all_schemas_text()

            return "\n".join(relevant_tables)
        except Exception as e:
            logger.warning("Schema RAG search failed, falling back to full schemas: %s", e)
            return self.get_all_schemas_text()
