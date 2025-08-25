# Agent 2 Pain Points - Architect Block 4

## Issue: Excessive complexity introduction with unnecessary features
The initial solution proposed creating an entirely new `EinkRenderEngine` class with multiple components (Init, Render, DrawHeader, DrawBody, DrawFooter) along with audio streaming integration for meeting functionality.

**Solution:**
Simplified to only core functionality - basic JSON message handling in existing `application.cc` without creating new files or complex engine architecture. Removed audio integration requirements for Day 1 implementation.

---

## Issue: Overengineering with runtime switches and fallback mechanisms
Proposed adding `RENDER_LITE_D1=true` runtime switch to toggle between old and new rendering paths, creating unnecessary configuration complexity.

**Solution:**
Eliminated runtime switches entirely after user feedback. Direct implementation without toggle mechanisms, reducing code branches and configuration overhead.

---

## Issue: Misunderstanding hardware complexity constraints  
Initial plan included meeting listener pages, pagination, partial screen updates, and complex UI features that violated the "core functionality only" principle.

**Solution:**
Stripped down to minimal requirements:
- Keep boot animation and welcome page
- Wake up to simple "waiting for backend commands" test page  
- Handle only `ui.render` (text/list) and `device.control: net.banner`
- No meeting pages, pagination, or partial refreshes

---

## Issue: Confusion about ACK (acknowledgment) concept
User didn't understand what "回 ACK" (return acknowledgment) meant in the context of device-backend communication.

**Solution:**
Clarified ACK as confirmation messages:
```json
{ "type": "ui.ack", "id": "d1-001", "status": "ok" }
```
Sent after successfully processing commands with IDs, allowing backend to track completion status.

---

## Issue: Unclear runtime switch explanation
Technical jargon around "runtime switches" was not accessible to non-technical stakeholders.

**Solution:**
Provided high-school level explanation comparing it to an ON/OFF button that can switch between new and old logic without recompilation. However, ultimately removed this complexity per user feedback.

---

## Issue: Backend vs hardware responsibility confusion
User questioned which program (backend or hardware) would check the runtime switch, indicating unclear separation of concerns.

**Solution:**
Clarified that the switch would be hardware-side (in firmware), checked when receiving WebSocket messages in `application.cc::OnIncomingJson`. Backend would have separate `render.enabled` flag for different purposes.

---

## Issue: Over-specification of file structure and interfaces
Initial plan created multiple new files (`render_schema.py`, `render_sender.py`, `render_orchestrator.py`, `eink_render_engine.h/.cc`) increasing development complexity.

**Solution:**  
Reduced to minimal file changes:
- Hardware: Only modify existing `application.cc` 
- Backend: Create lightweight `render_sender.py` with basic caching
- No new engine classes or complex orchestration files

---

## Issue: Unnecessary feature complexity in rendering engine
Proposed features like content hashing for partial updates, scrolling logs, multi-page lists violated the minimal implementation principle.

**Solution:**
Simplified to basic whole-screen refresh with 500ms throttling, UTF-8 truncation, and maximum 8-line lists. No partial updates or content change detection for Day 1.

---

## Issue: Integration complexity with existing business logic
Initial plan attempted to integrate with ASR/LLM workflows and complex meeting flows too early.

**Solution:**
Isolated rendering system testing without business logic integration. Focus purely on message parsing, rendering, and ACK functionality before adding workflow integration.