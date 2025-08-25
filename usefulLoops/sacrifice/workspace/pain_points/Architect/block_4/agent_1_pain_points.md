# Agent 1 Pain Points - Architect Block 4

## Issue: Over-engineering hardware requirements in initial proposal
The initial proposal included complex features like meeting listening pages, audio processing, and sophisticated UI that would increase hardware complexity unnecessarily.

**Solution:**
Simplified the requirements to focus only on core functionality: hardware-backend communication, receiving commands, and basic rendering. Removed meeting listening pages, complex pagination, local refresh capabilities, and audio streaming requirements.

---

## Issue: Confusion about ACK (acknowledgment) mechanism
User didn't understand what "回 ACK" (sending ACK) meant in the technical context.

**Solution:**
Provided clear explanation: ACK = acknowledgment/confirmation message sent from device back to backend after successfully processing a command. Defined when to send ACK (after processing commands with `id` field) and the exact JSON format:
```json
{ "type": "ui.ack", "id": "d1-001", "status": "ok" }
```

---

## Issue: Runtime switch concept adding unnecessary complexity
The proposal included a runtime switch `RENDER_LITE_D1=true` for toggling between old and new rendering logic, which the user rejected as meaningless complexity.

**Solution:**
Completely removed the runtime switch concept. Simplified to direct implementation of new rendering path without fallback mechanisms or configuration switches, reducing code complexity and eliminating unnecessary state management.

---

## Issue: Misunderstanding about which component handles the runtime switch
There was confusion about whether the runtime switch would be implemented on the backend or hardware side.

**Solution:**
Clarified that the switch would have been on the hardware side (firmware boolean), triggered when receiving WebSocket messages in `application.cc::OnIncomingJson`. However, this entire concept was ultimately removed per user feedback.

---

## Issue: Over-complicated implementation approach
Initial proposal suggested creating new engine classes, multiple files, and complex architectural changes.

**Solution:**
Streamlined to minimal changes: only modify existing `application.cc` file, add simple rendering function directly without creating new classes or files, implement only essential JSON message handling for `ui.render` and `device.control: net.banner`.

---

## Issue: Scope creep in feature requirements
The plan initially included audio processing, sophisticated pagination, local refresh optimization, and multiple page types that weren't needed for Day 1 testing.

**Solution:**
Focused strictly on minimal viable testing: preserve boot animation and welcome page, add simple "render test page" after wake-up, implement basic text/list rendering with whole-screen refresh and ≥500ms throttling, support only essential commands for testing hardware-backend communication.