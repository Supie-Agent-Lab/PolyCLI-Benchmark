# Architect Block 6 - Merged Pain Points Analysis

## Critical Issue: Hardware Infinite Restart Bug During Integration Testing
**Severity: Critical - System Failure**

The most severe issue discovered was hardware devices entering infinite restart loops when receiving certain backend messages, causing complete system failure during hardware-backend integration testing.

**Root Cause:** Backend lacked strict message validation and mode-aware message filtering, sending unsupported, malformed, or unsafe commands to hardware devices that violated the core design principle: "backend handles all logic and task orchestration while hardware only receives and executes backend tasks."

**Comprehensive Solution:**
- Implemented strict backend fail-closed safety orchestration principles
- Backend must maintain device session/mode state and only send whitelisted commands per mode
- Added comprehensive message sanitization (header title injection, text/list length limits, unknown field removal)
- Implemented ACK-driven messaging with timeout/retry/device freezing mechanisms
- Added per-device rate limiting (≤2 QPS) and bounded queues with drop counting

---

## High Priority: Backend Architecture Redesign for Hardware Protection
**Severity: High - Design Violation**

The original backend design did not properly protect hardware devices and was sending potentially harmful information without proper validation or mode awareness.

**Solution - Fail-Closed Backend Architecture:**
```
Core Principles:
- Single Source of Truth: Backend maintains device session/mode state
- Positive Gating: Only send messages allowed by current device mode  
- Message Purification: Schema validation + length limits + field cleanup
- ACK Driven: Every send waits for acknowledgment with exponential backoff retry
- Fail-Closed: Any uncertain/overlimit/unvalidated message is dropped, never sent
- Rate Limiting: ≤2 QPS per device rendering with bounded queues
```

**Backend State Management:**
Device state maintained as: `deviceId, badge, owner, group, currentMode, lastRenderId, lastAckTs, errorCounters, lastRenderSnapshot`

---

## High Priority: Device Mode Awareness and Command Whitelisting
**Severity: High - Safety Critical**

Backend was not tracking what mode each device was in, leading to inappropriate message types being sent to devices not ready to handle them.

**Solution - Mode-Command Whitelist Matrix:**
```
Device Modes: boot|welcome|testing|dialog|meeting|working|coding

Mode-Command Matrix:
- boot/welcome/testing: Only ui.render(text|list), device.control(net.banner)
- meeting/working/coding: Expanded command sets per mode (future implementation)
- Unknown commands for any mode: DROP and log with [DROP_BY_MODE]
```

**Implementation Details:**
- Backend maintains `currentMode` per device in memory
- All message forwarding checks mode compatibility before dispatch
- Unknown message types or actions are dropped with comprehensive logging
- Mode transitions controlled exclusively by backend orchestration logic
- Hardware never self-determines mode; all decisions made by backend based on state

---

## High Priority: Comprehensive Message Sanitization Pipeline
**Severity: High - Security/Safety**

Raw messages from UI or API were being forwarded directly to hardware without proper validation, length limits, or field cleanup, leading to potential crashes.

**Solution - Message Sanitization Framework:**

**Text/List Rendering Sanitization:**
```json
{
  "header.title": "Inject 'Badge{badge} · {owner}' format from devices.yaml, ≤16 chars",
  "body.text": "UTF-8 safe truncation, ≤200 chars", 
  "body.items": "≤8 items, each ≤50 chars",
  "icons.net/rec/battery": "Enum validation only - accept only enumerated/range values",
  "footer.hint": "≤50 chars",
  "unknown_fields": "Strip all unrecognized fields not in protocol contract"
}
```

**Device Control Sanitization:**
- Only allow enumerated `action` values
- Validate all required fields present
- Length limit all text fields
- Remove any fields not in protocol specification

---

## Medium Priority: ACK-Driven Communication with Device Health Monitoring
**Severity: Medium - Reliability**

No proper acknowledgment system existed to ensure messages were received and processed successfully by hardware, and no mechanism to track device health.

**Solution - ACK Tracking Flow:**
1. Generate unique `id` for each message requiring acknowledgment
2. Store in "pending acknowledgment table" with timestamp
3. Device sends `{type:"ui.ack", id:"...", status:"ok"}` on completion
4. Backend clears pending entry on ACK receipt
5. 3-second timeout triggers single retry attempt
6. Still no ACK → freeze device for 30 seconds (only allow `net.banner` and welcome page)
7. Multiple failures trigger circuit breaker to prevent message flooding

**Device Health Monitoring:**
- Track ACK latency P95 per device
- Count and log drop reasons per device with detailed counters
- Circuit breaker pattern for repeatedly failing devices
- Exponential backoff for failed devices

---

## Medium Priority: Rate Limiting and Queue Management
**Severity: Medium - Performance/Stability**

