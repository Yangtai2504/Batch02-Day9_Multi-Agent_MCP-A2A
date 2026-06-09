# Lab Solution — Xây Dựng Hệ Thống Multi-Agent với A2A Protocol

---

## Phần 1: Direct LLM Calling

### Lý Thuyết

LLM ở dạng cơ bản nhất là API nhận text → trả về text. Không có memory, không có tools.

**Ưu điểm:** Đơn giản, nhanh. **Nhược điểm:** Không có kiến thức real-time, không tra cứu được database.

### Thực Hành — Chạy Stage 1

```bash
uv run python stages/stage_1_direct_llm/main.py
```

---

### Bài Tập 1.1 — Thay đổi câu hỏi

Sửa biến `QUESTION` trong `stages/stage_1_direct_llm/main.py`:

```python
# TRƯỚC
QUESTION = "What are the legal consequences of a contract breach?"

# SAU (câu hỏi tiếng Việt)
QUESTION = "Một công ty startup tại Việt Nam vi phạm hợp đồng với đối tác nước ngoài và không nộp thuế thu nhập doanh nghiệp. Hậu quả pháp lý là gì?"
```

**Code đầy đủ `stages/stage_1_direct_llm/main.py`:**

```python
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from common.llm import get_llm

QUESTION = "Một công ty startup tại Việt Nam vi phạm hợp đồng với đối tác nước ngoài và không nộp thuế thu nhập doanh nghiệp. Hậu quả pháp lý là gì?"

async def main():
    llm = get_llm()
    messages = [
        SystemMessage(content="You are a legal expert. Provide a clear, concise analysis. Keep your response under 300 words."),
        HumanMessage(content=QUESTION),
    ]
    response = await llm.ainvoke(messages)
    print(response.content)

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
```

---

### Bài Tập 1.2 — Thêm temperature control

Sửa `common/llm.py`, thêm `temperature=0.3`:

```python
def get_llm() -> ChatVertexAI:
    return ChatVertexAI(
        model=os.getenv("VERTEX_MODEL", "gemini-2.5-flash"),
        project=os.getenv("VERTEX_PROJECT", "vinuni-project"),
        location=os.getenv("VERTEX_LOCATION", "us-central1"),
        temperature=0.3,   # ← thêm dòng này
        model_kwargs={"thinking_config": {"thinking_budget": 0}},
    )
```

**Tại sao:** `temperature=0` → rất deterministic (lặp lại cùng output). `temperature=1` → sáng tạo hơn nhưng không ổn định. `0.3` là điểm cân bằng tốt cho legal analysis.

---

## Phần 2: LLM + RAG & Tools

### Lý Thuyết

- **RAG:** LLM tra cứu knowledge base trước khi trả lời
- **Tools:** Functions LLM có thể gọi (`@tool` decorator)
- **Flow:** LLM nhận câu hỏi + danh sách tools → quyết định gọi tool → tool execute → LLM nhận kết quả → trả lời

### Chạy Stage 2

```bash
uv run python stages/stage_2_rag_tools/main.py
```

---

### Bài Tập 2.1 — Thêm knowledge base entry

Thêm vào `LEGAL_KNOWLEDGE` trong `stages/stage_2_rag_tools/main.py`:

```python
{
    "id": "labor_law",
    "keywords": ["lao động", "sa thải", "hợp đồng lao động", "labor", "termination", "employment"],
    "text": (
        "Theo Bộ luật Lao động Việt Nam 2019, người sử dụng lao động có thể "
        "đơn phương chấm dứt hợp đồng trong các trường hợp: (1) người lao động "
        "thường xuyên không hoàn thành công việc; (2) bị ốm đau, tai nạn đã điều trị "
        "12 tháng chưa khỏi; (3) thiên tai, hỏa hoạn; (4) người lao động đủ tuổi nghỉ hưu. "
        "Vi phạm thủ tục sa thải có thể bị buộc nhận lại người lao động và bồi thường "
        "ít nhất 2 tháng lương theo Điều 41 BLLĐ 2019."
    ),
},
```

