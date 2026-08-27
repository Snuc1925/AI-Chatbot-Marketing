# Hướng Dẫn & Báo Cáo Kiểm Thử (Pure Business Knowledge RAG)

Tài liệu này ghi lại các lệnh `curl` và `docker` thực tế để bạn kiểm thử luồng hoạt động mới sau khi **bỏ hoàn toàn Scenarios RAG** và chuyển sang **Pure Business Knowledge RAG (`business_knowledge.json`)**.

---

## 1. Đồng Bộ Tri Thức Nghiệp Vụ (Knowledge Sync API)

Đồng bộ 7 quy tắc tri thức từ file `backend/business_knowledge.json` vào Qdrant (Collection: `business_knowledge`):

```bash
curl -s -X POST http://localhost:8000/api/knowledge/sync \
  -H "Content-Type: application/json" \
  -d '{"force_reset": true}'
```

**Kết quả:**
```json
{
  "status": "success",
  "synced_count": 7,
  "total_count": 7
}
```

---

## 2. Kiểm thử Luồng Hội Thoại Động (Dynamic Clarification & Multi-SQL)

### Lượt 1: Gửi câu hỏi ban đầu (Thiếu tên chiến dịch ➡️ AI tự hỏi làm rõ)

```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tỷ lệ gửi SMS thành công của chiến dịch tháng này"
  }'
```

*Phản hồi mẫu:*
- `response_type: "clarify"`
- `message`: *"Bạn muốn xem tỷ lệ gửi SMS thành công của chiến dịch cụ thể nào trong tháng này? Vui lòng cho biết tên chiến dịch hoặc mã chương trình (program_code) để tôi tra cứu chính xác."*
- `missing_slots`: `["campaign_name"]`
- `suggested_options`: `["Chiến dịch 5G", "Chiến dịch DATA", "Chiến dịch VAS"]`

---

### Lượt 2: Bổ sung tên chiến dịch ➡️ AI sinh 3 câu SQL ClickHouse ➡️ Thực thi DB ➡️ Gắn Citations

```bash
# Thay SESSION_ID bằng session_id nhận được từ Lượt 1
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "query": "Chiến dịch KhuyenMai_4G"
  }'
```

*Phản hồi mẫu:*
- `response_type: "answer"`
- `message`:
  > - Tổng số thuê bao mục tiêu: `<cite id="sql_1">0 thuê bao</cite>`.
  > - Số thuê bao nhận tin SMS thành công: `<cite id="sql_2">0 thuê bao</cite>`.
  > - Số thuê bao mua gói: `<cite id="sql_3">0 thuê bao</cite>`.
  > - Tổng doanh thu: `<cite id="sql_3">0 VNĐ</cite>`.
- `citations`: Mảng chứa 3 query SQL độc lập (`sql_1`: 37ms, `sql_2`: 13ms, `sql_3`: 12ms) kèm kết quả DB thực tế.

---

## 3. Các Lệnh Tiện ích Khác

```bash
# Kiểm tra danh sách tri thức đang lưu trong hệ thống
curl -s http://localhost:8000/api/knowledge

# Kiểm tra sức khỏe hệ thống & kết nối ClickHouse
curl -s http://localhost:8000/api/health

# Xem bảng ClickHouse
curl -s http://localhost:8000/api/clickhouse/tables
```
