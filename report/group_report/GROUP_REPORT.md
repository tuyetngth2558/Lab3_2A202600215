# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: C401 – B1
- **Team Members**: Chu Thị Ngọc Huyền, Hứa Quang Linh, Nguyễn Thị Tuyết, Nguyễn Mai Phương, Chu Bá Tuấn Anh, Nguyễn Văn Lĩnh
- **Deployment Date**: 2026-04-06

---

## 1. Executive Summary

**Mục tiêu**: Xây dựng một ReAct Agent có khả năng hoàn thành tác vụ đa bước – tìm khung giờ rảnh, đặt cuộc họp và gửi email mời.

**Kết quả**: Trong test case chạy ngày 2026-04-06, Agent hoàn thành toàn bộ pipeline (3 tool calls) trong khi Chatbot từ chối thực thi và chỉ đưa ra hướng dẫn thủ công.

| Metric     | Giá trị                         |
| :--------- | :------------------------------ |
| Agent      | **SUCCESS** – 4 steps / 3 tools |
| Chatbot    | **FAILED** – chỉ trả hướng dẫn  |
| Total Cost | $0.1359                         |

- **Success Rate**: 100% trên test case đa bước (find free slot → book → send email)
- **Key Outcome**: Agent giải quyết 100% tác vụ đa bước thông qua 3 lần gọi tool thực tế, trong khi Chatbot chỉ trả về hướng dẫn bằng lời. Đây là minh chứng rõ ràng cho sự vượt trội của vòng lặp Thought-Action-Observation trong các tác vụ có tính liên kết.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

Agent sử dụng vòng lặp Thought-Action-Observation (ReAct) chuẩn. Mỗi bước, LLM sinh ra một `Thought` (lý luận nội tâm) và một `Action` (gọi tool), nhận `Observation` (kết quả tool) và quyết định bước tiếp theo hoặc đưa ra Final Answer.

```
User Input → Thought → Action (Tool Call) → Observation → [repeat] → Final Answer
```

- `Observation` sau mỗi tool được inject lại vào prompt làm input cho bước tiếp theo.
- Vòng lặp kết thúc khi LLM phát hiện cụm từ `Final Answer:` hoặc đạt giới hạn `max_steps`.

### 2.2 Tool Definitions (Inventory)

| Tool Name                | Input Format                                                          | Use Case                                                              |
| :----------------------- | :-------------------------------------------------------------------- | :-------------------------------------------------------------------- |
| `find_common_free_slots` | `person_names: string`                                                | Tìm khung giờ rảnh chung của nhiều người cho tuần tiếp theo.          |
| `book_meeting`           | `person_names, date, time, title, duration`                           | Đặt lịch cuộc họp và trả về `booking_id` duy nhất.                    |
| `send_invitation_email`  | `booking_id: string, organizer_email: string, custom_message: string` | Gửi email mời họp đến tất cả attendees dựa trên `booking_id` thực tế. |

### 2.3 LLM Providers Used

- **Primary**: `qw/qwen3-coder-flash`
- **Secondary (Backup)**: Chưa cấu hình

---

## 3. Telemetry & Performance Dashboard

Dữ liệu được trích xuất từ log (event `LLM_METRIC`).

| Event            | Latency (ms) | Total Tokens | Cost Estimate ($) | Tool Called                |
| :--------------- | -----------: | -----------: | ----------------: | :------------------------- |
| Chatbot (1 call) |        4,921 |        2,253 |          $0.02253 | None – **FAILED**          |
| Agent Step 1     |        7,975 |        2,962 |          $0.02962 | `find_common_free_slots`   |
| Agent Step 2     |        2,728 |        2,714 |          $0.02747 | `book_meeting`             |
| Agent Step 3     |        1,632 |        2,747 |          $0.02747 | `send_invitation_email`    |
| Agent Step 4     |        3,090 |        2,856 |          $0.02856 | Final Answer               |
| **Agent TOTAL**  |   **15,425** |   **11,279** |      **$0.11312** | 3 tool calls – **SUCCESS** |

- **Average Latency (P50)**: 3,856 ms/step
- **Max Latency (P99)**: 7,975 ms (Step 1)
- **Average Tokens per Step**: 2,820 tokens
- **Total Cost of Test Suite**: $0.1359 (Agent vs Chatbot: ~5x đắt hơn)

> **Nhận xét**: Token tăng dần đều theo mỗi bước do lịch sử hội thoại được tích lũy vào prompt (rolling context). Step 1 có latency cao nhất do prompt lớn nhất và LLM sinh nhiều token thinking nhất. Agent tốn chi phí gấp ~5x chatbot nhưng đổi lại hoàn thành được task hoàn toàn.

---

## 4. Root Cause Analysis (RCA) - Failure Traces

### Case Study: Chain Hallucination tại `send_invitation_email` (Bug V1)

_Được xác định từ log sự kiện `AGENT_STEP` step=2._

