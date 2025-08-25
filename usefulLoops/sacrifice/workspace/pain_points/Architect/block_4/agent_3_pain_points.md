# Pain Points Extracted from block_4.md

## Issue: Unnecessary Runtime Switch Complexity
The initial proposal included a runtime switch `RENDER_LITE_D1=true` to toggle between new and old rendering paths, which would add unnecessary complexity to hardware implementation.

**Solution:**
User rejected this approach, stating "完全没有必要要这个东西好吗 没有任何意义 还增加了硬件的复杂度" (This is completely unnecessary, it has no meaning and adds hardware complexity). The solution was to remove the runtime switch entirely and implement the new path directly without fallback mechanisms.

---

## Issue: Misunderstanding of ACK Concept
There was confusion about what "回 ACK" (sending ACK) meant in the context of hardware-backend communication.

**Solution:**
Clarified that ACK means acknowledgment - the device sends a confirmation message to the backend after successfully processing an instruction. Format:
```json
{ "type": "ui.ack", "id": "d1-001", "status": "ok" }
```
For failures:
```json
{ "type": "ui.error", "id": "d1-001", "code": "INVALID_PAYLOAD", "message": "字段缺失" }
```

---

## Issue: Overcomplicating Hardware Implementation
Initial plan included complex features like meeting listening pages, pagination, partial refresh, audio streaming integration, which violated the principle of keeping hardware implementation simple.

**Solution:**
Stripped down to core functionality only:
- Can connect to backend
- Can receive instructions  
- Can render according to instructions
- Can send ACK responses
- Removed meeting listening, pagination, partial refresh, and audio streaming from Day 1 requirements

---

## Issue: Confusion About Runtime Switch Implementation
User didn't understand the concept of a runtime switch and which program (backend vs hardware) would implement it.

**Solution:**
Clarified that it would be a hardware-side boolean flag checked when receiving WebSocket messages in `application.cc::OnIncomingJson`. However, this was ultimately removed as unnecessary complexity.

---

## Issue: Over-Engineering the Rendering Engine
Initial proposal suggested creating separate `EinkRenderEngine` class with complex methods for header/body/footer rendering.

**Solution:**
Simplified to a single function `RenderHeaderBodyFooter(title, body_text_or_list, hint)` directly in `application.cc` without creating new classes or files. Features:
- Full screen refresh only
- ≥500ms throttling
- UTF-8 safe truncation  
- Lists limited to ≤8 lines

---

## Issue: Scope Creep in Day 1 Implementation
Original Day 1 plan included too many features like meeting pages, device control actions, audio streaming, making it too complex for initial validation.

**Solution:**
Reduced Day 1 scope to absolute minimum:
- Boot animation → welcome page → wake up → "render test page"  
- Support only `ui.render` (text/list) and `device.control: net.banner`
- Ignore all other protocol fields and actions
- Focus on communication → rendering → ACK → reconnection flow validation

---