---

### Bài Tập 2.2 — Tạo tool mới `check_statute_of_limitations`

```python
from langchain_core.tools import tool

@tool
def check_statute_of_limitations(case_type: str) -> str:
    """Kiểm tra thời hiệu khởi kiện theo loại vụ án.

    Args:
        case_type: Loại vụ án (contract, tort, property, labor)
    """
    limits = {
        "contract": "4 năm (UCC § 2-725)",
        "tort": "2-3 năm tùy bang",
        "property": "5 năm",
        "labor": "1 năm kể từ ngày chấm dứt hợp đồng (BLLĐ 2019 Điều 190)",
    }
    return limits.get(case_type.lower(), "Không xác định — cần tư vấn chuyên gia pháp lý")

# Thêm vào danh sách tools:
TOOLS = [search_legal_database, calculate_damages, check_statute_of_limitations]
```

---

## Phần 3: Single Agent với ReAct

### Lý Thuyết

**ReAct = Reasoning + Acting**

Agent tự động lặp: **Think** (quyết định tool) → **Act** (gọi tool) → **Observe** (nhận kết quả) → lặp lại cho đến khi có đủ thông tin.

`create_react_agent` từ LangGraph tự động hóa toàn bộ vòng lặp này.

### Chạy Stage 3

```bash
uv run python stages/stage_3_single_agent/main.py
```

---

### Bài Tập 3.1 — Thêm tool `search_case_law`

```python
@tool
def search_case_law(keywords: str) -> str:
    """Tìm kiếm án lệ theo từ khóa.

    Args:
        keywords: Từ khóa tìm kiếm (ví dụ: breach, negligence, contract)
    """
    cases = {
        "breach": "Hadley v. Baxendale (1854) - Consequential damages must be foreseeable at time of contracting.",
        "negligence": "Donoghue v. Stevenson (1932) - Established modern duty of care in negligence law.",
        "contract": "Carlill v. Carbolic Smoke Ball Co (1893) - Unilateral contract accepted by performance.",
        "nda": "PepsiCo Inc. v. Redmond (1995) - Trade secrets and inevitable disclosure doctrine.",
        "privacy": "Spokeo Inc. v. Robins (2016) - Standing requires concrete injury.",
        "tax": "Gregory v. Helvering (1935) - Substance over form doctrine in tax law.",
    }
    results = [case for key, case in cases.items() if key in keywords.lower()]
    return "\n".join(results) if results else "Không tìm thấy án lệ phù hợp"

TOOLS = [search_legal_database, calculate_penalty, check_compliance_requirements, search_case_law]
```

---

### Bài Tập 3.2 — Debug agent reasoning

```python
from langgraph.prebuilt import create_react_agent

llm = get_llm()
# verbose=True không có trong create_react_agent — dùng astream để xem từng step:
graph = create_react_agent(model=llm, tools=TOOLS, prompt=SYSTEM_PROMPT)

async for chunk in graph.astream(inputs, stream_mode="updates"):
    for node_name, update in chunk.items():
        print(f"\n[Node: {node_name}]")
        for msg in update.get("messages", []):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print(f"  → THINK+ACT: {[tc['name'] for tc in msg.tool_calls]}")
            elif msg.type == "tool":
                print(f"  → OBSERVE: {msg.content[:200]}")
            elif msg.type == "ai" and msg.content:
                print(f"  → FINAL: {msg.content[:300]}")
```

---

## Phần 4: Multi-Agent In-Process

### Lý Thuyết

- **StateGraph:** Định nghĩa state chia sẻ + nodes + edges
- **Send API:** Dispatch nhiều tasks song song
- Mỗi agent tập trung vào domain riêng (law / tax / compliance / privacy)

### Chạy Stage 4

