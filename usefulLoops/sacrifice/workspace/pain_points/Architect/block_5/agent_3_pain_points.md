# Pain Points - Architect Block 5

## Issue: Architecture Design Debate - EinkRenderEngine vs Inline Implementation
Initial preference was to avoid creating a separate `EinkRenderEngine` file to reduce complexity and speed up Day 1 delivery. The architect suggested implementing rendering logic directly in `application.cc` as a simple internal function.

**Solution:**
User insisted on creating a dedicated `EinkRenderEngine` from the start, arguing for "one step to the final solution" approach rather than incremental evolution. Final decision was to build the independent `EinkRenderEngine` with minimal interface:
```cpp
void Init(EinkDisplayST7306* display);
bool Render(const RenderPayload& payload);
```

---

## Issue: Requirements Clarification for Complex Features
Initial explanation of advanced features (pagination, regional refresh, themes, multi-style lists) was too abstract and technical, making it difficult to understand when these would be needed.

**Solution:**
Provided concrete, high-school-level examples:
- Pagination: "Task list has 20 items but screen shows only 8 - like flipping book pages"
- Regional refresh: "Only change title or footer, don't redraw entire screen"
- Themes/fonts: "All pages use same style - black bold 18pt titles, 14pt body text"
- Multi-style lists: "Task lists show '[P0][In Progress] Title', meeting notes show '• Point', logs show '[INFO]/[ERROR] Message'"

---

## Issue: Scope Creep Prevention vs Future-Proofing Balance
Tension between "minimum implementation principle" (最小实现原则) and preparing for inevitable feature expansion. Risk of either over-engineering Day 1 or creating technical debt.

**Solution:**
Established clear trigger conditions for when to extract features into `EinkRenderEngine`:
- Need pagination/scrolling (>8 items)
- Need regional refresh based on `regionsChanged`
- Need unified themes/fonts
- Need ≥3 list display styles
- Need unit testing or multi-board support

---

## Issue: Hardware Requirements Misalignment
Initial plan didn't account for existing hardware boot sequence requirements (boot animation + welcome page) and assumed direct transition to render testing.

**Solution:**
User corrected to preserve existing boot flow: "保留开机动画与欢迎页；唤醒后切到'渲染测试页（文案固定：等待后端指令…）'". Updated architecture to maintain hardware boot sequence while adding new render testing state.

---

## Issue: Backend Task Assignment Granularity
Initial task breakdown mixed backend and testing responsibilities, making it unclear who owns what deliverables and creating potential coordination issues.

**Solution:**
Separated tasks clearly:
- Backend (w): WebSocket routing, message forwarding, rate limiting, caching, device mapping
- Testing (d): Control scripts, test payloads, reconnection scenarios, log validation
Established clear handoff points and verification criteria for each role.

---

## Issue: Message Protocol Validation Gaps
Risk of malformed payloads causing crashes or undefined behavior without proper schema validation and error handling.

**Solution:**
Added lightweight schema validation in `render_schema.py`:
- Only allow `body.kind: text|list` 
- Ignore unknown fields
- Return `{type:"ui.error", code:"INVALID_PAYLOAD"}` for parsing failures
- UTF-8 safe truncation for display limits

---

## Issue: Device Registration and Display Logic Confusion
Unclear how to handle unregistered devices - whether to show MAC addresses, generic identifiers, or hide device info entirely.

**Solution:**
Established clear policy:
- Registered devices: Show "工牌{badge} · {owner}" in title
- Unregistered devices: No device identifier on UI, only backend log "未注册设备:<mac>"
- Never display MAC addresses on device screens

---

## Issue: Testing Infrastructure Reuse Decision
Uncertainty whether to reuse existing `simulated_work_badge_1.html` test page or create new testing infrastructure for the updated message protocol.

**Solution:**
Left as open question at conversation end, but established criteria: existing page if it supports new `to:["device-id"]` message format with `ui.render`/`device.control` types, otherwise create dedicated test suite for protocol stability.