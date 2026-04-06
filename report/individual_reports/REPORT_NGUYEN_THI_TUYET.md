# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Thị Tuyết
- **Student ID**: 2A202600215
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

My contribution was part of the group scenario `book_meeting_schedule` in the updated group report (`GROUP_REPORT.docx`). I focused on core implementation tasks assigned to me and coordinated integration with teammates.

- **Modules I directly worked on**:
  - `src/agent/agent.py` (ReAct loop logic: parse action/final answer, execute tool, append observation)
  - `src/compare_chatbot_vs_agent.py` (prompt setup for chatbot vs agent comparison)
  - `report/individual_reports/REPORT_NGUYEN_THI_TUYET.md` (this report and evidence synthesis)

- **Modules completed collaboratively (team integration)**:
  - `src/chatbot.py` (baseline run and telemetry)
  - `src/tools/registry.py`, `src/tools/meeting_tools.py`, `data/meeting_case.json`
  - shared logging artifacts in `logs/`

- **Code Highlights (my scope)**:
  - Implemented/adjusted ReAct runtime behavior in `src/agent/agent.py` (loop control + action parsing).
  - Added guard behavior when model outputs `Action` and `Final Answer` in the same turn.
  - Updated comparison prompts in `src/compare_chatbot_vs_agent.py` to make chatbot-vs-agent contrast clearer.
  - Contributed to reviewing group logs and summarizing evidence in report form.

- **Documentation / Integration Notes**:
  - ReAct loop uses `Action: tool_name(arguments)` and runtime-generated `Observation`.
  - Tool metadata is passed to system prompt from registry (`name`, `description`, `args_schema`) by the integrated team code.
  - Baseline/agent comparison can be reproduced by running:
    - `.\venv\Scripts\python -m src.compare_chatbot_vs_agent`
  - Script now uses separate prompts for fair comparison:
    - chatbot prompt asks model to state limitation if it cannot access tools/files
    - agent prompt explicitly asks to use tools on `data/meeting_case.json`
  - Group run provider context: primary model is `qw/qwen3-coder-flash` (per group report), while my local reproduction used available API provider in `.env`.
  - This section reflects my assigned tasks, not full ownership of all project files.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:
  - In the group meeting scenario, the model produced chain hallucination in one turn: it emitted `book_meeting`, then self-fabricated an observation, then emitted `send_invitation_email(booking_id=12345)` before receiving real tool output.

- **Log Source**:
  - Group RCA trace (from updated group report) shows Step 2 output mixing multi-action chain with fake `booking_id=12345`.
  - Project telemetry confirms the same risk pattern with `AGENT_WARNING` events in `logs/2026-04-06.log`.
  - `logs/meeting_outbox.json` verifies successful send path when using real tool observations.

- **Diagnosis**:
  - Root cause #1: system prompt v1 did not enforce **ONE action per response**.
  - Root cause #2: tool schema did not clearly constrain temporal arguments (`date` could be wrong year, e.g., 2025 in group trace).
  - Root cause #3: parser behavior could accidentally hide bug by executing only the first action, masking invalid downstream actions.

- **Solution**:
  - Hardened system prompt in `src/agent/agent.py`:
    - exactly one action per turn
    - model must not output `Observation`
  - Updated parser/runtime:
    - parse first valid action line
    - prioritize real tool execution over model-written final answer in the same turn
    - keep `AGENT_WARNING` telemetry for auditing
  - Aligned with group Agent v2 direction:
    - enforce date format and validity (`YYYY-MM-DD` and `>= today`) in booking tool layer
    - raise/block when multiple `Action:` blocks appear in one model output

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**  
   `Thought` made reasoning explicit and debuggable. In this scenario, we can inspect the exact chain (`find_common_free_slots -> book_meeting -> send_invitation_email`) instead of relying on a single opaque answer.

2. **Reliability (when agent can be worse)**  
   Agent can perform worse on cost/latency for simple tasks. Group metrics show agent was ~5x costlier than chatbot in this scenario, even though agent was operationally successful.

3. **Observation impact**  
   Observation is the key differentiator from chatbot mode. `find_common_free_slots` output directly determines meeting slot and then drives `book_meeting` and `send_invitation_email`.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  - Move tool execution to asynchronous task queue and add retries/timeouts per tool.
  - Add tool routing layer for larger tool sets.

- **Safety**:
  - Enforce strict structured output (JSON schema) instead of regex parsing.
  - Add policy checker before executing sensitive tools (email/send/write operations).

- **Performance**:
  - Cache repeated tool observations by `(tool_name, args)`.
  - Use smaller/faster model for planning turns and stronger model only when needed.
  - Add fallback provider when free-tier quota is exhausted (observed 429 in testing).
  - Add cost-aware stopping policy (circuit breaker) when cumulative session cost crosses threshold.

## V. Alignment With Group Results (Optional Note)

- **Group Model**: `qw/qwen3-coder-flash`.
- **Group Outcome**: Agent SUCCESS in multi-step scheduling (4 steps / 3 tool calls), chatbot FAILED (manual guidance only).
- **Group Metrics Snapshot**:
  - Agent total latency: `15,425 ms`
  - Agent total tokens: `11,279`
  - Agent estimated cost: `$0.11312` (Agent-only); total test-suite cost in group report: `$0.1359`
  - Chatbot latency: `4,921 ms`, tokens: `2,253`, cost: `$0.02253`
- **Interpretation**: Agent has higher cost and latency, but is decisively better for action-oriented multi-step tasks.

---

> [!NOTE]
> Rename this file to `REPORT_[YOUR_NAME].md` before submission.