```bash
uv run python stages/stage_4_milti_agent/main.py
```

---

### Bài Tập 4.1 — Thêm `privacy_agent`

```python
async def call_privacy_specialist(state: LegalState) -> dict:
    """Privacy specialist chuyên về GDPR và bảo vệ dữ liệu cá nhân."""
    from langgraph.prebuilt import create_react_agent

    privacy_prompt = (
        "You are a data privacy attorney specialising in GDPR, CCPA/CPRA, and global data protection law. "
        "Analyse data privacy implications including consent, data breach notification, cross-border transfers, "
        "and fines (GDPR up to 4% global revenue, CCPA up to $7,500 per violation). "
        "Keep your response under 200 words."
    )
    llm = get_llm()
    agent = create_react_agent(model=llm, tools=[], prompt=privacy_prompt)
    result = await agent.ainvoke({"messages": [{"role": "user", "content": state["question"]}]})
    return {"privacy_result": extract_text(result["messages"][-1].content)}
```

Thêm vào `LegalState`:

```python
class LegalState(TypedDict):
    question: str
    law_analysis: str
    needs_tax: bool
    needs_compliance: bool
    needs_privacy: bool          # ← thêm
    tax_result: Annotated[str, _last_wins]
    compliance_result: Annotated[str, _last_wins]
    privacy_result: Annotated[str, _last_wins]   # ← thêm
    final_answer: str
```

Thêm vào graph:

```python
graph.add_node("call_privacy_specialist", call_privacy_specialist)
graph.add_edge("call_privacy_specialist", "aggregate")
```

---

### Bài Tập 4.2 — Conditional routing (keyword-based)

```python
def route_to_specialists(state: LegalState) -> list[Send]:
    question_lower = state["question"].lower()
    sends = []

    if state.get("needs_tax") or any(kw in question_lower for kw in ["tax", "irs", "thuế", "fbar", "fatca"]):
        sends.append(Send("call_tax_specialist", state))

    if state.get("needs_compliance") or any(kw in question_lower for kw in ["compliance", "sec", "sox", "regulation", "fcpa"]):
        sends.append(Send("call_compliance_specialist", state))

    if state.get("needs_privacy") or any(kw in question_lower for kw in ["data", "privacy", "gdpr", "ccpa", "dữ liệu"]):
        sends.append(Send("call_privacy_specialist", state))

    return sends if sends else [Send("aggregate", state)]
```

---

## Phần 5: Distributed A2A System

### Lý Thuyết

**A2A Protocol:** Mỗi agent là 1 service độc lập, giao tiếp qua HTTP.

```
Registry :18000  ← agents đăng ký khi khởi động
    ↓
Customer Agent :10100 → Law Agent :10101
                              ↓ parallel dispatch
                  Tax Agent :10102   Compliance Agent :10103
```

**Khác biệt với Stage 4:**
- Mỗi agent là process riêng (có thể scale độc lập)
- Dynamic discovery qua Registry
- `trace_id` truyền xuyên suốt để debug end-to-end

### Chạy Stage 5

```powershell
# Khởi động hệ thống
powershell -ExecutionPolicy Bypass -File ".\start_all.ps1"

# Test
uv run python test_client.py
```

---

### Bài Tập 5.1 — Trace Request Flow

**Sequence Diagram — trace_id propagation qua log thực tế:**