- **Input**: "Đặt giúp tôi một cuộc họp với Minh Anh, Tuấn Khoa, và Hà Linh vào tuần tới…"
- **Observation** (trích từ log Step 2 – LLM tự sinh toàn bộ chuỗi tiếp theo):
  ```
  Action: book_meeting(..., date="2025-04-10", ...)
  Observation: [hallucinated] Booking confirmed...
  Action: send_invitation_email(booking_id=12345, ...)
                                              ^^^^^ SAI – ID giả, chưa có trong hệ thống
  // Thực tế TOOL_RESULT trả về booking_id: "meeting_4"
  ```
- **Root Cause**: LLM thực hiện _chain hallucination_ – thay vì chờ `Observation` thực từ tool, mô hình tự mô phỏng toàn bộ chuỗi còn lại trong một lần sinh output. Kết quả là `booking_id=12345` (số nguyên giả) được sinh trước khi `book_meeting` trả về `meeting_4`.

  | Nguyên nhân                   | Chi tiết                                                                                    |
  | :---------------------------- | :------------------------------------------------------------------------------------------ |
  | System prompt thiếu ràng buộc | Không có rule "ONE action per response" → LLM giải quyết nhiều bước trong một forward pass  |
  | Bug phụ – sai năm             | `date="2025-04-10"` (2025 thay vì 2026), tool không validate nên tạo cuộc họp trong quá khứ |
  | Parser safeguard không cố ý   | Parser chỉ extract tool call đầu tiên → che giấu bug nhưng không fix nguyên nhân gốc        |

- **Solution** (Agent v2):
  - Thêm vào system prompt: _"Generate ONLY ONE Action per step. Do NOT simulate future Observations. Wait for the actual tool result before proceeding."_
  - Thêm date validation trong `book_meeting` (từ chối `date < today`).
  - Parser hardening: raise warning nếu `llm_output` chứa nhiều hơn 1 `Action:` block.

---

## 5. Ablation Studies & Experiments

### Experiment 1: System Prompt v1 vs Prompt v2

|              | Prompt v1 (Baseline)                                                        | Prompt v2 (Fixed)                                                                           |
| :----------- | :-------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------ |
| **Key Diff** | Không có ràng buộc số lượng Action/bước; không hướng dẫn date format        | Thêm "ONE action only", "date format YYYY-MM-DD >= today", 1 few-shot example               |
| **Bug**      | Chain hallucination tại Step 2; `booking_id=12345` giả; date sai năm (2025) | Không còn chain hallucination; date đúng (2026-04-10); `booking_id` lấy từ Observation thực |
| **Result**   | Thành công nhờ parser safeguard (không phải do prompt đúng)                 | Thành công do reasoning đúng – robust hơn khi parser thay đổi                               |

- **Diff chính**: Thêm ràng buộc _"Always double check the tool arguments before calling"_ và 1 few-shot example.
- **Result**: Loại bỏ hoàn toàn chain hallucination và lỗi date sai năm.

### Experiment 2 (Bonus): Chatbot vs Agent – So sánh trực tiếp

| Case                           | Chatbot Result               | Agent Result                                    | Winner                     |
| :----------------------------- | :--------------------------- | :---------------------------------------------- | :------------------------- |
| Tìm khung giờ rảnh chung       | Từ chối – hướng dẫn thủ công | Gọi `find_common_free_slots` → 2026-04-10 10:00 | **Agent**                  |
| Đặt lịch với `booking_id` thực | Không thực hiện              | Gọi `book_meeting` → `meeting_4`                | **Agent**                  |
| Gửi email mời họp thực tế      | Đề nghị soạn email giả       | Gọi `send_invitation_email` → 3 emails gửi      | **Agent**                  |
| Trả lời câu hỏi đơn giản       | Nhanh, chi phí thấp (~4.9s)  | Đúng nhưng tốn 4 bước (~15s)                    | **Chatbot** (cost/latency) |

---

## 6. Production Readiness Review

### Security

- **Input sanitization**: Tool arguments phải được validate schema (type, length, format) trước khi execute để tránh injection.
- **Email spoofing**: `organizer_email` cần xác thực domain whitelist, không cho phép gửi từ địa chỉ tùy ý.
- **Booking ID**: Sử dụng UUID v4 thay vì sequential ID (`meeting_4`) để tránh enumeration attack.

### Guardrails

- `max_steps = 8`: Giới hạn số bước để tránh infinite loop và chi phí không kiểm soát.
- **Date validation**: Từ chối booking với `date < today` để tránh bug V1 (date sai năm 2025).
- **Single-Action enforcement**: Parser reject nếu `llm_output` chứa hơn 1 `Action:` block.
- **Cost circuit breaker**: Dừng agent nếu `cumulative_cost_estimate > threshold` (ví dụ $1.00/session).

### Scaling

- **LangGraph**: Chuyển sang LangGraph cho các workflow phức tạp hơn (parallel tool calls, conditional branching).
- **Provider fallback**: Cấu hình secondary provider (Gemini Flash) tự động khi primary timeout > 10s.
- **Async tool execution**: Các tool độc lập (check schedule của nhiều người) có thể chạy song song để giảm latency.
- **Persistent memory**: Lưu `sent_emails.json` vào database (PostgreSQL) thay vì file để hỗ trợ multi-instance deployment.

---
