# Merged Pain Points - Architect Block 5

## Issue: Architecture Decision Conflict - EinkRenderEngine Creation vs Inline Implementation

**Severity: High** - Fundamental architecture decision affecting entire implementation approach

Multiple agents identified tension between speed-focused inline implementation versus structured architecture approach. Initial recommendation was to implement rendering directly in `application.cc` as a simple function for fastest Day 1 delivery, but user insisted on creating independent `EinkRenderEngine` from start.

**Solution:**
- User chose "one step to the final solution" approach over incremental evolution
- Final decision: Create dedicated `EinkRenderEngine` with minimal but comprehensive interface
- Minimum viable interface established:
  ```cpp
  void Init(EinkDisplayST7306* display);
  struct RenderPayload { 
    string page; 
    string headerTitle; 
    enum {TEXT, LIST} bodyKind; 
    string bodyText; 
    vector<string> bodyList; 
    string footerHint; 
  };
  bool Render(const RenderPayload& payload);
  ```
- Full-screen refresh with ≥500ms throttling, UTF-8 truncation, max 8 list items
- Reasoning: Better long-term maintainability outweighs initial complexity

---

## Issue: Requirements Scope Creep vs Future-Proofing Balance

**Severity: Medium** - Risk management for feature expansion without over-engineering

Advanced features (pagination, regional refresh, themes, multiple list styles, unit testing, multi-board support) were mentioned without clear understanding of necessity or timing, creating tension between minimum implementation principle and future-proofing.

**Solution:**
- Provided concrete, accessible examples for each requirement:
  - Pagination: "Task list has 20 items but screen shows only 8 - like flipping book pages"
  - Regional refresh: "Only change title or footer, don't redraw entire screen" 
  - Themes: "All pages use same style - black bold 18pt titles, 14pt body text"
  - Multiple list styles: "Tasks as '[P0][Progress] Title', meetings as '• Point', logs as '[INFO]/[ERROR] Message'"
- Established clear trigger conditions for when to extract into full EinkRenderEngine:
  - Need pagination/scrolling (>8 items)
  - Need `regionsChanged` partial refresh
  - Need unified themes/fonts across pages
  - Need ≥3 list display styles
  - Need unit testing or multi-board support

---

## Issue: Backend-Hardware Message Routing Architecture Gap

**Severity: High** - Critical infrastructure missing for device targeting

Hardware was already upgraded with device-id handshake (MAC: 94:a9:90:07:9d:88) visible in backend logs, but backend lacked message forwarding capability with `to` field targeting specific devices.

**Solution:**
- Implement hot-fix message forwarding in backend without disrupting existing protocols
- Required backend changes:
  - Add `send_to_device(device_id, payload)` function in websocket_server.py
  - Support `to: ["device-id"]` message routing, remove `to` field before forwarding
  - Message routing for `ui.render` and `device.control` types
  - Last render cache with automatic replay on device reconnection
  - Device mapping from devices.yaml to inject "工牌{badge} · {owner}" into headers
  - Rate limiting (≤2 QPS) for render commands

---

## Issue: Task Ownership and Responsibility Boundaries Confusion

**Severity: Medium** - Coordination and accountability challenges

Original task assignment mixed backend development and testing responsibilities, making progress tracking difficult and creating potential coordination issues between parallel work streams.

**Solution:**
- Clear separation established with specific deliverables:
  - **Backend (w)**: WebSocket routing, message forwarding, device registry, render caching, rate limiting, device mapping injection
  - **Testing (d)**: Control scripts/pages, demo payloads, reconnection scenarios, log assertions, payload validation
- Established clear handoff points and verification criteria for each role
- Specific technical deliverables defined:
  - Backend: WebSocket forwarding, last_render_cache, render_sender with rate limiting
  - Testing: demo_render.py/HTML page, parameterized device targeting, disconnect/reconnect test cases

---

## Issue: Hardware Boot Sequence Requirements Misalignment

**Severity: Medium** - Implementation conflicts with existing hardware behavior

Initial plan assumed direct transition to render testing without accounting for existing boot sequence requirements (boot animation + welcome page), creating potential disruption to established hardware behavior.

