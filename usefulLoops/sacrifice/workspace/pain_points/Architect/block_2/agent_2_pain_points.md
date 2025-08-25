# Pain Points Extracted from Architect Block 2

## Issue: Hardware state machine coupling complexity
The current `hardware/main/application.cc` mixes audio, display, mode, and protocol responsibilities, creating high coupling and making expansion/concurrent boundary management risky.

**Solution:**
- Implement "backend-driven mode" architecture where hardware only maintains network/display/audio channels
- Hardware removes "self-aware mode" branches and only handles two types of messages: `ui.render` and `device.control`
- Backend takes over all mode logic and state management

---

## Issue: E-ink display refresh cost and performance
ST7306 implementation primarily uses full-screen writes, lacking "true windowed local refresh/tile updates," which affects performance and lifespan.

**Solution:**
- Implement three-region rendering (header/body/footer) with partial refresh capability
- Start with full-screen + 500ms merge throttling for immediate delivery
- Reserve `regionsChanged` hooks for future rectangular local refresh when driver is ready
- Add region signature comparison to avoid invalid redraws

---

## Issue: Cross-device mode state consistency gap
Hardware self-aware mode and backend-determined mode can potentially become inconsistent, leading to state drift and lack of unified "rendering contract."

**Solution:**
- Implement unified rendering protocol where backend holds the "mode state machine"
- Backend maps business state to "rendering instructions + action instructions"
- Hardware doesn't persist mode state, only responds to rendering instructions
- Use "last render cache" for offline re-delivery to maintain consistency

---

## Issue: Scattered storage layer with JSON-based approach
Offline peer queues, meeting indexes, and task libraries all use file storage (though atomic/sharding/cleanup is implemented), which limits concurrent consistency and retrieval scalability.

**Solution:**
- Introduce SQLite + WAL for unified embedded storage (meeting indexes/fragment cursors, offline queues, task libraries)
- Keep JSON only for export and replay purposes
- Implement dual-write/shadow read during migration for rollback capability

---

## Issue: Rate limiting and access control scattered implementation
ACL/frequency control/quota policies are implemented in multiple places but haven't formed a unified policy center, creating inconsistency and bypass risks.

**Solution:**
- Implement unified governance layer with centralized authentication (Token/JWT + device whitelist), ACL, QPS/quota, request body limiting, and audit logging
- Consolidate all rate limiting to ≤2 QPS per device for rendering, ≤5 QPS for control
- Add queue bounds and backpressure strategies (discard oldest + count metrics)

---

## Issue: Environment coupling in testing tools
Testing/tools default to fixed LAN addresses (`192.168.0.94`), making migration/CI experience suboptimal.

**Solution:**
- Implement configurable backend endpoints in testing tools
- Add environment detection and auto-configuration
- Provide one-click demo scripts that work across different network environments

---

## Issue: Mixed thread/coroutine model complexity
Connection-level thread pool mixed with async events, though reduced and configurable, requires continuous boundary protection.

**Solution:**
- Standardize on connection-level mutex + task cancellation idempotency
- Add "operation-level idempotent keys" for concurrent finalize/push operations
- Implement clear separation between sync and async boundaries

---

## Issue: Three-day delivery timeline pressure with concurrent development
Risk of waiting between three teams (backend, hardware, firmware) during parallel development, potentially blocking integration.

**Solution:**
- Implement "protocol-first + fake data rendering" approach
- Define complete rendering protocol contract upfront for parallel development
- Create mock backends and hardware simulators for independent development
- Use feature flags for gradual rollout and easy rollback

---

## Issue: Hardware rendering engine implementation complexity
Concern about implementing a "universal rendering function" that can handle all page types and UI elements within the tight timeline.

**Solution:**
- Leverage existing `EinkDisplayST7306`/GFX capabilities with three-region layout (header/body/footer)
- Use simplified UI DSL with "page type + slot content" rather than complex canvas protocol  
- Start with full-screen refresh + throttling, gradually enhance to partial refresh
- Implement UTF-8 safe truncation, pagination (≤8 items per page), and unified footer format

---

## Issue: Protocol complexity and device compatibility
Risk of over-engineering the rendering protocol, making it difficult to implement reliably across different hardware configurations.

**Solution:**
- Keep protocol extremely simple: only `ui.render`, `device.control`, `ui.ack`, and `ui.error` message types
- Use structured JSON with clear field definitions and forward compatibility
- Implement defensive validation and graceful degradation for unknown fields
- Provide comprehensive examples and error code enumeration for consistent implementation

---