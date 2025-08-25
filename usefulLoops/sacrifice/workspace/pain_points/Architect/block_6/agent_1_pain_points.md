# Architect Block 6 - Agent 1 Pain Points

## Issue: Hardware infinite restart bug during integration testing
The biggest issue revealed was hardware entering infinite restart loops when receiving certain backend messages, causing complete system failure during hardware-backend integration testing.

**Solution:**
- Implemented strict backend fail-closed safety orchestration principles
- Backend must maintain device session/mode state and only send whitelisted commands per mode
- Added message sanitization (header title injection, text/list length limits, unknown field removal)
- Implemented ACK-driven messaging with timeout/retry/device freezing mechanisms
- Added per-device rate limiting (≤2 QPS) and bounded queues

---

## Issue: Backend lacks proper device mode awareness
Backend was sending messages without considering what mode each device was in or what messages were safe to send, leading to hardware receiving illegal/harmful instructions.

**Solution:**
- Backend must maintain Single Source of Truth for device states: `deviceId, badge, owner, group, currentMode, lastRenderId, lastAckTs, errorCounters, lastRenderSnapshot`
- Implemented mode-command whitelist matrix - only allow specific commands for each mode
- Stage 1: welcome/testing modes only allow `ui.render(text|list)` and `device.control(net.banner)`
- Unknown/unauthorized commands are dropped with `[DROP_BY_MODE]` logging

---

## Issue: Need for comprehensive testing approach without creating new test pages
Initially considered creating new test pages, but this would increase maintenance costs and create forked development paths.

**Solution:**
- Reuse existing `test/simulated_work_badge_1.html` as "web-based hardware" simulator
- Make minimal enhancements to existing page rather than creating new ones
- Add "target device ID" input field to existing render testing area
- Implement automatic ACK responses and end-to-end logging for full pipeline visibility

---

## Issue: Lack of intuitive hardware simulation for testing
Testing needed to feel more like real hardware interaction to be effective and intuitive for developers.

**Solution:**
- Transform test page to work like "web-based hardware badge"
- Add E-ink rendering engine (JS version) that processes `ui.render` messages
- Implement automatic ACK responses with timing statistics (P95 latency tracking)
- Add directional logging: `[RX][ui.render]`, `[ACK]`, `[ERR]` for clear visibility
- Display real-time statistics: ACK count, P95 latency, last reconnection recovery time

---

## Issue: Missing comprehensive safety validation and sanitization
Backend was not properly validating or cleaning messages before sending to hardware, allowing potentially harmful data through.

**Solution:**
- Implement message sanitization pipeline:
  - `header.title`: inject "Badge{badge} · {owner}" format
  - `body.text`: truncate to ≤200 characters (UTF-8 safe)
  - `body.items`: limit to ≤8 items, each ≤50 characters
  - `icons.net/rec/battery`: only accept enumerated/range values
  - `footer.hint`: limit to ≤50 characters
  - Remove any unknown fields not in protocol contract

---

## Issue: Need for proper ACK-driven messaging with failure handling
No proper acknowledgment system in place to ensure messages were received and processed successfully by hardware.

**Solution:**
- Implement ACK-driven flow:
  - Every message sent with unique `id` goes into pending confirmation table
  - Hardware responds with `{type:"ui.ack", id, status:"ok"}` after processing
  - 3-second timeout triggers one retry attempt
  - Still no ACK → freeze device for 30 seconds (only allow `net.banner` and welcome page)
  - Multiple failures trigger circuit breaker to prevent message flooding

---

## Issue: Insufficient rate limiting and queue management
No protection against overwhelming hardware devices with too many messages, potentially causing crashes or performance issues.

**Solution:**
- Implement per-device rate limiting: ≤2 QPS for rendering messages
- Add bounded queues that drop oldest messages when full (with drop counting)
- Offline reconnection only delivers "last render" snapshot (already sanitized and whitelisted)
- Reconnection recovery goes through same ACK process - stops if it fails

---

## Issue: Inadequate observability and debugging capabilities
Lack of proper logging and metrics made it difficult to diagnose issues during integration testing.

**Solution:**
- Implement directional logging with consistent format:
  - `[SEND] type=id=.. to=.. mode=..`
  - `[ACK] id=.. ms=..` 
  - `[DROP_INVALID] code=.. reason=..`
  - `[DROP_BY_MODE]` for unauthorized commands
  - `[FREEZE] device=.. seconds=30` for failure handling
  - `[REDELIVER] last_render sent` for reconnection
- Add per-device metrics: send count, ACK latency P95, drop reason counts, freeze count

---