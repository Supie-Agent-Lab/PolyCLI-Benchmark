# Comprehensive Pain Points Analysis - Architect Block 2

## Critical Issues (High Severity)

### Issue: Hardware-Backend State Synchronization Problem
The current architecture has hardware devices maintaining their own mode state (dialog, meeting, working, coding) which can drift from backend state, leading to inconsistency. The `application.cc` mixes audio/display/state/protocol multiple responsibilities, creating high coupling and making expansion/concurrent boundary management risky.

**Solution:**
- Implement a "backend-driven mode" architecture where hardware doesn't need to "know" what mode it's in
- Hardware only maintains network, display, and audio systems while backend judges and processes all logic
- Backend holds the "mode state machine" and maps business state to "rendering instructions + action instructions"
- Hardware removes "self-aware mode" branches and only handles two types of messages: `ui.render` and `device.control`
- Use "last render cache" (in-memory) with device reconnection auto-supplement of latest rendering state

---

### Issue: Tight Deadline Implementation Risk (3 Days)
Project needs to achieve software-hardware integration within 3 days (10h/day × 3 people), covering all modes (dialog, meeting, working, coding) which poses high risk for comprehensive rewrite and concurrent development blocking.

**Solution:**  
Use phased approach with protocol-first development:
- **D1**: Protocol and hardware skeleton (UI render/device control protocol; backend orchestration/contract; hardware rendering engine; test pages)
- **D2**: Three mode closed-loop + concurrency/offline supplementation  
- **D3**: Authentication/rate limiting/bounded queues and one-click demo
- Use "protocol-first + fake data rendering" to advance UI and demo, then connect real ASR/LLM at the end
- Create mock backends and hardware simulators for independent development
- Implement rollback capability: hardware "local static UI + manual prompts"; backend "close rendering layer, change to fixed demo pages"

---

## Performance Issues (Medium-High Severity)

### Issue: High E-ink Display Refresh Costs  
ST7306 implementation primarily uses full-screen writes, lacking "real windowed partial refresh/tile updates," affecting performance and lifespan.

**Solution:**
- Implement three-region rendering (header/body/footer) with partial refresh capability
- Use "page type + slot content" approach with region signature comparison to avoid invalid redraws
- **Phase 1**: Start with full-screen + 500ms merge throttling for immediate delivery
- **Phase 2**: Reserve `regionsChanged` hooks for future rectangular local refresh when driver is ready
- Use region-based refresh with fallback to full-screen throttling when driver doesn't support windowed refresh
- If driver doesn't support safe windowed refresh, use "region-level full-screen throttling + QPS limit"

---

### Issue: Rate Limiting and Queue Management Challenges
Need comprehensive rate limiting with proper backpressure handling to prevent device overwhelming and ensure system stability.

**Solution:**
- **Rendering rate limiting**: ≤2 QPS per device; when exceeded, discard oldest frames and retain newest
- **Control rate limiting**: ≤5 QPS per device (recommended); devices can merge short-term repeated commands  
- **Queue boundaries**: ≤10 bounded queue, discard old frames + counting metrics
- **Backpressure**: drop oldest + count metrics; LLM timeout metrics and failure degradation observation
- Handle ≥10 concurrent connections with ≥3 device interactions

---

## Architecture & Storage Issues (Medium Severity)

### Issue: Scattered JSON-based Storage Layer
Offline peer queue/meeting index/task library all use file storage (although atomic/sharding/cleanup is done), concurrent consistency and retrieval scaling is limited.

**Solution:**
- Introduce unified embedded storage layer using SQLite + WAL (meeting index/fragment cursor, offline queue, task library)
- Keep existing JSON only for export and replay purposes
- Implement dual-write/shadow read during migration: short-term parallel output of JSON + SQLite; read-only API goes SQLite first
- Provide rollback capability by directly switching back to JSON if needed
- Add daily JSON export and consistency verification to maintain simple operational model

---

### Issue: Basic Security and Rate Limiting Strategy
WS authentication alignment, ACL/frequency control/quota implemented in multiple places but not forming unified policy center, creating inconsistency and bypass risks.

**Solution:**
- Implement unified governance layer with centralized authentication (Token/JWT + device whitelist), ACL, QPS/quota, request body limiting, and audit logging
- Converge all rate limiting policies to avoid inconsistent multi-implementation
- Start with Token for easier implementation, then smooth upgrade to JWT later
- Implement management console with whitelist/exemption rules and real-time log panel
- Gradually tighten controls with proper monitoring to avoid blocking legitimate debugging work

