# Agent 3 Pain Points - Architect Block 6

## Issue: Hardware infinite reboot bug during testing
Hardware devices experiencing infinite restart loops when receiving certain messages from the backend during integration testing.

**Solution:**
Implemented strict fail-closed backend architecture with:
- Device state management with mode-based whitelisting
- Message sanitization and validation before sending to hardware
- ACK-driven communication with timeout/retry/freeze mechanisms
- Rate limiting (≤2 QPS per device) with bounded queues

---

## Issue: Backend sending unsafe/illegal messages to hardware
Backend was sending unchecked messages that could cause hardware malfunction, violating the design principle that "backend handles all logic while hardware only executes tasks."

**Solution:**
Created comprehensive safety framework:
- White-list matrix: Only allow specific message types per device mode
- Message sanitization: Strip unknown fields, limit text length, validate enums
- Schema validation before any message dispatch
- Drop and log any non-whitelisted or invalid messages with `[DROP_BY_MODE]` and `[DROP_INVALID]` tags

---

## Issue: Need for backend to track device states and modes
Backend had no awareness of what mode each device was in, leading to inappropriate message sending that could crash hardware.

**Solution:**
Implemented Single Source of Truth pattern:
- Backend maintains device state: `deviceId, badge, owner, group, currentMode, lastRenderId, lastAckTs, errorCounters, lastRenderSnapshot`
- Mode-based instruction matrix (boot/welcome/testing/dialog/meeting/working/coding)
- Hardware never self-determines mode; all decisions made by backend based on state

---

## Issue: Lack of message acknowledgment and retry logic
No mechanism to ensure messages were successfully processed by hardware, leading to potential message loss or system inconsistencies.

**Solution:**
Implemented ACK-driven communication:
- Every message sent with unique `id`
- Track pending acknowledgments in waiting table
- 3-second timeout with single retry attempt
- Device freeze for 30 seconds after repeated failures (only allow `net.banner` during freeze)
- Exponential backoff for failed devices

---

## Issue: No rate limiting or queue management
Unlimited message sending could overwhelm hardware devices and cause crashes or performance issues.

**Solution:**
Added comprehensive flow control:
- Rate limiting: ≤2 QPS per device for rendering, ≤5 QPS for control messages
- Bounded queues: Drop oldest messages when queue full, with counter tracking
- Backpressure handling: Queue overflow alerts and statistics
- Minimal reconnection strategy: Only replay "last render" on device reconnection

---

## Issue: Insufficient logging and observability
Hard to debug issues during integration testing due to lack of directional logging and metrics.

**Solution:**
Implemented comprehensive logging system:
- Directional logs: `[SEND] type=id=.. to=.. mode=..`, `[ACK] id=.. ms=..`, `[DROP_INVALID]`, `[DROP_BY_MODE]`, `[FREEZE] device=.. seconds=30`, `[REDELIVER] last_render sent`
- Performance metrics: Per-device send counts, ACK latency P95, drop reason counters, freeze counts
- Unified log format for easy correlation between test page and backend

---

## Issue: Message content sanitization for device safety
Raw user input or system-generated content could contain unsafe data (too long text, invalid characters, etc.) that might crash hardware.

**Solution:**
Created message sanitization pipeline:
- `header.title`: Inject standardized "Badge{badge} · {owner}" format
- `body.text`: Truncate to ≤200 UTF-8 safe characters
- `body.items`: Limit to ≤8 items, each ≤50 characters
- `icons.net/rec/battery`: Only accept enumerated values, drop invalid fields
- `footer.hint`: Limit to ≤50 characters
- Strip all unknown/extra fields from protocol messages

---

## Issue: Testing strategy needed hardware simulation
Required a way to test the full backend-to-hardware flow without depending on physical hardware availability.

**Solution:**
Enhanced existing `test/simulated_work_badge_1.html` as "web-based hardware":
- Auto-render `ui.render(text|list)` messages
- Respond to `device.control(net.banner)` with visual feedback
- Automatic ACK generation with timing statistics
- Real-time logging of all message exchanges
- P95 latency tracking for performance validation

---

## Issue: Device registration and identification complexity
Needed clean way to identify devices while hiding technical details (MAC addresses) from UI.

**Solution:**
Implemented device mapping system:
- `backend/data/devices.yaml` for badge/owner mapping
- Display only "Badge001 · Name" format in UI
- Unregistered devices: log-only, no UI display of device identifiers
- Canonical device-id format (lowercase MAC with colons)

---

## Issue: Reconnection and state recovery strategy
Devices disconnecting and reconnecting needed proper state restoration without message flooding.

**Solution:**
Minimal reconnection strategy:
- Only replay "last render" snapshot on device reconnection
- Last render cache updated only on successful message delivery
- No cascading retry loops or message flooding
- Clean reconnection flow with single state restoration message

---