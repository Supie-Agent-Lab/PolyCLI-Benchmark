# Pain Points Extracted from Architect Block 5

## Issue: Architecture decision conflict - file creation vs inline implementation
The user questioned why no new EinkRenderEngine file was created, leading to a fundamental architecture discussion about complexity vs speed.

**Solution:**
- Initially suggested inline implementation in `application.cc` for fastest Day 1 delivery
- Reasoning: fewer files, fewer interfaces, fewer CMake changes = lowest risk, fastest validation
- Compromise approach: create minimal shell (50 lines) with simple `Render(title, body, hint)` interface
- Final decision: User insisted on creating independent EinkRenderEngine from start for better long-term maintainability

---

## Issue: Requirements scope creep concern 
Multiple advanced features were mentioned (pagination, regional refresh, themes, multiple list styles, unit testing, multi-board support) without clear understanding of when they'd be needed.

**Solution:**
- Provided concrete examples for each requirement:
  - Pagination: "Task list has 20 items but screen shows only 8"  
  - Regional refresh: "Only title changed, don't redraw entire screen"
  - Themes: "Consistent font styles across all pages"
  - Multiple list styles: "Tasks as '[P0][Progress] Title', meetings as '• Point', logs as '[INFO]/[ERROR] Message'"
- Established clear triggers for when to extract into full EinkRenderEngine
- User ultimately chose immediate full implementation approach

---

## Issue: Implementation approach disagreement
Assistant recommended gradual approach (inline → minimal shell → full engine) but user wanted direct jump to full EinkRenderEngine.

**Solution:**
- User clarified requirements: preserve boot animation and welcome screen, then switch to "render test page" awaiting backend commands
- Agreed on one-step implementation of independent EinkRenderEngine
- Established minimum viable interface:
  ```cpp
  void Init(EinkDisplayST7306* display);
  struct RenderPayload { string page; string headerTitle; enum {TEXT, LIST} bodyKind; string bodyText; vector<string> bodyList; string footerHint; };
  bool Render(const RenderPayload& p);
  ```
- Full-screen refresh with ≥500ms throttling, UTF-8 truncation, max 8 list items

---

## Issue: Backend-hardware integration gap
Hardware was already upgraded with device-id handshake (MAC: 94:a9:90:07:9d:88) but backend couldn't forward the two required message types.

**Solution:**
- Identified need for message forwarding with `to:["<device-id>"]` targeting
- Required backend changes:
  - `send_to_device(device_id, payload)` function in websocket_server.py
  - Message routing for `ui.render` and `device.control` types
  - Last render cache with automatic replay on device reconnection
  - Device mapping from devices.yaml to inject "工牌{badge} · {owner}" into headers
- Hot-fix approach: add forwarding branch without changing existing protocols

---

## Issue: Task ownership confusion between backend and testing
Original task assignment mixed backend development and testing responsibilities.

**Solution:**
- Clear separation established:
  - **Backend (w)**: Message routing, device registry, render caching, rate limiting (≤2 QPS), device mapping injection
  - **Testing (d)**: Control scripts, demo pages, reconnection scenarios, log assertions, payload validation
- Specific deliverables defined:
  - Backend: WebSocket forwarding, last_render_cache, render_sender with rate limiting
  - Testing: demo_render.py/HTML page, parameterized device targeting, disconnect/reconnect test cases

---

## Issue: Test infrastructure reuse decision
Question arose whether to reuse existing `simulated_work_badge_1.html` test page or create new testing suite for the current logic.

**Solution:**
This was identified as the final question but not resolved in the conversation block. The concern was about testing stability - whether existing test infrastructure could support the new message forwarding logic or if a clean slate approach would be more reliable.

---

## Issue: JSON payload duplication in documentation
Multiple identical JSON examples were repeated in the conversation, creating confusion and verbosity.

**Solution:**
- Standardized on three core test payloads:
  - Text render: `{"type":"ui.render","id":"d1-001","page":"dialog.chat","header":{"title":"工牌001 · 文先生"},"body":{"kind":"text","text":"Hello 渲染测试"},"footer":{"hint":"后端→设备 OK"}}`
  - List render: `{"type":"ui.render","id":"d1-002","page":"dialog.chat","header":{"title":"工牌001 · 文先生"},"body":{"kind":"list","items":["第一行","第二行","第三行"]},"footer":{"hint":"最多显示8行"}}`
  - Banner control: `{"type":"device.control","id":"d1-003","action":"net.banner","text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000}`
- All payloads require `to:["94:a9:90:07:9d:88"]` for device targeting

---

## Issue: Verification criteria ambiguity
Initial success criteria were too vague for Day 1 validation.

**Solution:**
- Established concrete verification requirements:
  - Device sequence: Boot → Welcome → Wake → "Render test page"
  - Three payload types must render correctly and return `ui.ack`
  - Parse failures must return `ui.error: INVALID_PAYLOAD` 
  - Disconnect/reconnect should trigger backend replay of last render
  - Response time target: P95 ≤3s for ACK messages
  - UI text constraint: Only show "工牌{badge} · {owner}", unregistered devices show no identifier (backend logs only)