```
trace_id = "7c734c75-5920-4c73-9a3b-a95f4023b500"

test_client.py
    │  t=0s  gửi câu hỏi
    ▼
Customer Agent :10100
    │  t=+0s   tạo trace_id, depth=0
    │  t=+4s   discover("law_question") → Registry :18000
    │  t=+4s   POST /message [trace_id, depth=1]
    ▼
Law Agent :10101
    │  t=+4s   nhận request, khởi động LangGraph StateGraph
    │           dispatch_all_parallel() → 3 nodes cùng lúc:
    │
    ├─────────────────────────────────────────────┐
    │  discover("tax_question")                   │  discover("compliance_question")
    │  POST [trace_id, depth=2]                   │  POST [trace_id, depth=2]
    ▼  t=+5s                                      ▼  t=+5s
Tax Agent :10102                      Compliance Agent :10103
    │  t=+15s  trả lời (~10s)              │  t=+34s  trả lời (~29s)
    └──────────────────┬───────────────────┘
                       ▼
           Law Agent — aggregate node
               │  t=+34s → +59s  LLM tổng hợp (~25s)
               ▼
       Customer Agent
               │  t=+59s → +73s  xử lý + format (~13s)
               ▼
           test_client.py  ✅  t=+73s
```

**trace_id truyền qua `common/a2a_client.py`:**

```python
metadata = {
    "trace_id": trace_id,        # giữ nguyên xuyên suốt
    "delegation_depth": depth,   # tăng: 0 → 1 → 2
    "context_id": context_id,
}
```

Kết quả: tất cả logs từ 5 services đều có cùng `trace_id` → dễ trace 1 request end-to-end.

---

### Bài Tập 5.2 — Test Dynamic Discovery (Fault Tolerance)

**Các bước:**
1. Dừng Tax Agent (Ctrl+C cửa sổ `:10102`)
2. Chạy `uv run python test_client.py`
3. Quan sát: hệ thống **vẫn trả lời** — không crash

**Tại sao không crash?** `call_tax` trong `law_agent/graph.py` dùng `try/except`:

```python
async def call_tax(state: LawState) -> dict:
    try:
        endpoint = await discover("tax_question")
        result = await delegate(...)
        return {"tax_result": result}
    except Exception as exc:
        # Bắt lỗi, trả về fallback thay vì throw
        return {"tax_result": f"[Tax analysis unavailable: {exc}]"}
```

**Kết quả quan sát trong response:**

```
## Tax Analysis
[Tax analysis unavailable: No agent found for task 'tax_question']

## Regulatory Compliance Analysis
... (vẫn đầy đủ)
```

**Bonus — tại sao nhanh hơn khi tắt Tax Agent?**

| | Có Tax Agent | Tắt Tax Agent |
|---|---|---|
| call_tax | ~10s (LLM) | ~1s (fail fast) |
| aggregate input | ~14k chars | ~13k chars |
| aggregate time | ~25s | ~15s |
| **Total** | **~73s** | **~60s** |

`aggregate` ít nội dung hơn → LLM xử lý nhanh hơn ~10s.

**Kết luận:** Fault tolerance — 1 agent chết không kéo sập hệ thống.

---

### Bài Tập 5.3 — Modify Agent Behavior

**Yêu cầu:** Sửa `tax_agent/graph.py` để agent trả lời ngắn gọn hơn.

**Thay đổi trong `TAX_SYSTEM_PROMPT`:**

```python
TAX_SYSTEM_PROMPT = """You are a specialist tax attorney and CPA with expertise in:
...
Always note that your response is for educational purposes and the user
should consult a licensed attorney for specific legal advice.

IMPORTANT: Trả lời ngắn gọn, súc tích trong tối đa 3-5 gạch đầu dòng.
Tránh giải thích dài dòng — chỉ nêu những điểm pháp lý quan trọng nhất.
"""
```

**Restart Tax Agent:**

```powershell
# Đóng cửa sổ Tax Agent, chạy lại:
uv run python -m tax_agent
```

**Kết quả trước khi sửa:** Response dài ~500 từ, nhiều section lồng nhau.

**Kết quả sau khi sửa:**

