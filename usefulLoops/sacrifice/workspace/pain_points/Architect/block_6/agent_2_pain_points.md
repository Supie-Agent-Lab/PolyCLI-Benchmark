# Pain Points Extracted from Architect Block 6 - Agent 2

## Issue: Hardware Infinite Restart Bug Due to Backend Unsafe Messages
During hardware-backend integration testing, the hardware devices experienced infinite restart loops, indicating that the backend was sending unsafe or malformed messages that caused hardware crashes.

**Root Cause:** Backend lacked strict message validation and mode-aware message filtering, sending unsupported or malformed commands to hardware devices.

**Solution:**
Implement fail-closed backend architecture with strict message validation:
- **Device State Management**: Backend maintains single source of truth for each device: `deviceId, badge, owner, group, currentMode, lastRenderId, lastAckTs, errorCounters, lastRenderSnapshot`
- **Whitelist Matrix**: Only allow specific message types per device mode:
  - `welcome/testing` mode: Only `ui.render(text|list)` and `device.control(net.banner)`
  - Block all other message types with `[DROP_BY_MODE]` logging
- **Message Sanitization**: All outgoing messages must pass schema validation, length limiting, and field stripping before sending
- **ACK-Driven Flow**: Every message with `id` requires acknowledgment within 3s timeout, with retry once then device freeze for 30s if no response

---

## Issue: Backend Architecture Not Properly Protecting Hardware
The original backend design did not follow the established principle that "backend handles all logic and task orchestration while hardware only receives and executes backend tasks." Backend was sending potentially harmful information to hardware.

**Solution:**
Redesign backend as protective orchestration layer:
```
- Single Source of Truth: Backend maintains device session/mode state
- Positive Gating: Only send messages allowed by current device mode  
- Message Purification: Schema validation + length limits + field cleanup
- ACK Driven: Every send waits for acknowledgment with exponential backoff retry
- Fail-Closed: Any uncertain/overlimit/unvalidated message is dropped, never sent
- Rate Limiting: ≤2 QPS per device rendering with bounded queues
```

**Backend Core Principles:**
- White-list only approach for message types per device mode
- Strict schema validation and field sanitization before any message dispatch
- Device freeze mechanism (30s cooldown) for unresponsive devices
- Comprehensive directional logging: `[SEND]`, `[ACK]`, `[DROP_INVALID]`, `[DROP_BY_MODE]`, `[FREEZE]`

---

## Issue: Lack of Device Mode Awareness in Message Routing
Backend was not tracking what mode each device was in, leading to inappropriate message types being sent to devices not ready to handle them.

**Solution:**
Implement device mode state machine:
```
Device Modes: boot|welcome|testing|dialog|meeting|working|coding

Mode-Command Matrix:
- boot/welcome: Only ui.render(text|list), device.control(net.banner)
- testing: ui.render(text|list), device.control(net.banner) 
- meeting/working/coding: Expanded command sets per mode
- Unknown commands for any mode: DROP and log
```

**Implementation Details:**
- Backend maintains `currentMode` per device in memory
- All message forwarding checks mode compatibility before dispatch
- Unknown message types or actions are dropped with logging
- Mode transitions controlled by backend orchestration logic

---

## Issue: Missing Message Sanitization Leading to Hardware Crashes
Raw messages from UI or API were being forwarded directly to hardware without proper validation, length limits, or field cleanup.

**Solution:**
Implement comprehensive message sanitization pipeline:

**Text/List Rendering Sanitization:**
```json
{
  "header.title": "Inject badge/owner from devices.yaml, ≤16 chars",
  "body.text": "UTF-8 safe truncation, ≤200 chars", 
  "body.items": "≤8 items, each ≤50 chars",
  "icons.net/rec/battery": "Enum validation only",
  "footer.hint": "≤50 chars",
  "unknown_fields": "Strip all unrecognized fields"
}
```

**Device Control Sanitization:**
- Only allow enumerated `action` values
- Validate all required fields present
- Length limit all text fields
- Remove any fields not in protocol specification

---

## Issue: No ACK Tracking or Device Health Monitoring
Backend was sending messages without tracking whether devices successfully processed them, leading to potential message loss and inability to detect device health issues.

**Solution:**
Implement ACK-driven message delivery with device health tracking:

**ACK Tracking Flow:**
1. Generate unique `id` for each message requiring acknowledgment
2. Store in "pending acknowledgment table" with timestamp
3. Device sends `{type:"ui.ack", id:"...", status:"ok"}` on completion
4. Backend clears pending entry on ACK receipt
5. 3s timeout triggers single retry
6. Second failure freezes device for 30s (only allow net.banner)

**Device Health Monitoring:**
- Track ACK latency P95 per device
- Count and log drop reasons per device  
- Circuit breaker pattern for repeatedly failing devices
- Comprehensive logging: `[SEND]`, `[ACK]`, `[TIMEOUT]`, `[FREEZE]`, `[RECOVER]`

---

## Issue: Unlimited Message Rate Could Overwhelm Hardware
Backend had no rate limiting, potentially sending messages faster than hardware could process, leading to queue overflow and crashes.

**Solution:**
Implement strict rate limiting and queue management:

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
- Online reconnection only delivers last render snapshot (not full history)
- No auto-retry loops that could amplify traffic
- Device freeze mechanism prevents message storm to failing devices

---