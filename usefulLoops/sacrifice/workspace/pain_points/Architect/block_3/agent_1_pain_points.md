# Pain Points Extracted from Architect Block 3

## Issue: Confusion about device-id concept and its relationship with MAC address
The user was unclear about what "device-id" meant when the system architect mentioned "后端把 device-id 注入 header/body/footer 文案显示". There was uncertainty about whether device-id was the same as MAC address and how it related to human-readable identifiers.

**Solution:**
Clarified that device-id should be the hardware MAC address (e.g., "94:a9:90:07:9d:88") used in WebSocket handshake. Created a mapping system where MAC addresses map to human-readable information (badge numbers and owner names) stored in backend configuration files.

---

## Issue: Protocol completeness uncertainty before hardware development
The user needed confirmation about whether the rendering protocol contract was complete enough to start parallel hardware and backend development. There was concern about missing specifications that could block development.

**Solution:**
Confirmed the protocol was ready for parallel development with specific implementation guidelines:
- Render rate limiting: ≤2 QPS per device
- Screen refresh throttling: ≥500ms 
- Pagination: ≤8 items per page
- ACK rules for ui.render/device.control commands
- Fallback strategies for device reconnection

---

## Issue: Device identification display strategy confusion
Initially there was confusion about where and how to display device MAC addresses in the UI, with concerns about protocol modifications needed for this functionality.

**Solution:**
Established that MAC addresses don't need new protocol fields. Instead, backend injects human-readable device information (badge number + owner name) directly into existing ui.render content slots (header/body/footer). No protocol structure changes required.

---

## Issue: Hardware development approach uncertainty
The user was unsure whether to create new EinkRenderEngine first or delete existing logic first, concerned about development risk and rollback strategies.

**Solution:**
Recommended incremental approach:
1. Create new EinkRenderEngine alongside existing logic
2. Use compile-time or runtime switches to prefer new path
3. Maintain old logic as fallback during development
4. Only remove old logic after new system is fully tested
This approach allows parallel development and reduces downtime risk.

---

## Issue: Device mapping storage location ambiguity
There was uncertainty about where to store the device-to-user mapping information and what format to use for the configuration.

**Solution:**
Chose Option A: Create `backend/data/devices.yaml` as a dedicated configuration file with clear YAML structure:
```yaml
devices:
  "94:a9:90:07:9d:88":
    badge: "001"
    owner: "文先生"
```
This approach provides clear separation of concerns and easy maintenance.

---

## Issue: Fallback behavior for unregistered devices
Initial proposal suggested displaying MAC address for unknown devices, but user preferred not showing any device identifier for unmapped devices.

**Solution:**
Modified fallback behavior to:
- Display nothing in UI for unregistered devices
- Log "未注册设备: <mac>" message in backend logs only
- No device identification shown to end users for security/privacy

---