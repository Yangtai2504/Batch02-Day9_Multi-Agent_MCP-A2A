# Stage 5 — Nộp Bài Tập 5.1 / 5.2 / 5.3

---

## Bài Tập 5.1 — Trace Request Flow (Sequence Diagram)

**Yêu cầu:** Tìm `trace_id` trong logs, theo dõi request đi qua các agents, vẽ sequence diagram.

### Sequence Diagram

```
Client (test_client.py)
    │
    │  POST /message  (câu hỏi pháp lý)
    ▼
Customer Agent :10100
    │  trace_id = "abc-123" được tạo tại đây
    │
    │  discover("law_question") → Registry :18000
    │  POST /message  [metadata: trace_id="abc-123", depth=1]
    ▼
Law Agent :10101
    │  Nhận trace_id từ metadata, tiếp tục truyền xuống
    │
    │  [Parallel dispatch via LangGraph Send API]
    ├──────────────────────────────────────────────┐
    │                                              │
    │  discover("tax_question")                    │  discover("compliance_question")
    │  POST /message [trace_id="abc-123", depth=2] │  POST /message [trace_id="abc-123", depth=2]
    ▼                                              ▼
Tax Agent :10102                        Compliance Agent :10103
    │  Xử lý, trả lời                       │  Xử lý, trả lời
    │                                       │
    └──────────────┬────────────────────────┘
                   │  Cả 2 kết quả về cùng lúc
                   ▼
           Law Agent (aggregate node)
               │  Tổng hợp 3 phần: law + tax + compliance
               │  Trả về final_answer
               ▼
       Customer Agent
               │  Format response
               ▼
           Client  ✅
```

### trace_id truyền như thế nào?

Mỗi khi Law Agent gọi Tax Agent hoặc Compliance Agent qua A2A, nó đính kèm `trace_id` vào metadata của request:

```python
# common/a2a_client.py
metadata = {
    "trace_id": trace_id,        # giữ nguyên xuyên suốt
    "delegation_depth": depth,   # tăng dần: 0 → 1 → 2
    "context_id": context_id,
}
```

Kết quả: tất cả log từ 5 services đều có cùng `trace_id` → dễ debug và theo dõi 1 request end-to-end.

---

## Bài Tập 5.2 — Test Dynamic Discovery (Fault Tolerance)

**Yêu cầu:** Dừng Tax Agent, chạy lại `test_client.py`, quan sát cách hệ thống xử lý lỗi.

### Các bước thực hiện

1. Kill Tax Agent (đang chạy ở port 10102)
2. Chạy `uv run python test_client.py`

### Kết quả quan sát

Hệ thống **vẫn trả lời được** — không crash, không báo lỗi ra client.

Law Agent bắt exception khi Tax Agent không phản hồi và tự động fallback:

```python
# law_agent/graph.py — node call_tax
async def call_tax(state: LawState) -> dict:
    try:
        endpoint = await discover("tax_question")   # Registry trả về lỗi: không tìm thấy agent
        result = await delegate(...)
        return {"tax_result": result}
    except Exception as exc:
        return {"tax_result": f"[Tax analysis unavailable: {exc}]"}  # fallback
```

Response cuối vẫn bao gồm phần Law Analysis + Compliance Analysis, chỉ thiếu Tax Analysis:

```
## Tax Analysis
[Tax analysis unavailable: No agent found for task 'tax_question']

## Regulatory Compliance Analysis
... (vẫn đầy đủ)
```

**Kết luận:** Hệ thống đạt fault tolerance — 1 agent chết không kéo sập toàn bộ hệ thống.

---

## Bài Tập 5.3 — Modify Agent Behavior (System Prompt)

**Yêu cầu:** Sửa `tax_agent/graph.py`, thay đổi system prompt để agent trả lời ngắn gọn hơn. Restart và test lại.

### Thay đổi trong `tax_agent/graph.py`

Thêm 2 dòng cuối vào `TAX_SYSTEM_PROMPT`:

```python
# TRƯỚC (không có):
Always note that your response is for educational purposes...

# SAU (thêm vào):
Always note that your response is for educational purposes...

IMPORTANT: Trả lời ngắn gọn, súc tích trong tối đa 3-5 gạch đầu dòng.
Tránh giải thích dài dòng — chỉ nêu những điểm pháp lý quan trọng nhất.
```

### Kết quả trước khi sửa

Tax Agent trả về response dài ~500 từ, nhiều section, bullet points lồng nhau.

### Kết quả sau khi sửa (test trực tiếp Tax Agent tại port 10102)

```
Đây là những điểm pháp lý quan trọng nhất:

• Trách nhiệm dân sự: Phạt liên quan đến độ chính xác (IRC § 6662, 20%) hoặc
  phạt gian lận dân sự (IRC § 6663, 75% số thuế thiếu), cộng với lãi suất.

• Trách nhiệm hình sự: Nếu cố ý (18 U.S.C. § 7201), công ty bị phạt đến
  $500.000, cá nhân phạt $100.000 và tối đa 5 năm tù cho mỗi tội danh.

• Cơ quan xử lý: IRS (Criminal Investigation) điều tra, DOJ (Tax Division)
  truy tố. Giám đốc/cán bộ chỉ đạo hành vi có thể chịu trách nhiệm hình sự cá nhân.

• Thời hiệu: Không có thời hiệu với tờ khai gian lận; 6 năm với khai thiếu.

*Lưu ý: Phản hồi này chỉ mang tính giáo dục. Cần tư vấn luật sư cho trường hợp cụ thể.*
```

**Kết luận:** Thay đổi system prompt có hiệu lực ngay sau khi restart agent — response ngắn gọn, đúng format yêu cầu.

---

## Tóm Tắt

| Bài | Yêu cầu | Kết quả |
|-----|---------|---------|
| 5.1 | Vẽ sequence diagram theo trace_id | Vẽ xong, trace_id truyền qua 4 agents: Customer → Law → Tax/Compliance |
| 5.2 | Kill Tax Agent, test fault tolerance | Hệ thống vẫn chạy, fallback gracefully, client nhận được response |
| 5.3 | Sửa system prompt cho ngắn gọn | Tax Agent trả về 4 bullet points thay vì response dài 500 từ |
