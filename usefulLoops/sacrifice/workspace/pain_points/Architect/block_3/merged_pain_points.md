# Comprehensive Pain Points from Architect Block 3

## Critical Issue: Confusion about device-id concept and hardware identity mapping
The user was fundamentally unclear about what "device-id" meant in the rendering protocol context, specifically asking "我不太确定'后端把 device-id 注入 header/body/footer 文案显示（协议无需新增字段）。' 这个描述中的device-id是什么意思?" This confusion extended to uncertainty about the relationship between MAC addresses and human-readable identifiers.

**Solution:**
Clarified that device-id refers to the hardware MAC address (e.g., `94:a9:90:07:9d:88`) used during WebSocket handshake as device identifier. Implemented a comprehensive mapping system where MAC addresses map to human-readable information (badge numbers and owner names) stored in backend configuration files. The backend injects this readable information into existing ui.render content slots (header/body/footer) without requiring protocol structure changes.

---

## High Priority: Protocol completeness uncertainty blocking parallel development
The user questioned whether the rendering protocol contract was complete enough to start hardware development, showing uncertainty about readiness for parallel backend and hardware development. There was concern about missing specifications that could block development progress.

**Solution:**
Confirmed the `## 0. 渲染协议契约（完整规范 v1）` was sufficient to begin hardware rendering engine development and backend adjustments in parallel. Provided specific implementation guidelines:
- Render rate limiting: ≤2 QPS per device
- Screen refresh throttling: ≥500ms 
- Pagination: ≤8 items per page
- ACK rules for ui.render/device.control commands
- Fallback strategies for device reconnection

---

## High Priority: Device registry structure and storage implementation
Need for a centralized system to store device mappings between MAC addresses and human identifiers (badge numbers and owners), with no defined storage mechanism initially.

**Solution:**
Created dedicated `backend/data/devices.yaml` configuration file with clear YAML structure:
```yaml
devices:
  "94:a9:90:07:9d:88":
    badge: "001"
    owner: "文先生"
    group: "硬件部"
  "80:b5:4e:ee:cb:60":
    badge: "002"
    owner: "彭先生"
    group: "硬件部"
  "d0:cf:13:25:02:7c":
    badge: "003"
    owner: "邓先生"
    group: "研发部"
```
This approach provides clear separation of concerns, easy maintenance, and organizational grouping capabilities.

---

## Medium Priority: UI display preferences and security requirements for device information
User wanted to hide raw MAC addresses from users, showing only badge numbers and owner names. Also wanted silent handling of unregistered devices with specific privacy/security considerations.

**Solution:**
- Display format: `"工牌001 · 文先生"` in UI headers/bodies/footers
- Unregistered devices: No UI display of device identifier, backend logs "未注册设备: <mac>" only
- Render implementation example:
```json
{
  "type": "ui.render",
  "page": "welcome", 
  "header": { "title": "工牌001 · 文先生" },
  "body": { "kind": "text", "text": "已连接后端，准备就绪" }
}
```

---

## Medium Priority: Hardware implementation strategy and risk management
User was uncertain about development approach - whether to create new `EinkRenderEngine` first or delete existing logic first. Concerns about development risk and rollback strategies during implementation.

**Solution:**
Recommended incremental approach to minimize risk:
1. Create new `EinkRenderEngine` alongside existing logic
2. Use compile-time or runtime switches to prefer new rendering path
3. Add feature flags for gradual migration between old and new systems
4. Maintain old logic as fallback during development and testing
5. Only remove old logic after new system is fully tested and validated
This approach allows parallel development, reduces system unavailability risk, and provides emergency rollback options.

---

## Low Priority: Device registry scaling and organizational management
Initially only had single device mapping concept, but needed to scale to multiple devices and add organizational grouping for better device management across different departments.

**Solution:**
Extended devices.yaml structure to include organizational concepts:
- Added group/department fields (硬件部, 研发部, 生态部, 算法部)
- Enabled hierarchical organization of hardware devices
- Supported scalable device management across multiple organizational units
- Recognized need for future organizational management features

---