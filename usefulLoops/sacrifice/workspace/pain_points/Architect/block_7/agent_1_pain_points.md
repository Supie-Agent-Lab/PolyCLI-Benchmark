# Pain Points from Architect Block 7

## Issue: Incorrect validation order causing wrong DROP_BY_MODE instead of DROP_INVALID
When sending a JSON message missing the `body` field like `{ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"bad-002","page":"dialog.chat" }`, the system displays `[DROP_BY_MODE] type=ui.render reason=not-allowed-in-mode mode=None detail=None` instead of the expected `[DROP_INVALID] reason=schema-invalid missing=body`.

**Solution:**
Change validation order in the backend. The current process does "whitelist first, then structure validation". It should be "structure/schema validation first (body.kind must be text|list), then if passed, proceed to mode whitelist validation". This ensures proper error categorization.

---

## Issue: Rate limiting incorrectly showing "device offline" instead of rate-limited message
When sending 3 ui.render commands within 1 second to test rate limiting, the logs show "device offline" instead of the expected rate-limited message like `qps=limited` or `rate-limited`.

**Solution:**
Distinguish between rate limiting and actual offline status in the logging system. The current issue is that when rate limiting triggers, the send function returns False, which the forwarding entry treats as "send failed/offline" and logs it as device offline. Instead, it should log as `[DROP_INVALID reason=rate-limited]` or show `qps=limited` in the [SEND] log.

---

## Issue: Misunderstanding of device welcome page rendering responsibility
There was confusion about whether the backend should send welcome page renders immediately upon device connection/hello. The architect initially suggested that backend should send welcome ui.render messages after connection.

**Solution:**
Clarify that device "boot animation/welcome page" is handled locally by the hardware and is pre-built. The backend should NOT send any `ui.render` during the "connect/hello" phase. Backend should only start rendering and control AFTER the device is "awakened" (唤醒). This follows the principle of "only render after awakening".

---

## Issue: Lack of comprehensive state machine design for device modes
Initial design was too simplistic and didn't cover all the modes and transitions needed for the complete system (dialog, meeting, working, coding modes).

**Solution:**
Implement a comprehensive state machine in the backend that tracks each device's current state:
- States: `boot(local) → connected(idle) → dialog.preparing → dialog.active` and similar paths for meeting, working, coding modes
- Events: `mode.start(dialog)`, `listen.start`, `listen.detect`, etc.
- Whitelist matrix: Only allow certain commands based on current device state
- Proper state transitions with logging for each state change

---

## Issue: Incomplete dialog conversation flow implementation
The system was missing the actual conversation capability - while it could render and receive ACKs, it couldn't handle the full ASR→LLM→TTS pipeline for actual conversations.

**Solution:**
Implement the complete dialog conversation chain:
1. ASR: Receive audio/text from device → speech recognition → get recognized text
2. LLM: Feed recognized text to LLM → generate appropriate text response  
3. TTS: Convert LLM response to audio → send audio frames to device for playback
4. Add error handling for each step with fallback ui.render messages like "Sorry, couldn't hear clearly..." or "Please try again later..."

---

## Issue: Confusion about direct message forwarding with `to` field
There was uncertainty about how direct message forwarding should work with the whitelist system - should it check the sender's mode or the target device's mode.

**Solution:**
Implement "target device mode" checking for direct `to` forwarding. When a message has `to:["device-id"]`, the backend should check the TARGET device's `currentMode`. Only if the target device is in `dialog.preparing` or `dialog.active` should it allow `ui.render(page==dialog.chat)` and `device.control(net.banner|play.tone)`. All other messages should be `[DROP_BY_MODE]`.

---

## Issue: Overcomplicating the core requirements for Stage 2
Initial design included too many non-essential features like detailed ACK tracking, freeze mechanisms, and complex retry logic that weren't critical for the minimum viable dialog loop.

**Solution:**
Focus on the absolute core changes needed for Stage 2:
1. Wake-up triggered rendering (no rendering until awakened)
2. Device state machine implementation
3. Direct forwarding whitelist based on target device mode  
4. Complete ASR→LLM→TTS conversation pipeline
Keep existing features (rendering sanitization, rate limiting, unified logging) as baseline without re-implementing them.

---

## Issue: Log format inconsistency and missing structured logging
The system lacked unified, structured logging format for tracking message flow, making debugging difficult.

**Solution:**
Implement unified logging with key=value format for easy parsing:
- `[SEND] type=ui.render id=d1-002 to=94:a9:90:07:9d:88 mode=testing page=dialog.chat body=list qps=ok`
- `[ACK] id=d1-002 device=94:a9:90:07:9d:88 elapsedMs=215`
- `[DROP_BY_MODE] type=ui.render body=logs reason=not-allowed-in-mode mode=testing`
- `[DROP_INVALID] type=ui.render reason=schema-invalid missing=header/body`
- `[FREEZE] device=94:a9:90:07:9d:88 seconds=30 reason=ack-timeout id=d1-004`
- `[REDELIVER] device=94:a9:90:07:9d:88 id=wel-001 page=welcome`