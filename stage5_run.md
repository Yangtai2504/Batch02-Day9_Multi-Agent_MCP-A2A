# Stage 5 — Demo Guide

## Chuẩn bị trước khi demo

Mở 2 terminal. Terminal 1 khởi động hệ thống, Terminal 2 chạy demo.

**Terminal 1 — Khởi động toàn bộ hệ thống:**

```powershell
cd "C:\VinAI\Lab coding\Batch02-Day9_Multi-Agent_MCP-A2A"
.\start_all.ps1
```

Chờ 5 cửa sổ:
- Registry `:18000`
- Customer Agent `:10100`
- Law Agent `:10101`
- Tax Agent `:10102`
- Compliance Agent `:10103`

**Terminal 2 — Chạy demo:**

```powershell
cd "C:\VinAI\Lab coding\Batch02-Day9_Multi-Agent_MCP-A2A"
uv run python demo_stage5.py
```

---

## Demo chạy theo 3 phase, nhấn Enter để chuyển phase

---

### Phase 1 — Baseline Architecture

Script in ra sơ đồ luồng **trước khi optimize**:

```
Client
  │
  ▼  (1) gửi câu hỏi
Customer Agent :10100
  │
  ▼  (2) analyze_law  ──────────────── ~25s
Law Agent :10101
  │
  ▼  (3) check_routing (LLM call) ──── ~8s  ← LÃN PHÍ
  │
  ├──▶ call_tax         ──────────────── ~25s
  │         (chờ xong mới chạy)
  └──▶ call_compliance  ──────────────── ~25s

Tổng: 25 + 8 + 25 + 25 = ~83–90s  (sequential)
```

**Điểm nói khi demo:**
- `check_routing` gọi thêm 1 LLM call chỉ để quyết định routing → lãng phí ~8s
- Tax và Compliance chạy **sau** analyze_law, không song song → cộng dồn latency
- Baseline đo được: **87.86s**

---

### Phase 2 — Live Latency Measurement

Script gửi 1 request thật đến hệ thống và đo thời gian end-to-end.

In ra mỗi 5 giây một dòng để thấy hệ thống đang xử lý:

```
... 5s elapsed
... 10s elapsed
... 15s elapsed
...
```

Kết thúc in bảng kết quả:

```
┌──────────────────────────────────────────┐
│                                          │
│   Latency đo thực tế:    67.xx s         │
│   (End-to-end: Client → hệ thống → Client)│
│                                          │
└──────────────────────────────────────────┘
```

---

### Phase 3 — Optimization & So Sánh

Script giải thích phương án tối ưu và in bảng so sánh.

**Phương án: Parallel Dispatch từ START**

```
BEFORE:
START → analyze_law → check_routing (LLM) → call_tax
                                           → call_compliance

AFTER:
START ──┬──▶ analyze_law      (chạy song song)
        ├──▶ call_tax          (chạy song song)
        └──▶ call_compliance   (chạy song song)
                  │
                  ▼
              aggregate → END
```

**Code thay đổi trong `law_agent/graph.py`:**

```python
def dispatch_all_parallel(state):
    return [
        Send("analyze_law", state),
        Send("call_tax", state),
        Send("call_compliance", state),
    ]

graph.add_conditional_edges(
    "__start__", dispatch_all_parallel,
    ["analyze_law", "call_tax", "call_compliance"]
)
```

**Bảng so sánh in ra:**

```
Phiên bản               Latency   Bar
──────────────────────────────────────────────────────────────
Baseline  (sequential)    87.9s   ████████████████████████████████████████
Optimized (parallel)      67.x s  █████████████████████████████████

Tiết kiệm: ~20s  (23% nhanh hơn)

• Xóa 1 LLM call thừa (check_routing): tiết kiệm ~8s
• 3 nhánh chạy song song thay vì tuần tự: tiết kiệm thêm ~20s
• Tổng: ~20s (23%) nhanh hơn baseline
```

---

## Nếu chỉ muốn chạy nhanh không cần demo step-by-step

```powershell
uv run python demo_latency.py
```

In thẳng kết quả so sánh:

```
═══════════════════════════════════════════════════════
  LATENCY DEMO — A2A Multi-Agent System
═══════════════════════════════════════════════════════
[OPTIMIZED (parallel)] Done in 67.xx s

═══════════════════════════════════════════════════════
  RESULT SUMMARY
═══════════════════════════════════════════════════════
  Baseline  (sequential):  87.9s
  Optimized (parallel):    67.x s
  Saved:                   ~20.x s  (23% faster)
═══════════════════════════════════════════════════════
```

---

## Kiến trúc hệ thống (để show khi giới thiệu)

```
                    ┌─────────────────────────────────┐
                    │         REGISTRY  :18000         │
                    │   (service discovery + registry) │
                    └────────────┬────────────────────┘
                                 │ agents đăng ký khi khởi động
          ┌──────────────────────┼──────────────────────┐
          │                      │                       │
   ┌──────┴──────┐        ┌──────┴──────┐        ┌──────┴──────┐
   │  Tax Agent  │        │  Law Agent  │        │ Compliance  │
   │   :10102    │        │   :10101    │        │   :10103    │
   └─────────────┘        └──────┬──────┘        └─────────────┘
                                 │ delegate + trace_id
                          ┌──────┴──────┐
                          │  Customer   │
                          │   Agent     │
                          │   :10100    │
                          └──────┬──────┘
                                 │ A2A HTTP
                            test_client.py
```

- **trace_id** được tạo tại Customer Agent, truyền xuyên suốt đến Tax + Compliance
- **fault tolerance**: nếu Tax Agent chết, Law Agent fallback gracefully, hệ thống vẫn trả lời
- **parallel dispatch**: Law Agent gọi 3 nodes cùng lúc via LangGraph `Send` API