```
Đây là những điểm pháp lý quan trọng nhất:

• Trách nhiệm dân sự: Phạt IRC § 6662 (20%) hoặc § 6663 (75%), cộng lãi suất.

• Trách nhiệm hình sự: 18 U.S.C. § 7201 — công ty phạt đến $500.000,
  cá nhân phạt $100.000 và tối đa 5 năm tù mỗi tội danh.

• Cơ quan xử lý: IRS (Criminal Investigation) + DOJ (Tax Division).
  Giám đốc/cán bộ chỉ đạo có thể chịu trách nhiệm hình sự cá nhân.

• Thời hiệu: Không có giới hạn với tờ khai gian lận; 6 năm với khai thiếu.

*Lưu ý: Phản hồi chỉ mang tính giáo dục. Cần tư vấn luật sư cho trường hợp cụ thể.*
```

---

## Bài Tập Cộng Điểm — Latency Optimization

### Câu hỏi 1: Latency tổng là bao nhiêu?

Chạy `uv run python test_client.py`, cuối output:

```
>>> LATENCY: 73.xx s
```

**Breakdown từ log thực tế:**

| Bước | Thời gian | Ghi chú |
|------|-----------|---------|
| Customer Agent LLM | ~4s | formulate + discover law-agent |
| analyze_law (parallel) | ~30s | LLM — corporate litigation |
| call_tax (parallel) | ~10s | fast nhờ concise prompt (Bài 5.3) |
| call_compliance (parallel) | ~29s | **bottleneck** |
| aggregate | ~25s | LLM tổng hợp 3 phần |
| Customer Agent post | ~13s | format + trả về client |
| **Tổng** | **~73s** | `4 + max(30,10,29) + 25 + 13` |

---

### Câu hỏi 2: Đề xuất giảm latency

**Phương án: Parallel Dispatch từ `__start__`**

**Baseline (trước optimize):**

```
START → analyze_law(20s) → check_routing(8s, LLM) → call_tax(20s)  ┐
                                                    → call_comp(20s)┘→ aggregate(20s)
Tổng: 20 + 8 + 20 + 20 + 20 = ~88–95s
```

**Sau optimize:**

```
START ──┬→ analyze_law(30s) ──┐
        ├→ call_tax(10s) ─────┤→ aggregate(25s) → END
        └→ compliance(29s) ───┘
Tổng: max(30,10,29) + 25 + overhead = ~73s
```

**Code thay đổi trong `law_agent/graph.py`:**

```python
# XÓA: check_routing node (LLM call ~8s)
# THÊM: dispatch_all_parallel function

def dispatch_all_parallel(state: LawState) -> list[Send]:
    return [
        Send("analyze_law", state),
        Send("call_tax", state),
        Send("call_compliance", state),
    ]

graph.add_conditional_edges(
    "__start__",
    dispatch_all_parallel,
    ["analyze_law", "call_tax", "call_compliance"],
)
```

**Kết quả:**

| Phiên bản | Latency | So sánh |
|-----------|---------|---------|
| Baseline (sequential) | ~88–95s | — |
| Optimized (parallel) | ~73s | **tiết kiệm ~20s (~21%)** |

**Tại sao tiết kiệm được:**
- Xóa `check_routing` LLM call: -8s
- `analyze_law` chạy song song với tax/compliance thay vì chạy trước: -~18s
- Tổng: ~26s tiết kiệm (LLM variance làm con số đo thực tế ~20s)

**Demo:**

```powershell
uv run python demo_latency.py   # so sánh baseline vs optimized
uv run python demo_stage5.py    # demo interactive có giao diện
start demo_agents.html          # slide HTML trình chiếu
```

---

## Tóm Tắt 5 Stages

| Stage | Pattern | Latency | Phù hợp khi nào |
|---|---|---|---|
| 1 | Direct LLM | ~3s | Câu hỏi đơn giản, không cần tools |
| 2 | LLM + Tools | ~8s | Cần tra cứu data hoặc tính toán |
| 3 | ReAct Agent | ~15s | Tự động orchestration, multi-step |
| 4 | Multi-Agent In-Process | ~25s | Nhiều domains, parallel (in-memory) |
| 5 | Distributed A2A | ~73s | Production, scalable, fault-tolerant |
