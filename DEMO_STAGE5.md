# Chạy ngay — đã start_all.ps1 xong rồi


## B1:

```powershell
cd "C:\VinAI\Lab coding\Batch02-Day9_Multi-Agent_MCP-A2A"
.\start_all.ps1
```

## Bước tiếp theo (mở terminal mới, KHÔNG đóng 5 cửa sổ kia)

```powershell
cd "C:\VinAI\Lab coding\Batch02-Day9_Multi-Agent_MCP-A2A"
```

---

## 1. Đo latency hệ thống hiện tại (optimized)

```powershell
uv run python test_client.py
```

Chờ ~60-90s. Cuối output thấy:
```
>>> LATENCY: xx.xxs   ← đây là con số cần ghi lại
```

---

## 2. Lấy log baseline (chạy bản cũ để so sánh)

**Swap sang graph baseline:**

```powershell
copy "law_agent\graph.py" "law_agent\graph_optimized.py"
copy "law_agent\graph_baseline.py" "law_agent\graph.py"
```

**Đóng cửa sổ Law Agent (port 10101), rồi chạy lại:**

```powershell
cd "C:\VinAI\Lab coding\Batch02-Day9_Multi-Agent_MCP-A2A"

uv run python -m law_agent
```

**Đo baseline:**

```powershell
uv run python test_client.py
```

Ghi lại số `LATENCY: xx.xxs` — đây là baseline.

**Swap lại bản optimized:**

```powershell
copy "law_agent\graph_optimized.py" "law_agent\graph.py"
```

Restart law agent lại như trên.

---

## 3. Demo so sánh có giao diện đẹp

```powershell
uv run python demo_stage5.py
```

Nhấn Enter để chuyển từng phase.

---

## 4. Mở slide HTML để trình chiếu

```powershell
start demo_agents.html
```

---

## Tóm tắt thứ tự chạy

| Bước | Lệnh | Mục đích |
|------|------|----------|
| 1 | `uv run python test_client.py` | Đo optimized latency |
| 2 | swap baseline → đo → swap lại | Lấy số baseline để so sánh |
| 3 | `uv run python demo_stage5.py` | Demo terminal đẹp |
| 4 | `start demo_agents.html` | Slide HTML trình chiếu |
