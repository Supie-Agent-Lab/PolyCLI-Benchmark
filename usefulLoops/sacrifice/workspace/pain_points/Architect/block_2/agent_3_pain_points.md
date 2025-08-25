# Agent 3 Pain Points - Architect Block 2

## Issue: Hardware State Machine Coupling Too High
`application.cc` mixes audio/display/state/protocol multiple responsibilities, making extension and concurrent boundary risks high. The hardware side has multiple tightly coupled responsibilities concentrated in one module.

**Solution:**
Implement a "backend-driven" architecture where hardware only needs to guarantee network/display/audio channels. Remove "hardware self-aware mode" branches and keep only network/display/audio initialization. Use a universal rendering function approach where hardware acts like a frontend page, ensuring pages can switch and refresh normally.

---

## Issue: E-ink Display Refresh Cost Too High
ST7306 implementation is mainly based on full-screen writing, lacking "real windowed partial refresh/tile updates", affecting performance and lifespan. Current implementation uses full-screen refresh which causes performance bottlenecks and reduces display lifespan.

**Solution:**
- First stage: Use "full-screen + merge throttling (≥500ms)" to avoid E-ink flickering
- Reserve `regionsChanged` hooks for future partial refresh when driver supports rectangle refresh
- Implement three-region rendering (header/body/footer) with region signature comparison to avoid unnecessary redraws
- If driver doesn't support safe windowed refresh, use "region-level full-screen throttling + QPS limit" for delivery guarantee

---

## Issue: Cross-Device Mode Consistency Gap
Hardware self-aware mode and backend-judged mode have potential inconsistencies, prone to state drift; lack of unified "rendering contract". Hardware knows its own mode but backend also judges mode, creating potential synchronization issues.

**Solution:**
Implement unified "rendering protocol" where mode logic returns to backend, significantly reducing hardware complexity. Backend holds "mode state machine" and maps business state to "rendering instructions + action instructions". Hardware doesn't persist modes and only responds to backend commands through UI DSL.

---

## Issue: Storage Layer Scattered and JSON-Based
Offline peer queue/meeting index/task library are all file storage (though atomic/sharding/cleanup is done), concurrent consistency and retrieval scaling are limited. Multiple storage implementations with JSON causing scalability issues.

**Solution:**
Introduce unified local embedded storage layer: SQLite + WAL for meeting index/fragment cursor, offline queue, task library. Keep existing JSON only for export and playback. Implement dual-write/shadow read: short-term parallel output of JSON + SQLite; read-only API goes SQLite first, rollback directly switches back to JSON.

---

## Issue: Security and Rate Limiting Strategy Still Basic
WS authentication alignment, ACL/frequency control/quota implemented in multiple places but haven't formed unified strategy center. Multiple implementations of rate limiting and access control without centralized management.

**Solution:**
Implement unified governance layer: authentication (Token/JWT + device whitelist), ACL, QPS/quota, request body limiting, audit logs. Converge ACL/frequency control/quota policies to one place to avoid inconsistent multi-implementation and bypass risks. Start with Token for easier implementation, then smooth upgrade to JWT later.

---

## Issue: Environment Coupling in Test Tools
Test/tools default to fixed LAN address (`192.168.0.94`), making migration/CI experience poor. Development and testing tools are hardcoded to specific network addresses.

**Solution:**
Make test tools environment-configurable. Implement proper configuration management for different deployment environments. Remove hardcoded IP addresses and support dynamic configuration for different network environments.

---

## Issue: Mixed Thread/Coroutine Model Complexity
Connection-level thread pool mixed with async events, though reduced and configurable, boundaries need continuous protection. Complex concurrency model with mixed threading approaches.

**Solution:**
Maintain connection-level mutex + task cancellation idempotency that already exists, continue adding "operation-level idempotency keys". Use consistent async/await patterns where possible and clearly document thread boundaries.

---

## Issue: Rate Limiting and Queue Management Challenges
Need to implement proper rate limiting (≤2 QPS per device for rendering, ≤5 QPS for control) with queue bounds and backpressure strategies. Risk of overwhelming devices with too many render commands.

**Solution:**
- Implement rendering rate limiting: ≤2 QPS per device; when exceeded, discard oldest frames and retain newest
- Control rate limiting: ≤5 QPS per device (recommended); devices can merge short-term repeated commands  
- Queue boundaries: ≤10 bounded queue, discard old frames + counting metrics
- Backpressure: drop oldest + count metrics; LLM timeout metrics and failure degradation observation

---

## Issue: Offline Redelivery Consistency Complexity
Need to handle offline device reconnection and state synchronization without causing message pile-up or out-of-order delivery. Complex scenarios around device disconnection and reconnection.

**Solution:**
Only redeliver "last rendering" rather than historical queue to avoid pile-up and out-of-order issues. Backend actively sends snapshot once after reconnection. Device-level "last rendering cache" (memory + optional persistence); reconnect triggers automatic redelivery of last render state.

---

## Issue: Three-Day Implementation Timeline Pressure
Tight 3-day deadline (10h/day × 3 people) to implement full four-mode system (dialog/meeting/work/coding) with concurrent >10 devices and offline redelivery. High risk of incomplete implementation.

**Solution:**
- D1: Protocol and rendering skeleton (backend orchestration/contract; hardware rendering engine; test pages)
- D2: Three-mode closed-loop + concurrency and offline redelivery 
- D3: Authentication/rate limiting/bounded queues and one-click demo
- Use "protocol-first + fake data rendering" to advance UI and demos, then connect real ASR/LLM last
- Implement rollback strategy: hardware "local static UI + manual prompts"; backend "close rendering layer, change to fixed demo pages"

---

## Issue: UI DSL Complexity vs Flexibility Trade-off
Need to balance between too fine-grained remote canvas (complex/inefficient) and too coarse page templates. Risk of either over-engineering or under-functionality.

**Solution:**
Use "page type + slot content" approach to balance controllability and generality. Implement five body kinds: list, bullets, text, logs, kv. Keep UI DSL simple with header/body/footer structure. This covers 80% of pages with low cost compared to universal canvas protocol.

---

## Issue: ACK and Error Handling Complexity
Need proper acknowledgment and error handling for rendering and control commands with proper retry strategies and error codes. Risk of silent failures or infinite retry loops.

**Solution:**
Implement comprehensive error code enumeration:
- `INVALID_PAYLOAD` (missing fields/type errors)
- `RATE_LIMITED` (reached rate limit or queue limit) 
- `BUSY` (device busy, temporarily unable to render/control)
- `UNSUPPORTED_PAGE`, `UNSUPPORTED_BODY_KIND`
- `DISPLAY_FAILURE`, `AUDIO_FAILURE`
- `INTERNAL_ERROR`

Send ACK within ≤5s after completing render/control actions; repeated `id` should be idempotent.