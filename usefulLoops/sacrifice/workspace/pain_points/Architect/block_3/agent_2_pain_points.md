# Pain Points Extracted from Architect Block 3

## Issue: Protocol completeness uncertainty
The user questioned whether the rendering protocol contract was complete enough to start hardware development, showing uncertainty about readiness for parallel development.

**Solution:**
Confirmed the `## 0. 渲染协议契约（完整规范 v1）` was sufficient to begin hardware rendering engine development and backend adjustments in parallel. Provided specific execution guidelines including rate limiting (≤2 QPS per device), pagination rules (≤8 items per page), ACK rules, and fallback strategies.

---

## Issue: Device identity display confusion
Confusion about what "device-id" meant and how to properly display hardware MAC addresses in the UI, with specific requirements for mapping MAC addresses to human-readable identifiers.

**Solution:**
Clarified that device-id is the hardware MAC address from WebSocket handshake. Implemented a mapping system using `backend/data/devices.yaml` to map MAC addresses to badge numbers and owners (e.g., `94:a9:90:07:9d:88` → `工牌001 · 文先生`). The backend injects this human-readable information into `ui.render` content slots without requiring protocol changes.

---

## Issue: Missing device registry structure
Need for a centralized way to store device mappings between MAC addresses and human identifiers (badge numbers and owners).

**Solution:**
Created `backend/data/devices.yaml` with structure:
```yaml
devices:
  "94:a9:90:07:9d:88":
    badge: "001"
    owner: "文先生"
  "80:b5:4e:ee:cb:60":
    badge: "002"
    owner: "彭先生"
  "d0:cf:13:25:02:7c":
    badge: "003"
    owner: "邓先生"
```

---

## Issue: Hardware implementation strategy uncertainty
Uncertainty about whether to create new `EinkRenderEngine` first or delete existing logic first, with concerns about development risk.

**Solution:**
Recommended incremental approach: build new `EinkRenderEngine` alongside existing logic, use feature flags for gradual migration, maintain fallback capability. This allows parallel development, reduces unavailability risk, and provides emergency rollback options.

---

## Issue: Incomplete device display requirements
Initial requirement was unclear about whether to show MAC addresses in UI, leading to multiple clarifications about what information should be visible to users.

**Solution:**
Refined requirements to only display badge number and owner name (`工牌001 · 文先生`), never show MAC addresses in UI. For unmapped devices, log "未注册设备" in backend without displaying any device identifier in UI.

---

## Issue: Organizational grouping missing from device registry
User requested adding organizational concepts to device registry after initial implementation, showing the need for hierarchical organization.

**Solution:**
Recognized need to extend `devices.yaml` structure to include group/department concepts for better organizational management of hardware devices across different departments (硬件部, 研发部, 生态部, 算法部).