# Agent 2 Pain Points - Block 5

## Issue: Architecture decision tension between speed and structure
The initial suggestion was to implement rendering directly in `application.cc` as a simple function to achieve "today can run through" without adding complexity. However, the user wanted a proper `EinkRenderEngine` structure from day 1.

**Solution:**
Compromised on a hybrid approach - create an independent `EinkRenderEngine` with minimal interface but comprehensive enough for future expansion:
- `void Init(EinkDisplayST7306* display);`  
- `bool Render(const RenderPayload& payload);` with full screen refresh ≥500ms throttling
- `struct RenderPayload` with essential fields for header/body/footer rendering

---

## Issue: Scope creep prevention vs future-proofing balance  
There was tension between implementing only the absolute minimum (text/list rendering + ACK) versus preparing for known future requirements like pagination, partial refresh, themes, etc.

**Solution:**
Defined clear trigger conditions for when to expand the engine:
- Pagination/scrolling (lists >8 items)
- `regionsChanged` partial refresh needs
- Theme/font reuse requirements  
- Multiple list display styles (≥3 types)
- Unit testing or multi-board support needs

---

## Issue: Hardware initialization sequence confusion
User corrected the assumption about hardware boot flow - needed to preserve boot animation and welcome page, then transition to a "render test page" with fixed text waiting for backend commands.

**Solution:**
Clarified the proper sequence:
1. Boot animation → Welcome page (preserved)
2. After wake → "Render test page" (fixed text: "等待后端指令...")
3. Then transition to dynamic rendering via `EinkRenderEngine`

---

## Issue: Message routing architecture not yet implemented
Hardware was already upgraded with device-id handshake (MAC: 94:a9:90:07:9d:88 visible in backend logs), but backend couldn't route messages with `to` field to specific devices.

**Solution:**
Defined hot-fix message forwarding in backend:
- Add `to: ["device-id"]` support in message routing
- Remove `to` field before forwarding to target device
- Implement `send_to_device(device_id, payload)` function
- Add automatic re-injection of last render on device reconnection

---

## Issue: Task ownership and responsibility boundaries unclear
Initially mixed backend and testing tasks together, making it hard to track progress and coordinate parallel work.

**Solution:**  
Separated responsibilities clearly:
- **Backend (w)**: WebSocket routing, message forwarding, rate limiting, device mapping injection, last render caching
- **Testing (d)**: Control scripts/pages, test payload generation, reconnection scenarios, log assertion and validation

---

## Issue: Device identification display strategy
Uncertainty about whether to show MAC addresses, device IDs, or user-friendly identifiers on the device screen.

**Solution:**
Decided on badge-based identification:
- Display format: "工牌{badge} · {owner}" 
- Read from `backend/data/devices.yaml`
- Unregistered devices: no UI display, backend logs only "未注册设备:<mac>"
- Never show raw MAC addresses to users

---

## Issue: Testing infrastructure reuse vs fresh start decision
Question arose whether to reuse existing `simulated_work_badge_1.html` test page (already optimized for backend-hardware liaison) or create completely new testing infrastructure.

**Solution:**
Left decision point open for testing team to evaluate:
- **Reuse**: Faster iteration, proven liaison patterns, less development time
- **Fresh**: Clean separation of concerns, tailored for new message routing logic, better long-term maintainability

---