**Solution:**
- User clarified correct sequence: "保留开机动画与欢迎页；唤醒后切到'渲染测试页（文案固定：等待后端指令…）'"
- Proper initialization flow established:
  1. Boot animation → Welcome page (preserved existing behavior)
  2. After wake → "Render test page" with fixed text: "等待后端指令..."
  3. Then transition to dynamic rendering via `EinkRenderEngine`
- Architecture updated to maintain hardware boot sequence while adding new render testing state

---

## Issue: Device Registration and Display Logic Strategy

**Severity: Medium** - User experience and security considerations for device identification

Uncertainty about how to handle device identification display - whether to show MAC addresses, device IDs, or user-friendly identifiers, with implications for both UX and security.

**Solution:**
- Established clear badge-based identification policy:
  - Registered devices: Display "工牌{badge} · {owner}" format
  - Read identification from `backend/data/devices.yaml` 
  - Unregistered devices: No UI identifier display, backend logs only "未注册设备:<mac>"
  - Never expose raw MAC addresses to users on device screens
- Backend handles device mapping injection automatically

---

## Issue: Message Protocol Validation and Error Handling Gaps

**Severity: Medium** - System reliability and crash prevention

Risk of malformed payloads causing crashes or undefined behavior without proper schema validation and comprehensive error handling throughout the message processing pipeline.

**Solution:**
- Implement lightweight schema validation in `render_schema.py`:
  - Only allow `body.kind: text|list` with strict type checking
  - Ignore unknown fields gracefully without errors
  - Return standardized error format: `{type:"ui.error", code:"INVALID_PAYLOAD"}` for parsing failures
  - UTF-8 safe truncation for display limits (max 8 list items)
  - Parse failures must return `ui.error: INVALID_PAYLOAD` immediately

---

## Issue: Testing Infrastructure Reuse Decision Point

**Severity: Low** - Resource allocation and maintainability trade-offs

Unresolved question about whether to reuse existing `simulated_work_badge_1.html` test page or create new testing suite for updated message routing logic, with implications for development speed vs maintainability.

**Solution:**
- Left as open decision point with clear evaluation criteria:
  - **Reuse existing**: Faster iteration, proven liaison patterns, less development time
  - **Create new**: Clean separation of concerns, tailored for new message routing, better long-term maintainability
- Decision depends on whether existing infrastructure supports new `to:["device-id"]` message format with `ui.render`/`device.control` types
- Recommendation: Evaluate existing page capability first, create dedicated suite only if compatibility issues arise

---

## Issue: JSON Payload Documentation and Standardization

**Severity: Low** - Development efficiency and communication clarity

Multiple identical JSON examples were repeated across conversations, creating confusion, verbosity, and inconsistent formatting in technical documentation.

**Solution:**
- Standardized on three core test payloads with consistent formatting:
  - **Text render**: `{"type":"ui.render","id":"d1-001","page":"dialog.chat","header":{"title":"工牌001 · 文先生"},"body":{"kind":"text","text":"Hello 渲染测试"},"footer":{"hint":"后端→设备 OK"}}`
  - **List render**: `{"type":"ui.render","id":"d1-002","page":"dialog.chat","header":{"title":"工牌001 · 文先生"},"body":{"kind":"list","items":["第一行","第二行","第三行"]},"footer":{"hint":"最多显示8行"}}`
  - **Banner control**: `{"type":"device.control","id":"d1-003","action":"net.banner","text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000}`
- All payloads require `to:["94:a9:90:07:9d:88"]` for proper device targeting

---

## Issue: Verification Criteria and Success Metrics Ambiguity

**Severity: Medium** - Quality assurance and acceptance criteria clarity

Initial success criteria were too vague for Day 1 validation, making it difficult to determine when implementation is complete and ready for production deployment.

**Solution:**
- Established concrete, measurable verification requirements:
  - Device sequence validation: Boot → Welcome → Wake → "Render test page"
  - Three payload types must render correctly and return `ui.ack` acknowledgment
  - Parse failures must return `ui.error: INVALID_PAYLOAD` with proper error codes
  - Disconnect/reconnect scenarios should trigger backend replay of last render automatically
  - Performance target: P95 ≤3s response time for ACK messages
  - UI text constraint enforcement: Only show "工牌{badge} · {owner}" for registered devices, unregistered devices show no identifier (backend logs only)