No protection against overwhelming hardware devices with too many messages, potentially causing crashes or performance issues.

**Solution - Comprehensive Flow Control:**

**Rate Limiting:**
- Maximum 2 QPS (queries per second) for `ui.render` messages per device
- Maximum 5 QPS for `device.control` messages per device
- Bounded message queues per device (drop oldest when full)
- Count and log all dropped messages with reasons

**Queue Management:**
```python
# Pseudo-code
if device_queue.size() >= MAX_QUEUE_SIZE:
    dropped_msg = device_queue.pop_oldest()
    log_drop_counter.increment(device_id, "QUEUE_FULL")
    
if device_render_rate > 2.0:  # QPS
    log_drop_counter.increment(device_id, "RATE_LIMITED")
    return False  # Don't send
```

**Backpressure Handling:**
- Online reconnection only delivers "last render" snapshot (already sanitized and whitelisted)
- Reconnection recovery goes through same ACK process - stops if it fails
- No auto-retry loops that could amplify traffic
- Device freeze mechanism prevents message storm to failing devices

---

## Medium Priority: Comprehensive Observability and Debugging
**Severity: Medium - Maintainability**

Lack of proper logging and metrics made it difficult to diagnose issues during integration testing and ongoing operations.

**Solution - Unified Logging System:**

**Directional Logging Format:**
- `[SEND] type=id=.. to=.. mode=..` - Message dispatch with context
- `[ACK] id=.. ms=..` - Acknowledgment received with timing
- `[DROP_INVALID] code=.. reason=..` - Schema/validation failures
- `[DROP_BY_MODE]` - Unauthorized commands for current device mode
- `[FREEZE] device=.. seconds=30` - Device punishment for failures
- `[REDELIVER] last_render sent` - Reconnection recovery
- `[TIMEOUT]`, `[RECOVER]` - Additional state transitions

**Performance Metrics:**
- Per-device send count tracking
- ACK latency P95 measurement
- Drop reason counters by category
- Device freeze count and recovery statistics
- Unified log format for easy correlation between test page and backend

---

## Low Priority: Enhanced Testing Strategy with Hardware Simulation
**Severity: Low - Development Efficiency**

Need for comprehensive testing approach without creating new test pages that would increase maintenance costs and create forked development paths.

**Solution - Reuse and Enhance Existing Infrastructure:**
- Reuse existing `test/simulated_work_badge_1.html` as "web-based hardware" simulator
- Make minimal enhancements to existing page rather than creating new ones
- Add "target device ID" input field to existing render testing area
- Transform test page to work like "web-based hardware badge"

**Enhanced Test Page Features:**
- Add E-ink rendering engine (JS version) that processes `ui.render` messages
- Implement automatic ACK responses with timing statistics (P95 latency tracking)
- Auto-render `ui.render(text|list)` messages with visual feedback
- Respond to `device.control(net.banner)` with appropriate visual updates
- Display real-time statistics: ACK count, P95 latency, last reconnection recovery time
- Real-time logging of all message exchanges with directional tags

---

## Low Priority: Device Registration and Identification Management
**Severity: Low - User Experience**

Need clean way to identify devices while hiding technical details (MAC addresses) from UI and maintaining proper device-to-user mapping.

**Solution - Device Mapping System:**
- `backend/data/devices.yaml` for badge/owner mapping
- Display only "Badge{badge} · {owner}" format in UI (injected into header.title)
- Unregistered devices: log-only, no UI display of device identifiers
- Canonical device-id format (lowercase MAC with colons)
- Hide technical MAC addresses from user-facing interfaces

---

## Low Priority: Optimized Reconnection and State Recovery
**Severity: Low - Network Efficiency**

Devices disconnecting and reconnecting needed proper state restoration without message flooding or cascading retry loops.

**Solution - Minimal Reconnection Strategy:**
- Only replay "last render" snapshot on device reconnection
- Last render cache updated only on successful message delivery (confirmed by ACK)
- No cascading retry loops or message flooding
- Clean reconnection flow with single state restoration message
- Reconnection uses same ACK-driven process as normal messages
- State recovery stops immediately if ACK fails, triggering device freeze

---

## Summary

The merged analysis reveals a systematic approach to solving hardware-backend integration issues through:

1. **Safety First**: Fail-closed architecture that never sends uncertain messages
2. **State Management**: Backend as single source of truth for all device states
3. **Validation Pipeline**: Comprehensive sanitization before any hardware communication
4. **Reliability**: ACK-driven communication with timeout/retry/freeze mechanisms
5. **Performance**: Rate limiting and queue management to prevent device overload
6. **Observability**: Comprehensive logging and metrics for debugging and monitoring

All solutions maintain the core principle that "backend handles all logic and task orchestration while hardware only receives and executes backend tasks," ensuring hardware devices remain simple, reliable, and protected from potentially harmful instructions.