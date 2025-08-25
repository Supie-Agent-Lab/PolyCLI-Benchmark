# Pain Points Extracted from Architect Block 2 Conversation

## Issue: Hardware-Backend State Synchronization Problem
The current architecture has hardware devices maintaining their own mode state (dialog, meeting, working, coding) which can drift from backend state, leading to inconsistency.

**Solution:**
Implement a backend-driven approach where hardware doesn't need to "know" what mode it's in. Hardware only maintains network, display, and audio systems while backend judges and processes all logic, marking states and instructing hardware which mode to enter.

---

## Issue: High E-ink Display Refresh Costs  
ST7306 implementation primarily uses full-screen writes, lacking "real windowed partial refresh/tile updates," affecting performance and lifespan.

**Solution:**
Implement partial refresh capability with "rectangular local refresh/tile rendering" where UI components are marked with "locally refreshable regions" to reduce full-screen redraws. Use region-based refresh with fallback to full-screen throttling when driver doesn't support windowed refresh.

---

## Issue: Hardware Application Loop High Coupling
`application.cc` mixes audio/display/state/protocol multiple responsibilities, making expansion and concurrent boundary risks high.

**Solution:**
Simplify hardware to a "universal rendering function" similar to frontend pages, ensuring pages can switch and refresh normally. Backend sends instructions, hardware receives instructions and uses the universal rendering function to draw required pages.

---

## Issue: Scattered JSON-based Storage Layer
Offline peer queue/meeting index/task library all use file storage (although atomic/sharding/cleanup is done), concurrent consistency and retrieval scaling is limited.

**Solution:**
Introduce unified embedded storage layer using SQLite + WAL (meeting index/fragment cursor, offline queue, task library) with existing JSON only for export and replay.

---

## Issue: Basic Security and Rate Limiting Strategy
WS authentication alignment, ACL/frequency control/quota implemented in multiple places but not forming unified policy center.

**Solution:**
Implement unified governance layer with centralized authentication (Token/JWT + device whitelist), ACL, QPS/quota, request body limiting, and audit logging.

---

## Issue: Environment Coupling in Testing
Test/tools default to fixed LAN addresses (`192.168.0.94`), migration/CI experience is poor.

**Solution:**
Make testing tools environment-agnostic and avoid hardcoded IP addresses in test configurations.

---

## Issue: Mixed Thread/Coroutine Model Boundaries
Connection-level thread pool mixed with async events, although reduced and configurable, boundaries need continuous protection.

**Solution:**
Maintain clear boundaries between connection-level mutexes + task cancellation idempotency, and continue adding "operation-level idempotent keys."

---

## Issue: Tight Deadline Implementation Risk (3 Days)
Project needs to achieve software-hardware integration within 3 days, covering all modes (dialog, meeting, working, coding) which poses high risk for comprehensive rewrite.

**Solution:**  
Use phased approach:
- D1: Protocol and hardware skeleton (UI render/device control protocol)
- D2: Three mode closed-loop + concurrency/offline supplementation  
- D3: Demonstration and hardening with rollback capability
Use "protocol-first + fake data rendering" to advance UI and demo, then connect real ASR/LLM at the end.

---

## Issue: Protocol Design Complexity vs Simplicity Balance
Need to balance between overly detailed remote canvas (complex/inefficient) vs overly simple page templates.

**Solution:**
Use "page type + slot content" approach with header/body/footer structure. Define UI DSL with page types (welcome, dialog.chat, meeting.listen, etc.) and body kinds (list, bullets, text, logs, kv) for 80% coverage while remaining extensible.

---

## Issue: E-ink Partial Refresh Uncertainty
Hardware differences/window register inconsistencies may cause partial refresh instability.

**Solution:**
Start with development board and small sample validation, set "full-screen fallback" threshold. Implement region-level full-screen throttling + QPS limiting first to ensure delivery, then enhance with rectangular partial refresh when driver is ready.

---

## Issue: Rate Limiting and ACL Potential False Positives  
Rate limiting/ACL might block legitimate debugging and development work.

**Solution:**
Implement management console with whitelist/exemption rules and real-time log panel, gradually tighten controls with proper monitoring.

---

## Issue: Concurrent Finalize/Push and Queue Conflicts
Concurrent finalize operations and push notifications could conflict with queue operations.

**Solution:**
Use connection-level mutexes + task cancellation idempotency already existing, continue adding "operation-level idempotent keys" for safe concurrent operations.

---

## Issue: Database Introduction Complexity
Introducing DB adds device/container permissions and backup strategy complexity.

**Solution:**
Use embedded SQLite + WAL, provide daily JSON export and consistency verification to maintain simple operational model.

---

## Issue: Multi-device Coordination and Offline Re-delivery
Need to handle ≥10 concurrent connections with ≥3 device interactions and offline supplementation scenarios.

**Solution:**
Implement "last render cache" (in-memory) with device reconnection auto-supplement of latest rendering state. Use bounded queues with oldest frame dropping + count metrics for backpressure handling.

---

## Issue: Rendering Protocol Error Handling
Need comprehensive error handling for invalid payloads, rate limits, device busy states, etc.

**Solution:**
Define structured error codes: `INVALID_PAYLOAD`, `RATE_LIMITED`, `BUSY`, `UNSUPPORTED_PAGE`, `DISPLAY_FAILURE`, `AUDIO_FAILURE`, `INTERNAL_ERROR` with proper error message format and retry strategies.

---

## Issue: Compatibility and Protocol Evolution
Need to handle protocol version compatibility as system evolves.

**Solution:**
Design protocol with forward compatibility - devices should ignore unknown fields and unknown page types. Include schema versioning and handle unknown message types gracefully.

---