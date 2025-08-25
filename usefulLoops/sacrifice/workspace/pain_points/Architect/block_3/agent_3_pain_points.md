# Pain Points from Architect Block 3

## Issue: Confusion about device-id concept and its relationship to hardware identity
The user was unclear about what "device-id" meant in the context of the rendering protocol, specifically asking "我不太确定'后端把 device-id 注入 header/body/footer 文案显示（协议无需新增字段）。' 这个描述中的device-id是什么意思?"

**Solution:**
Clarified that device-id refers to the hardware MAC address (e.g., `94:a9:90:07:9d:88`) used during WebSocket handshake as device identifier. The backend maps this MAC address to human-readable information (badge number + owner name) stored in a configuration file, then injects this readable info into UI render messages rather than showing raw MAC addresses.

---

## Issue: Need for hardware identity mapping system
User wanted to implement a system where hardware MAC addresses map to badge numbers and human owners (e.g., MAC `94:a9:90:07:9d:88` → badge `001` → owner `文先生`), but there was no defined storage mechanism.

**Solution:**
Implemented a YAML-based device registry at `backend/data/devices.yaml`:
```yaml
devices:
  "94:a9:90:07:9d:88":
    badge: "001"
    owner: "文先生"
```
Backend reads this mapping during WebSocket handshake and injects human-readable info into render messages.

---

## Issue: UI display preferences for device information
User wanted to hide raw MAC addresses from users, showing only badge numbers and owner names. Also wanted silent handling of unregistered devices (no UI indication, just backend logging).

**Solution:**
- Display format: `"工牌001 · 文先生"` in UI headers/bodies
- Unregistered devices: No UI display, backend logs "未注册设备: <mac>" 
- Render example:
```json
{
  "type": "ui.render",
  "page": "welcome", 
  "header": { "title": "工牌001 · 文先生" },
  "body": { "kind": "text", "text": "已连接后端，准备就绪" }
}
```

---

## Issue: Hardware implementation strategy uncertainty
User was unsure whether to create new `EinkRenderEngine` first or delete existing rendering logic first when implementing the new rendering protocol.

**Solution:**
Recommended incremental approach:
1. Create new `EinkRenderEngine` alongside existing logic
2. Add compile/runtime switch to choose between old and new rendering paths
3. Implement new rendering with fallback capability 
4. Only remove old logic after new system is fully validated
This approach reduces risk and allows emergency rollback during development.

---

## Issue: Device registry scaling and organization
Initially only had single device mapping, but needed to scale to multiple devices and add organizational grouping concept.

**Solution:**
Extended devices.yaml structure to include group concept:
```yaml
devices:
  "94:a9:90:07:9d:88": { badge: "001", owner: "文先生", group: "硬件部" }
  "80:b5:4e:ee:cb:60": { badge: "002", owner: "彭先生", group: "硬件部" }
```
Added multiple departments (研发部, 生态部, 算法部) for better device management and organization.