---

### Issue: Mixed Thread/Coroutine Model Boundaries
Connection-level thread pool mixed with async events, although reduced and configurable, boundaries need continuous protection.

**Solution:**
- Maintain clear boundaries between connection-level mutexes + task cancellation idempotency
- Continue adding "operation-level idempotent keys" for concurrent finalize/push operations
- Implement clear separation between sync and async boundaries
- Use consistent async/await patterns where possible and clearly document thread boundaries

---

## Protocol & Communication Issues (Medium Severity)

### Issue: Protocol Design Complexity vs Simplicity Balance
Need to balance between overly detailed remote canvas (complex/inefficient) vs overly simple page templates while ensuring device compatibility.

**Solution:**
- Use "page type + slot content" approach with header/body/footer structure
- Define UI DSL with page types (welcome, dialog.chat, meeting.listen, etc.) and body kinds (list, bullets, text, logs, kv) for 80% coverage
- Keep protocol extremely simple: only `ui.render`, `device.control`, `ui.ack`, and `ui.error` message types
- Use structured JSON with clear field definitions and forward compatibility
- Implement defensive validation and graceful degradation for unknown fields
- Include schema versioning and handle unknown message types gracefully

---

### Issue: Comprehensive Error Handling and ACK System
Need proper acknowledgment and error handling for rendering and control commands with retry strategies to prevent silent failures.

**Solution:**
Define structured error codes with comprehensive enumeration:
- `INVALID_PAYLOAD` (missing fields/type errors)
- `RATE_LIMITED` (reached rate limit or queue limit)
- `BUSY` (device busy, temporarily unable to render/control)
- `UNSUPPORTED_PAGE`, `UNSUPPORTED_BODY_KIND`
- `DISPLAY_FAILURE`, `AUDIO_FAILURE`
- `INTERNAL_ERROR`

Send ACK within ≤5s after completing render/control actions; repeated `id` should be idempotent.

---

### Issue: Offline Redelivery Consistency Complexity
Need to handle offline device reconnection and state synchronization without causing message pile-up or out-of-order delivery.

**Solution:**
- Only redeliver "last rendering" rather than historical queue to avoid pile-up and out-of-order issues
- Backend actively sends snapshot once after reconnection
- Device-level "last rendering cache" (memory + optional persistence)
- Reconnect triggers automatic redelivery of last render state
- Use bounded queues with oldest frame dropping + count metrics for backpressure handling

---

## Development & Testing Issues (Low-Medium Severity)

### Issue: Environment Coupling in Testing
Test/tools default to fixed LAN addresses (`192.168.0.94`), migration/CI experience is poor.

**Solution:**
- Make testing tools environment-agnostic and avoid hardcoded IP addresses in test configurations
- Implement configurable backend endpoints in testing tools
- Add environment detection and auto-configuration
- Provide one-click demo scripts that work across different network environments

---

### Issue: Hardware Rendering Engine Implementation Complexity
Concern about implementing a "universal rendering function" that can handle all page types and UI elements within the tight timeline.

**Solution:**
- Leverage existing `EinkDisplayST7306`/GFX capabilities with three-region layout (header/body/footer)
- Use simplified UI DSL with "page type + slot content" rather than complex canvas protocol  
- Start with full-screen refresh + throttling, gradually enhance to partial refresh
- Implement UTF-8 safe truncation, pagination (≤8 items per page), and unified footer format
- Simplify hardware to a "universal rendering function" similar to frontend pages

---

## Implementation Notes

### Key Technical Decisions:
1. **Backend-driven architecture**: Hardware becomes a rendering client, backend holds all business logic
2. **Phased delivery approach**: Protocol-first, fake data rendering, then real integration
3. **Conservative refresh strategy**: Full-screen + throttling first, partial refresh when ready
4. **Unified storage migration**: SQLite + WAL with JSON fallback for rollback safety
5. **Centralized governance**: Single policy center for auth, rate limiting, and ACL

### Risk Mitigation:
- Protocol-first development enables parallel team work
- Rollback strategies at each layer (hardware, backend, storage)
- Conservative performance optimizations with fallback mechanisms
- Comprehensive error handling and monitoring from day one