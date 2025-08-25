
## 编辑内容03 后端渲染路由与发送接入（阶段1）
编辑人 -w
- 变更内容 
    - backend/core/websocket_server.py：新增设备直达发送与补投；注册流程补投 last_render
    - backend/core/handle/textHandle.py：统一入口实现 `ui.render` / `device.control` 转发与 ACK/ERROR 日志
    - backend/core/orchestration/render_schema.py：渲染负载轻量清洗（仅 text|list，忽略未知字段）并注入标题
    - backend/core/orchestration/render_sender.py：发送器（每设备≤2 QPS 限频、成功后缓存 last_render）
    - backend/core/utils/last_render_cache.py：内存缓存 set_last/get_last
    - backend/core/utils/device_registry.py：读取 `backend/data/devices.yaml`，提供 `get_display_title()`

- 新增文件/接口
  - websocket_server：`async def send_to_device(device_id, payload)`（直达路由；自动去除 `to` 字段；`ui.render`→清洗+限频+缓存，`device.control`→阶段1仅支持 `net.banner`）
  - websocket_server：`async def deliver_last_render_snapshot(device_id, handler)`（设备注册后补投“最后一次渲染”）
  - render_schema：`clean_render_payload(device_id, payload)`（只允许 `body.kind: text|list`，UTF-8 安全；忽略未知字段；注入标题）
  - render_sender：`send_render(conn_or_device_id, payload)`、`send_control(conn_or_device_id, action="net.banner", **kw)`（限频≥500ms/设备；成功后 `set_last`）
  - last_render_cache：`set_last/get_last`
  - device_registry：`get_display_title(device_id)`（返回“工牌{badge} · {owner}”，未注册返回 None）

- 行为/协议（阶段1）
  - 任意已连接客户端可发送顶层 `ui.render` / `device.control`，当携带 `to:["<device-id>", ...]` 时：
    - 标准化目标ID（小写、去空格/引号）
    - 删除 `to` 字段后分别投递到每个在线设备；不在线仅日志，不回执给发起方
  - 设备上行 `{type:"ui.ack"|"ui.error"}`：仅透传到服务端日志（不回送发起方）
  - 设备注册成功后：若存在 `last_render_cache`，立即补投一次
  - 渲染清洗：仅支持 `body.kind in [text|list]`；列表≤8行；忽略未知字段
  - 标题注入：若设备已在 `backend/data/devices.yaml` 注册，则覆盖为“工牌{badge} · {owner}”；未注册只记录日志，不在 UI 显示设备标识
  - 限频：每设备≥500ms（≤2 QPS），命中限频丢弃旧帧并记录日志

- 测试指引（后端侧联调）
  - 文本渲染：
    ```json
    { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat","header":{},"body":{"kind":"text","text":"Hello 渲染测试"},"footer":{"hint":"后端→设备 OK"} }
    ```
  - 列表渲染：
    ```json
    { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-002","page":"dialog.chat","header":{},"body":{"kind":"list","items":["第一行","第二行","第三行"]},"footer":{"hint":"最多显示8行"} }
    ```
  - 顶部横幅：
    ```json
    { "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner","text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
    ```

## 编辑内容04 后端直达转发白名单与补投日志（阶段1）
编辑人 -w
- 变更内容 
    - backend/core/websocket_server.py：`send_to_device` 兼容字符串载荷（自动解析 JSON）；补投 last_render 日志改为 `[REDELIVER] device=.. id=..`
    - backend/core/handle/textHandle.py：顶层 `ui.render`/`device.control` 转发加入白名单校验（仅 text|list / net.banner），不通过记 `[DROP_BY_MODE]`；设备上行 `ui.ack/ui.error` 记录耗时（若含 ts）

- 白名单与净化
  - 顶层直达消息：`ui.render` 仅允许 `body.kind in [text,list]`；`device.control` 仅允许 `action==net.banner`
  - 通过服务端 `send_to_device` 下发（内部仍会触发清洗与限频），未通过直接丢弃并日志 `[DROP_BY_MODE]`

- 兼容性
  - 维持既有协议不变，发起方无需调整；阶段1 不回发起方任何回执
  - 设备 ACK/ERROR 统一落日志，若带 `ts` 追加 `elapsedMs`

## 编辑内容05 移除设备上线补发“最后一次渲染”
编辑人 -w
- 变更内容
  - backend/core/websocket_server.py：删除注册时的 last_render 补投调用与实现，后端不再自动补发“上一屏”。
- 原因与影响
  - 原因：阶段1聚焦最小闭环；上线补发非必需且可能引起误会。
  - 影响：设备上线后由编排端决定是否主动下发渲染指令；不影响既有转发、白名单、限频与标题注入逻辑。

```

- 我已删除“设备上线补发最后一次渲染”的后端逻辑：
  - 从 `backend/core/websocket_server.py` 移除了注册时的补投调用与对应函数实现。
  - 不再导入或使用 `get_last`；上线后由业务主动发送需要的渲染。

- 我也在 `collaboration/log.md` 新增“编辑内容05”，记录此次移除及原因与影响。

- 现状不变的能力：定向转发、白名单校验、渲染清洗与限频、设备标题注入、ACK/ERROR 耗时日志仍然保留。

---

**User**

检查这个问题“backend/core/utils/last_render_cache.py::_normalize_device_id 中变量名疑似笔误（使用了未定义的 v），虽不影响当前主链路，但建议尽快修复。”

---

**Cursor**

我先查看该文件的当前实现以确认是否存在变量名笔误，然后如有问题会直接修复并运行 lints。

### 1. 需求分析与方案设计
- 目标：核查 `backend/core/utils/last_render_cache.py::_normalize_device_id` 是否存在“使用未定义的 v”的笔误，并评估是否需要修复。
- 方法：直接审阅函数实现与调用点，确认变量作用域与逻辑正确性。

```9:16:backend/core/utils/last_render_cache.py
def _normalize_device_id(device_id: str | None) -> str | None:
    try:
        if device_id is None:
            return None
        v = str(device_id).strip().strip('"').strip("'")
        return v.lower() if v else None
    except Exception:
        return None
```

结论：`v` 在函数内被明确赋值后再使用，不是未定义变量；函数行为正确，无功能性缺陷。

### 2. 代码实现
无需修改。若你希望提升可读性，可将变量名 `v` 改为更语义化的 `normalized`（非功能性变更，当前不必做）。

### 3. 设计理由与取舍
- 现状正确：`v` 是本地变量，定义即用，不存在“未定义使用”的错误；`set_last/get_last` 的调用链也不受影响。
- 避免无谓改动：阶段1强调最小闭环与稳定性，无需为纯命名偏好引入代码 churn。
- 可选优化：若团队代码规范更偏向语义化命名，再做重命名即可，不改变逻辑与接口。

```python
def _normalize_device_id(device_id: str | None) -> str | None:
    try:
        if device_id is None:
            return None
        v = str(device_id).strip().strip('"').strip("'")
        return v.lower() if v else None
    except Exception:
        return None
```

---

**User**

# 已知内容
项目架构和实施原则请参考bulid.md , 现在是阶段1的收尾, 你负责后端部分 后端部分代码是backend;

# 具体任务1 统一打印口径（五类）
  - SEND（发送前）
    - 打点处：
      - `backend/core/websocket_server.py::send_to_device`（ui.render/device.control 两分支）
      - `backend/core/orchestration/render_sender.py::send_render/send_control`（如有直发）
    - 字段：type, id?, to, mode?, page|action, qps=ok|limited
    - 示例：
      - [SEND] type=ui.render id=d1-002 to=94:a9:90:07:9d:88 mode=testing page=dialog.chat body=list qps=ok
      - [SEND] type=device.control id=d1-003 to=94:a9:90:07:9:88 mode=testing action=net.banner
  - ACK（设备回执）
    - 打点处：`backend/core/handle/textHandle.py` 收到 `ui.ack` 时
    - 字段：id, device, elapsedMs（若 msg.ts 可计算）
    - 示例：[ACK] id=d1-002 device=94:a9:90:07:9d:88 elapsedMs=215
  - DROP（两类）
    - [DROP_BY_MODE]（白名单不通过）：`textHandle.py` 转发入口
      - 字段：type, reason=not-allowed-in-mode, mode, extra（如 body.kind/logs）
    - [DROP_INVALID]（清洗/schema失败/缺字段）：`render_schema.py`/`send_to_device` 失败路径
      - 字段：type, reason, missing? / invalidField?
  - FREEZE（临时封禁）— 本阶段仅日志预留，不启用逻辑
    - 打点处：`render_sender.py`（预留一处日志，不触发真正冻结）
    - 示例：[FREEZE] device=94:a9:90:07:9d:88 seconds=30 reason=ack-timeout id=d1-004（仅示例，阶段1不触发）
  - REDELIVER（补投）— 若当前采取“编排端显式补投”，仅在编排触发处打印
    - 字段：device, id, page
    - 示例：[REDELIVER] device=94:a9:90:07:9d:88 id=wel-001 page=welcome

## 具体改动点与建议实现
  - `backend/core/websocket_server.py::send_to_device`
    - 在分支 `ui.render`/`device.control` 调用前打印 [SEND]，组装字段：
      - type、id（payload.id）、to（device_id）、page 或 action、qps（从 `render_sender` 返回值/状态判断，如限频可标记 limited）
  - `backend/core/orchestration/render_sender.py`
    - 在限频丢帧处，统一用 `[DROP_INVALID] type=ui.render reason=rate-limited interval=<ms> device=<id>`
    - 成功发送后，返回一个状态（ok/limited），供 `send_to_device` 打印 qps=ok|limited（或由此处直接打印 [SEND]）
  - `backend/core/handle/textHandle.py`
    - `ui.ack/ui.error`：统一打印 [ACK]（error 也打印为 ACK，但附 `code` 字段）
      - 带 device（`conn.device_id`）、id（msg.id）、elapsedMs（若 msg.ts 可计算）
    - `DROP_BY_MODE`：已存在，确保键=值风格并补充 `mode=<conn.current_mode>` 与 `detail=<body.kind|action>`
  - `backend/core/orchestration/render_schema.py`
    - 清洗失败/缺字段：打印 `[DROP_INVALID] type=ui.render reason=schema-invalid missing=header/body|kind`（键=值）


# 具体任务2 在确认完成上述任务1后,总结刚刚w做的更新,并在log.md@log.md 新增编辑内容08 编辑人是w (参考之前的log格式);


---

**Cursor**

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional
from copy import deepcopy
from config.logger import setup_logging
from core.utils.device_registry import get_display_title


_logger = setup_logging()


def _norm_str(v: Any) -> Optional[str]:
    try:
        if v is None:
            return None
        s = str(v)
        s = s.strip()
        return s if len(s) > 0 else None
    except Exception:
        return None


def _ensure_list_of_str(items: Any, limit: int = 8) -> Optional[List[str]]:
    if not isinstance(items, list):
        return None
    out: List[str] = []
    for it in items:
        s = _norm_str(it)
        if s is None:
            continue
        out.append(s)
        if len(out) >= limit:
            break
    return out


def _normalize_device_id(v: Optional[str]) -> Optional[str]:
    try:
        if v is None:
            return None
        s = str(v).strip().strip('"').strip("'")
        return s.lower() if s else None
    except Exception:
        return None


def clean_render_payload(device_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """轻量清洗渲染负载。仅允许 body.kind: text|list，并注入设备标题。

    - 强制保留字段：type=ui.render, page, header.title, body, footer.hint, id?
    - body: { kind: text, text } 或 { kind: list, items<=8 }
    - 其它未知字段忽略
    - 注入 header.title：若设备已注册 -> "工牌{badge} · {owner}"；未注册 -> 不注入，仅日志
    """
    if not isinstance(payload, dict):
        try:
            _logger.info("[DROP_INVALID] type=ui.render reason=payload-not-dict device=%s" % device_id)
        except Exception:
            pass
        return None

    device_id_norm = _normalize_device_id(device_id)
    if device_id_norm is None:
        try:
            _logger.info("[DROP_INVALID] type=ui.render reason=device-id-missing")
        except Exception:
            pass
        return None

    typ = _norm_str(payload.get("type")) or "ui.render"
    if typ != "ui.render":
        try:
            _logger.info(f"[DROP_INVALID] type={typ} reason=type-mismatch expected=ui.render device={device_id_norm}")
        except Exception:
            pass
        return None

    page = _norm_str(payload.get("page"))
    if page is None:
        try:
            _logger.info(f"[DROP_INVALID] type=ui.render reason=schema-invalid missing=page device={device_id_norm}")
        except Exception:
            pass
        return None

    header_in = payload.get("header") or {}
    body_in = payload.get("body") or {}
    footer_in = payload.get("footer") or {}

    body_kind = _norm_str(body_in.get("kind"))
    cleaned_body: Optional[Dict[str, Any]] = None
    if body_kind == "text":
        text = _norm_str(body_in.get("text")) or ""
        cleaned_body = {"kind": "text", "text": text}
    elif body_kind == "list":
        items = _ensure_list_of_str(body_in.get("items"), limit=8) or []
        cleaned_body = {"kind": "list", "items": items}
    else:
        # 不支持的 body，直接返回 None
        try:
            _logger.info(f"[DROP_INVALID] type=ui.render reason=unsupported-body-kind kind={body_kind} device={device_id_norm}")
        except Exception:
            pass
        return None

    # 注入标题：如果设备注册过则覆盖；否则不注入，仅日志
    injected_title = get_display_title(device_id_norm)
    if injected_title is None:
        try:
            _logger.info(f"未注册设备，不注入标题 device={device_id_norm}")
        except Exception:
            pass
        title = _norm_str(header_in.get("title")) or ""
    else:
        title = injected_title

    cleaned: Dict[str, Any] = {
        "type": "ui.render",
        "page": page,
        "header": {"title": title},
        "body": cleaned_body,
    }

    # 透传 footer.hint 与 footer.page（若可解析）
    hint = _norm_str(footer_in.get("hint"))
    page_obj = footer_in.get("page") or {}
    try:
        page_index = int(page_obj.get("index"))
        page_total = int(page_obj.get("total"))
        if page_index >= 1 and page_total >= 1:
            footer_page = {"index": page_index, "total": page_total}
        else:
            footer_page = None
    except Exception:
        footer_page = None

    footer_out = {}
    if hint is not None:
        footer_out["hint"] = hint
    if footer_page is not None:
        footer_out["page"] = footer_page
    if len(footer_out) > 0:
        cleaned["footer"] = footer_out

    # 保留 id（幂等/ACK 关联）
    if payload.get("id") is not None:
        cleaned["id"] = str(payload.get("id"))

    return cleaned



```

```python
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional
from config.logger import setup_logging
from core.orchestration.render_schema import clean_render_payload
from core.utils.last_render_cache import set_last


_logger = setup_logging()

# 每设备渲染限频（QPS ≤ 2），实现为最小间隔 500ms
_MIN_INTERVAL_MS = 500

# 记录最近一次发送时间（内存） device_id -> ms
_last_send_ms: dict[str, int] = {}


def _normalize_device_id(v: Optional[str]) -> Optional[str]:
    try:
        if v is None:
            return None
        s = str(v).strip().strip('"').strip("'")
        return s.lower() if s else None
    except Exception:
        return None


async def _send_via_handler(handler, payload: Dict[str, Any]) -> bool:
    try:
        if handler is None:
            return False
        await handler.send_json(payload)
        return True
    except Exception:
        return False


async def send_render(conn_or_device_id: Any, payload: Dict[str, Any]) -> tuple[bool, str]:
    """发送渲染指令：清洗->限频->发送->缓存last。

    conn_or_device_id: ConnectionHandler | str
    """
    # 解析目标 device_id 与 handler
    handler = None
    device_id = None
    if hasattr(conn_or_device_id, "device_id"):
        handler = conn_or_device_id
        device_id = getattr(conn_or_device_id, "device_id", None)
    else:
        device_id = conn_or_device_id
        # 从 server 路由表查找
        try:
            server = getattr(conn_or_device_id, "server", None)
        except Exception:
            server = None
    device_id = _normalize_device_id(device_id)
    if device_id is None:
        return False, "invalid"

    try:
        if handler is None:
            try:
                # 从全局在线表取 handler（通过任一在线连接的 server）
                # 这里通过任何一个已知连接对象的 server 获取在线表；
                # 若不可用，请在调用方传入 handler。
                from core.websocket_server import WebSocketServer  # 仅类型提示
            except Exception:
                pass
            # 兜底：不通过 server 查询（调用方应传 handler）
    except Exception:
        pass

    # 清洗
    cleaned = clean_render_payload(device_id, payload)
    if cleaned is None:
        _logger.info(f"[DROP_INVALID] type=ui.render reason=schema-invalid device={device_id}")
        return False, "invalid"

    # 限频（每设备 ≥500ms）
    now_ms = int(time.time() * 1000)
    last_ms = int(_last_send_ms.get(device_id, 0))
    if now_ms - last_ms < _MIN_INTERVAL_MS:
        # 丢弃旧帧，更新时间戳以允许下次尽快发送
        _last_send_ms[device_id] = now_ms
        _logger.info(f"[DROP_INVALID] type=ui.render reason=rate-limited interval={now_ms - last_ms} device={device_id}")
        return False, "limited"
    _last_send_ms[device_id] = now_ms

    # 发送
    ok = False
    if handler is not None:
        ok = await _send_via_handler(handler, cleaned)
    else:
        # 调用方未提供 handler，由上层调用 send_to_device 实现
        _logger.warning(f"send_render 未提供 handler，请使用 send_to_device 进行路由发送 device={device_id}")
        return False, "invalid"

    if ok:
        try:
            set_last(device_id, cleaned)
        except Exception:
            pass
    return ok, "ok"


async def send_control(conn_or_device_id: Any, action: str = "net.banner", **kw) -> tuple[bool, str]:
    """发送设备控制指令（阶段1仅支持 net.banner）。"""
    handler = None
    device_id = None
    if hasattr(conn_or_device_id, "device_id"):
        handler = conn_or_device_id
        device_id = getattr(conn_or_device_id, "device_id", None)
    else:
        device_id = conn_or_device_id
    device_id = _normalize_device_id(device_id)
    if device_id is None:
        return False, "invalid"

    if action != "net.banner":
        _logger.info(f"[DROP_INVALID] type=device.control reason=unsupported-action action={action} device={device_id}")
        return False, "invalid"

    payload = {
        "type": "device.control",
        "action": "net.banner",
    }
    for k, v in kw.items():
        if k in ("text", "level", "duration_ms", "id"):
            payload[k] = v

    if handler is None:
        _logger.warning("send_control 未提供 handler，请使用 send_to_device 进行路由发送")
        return False, "invalid"
    ok = await _send_via_handler(handler, payload)
    return ok, "ok"



```

```python
import asyncio
import time
import json
import websockets
import socket
from http import HTTPStatus
from config.logger import setup_logging
from core.connection import ConnectionHandler
from config.config_loader import get_config_from_api
from core.utils.modules_initialize import initialize_modules
from core.utils.tasks_store import get_task_store
from core.utils.util import check_vad_update, check_asr_update
from core.utils.offline_queue import pop_offline_for_device
from urllib.parse import urlparse, parse_qs
from core.orchestration.render_sender import send_render, send_control

TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.config_lock = asyncio.Lock()
        self._started_event: asyncio.Event = asyncio.Event()
        self.startup_error: Exception | None = None
        # 设备路由映射：device-id -> ConnectionHandler
        self.device_handlers = {}
        self.device_handlers_lock = asyncio.Lock()
        # 握手缓存：按连接对象 id 缓存原始 path 与解析到的 ids，供 handler 兜底读取
        self._handshake_cache: dict[int, dict] = {}
        modules = initialize_modules(
            self.logger,
            self.config,
            "VAD" in self.config["selected_module"],
            "ASR" in self.config["selected_module"],
            "LLM" in self.config["selected_module"],
            False,
            "Memory" in self.config["selected_module"],
            "Intent" in self.config["selected_module"],
        )
        self._vad = modules["vad"] if "vad" in modules else None
        self._asr = modules["asr"] if "asr" in modules else None
        self._llm = modules["llm"] if "llm" in modules else None
        self._intent = modules["intent"] if "intent" in modules else None
        self._memory = modules["memory"] if "memory" in modules else None

        self.active_connections = set()
        # LLM 单例注册表：key = alias + overrides 指纹
        self.llm_registry: dict[str, object] = {}

    def _normalize_id(self, value: str | None) -> str | None:
        try:
            if value is None:
                return None
            v = str(value).strip().strip('"').strip("'")
            if v == "":
                return None
            return v.lower()
        except Exception:
            return None

    # --- Task 2: Handshake parsing split into pure helpers ---
    @staticmethod
    def extract_raw_path(ws_or_conn, path) -> tuple[str | None, object | None]:
        """Best-effort extract raw path string and return (raw_path, conn_obj)."""
        raw_path_str = None
        conn_obj = None
        if isinstance(path, str) and path:
            raw_path_str = path
        if raw_path_str is None and ws_or_conn is not None and not isinstance(ws_or_conn, str):
            conn_obj = ws_or_conn
            for attr in ("path", "request_uri", "raw_request_uri", "request_path", "raw_path"):
                try:
                    val = getattr(conn_obj, attr, None)
                    if isinstance(val, str) and val:
                        raw_path_str = val
                        break
                except Exception:
                    continue
            if raw_path_str is None:
                try:
                    req = getattr(conn_obj, "request", None) or getattr(conn_obj, "_request", None)
                    if req is not None:
                        for attr in ("path", "target", "raw_path"):
                            try:
                                val = getattr(req, attr, None)
                                if isinstance(val, str) and val:
                                    raw_path_str = val
                                    break
                            except Exception:
                                continue
                except Exception:
                    pass
        return raw_path_str, conn_obj

    @staticmethod
    def parse_query_ids(raw_path_str: str | None) -> tuple[str | None, str | None]:
        """Parse device-id/client-id from raw path query."""
        if not isinstance(raw_path_str, str) or raw_path_str == "":
            return None, None
        try:
            parsed = urlparse(raw_path_str)
            qs = parse_qs(parsed.query or "")
            device_vals = qs.get("device-id") or qs.get("device_id")
            client_vals = qs.get("client-id") or qs.get("client_id")
            device_id = None
            client_id = None
            if device_vals:
                device_id = device_vals[0]
            if client_vals:
                client_id = client_vals[0]
            return device_id, client_id
        except Exception:
            return None, None

    def cache_handshake(self, conn_obj, raw_path_str: str | None, device_id: str | None, client_id: str | None) -> None:
        """Cache handshake info keyed by connection object id."""
        try:
            if conn_obj is not None and device_id is not None:
                self._handshake_cache[id(conn_obj)] = {
                    "raw_path": raw_path_str,
                    "device-id": self._normalize_id(device_id),
                    "client-id": self._normalize_id(client_id) or self._normalize_id(device_id),
                }
        except Exception:
            pass

    def parse_ids_from_handshake(self, ws_or_conn, path) -> tuple[str | None, str | None, str | None]:
        """Thin wrapper using pure helpers."""
        raw_path_str, conn_obj = self.extract_raw_path(ws_or_conn, path)
        device_id, client_id = self.parse_query_ids(raw_path_str)
        did = self._normalize_id(device_id)
        cid = self._normalize_id(client_id) or did
        self.cache_handshake(conn_obj, raw_path_str, did, cid)
        return did, cid, raw_path_str

    def get_or_create_llm(self, alias: str, overrides: dict | None = None):
        """按别名与可选覆盖创建/复用共享 LLM 实例。

        key 规则：f"{alias}::" + json.dumps(overrides, sort_keys=True)（None 视为{}）。
        基础配置来源 self.config['LLM'][alias]，覆盖与类型解析后实例化。
        """
        try:
            import json as _json
            from core.utils import llm as llm_utils
        except Exception:
            raise
        if not isinstance(alias, str) or len(alias) == 0:
            return None
        ov = overrides or {}
        try:
            key = f"{alias}::{_json.dumps(ov, ensure_ascii=False, sort_keys=True)}"
        except Exception:
            # Fallback literal '{}'
            key = f"{alias}::" + "{}"
        # 命中共享实例
        if key in self.llm_registry:
            return self.llm_registry[key]
        # 构造配置
        base_conf = None
        try:
            base_conf = dict(self.config.get("LLM", {}).get(alias, {}))
        except Exception:
            base_conf = None
        if not base_conf:
            # 无法构造，返回 None
            return None
        if isinstance(ov, dict) and ov:
            try:
                for k, v in ov.items():
                    base_conf[k] = v
            except Exception:
                pass
        llm_type = base_conf.get("type", alias)
        instance = llm_utils.create_instance(llm_type, base_conf)
        self.llm_registry[key] = instance
        return instance

    async def start(self):
        # reset start state
        try:
            self._started_event.clear()
        except Exception:
            self._started_event = asyncio.Event()
        self.startup_error = None
        server_config = self.config.get("server", {}) or {}
        host = server_config.get("ip") or "0.0.0.0"
        # 端口健壮化解析
        raw_port = server_config.get("port", 8000)
        try:
            port = int(raw_port) if str(raw_port).strip() != "" else 8000
        except Exception:
            port = 8000

        # 预绑定检测：尽早暴露“端口被占用/权限不足”等问题
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
        except OSError as e:
            self.logger.bind(tag=TAG).error(
                f"WebSocketServer failed to bind preflight {host}:{port}: {e}. \n"
                f"可能原因：端口被占用/权限不足/host非法。请确认无旧进程占用端口或调整 server.port。"
            )
            self.startup_error = e
            self._started_event.set()
            # 直接抛出以让上层捕获（避免静默失败）
            raise

        # 真正启动 WS 服务
        try:
            async with websockets.serve(
                self._handle_connection,
                host,
                port,
                process_request=self._http_response,
                ping_interval=20,
                ping_timeout=50,
                close_timeout=5,
            ):
                # 启动时打印当前在线设备快照（通常为空），便于对照测试页
                online_ids = self.get_online_device_ids()
                self.logger.bind(tag=TAG).info(
                    f"WebSocketServer started on {host}:{port}, online_count={self.get_device_count()}, online={online_ids}; server.stats broadcasting enabled"
                )
                # 标记已启动
                try:
                    self._started_event.set()
                except Exception:
                    pass
                # 周期性广播服务端统计
                asyncio.create_task(self._periodic_stats_task())
                await asyncio.Future()
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"WebSocketServer failed to start on {host}:{port}: {e}"
            )
            self.startup_error = e
            try:
                self._started_event.set()
            except Exception:
                pass
            raise

    async def wait_started(self) -> None:
        await self._started_event.wait()
        if self.startup_error is not None:
            raise self.startup_error

    async def _handle_connection(self, websocket, path=None):
        """处理新连接，每次创建独立的ConnectionHandler
        兼容 websockets 旧接口，接收 path 参数，传递给后续处理。
        """
        # 创建ConnectionHandler时传入当前server实例
        handler = ConnectionHandler(
            self.config,
            self._vad,
            self._asr,
            self._llm,
            self._memory,
            self._intent,
            self,  # 传入server实例
        )
        self.active_connections.add(handler)
        try:
            await handler.handle_connection(websocket, path)
        finally:
            self.active_connections.discard(handler)

    def _http_response(self, path, request_headers):
        """
        websockets 的 process_request 回调。
        - 返回 None 继续握手（WebSocket 升级）
        - 返回 (status, headers, body) 处理普通 HTTP 请求
        """
        try:
            # 诊断：记录升级请求的原始 path（含 query）与关键头部；同时填充握手缓存（若可）
            try:
                _, _, raw_path_str = self.parse_ids_from_handshake(path, path)
                self.logger.bind(tag=TAG).info(
                    f"HTTP upgrade request path={raw_path_str if raw_path_str is not None else path}"
                )
            except Exception:
                pass
            connection_header = (
                (request_headers.get("Connection", "") or request_headers.get("connection", ""))
                .strip()
                .lower()
            )
            upgrade_header = (
                (request_headers.get("Upgrade", "") or request_headers.get("upgrade", ""))
                .strip()
                .lower()
            )
            if "upgrade" in connection_header and upgrade_header == "websocket":
                return None
        except Exception:
            # 容错：如遇到异常，默认继续握手
            return None

        body = b"Server is running\n"
        headers = [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))]
        return 200, headers, body

    async def update_config(self) -> bool:
        """更新服务器配置并重新初始化组件

        Returns:
            bool: 更新是否成功
        """
        try:
            async with self.config_lock:
                # 重新获取配置
                new_config = get_config_from_api(self.config)
                if new_config is None:
                    self.logger.bind(tag=TAG).error("获取新配置失败")
                    return False
                self.logger.bind(tag=TAG).info(f"获取新配置成功")
                # 检查 VAD 和 ASR 类型是否需要更新
                update_vad = check_vad_update(self.config, new_config)
                update_asr = check_asr_update(self.config, new_config)
                self.logger.bind(tag=TAG).info(
                    f"检查VAD和ASR类型是否需要更新: {update_vad} {update_asr}"
                )
                # 更新配置
                self.config = new_config
                # 重新初始化组件
                modules = initialize_modules(
                    self.logger,
                    new_config,
                    update_vad,
                    update_asr,
                    "LLM" in new_config["selected_module"],
                    False,
                    "Memory" in new_config["selected_module"],
                    "Intent" in new_config["selected_module"],
                )

                # 更新组件实例
                if "vad" in modules:
                    self._vad = modules["vad"]
                if "asr" in modules:
                    self._asr = modules["asr"]
                if "llm" in modules:
                    self._llm = modules["llm"]
                if "intent" in modules:
                    self._intent = modules["intent"]
                if "memory" in modules:
                    self._memory = modules["memory"]
                
                # 通知现有连接：清理用途LLM缓存，避免使用旧配置实例
                try:
                    for handler in list(self.active_connections):
                        try:
                            if hasattr(handler, "_llm_cache") and isinstance(handler._llm_cache, dict):
                                handler._llm_cache.clear()
                                # 同时清理 meeting 推送周期，使热更后的间隔在下一周期生效
                                if hasattr(handler, "meeting_push_interval_ms_current"):
                                    try:
                                        delattr(handler, "meeting_push_interval_ms_current")
                                    except Exception:
                                        pass
                        except Exception:
                            continue
                except Exception:
                    pass
                self.logger.bind(tag=TAG).info(f"更新配置任务执行完毕")
                return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"更新服务器配置失败: {str(e)}")
            return False

    # --- Task 2: Decompose register/broadcast/offline/snapshot responsibilities ---
    async def register_or_replace_device_route(self, device_id: str, handler: ConnectionHandler) -> None:
        """Register or replace an existing device route with graceful dual-channel transition."""
        async with self.device_handlers_lock:
            existed = self.device_handlers.get(device_id)
            if existed is not None and existed is not handler:
                self.logger.bind(tag=TAG).warning(
                    f"检测到重复连接，启用双通道过渡(≤2s)并接受新连接: device={device_id}"
                )
                try:
                    if existed.websocket:
                        try:
                            await existed.send_json({
                                "type": "system",
                                "message": "检测到新连接，当前通道将于约1.5秒后关闭以切换到新通道"
                            })
                        except Exception:
                            pass
                        async def _deferred_close(old_handler):
                            try:
                                await asyncio.sleep(1.5)
                                await old_handler.close(old_handler.websocket)
                            except Exception:
                                pass
                        asyncio.create_task(_deferred_close(existed))
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"计划关闭旧连接失败(已忽略): {e}")
            self.device_handlers[device_id] = handler
        self.logger.bind(tag=TAG).info(f"注册设备路由: {device_id}")

    async def deliver_offline_messages(self, device_id: str, handler: ConnectionHandler) -> None:
        """Deliver queued offline messages to the device and notify senders."""
        try:
            pending, dropped = pop_offline_for_device(device_id)
            if not pending:
                return
            try:
                from collections import defaultdict
                sender_counts = defaultdict(int)
            except Exception:
                sender_counts = {}
            sent = 0
            for env in pending:
                try:
                    if handler:
                        await handler.send_json(env)
                    sent += 1
                    try:
                        origin = env.get("from")
                        if isinstance(origin, str) and origin:
                            key = origin.strip().lower()
                            if isinstance(sender_counts, dict):
                                sender_counts[key] = sender_counts.get(key, 0) + 1
                            else:
                                sender_counts[key] += 1
                    except Exception:
                        pass
                except Exception:
                    continue
            self.logger.bind(tag=TAG).info(
                f"离线补投递: device={device_id}, sent={sent}, dropped={dropped}"
            )
            try:
                if isinstance(sender_counts, dict):
                    for origin_id, cnt in sender_counts.items():
                        try:
                            origin_handler = self.device_handlers.get(origin_id)
                            if origin_handler and origin_handler.websocket:
                                payload = {
                                    "type": "peer",
                                    "event": "redelivered",
                                    "to": device_id,
                                    "count": int(cnt),
                                }
                                try:
                                    await origin_handler.send_json(payload)
                                except Exception:
                                    continue
                        except Exception:
                            continue
            except Exception:
                pass
        except Exception:
            pass

    async def broadcast_online_snapshot(self) -> None:
        """Broadcast server stats to all online connections."""
        await self.broadcast_server_stats()

    async def snapshot_workflow_to_group(self, device_id: str, handler: ConnectionHandler) -> None:
        """Send workflow snapshot to the single device's group with optional delay based on config."""
        try:
            try:
                group_key = str(device_id)[:8]
            except Exception:
                group_key = "default"
            tasks = get_task_store().list_by_group(group_key)
            if tasks is None:
                return
            try:
                wf_cfg = (self.config.get("workflow", {}) or {}) if isinstance(self.config, dict) else {}
                test_mode = bool(wf_cfg.get("test_mode", False))
                delay_ms = int(wf_cfg.get("snapshot_on_register_delay_ms", 0))
            except Exception:
                test_mode = False; delay_ms = 0

            async def _send_snapshot():
                envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                try:
                    await handler.send_json(envelope)
                except Exception:
                    pass
                self.logger.bind(tag=TAG).info(f"[Workflow] op=snapshot source=register group={group_key} to={device_id} count={len(tasks)} test_mode={test_mode}")

            if test_mode and delay_ms > 0:
                async def _delayed_snapshot():
                    try:
                        await asyncio.sleep(delay_ms/1000.0)
                        await _send_snapshot()
                    except Exception:
                        pass
                asyncio.create_task(_delayed_snapshot())
            else:
                await _send_snapshot()
        except Exception:
            pass

    async def register_device_handler(self, device_id: str, handler: ConnectionHandler) -> bool:
        """Boundary method: orchestrates registration, stats broadcast, offline redelivery, and workflow snapshot."""
        try:
            await self.register_or_replace_device_route(device_id, handler)
            await self.broadcast_online_snapshot()
            await self.deliver_offline_messages(device_id, handler)
            await self.snapshot_workflow_to_group(device_id, handler)
            return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"注册设备路由失败 {device_id}: {e}")
            return False

    async def unregister_device_handler(self, device_id: str, handler: ConnectionHandler) -> None:
        """注销设备与连接处理器的映射"""
        try:
            async with self.device_handlers_lock:
                if self.device_handlers.get(device_id) is handler:
                    del self.device_handlers[device_id]
            self.logger.bind(tag=TAG).info(f"注销设备路由: {device_id}")
            # 注销后广播一次在线快照
            await self.broadcast_server_stats()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"注销设备路由失败 {device_id}: {e}")

    def get_device_handler(self, device_id: str) -> ConnectionHandler | None:
        """查询目标设备的连接处理器（只读，不加锁用于快速路径）"""
        return self.device_handlers.get(device_id)

    # 便捷查询方法
    def is_device_online(self, device_id: str) -> bool:
        """判断设备是否在线。"""
        return self.device_handlers.get(device_id) is not None

    def get_online_device_ids(self) -> list[str]:
        """获取当前在线设备列表（快照）。"""
        try:
            return list(self.device_handlers.keys())
        except Exception:
            return []

    async def get_online_device_ids_async(self) -> list[str]:
        """获取在线设备ID（加锁快照），避免与注册/注销竞态。"""
        try:
            async with self.device_handlers_lock:
                return list(self.device_handlers.keys())
        except Exception:
            return []

    def get_device_count(self) -> int:
        """在线设备数量。"""
        return len(self.device_handlers)

    def get_broadcast_targets(self, exclude_device_id: str | None = None) -> list[str]:
        """广播目标集合（可排除某个设备）。"""
        ids = self.get_online_device_ids()
        if exclude_device_id is None:
            return ids
        return [d for d in ids if d != exclude_device_id]

    async def get_broadcast_targets_async(self, exclude_device_id: str | None = None) -> list[str]:
        """广播目标集合（加锁）。"""
        ids = await self.get_online_device_ids_async()
        if exclude_device_id is None:
            return ids
        return [d for d in ids if d != exclude_device_id]

    def get_server_stats_json(self) -> dict:
        """构造服务器观测数据 JSON。"""
        stats = {
            "type": "server",
            "event": "stats",
            "ts": int(time.time() * 1000),
            "deviceCount": self.get_device_count(),
            "online": self.get_online_device_ids(),
        }
        try:
            import psutil  # 已在 requirements 中

            stats["cpuPercent"] = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            stats["memPercent"] = vm.percent
            stats["memUsedMB"] = int(vm.used / (1024 * 1024))
            stats["memTotalMB"] = int(vm.total / (1024 * 1024))
        except Exception:
            pass
        return stats

    async def broadcast_server_stats(self) -> None:
        """向所有在线连接广播服务端统计。"""
        try:
            payload = self.get_server_stats_json()
            for handler in list(self.device_handlers.values()):
                try:
                    if handler:
                        await handler.send_json(payload)
                except Exception:
                    continue
        except Exception:
            pass

    async def _periodic_stats_task(self) -> None:
        """周期广播服务端统计信息。"""
        try:
            while True:
                await asyncio.sleep(10)
                await self.broadcast_server_stats()
        except asyncio.CancelledError:
            return
        except Exception:
            return

    # --- Task 1: 路由与发送 ---
    async def send_to_device(self, device_id: str, payload) -> bool:
        """向指定在线设备发送两类消息：ui.render / device.control。

        - 标准化 device_id
        - 去除 payload.to 字段
        - ui.render: 调用 send_render（限频+清洗+缓存）
        - device.control: 调用 send_control（阶段1仅支持 net.banner）
        """
        try:
            # 兼容字符串载荷：尝试解析为 JSON
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    self.logger.bind(tag=TAG).warning("send_to_device: string payload 不是有效 JSON，已丢弃")
                    return False
            if not isinstance(payload, dict):
                return False
            did = self._normalize_id(device_id)
            if did is None:
                return False
            handler = self.get_device_handler(did)
            if handler is None:
                self.logger.bind(tag=TAG).info(f"目标设备不在线，忽略下发 device={did}")
                return False
            # 拷贝并去除 to
            to_remove = dict(payload)
            try:
                to_remove.pop("to", None)
            except Exception:
                pass
            typ = (to_remove.get("type") or "").strip().lower()
            if typ == "ui.render":
                # 打印 [SEND]（qps 状态由 render_sender 返回）
                page = (to_remove.get("page") or "").strip()
                body = (to_remove.get("body") or {}).get("kind")
                _id = to_remove.get("id")
                ok, status = await send_render(handler, to_remove)
                qps = "limited" if status == "limited" else "ok"
                try:
                    self.logger.bind(tag=TAG).info(
                        f"[SEND] type=ui.render id={_id} to={did} mode={getattr(handler, 'current_mode', None)} page={page} body={body} qps={qps}"
                    )
                except Exception:
                    pass
                return bool(ok)
            elif typ == "device.control":
                action = (to_remove.get("action") or "").strip()
                _id = to_remove.get("id")
                extras = {k: v for k, v in to_remove.items() if k in ("text", "level", "duration_ms", "id")}
                ok, status = await send_control(handler, action=action, **extras)
                try:
                    self.logger.bind(tag=TAG).info(
                        f"[SEND] type=device.control id={_id} to={did} mode={getattr(handler, 'current_mode', None)} action={action}"
                    )
                except Exception:
                    pass
                return bool(ok)
            else:
                self.logger.bind(tag=TAG).warning(f"send_to_device: 不支持的type={typ}")
                return False
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"send_to_device 异常: {e}")
            return False

```

```python
import json
import asyncio
import time
from typing import Dict, Callable, Any
from core.handle.abortHandle import handleAbortMessage
from core.handle.helloHandle import handleHelloMessage
from core.handle.mcpHandle import handle_mcp_message
from core.handle.peerHandle import handle_peer_message
from core.handle.meeting_handle import handle_meeting_message, finalize_meeting_and_send_summary
from core.handle.coding_handle import handle_coding_message
from core.handle.workflow_handle import handle_workflow_message
from core.utils.util import remove_punctuation_and_length, filter_sensitive_info
from core.handle.receiveAudioHandle import startToChat, handleAudioMessage
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.iotHandle import handleIotDescriptors, handleIotStatus
from core.handle.reportHandle import enqueue_asr_report
from core.utils.tasks_store import get_task_store
from config.logger import truncate_for_log

TAG = __name__


async def handle_hello(conn, msg_json: Dict[str, Any]) -> None:
    """处理 hello 消息"""
    await handleHelloMessage(conn, msg_json)


async def handle_abort(conn, msg_json: Dict[str, Any]) -> None:
    """处理 abort 消息"""
    await handleAbortMessage(conn)


# 序号解析与直达意图分类（detect 与 STT 复用）
def _parse_target_index(text: str):
    """解析序号：第N个/第N条/任务一/工作一/数字/task N/first/second/third。返回1-based或None。"""
    try:
        t = (text or "").lower().strip()
        if not t:
            return None
        # 英文序数词
        ord_en = {
            "first":1,"second":2,"third":3,"fourth":4,"fifth":5,
            "sixth":6,"seventh":7,"eighth":8,"ninth":9,"tenth":10
        }
        for k,v in ord_en.items():
            if k in t:
                return v
        import re
        # task N / 第N个 / 第N条 / 第N
        m = re.search(r"(?:task|第|条|个)\s*(\d+)", t)
        if m:
            n = int(m.group(1))
            return n if n>0 else None
        # 任务一/工作一/第十
        ord_cn = {"一":1,"二":2,"两":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
        for k,v in ord_cn.items():
            if f"任务{k}" in t or f"工作{k}" in t or f"第{k}" in t:
                return v
        # 裸数字
        m2 = re.search(r"\b(\d{1,2})\b", t)
        if m2:
            n = int(m2.group(1))
            return n if n>0 else None
    except Exception:
        return None
    return None


async def handle_listen(conn, msg_json: Dict[str, Any]) -> None:
    """处理 listen 消息"""
    if "mode" in msg_json:
        conn.client_listen_mode = msg_json["mode"]
        conn.logger.bind(tag=TAG).debug(f"客户端拾音模式：{conn.client_listen_mode}")
    
    state = msg_json.get("state")
    if state == "start":
        # 最小去抖：忽略距上次同类事件 <300ms 的重复 start
        now_ms = int(time.time() * 1000)
        last_ms = int(getattr(conn, "_last_listen_start_ms", 0) or 0)
        if now_ms - last_ms < 300:
            return
        conn._last_listen_start_ms = now_ms
        
        conn.client_have_voice = True
        conn.client_voice_stop = False
        # 记录设备侧边界最新时间，用于回退策略判断
        conn._last_listen_event_ms = now_ms
        
    elif state == "stop":
        # 最小去抖：忽略距上次同类事件 <300ms 的重复 stop
        now_ms = int(time.time() * 1000)
        last_ms = int(getattr(conn, "_last_listen_stop_ms", 0) or 0)
        if now_ms - last_ms < 300:
            return
        conn._last_listen_stop_ms = now_ms

        conn.client_have_voice = True
        conn.client_voice_stop = True
        conn._last_listen_event_ms = now_ms

        # 通知流式ASR“本段结束”，促使尽快产出最终结果（保留兜底）
        try:
            if getattr(conn, "asr", None) is not None and hasattr(conn.asr, "on_client_listen_stop"):
                maybe = conn.asr.on_client_listen_stop(conn)
                if asyncio.iscoroutine(maybe):
                    await maybe
        except Exception:
            pass

        # 兼容旧流程：仍保留 b"" 触发兜底
        if len(conn.asr_audio) > 0:
            await handleAudioMessage(conn, b"")
            
    elif state == "detect":
        conn.client_have_voice = False
        conn.asr_audio.clear()
        
        if "text" in msg_json:
            await handle_listen_detect(conn, msg_json)


async def handle_listen_detect(conn, msg_json: Dict[str, Any]) -> None:
    """处理 listen detect 消息的文本识别部分"""
    original_text = msg_json["text"]
    filtered_len, filtered_text = remove_punctuation_and_length(original_text)
    
    # 模式切换（进入工作模式）意图识别
    normalized = str(original_text or "").strip().lower()
    mode_switch_keywords = [
        "进入工作模式", "工作模式", "切到工作模式", "切换到工作模式",
        "workflow mode", "working mode", "switch to working mode", "enter working mode",
    ]
    if any(k.lower() in normalized for k in mode_switch_keywords):
        # 下发带意图标注的 STT
        await conn.send_json({
            "type": "stt",
            "text": original_text,
            "intent": "mode_switch",
            "target_mode": "working",
            "session_id": getattr(conn, "session_id", ""),
        })
        
        # 复用现有 mode 流程
        await handle_mode(conn, {"type": "mode", "state": "start", "mode": "working"})
        return
    
    # 识别是否是唤醒词
    is_wakeup_words = filtered_text in conn.config.get("wakeup_words")
    enable_greeting = conn.config.get("enable_greeting", True)
    
    if is_wakeup_words and not enable_greeting:
        await send_stt_message(conn, original_text)
        await send_tts_message(conn, "stop", None)
        conn.client_is_speaking = False
    elif is_wakeup_words:
        conn.just_woken_up = True
        enqueue_asr_report(conn, "嘿，你好呀", [])
        await startToChat(conn, "嘿，你好呀")
    else:
        # 语音指令直达（工作模式）
        if getattr(conn, "current_mode", None) == "working":
            if await handle_working_voice_command(conn, original_text):
                return
        
        # 默认走常规对话
        enqueue_asr_report(conn, original_text, [])
        await startToChat(conn, original_text)


async def handle_working_voice_command(conn, text: str) -> bool:
    """处理工作模式的语音指令，返回是否已处理"""
    normalized = str(text or "").strip().lower()
    
    # 同义词扩充，允许“工作/任务”混用
    assign_kw   = ["认领任务","领取任务","我来做","assign to me","claim task","接收","接受","接手","接单","接收工作","接受工作","接手工作"]
    complete_kw = ["完成任务","标记完成","做完了","mark done","complete task","搞定了","已完成","完成工作","办完工作"]
    refresh_kw  = ["刷新列表","刷新任务","拉取任务","刷新","update list","pull","更新列表"]
    
    intent = None
    if any(k.lower() in normalized for k in assign_kw):
        intent = "assign"
    elif any(k.lower() in normalized for k in complete_kw):
        intent = "complete"
    elif any(k.lower() in normalized for k in refresh_kw):
        intent = "refresh"
    
    # 统一序号解析：第N个/任务一/工作一/数字/task N/first/second/third
    index = _parse_target_index(normalized)
    
    if intent is None:
        return False
    
    # 发送轻量意图回包
    await conn.send_json({
        "type": "workflow",
        "event": "command",
        "intent": intent,
    })
    
    # 执行具体指令
    store = get_task_store()
    group_key = (getattr(conn, "device_id", "") or "")[:8]
    # 诊断日志
    try:
        tasks_open_for_log = [t for t in (store.list_by_group(group_key) or []) if (t.get("status") or "open") == "open"]
        target_id_log = None
        if index and 1 <= index <= len(tasks_open_for_log):
            target_id_log = tasks_open_for_log[index - 1].get("id")
        conn.logger.bind(tag=TAG).info(f"working_voice_intent: intent={intent} n={index} open_count={len(tasks_open_for_log)} target_id={target_id_log}")
    except Exception:
        pass
    
    if intent == "refresh":
        tasks = store.list_by_group(group_key)
        envelope = {"type": "workflow", "event": "update", "tasks": tasks}
        await conn.send_json(envelope)
        return True
    
    # 认领/完成：取最近一个可操作任务
    tasks = store.list_by_group(group_key) or []
    target_id = None
    
    if intent == "assign":
        tasks_open = [t for t in tasks if (t.get("status") or "open") == "open"]
        if index and tasks_open and 1 <= index <= len(tasks_open):
            target_id = tasks_open[index - 1].get("id")
        else:
            for t in tasks:
                if t.get("status") == "open" and (not t.get("owner") or t.get("owner") != getattr(conn, "device_id", None)):
                    target_id = t.get("id")
                    break
            if target_id is None and tasks:
                target_id = tasks[0].get("id")
        if target_id:
            await handle_workflow_message(conn, {"type": "workflow", "event": "assign", "id": target_id})
            return True
            
    elif intent == "complete":
        tasks_open = [t for t in tasks if (t.get("status") or "open") == "open"]
        if index and tasks_open and 1 <= index <= len(tasks_open):
            target_id = tasks_open[index - 1].get("id")
        else:
            for t in tasks:
                if t.get("status") == "open":
                    target_id = t.get("id")
                    break
        if target_id:
            await handle_workflow_message(conn, {"type": "workflow", "event": "complete", "ids": [target_id]})
            return True
    
    return False


async def handle_iot(conn, msg_json: Dict[str, Any]) -> None:
    """处理 IoT 消息"""
    if "descriptors" in msg_json:
        asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
    if "states" in msg_json:
        asyncio.create_task(handleIotStatus(conn, msg_json["states"]))


async def handle_mcp(conn, msg_json: Dict[str, Any]) -> None:
    """处理 MCP 消息"""
    if "payload" in msg_json:
        asyncio.create_task(handle_mcp_message(conn, conn.mcp_client, msg_json["payload"]))


async def handle_meeting(conn, msg_json: Dict[str, Any]) -> None:
    """处理会议消息"""
    if msg_json.get("phase") == "finalize":
        # 立即回执
        conn.logger.bind(tag=TAG).info("finalize request")
        ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
        pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
        await conn.send_json({
            "type": "meeting",
            "phase": "finalize",
            "sessionId": getattr(conn, "session_id", ""),
            "startedAt": ack_started_at,
            "pendingCount": pending_count,
        })
        conn.logger.bind(tag=TAG).info("send ack")
        
        # 标记 finalize 中
        setattr(conn, "meeting_finalizing", True)
        
        # 停止会中定时任务
        try:
            from core.handle.meeting_handle import stop_meeting_timers
            stop_meeting_timers(conn)
            conn.logger.bind(tag=TAG).info("stop timers done")
        except Exception:
            conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
        
        # 关闭/重置 ASR 流式连接
        try:
            if getattr(conn, "asr", None) is not None:
                if hasattr(conn.asr, "stop_ws_connection"):
                    conn.asr.stop_ws_connection()
                import inspect
                if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                    asyncio.create_task(conn.asr.close())
        except Exception:
            pass
        
        # 异步生成并下发最终纪要
        asyncio.create_task(finalize_meeting_and_send_summary(conn))
    else:
        asyncio.create_task(handle_meeting_message(conn, msg_json))


async def handle_coding(conn, msg_json: Dict[str, Any]) -> None:
    """处理编码消息"""
    asyncio.create_task(handle_coding_message(conn, msg_json))


async def handle_workflow(conn, msg_json: Dict[str, Any]) -> None:
    """处理工作流消息"""
    asyncio.create_task(handle_workflow_message(conn, msg_json))
    # 接受 workflow.update 以落库任务（便于种子任务注入）
    if msg_json.get("event") == "update":
        try:
            store = get_task_store()
            group_key = (getattr(conn, "device_id", "") or "")[:8]
            for t in (msg_json.get("tasks") or []):
                try:
                    store.upsert(group_key, t)
                except Exception:
                    pass
        except Exception:
            pass


async def handle_config_update(conn, msg_json: Dict[str, Any]) -> None:
    """处理配置更新消息（兼容旧版）"""
    try:
        cfg_keys = list((msg_json.get("config") or {}).keys())
        conn.logger.bind(tag=TAG).info(f"收到兼容 config_update（忽略实际更新）：keys={cfg_keys}")
    except Exception:
        conn.logger.bind(tag=TAG).info("收到兼容 config_update（忽略实际更新）")
    
    await conn.send_json({"type": "config_update", "status": "ok", "noop": True})


async def handle_mode(conn, msg_json: Dict[str, Any]) -> None:
    """处理模式切换消息"""
    state = msg_json.get("state")
    mode = msg_json.get("mode")
    
    if state not in ["start", "end"] or mode not in ["meeting", "coding", "working"]:
        return
    
    if state == "start":
        # 幂等：若已处于该模式则直接回执
        if getattr(conn, "current_mode", None) == mode:
            await conn.send_json({
                "type": "mode",
                "status": "ok",
                "state": "start",
                "mode": mode
            })
            return
        
        conn.current_mode = mode
        
        if mode == "meeting":
            await handle_meeting_mode_start(conn)
        elif mode == "working":
            await handle_working_mode_start(conn)
        elif mode == "coding":
            await handle_coding_mode_start(conn)
    
    elif state == "end":
        if conn.current_mode == mode:
            conn.current_mode = None
            # 清理相关状态
            if mode == "meeting":
                conn.meeting_segments.clear()
                conn.meeting_start_ts = 0
            elif mode == "coding":
                conn.coding_stream_running = False
                conn.coding_phase_name = ""
        
        await conn.send_json({
            "type": "mode",
            "status": "ok",
            "state": "end",
            "mode": mode
        })


async def handle_meeting_mode_start(conn) -> None:
    """处理会议模式启动"""
    conn.meeting_segments.clear()
    conn.meeting_start_ts = time.time() * 1000
    conn.meeting_last_snippet_ts = 0.0
    conn.meeting_last_snippet_index = 0
    
    # 播放进入会议提示音
    await conn.send_json({
        "type": "tts",
        "state": "start",
        "url": "config/assets/evening.wav",
        "text": "已进入会议模式"
    })
    await conn.send_json({
        "type": "tts",
        "state": "stop"
    })
    
    # 会议模式优先设备侧VAD
    try:
        srv = getattr(conn, "server", None)
        base_cfg = getattr(srv, "config", None) if srv else None
        if isinstance(base_cfg, dict):
            meeting_cfg = base_cfg.get("meeting", {})
        else:
            meeting_cfg = conn.config.get("meeting", {})
    except Exception:
        meeting_cfg = conn.config.get("meeting", {})
    
    if bool(meeting_cfg.get("prefer_device_vad", True)):
        conn.client_listen_mode = "manual"
        conn.logger.bind(tag=TAG).info("会议模式已启用设备侧VAD优先")
    
    # 尝试加载活跃会中状态
    try:
        from core.handle.meeting_handle import load_active_state_if_any, start_meeting_timers
        await load_active_state_if_any(conn)
        start_meeting_timers(conn)
    except Exception:
        pass
    
    await conn.send_json({
        "type": "mode",
        "status": "ok",
        "state": "start",
        "mode": "meeting"
    })


async def handle_working_mode_start(conn) -> None:
    """处理工作模式启动"""
    # 发送一次任务列表
    store = get_task_store()
    group_key = (getattr(conn, "device_id", "") or "")[:8]
    tasks = store.list_by_group(group_key)
    await conn.send_json({
        "type": "workflow",
        "event": "update",
        "tasks": tasks
    })
    
    await conn.send_json({
        "type": "mode",
        "status": "ok",
        "state": "start",
        "mode": "working"
    })


async def handle_coding_mode_start(conn) -> None:
    """处理编码模式启动"""
    conn.coding_stream_running = False
    conn.coding_phase_name = ""
    
    await conn.send_json({
        "type": "mode",
        "status": "ok",
        "state": "start",
        "mode": "coding"
    })


async def handle_peer(conn, msg_json: Dict[str, Any]) -> None:
    """处理 peer 消息"""
    try:
        # 透传顶层路由字段 to 给处理器，避免在 handler 内部引用未定义的变量
        to_list = msg_json.get("to", []) or []
        category = msg_json.get("category")  # 可选，主要用于快捷路径；不参与 schema 校验
        payload = msg_json.get("payload") or {}
        asyncio.create_task(handle_peer_message(conn, category, payload, to_list))
    except Exception:
        asyncio.create_task(handle_peer_message(conn, None, {}, []))


# 消息处理路由表
MESSAGE_HANDLERS: Dict[str, Callable] = {
    "hello": handle_hello,
    "abort": handle_abort,
    "listen": handle_listen,
    "iot": handle_iot,
    "mcp": handle_mcp,
    "meeting": handle_meeting,
    "coding": handle_coding,
    "workflow": handle_workflow,
    "config_update": handle_config_update,
    "mode": handle_mode,
    "peer": handle_peer,
}


async def handleTextMessage(conn, message):
    """处理文本消息的主入口"""
    try:
        msg_json = json.loads(message)
        
        # 处理整数消息（回显）
        if isinstance(msg_json, int):
            try:
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message if isinstance(message, str) else str(message)
            conn.logger.bind(tag=TAG).info(f"收到文本消息：{safe_msg}")
            await conn.send_text(message)
            return
        
        # 获取消息类型
        msg_type = msg_json.get("type")
        if not msg_type:
            conn.logger.bind(tag=TAG).warning(f"收到未知类型消息：{truncate_for_log(message)}")
            return
        
        # 设备上行 ACK/ERROR 统一 [ACK] 打点（阶段1不回发起方）
        if msg_type in ("ui.ack", "ui.error"):
            try:
                ts = msg_json.get("ts")
                elapsed = None
                if isinstance(ts, (int, float)):
                    try:
                        now_ms = int(time.time() * 1000)
                        elapsed = now_ms - int(ts)
                    except Exception:
                        elapsed = None
                _id = msg_json.get("id")
                code = msg_json.get("code") if msg_type == "ui.error" else None
                base = f"[ACK] id={_id} device={getattr(conn, 'device_id', None)}"
                if elapsed is not None:
                    base += f" elapsedMs={elapsed}"
                if code is not None:
                    base += f" code={code}"
                conn.logger.bind(tag=TAG).info(base)
            except Exception:
                conn.logger.bind(tag=TAG).info("[ACK] malformed")
            return

        # 消息转发：ui.render / device.control（热修，不改协议）
        if msg_type in ("ui.render", "device.control") and isinstance(msg_json.get("to"), list):
            to_list = [
                str(x).strip().strip('"').strip("'").lower()
                for x in (msg_json.get("to") or [])
                if str(x).strip() != ""
            ]
            if len(to_list) == 0:
                conn.logger.bind(tag=TAG).info("转发忽略：to 为空")
                return
            # 白名单校验：阶段1 仅允许 ui.render(text|list) 与 device.control(net.banner)
            allow = False
            if msg_type == "ui.render":
                body_kind = None
                try:
                    body = msg_json.get("body") or {}
                    body_kind = (body.get("kind") or "").strip().lower()
                except Exception:
                    body_kind = None
                allow = body_kind in ("text", "list")
            elif msg_type == "device.control":
                allow = (msg_json.get("action") == "net.banner")

            if not allow:
                mode = getattr(conn, "current_mode", None)
                detail = (msg_json.get("body") or {}).get("kind") if msg_type == "ui.render" else msg_json.get("action")
                conn.logger.bind(tag=TAG).info(
                    f"[DROP_BY_MODE] type={msg_type} reason=not-allowed-in-mode mode={mode} detail={detail}"
                )
                return

            # 并发转发到各在线设备；不在线仅日志；不回执
            async def _forward_one(did: str):
                try:
                    server = getattr(conn, "server", None)
                    if server is None or not hasattr(server, "send_to_device"):
                        return
                    ok = await server.send_to_device(did, msg_json)
                    if not ok:
                        conn.logger.bind(tag=TAG).info(f"设备不在线或发送失败：{did}")
                except Exception:
                    pass

            await asyncio.gather(*[_forward_one(d) for d in to_list])
            return

        # 记录消息日志
        try:
            if msg_type in ["hello", "listen", "iot", "mcp"]:
                safe_msg = truncate_for_log(message)
            elif msg_type in ["meeting", "coding", "workflow"]:
                safe_msg = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            else:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到{msg_type}消息：{safe_msg}")
        except Exception:
            conn.logger.bind(tag=TAG).info(f"收到{msg_type}消息")
        
        # 查找并执行对应的处理器
        handler = MESSAGE_HANDLERS.get(msg_type)
        if handler:
            await handler(conn, msg_json)
        else:
            conn.logger.bind(tag=TAG).warning(f"未知消息类型：{msg_type}")
            
    except json.JSONDecodeError:
        conn.logger.bind(tag=TAG).error(f"JSON解析失败：{truncate_for_log(message)}")
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"处理文本消息异常：{e}")

```

```markdown
## 协同工作日志记录

8.22

## 编辑内容1 框架更新 确定渲染协议契约（v1）
编辑人 -w
- 变更内容 build.md prompt.md 全流程演示.md

## 编辑内容02 硬件引擎接入 UI 渲染最小闭环（阶段1）
编辑人 -w
- 变更内容 
    - hardware/main 增加 display/eink_render_engine.*；
    - 接入 application.cc OnIncomingJson 处理 ui.render 与 device.control(net.banner)；
    - 新增 Protocol::SendJson；唤醒后进入渲染测试页（等待后端指令…）；更新 CMakeLists.txt 编译新引擎；
    - 日志输出 [RENDER_RX]/[RENDER_OK]/[RENDER_ERR]

- 新增文件/接口
  - hardware/main/display/eink_render_engine.h/.cc：新增 `EinkRenderEngine`
    - 接口：`void Init(EinkDisplayST7306* display)`；`bool Render(const RenderPayload& payload)`；`void ShowNetBanner(const std::string& text, int duration_ms=3000)`
    - 数据结构：`RenderPayload{ page, headerTitle, bodyKind(TEXT|LIST), bodyText, bodyList(≤8), footerHint }`
    - 能力：整屏刷新、≥500ms合并节流（后台任务）、UTF‑8安全截断（title≤96B、正文≤120B、footer≤96B）、列表最多8行
  - hardware/main/display/eink_display_st7306.h/.cc：增加最小渲染辅助
    - `bool RenderSimplePage(title, bodyIsList, bodyText, bodyList, footerHint)` 整屏渲染并切换 `STATE_INTERACTIVE_UI`，避免欢迎/名片页时钟覆盖
    - `void ShowTopBanner(text)` 顶部红条白字横幅（3s 由引擎恢复上次渲染）

- application 接入
  - 初始化引擎：在 `Start()` 中对 `EinkDisplayST7306` 调用 `g_eink_render_engine.Init(...)`
  - 打开控制通道：`Opening control channel for render engine...`（保证能接收 JSON 指令）
  - OnIncomingJson 仅保留渲染相关分支：
    - `type=="ui.render"`：解析 header.title / body.kind in [text|list] / body.text / body.items / footer.hint / id?；调用 `EinkRenderEngine::Render(payload)`；回 `{type:"ui.ack",status:"ok",id}`；错误回 `{type:"ui.error",code:"INVALID_PAYLOAD",id?}`
    - `type=="device.control" && action=="net.banner"`：显示顶部横幅3s；含 id 回 ACK
    - `type=="peer"`（透传）：当 `payload.type` 为 `ui.render|device.control` 时等价处理（便于后端经 peer 转发）
  - 唤醒流程（阶段1）：欢迎态唤醒仅渲染固定“渲染测试页（等待后端指令…）”，不建立语音会话、不上报音频；停止唤醒词检测，置 Idle
  - 日志：`[RENDER_RX] type/page/id`、`[RENDER_OK] id`、`[RENDER_ERR] code`

- 协议/网络
  - `protocols/protocol.h/.cc`：新增 `bool SendJson(const std::string& json)` 复用底层 `SendText` 用于回 ACK/错误
  - `protocols/websocket_protocol.cc`：连接 URL 追加查询参数 `?device-id=<mac小写>&client-id=<uuid>`，确保后端正确路由设备（后端日志显示握手解析 device-id）

- 构建/依赖
  - `hardware/main/CMakeLists.txt`：新增源文件 `display/eink_render_engine.cc`

- 显示行为变化
  - 欢迎页→时钟更新只在 `STATE_WELCOME/STATE_CARD_DISPLAY` 下执行；渲染页切到 `STATE_INTERACTIVE_UI` 后不再被时钟覆盖
  - 横幅 3 秒后自动恢复上次渲染内容 (“临时提醒/公告”，对当前页面非侵入式覆盖展示，约 3 秒后自动回到原页面。)

- 测试指引（硬件侧联调）
  - 首选：后端直发顶层 `ui.render` / `device.control`，按 `device-id` 路由到设备（可在消息中带 `to:["<device-id>"]` 或后端通过握手 `device-id` 直接匹配路由）
  - 可选（过渡，不推荐）：`peer` 透传渲染，仅用于后端尚未实现直达路由时的应急联调

## 编辑内容03 后端渲染路由与发送接入（阶段1）
编辑人 -w
- 变更内容 
    - backend/core/websocket_server.py：新增设备直达发送与补投；注册流程补投 last_render
    - backend/core/handle/textHandle.py：统一入口实现 `ui.render` / `device.control` 转发与 ACK/ERROR 日志
    - backend/core/orchestration/render_schema.py：渲染负载轻量清洗（仅 text|list，忽略未知字段）并注入标题
    - backend/core/orchestration/render_sender.py：发送器（每设备≤2 QPS 限频、成功后缓存 last_render）
    - backend/core/utils/last_render_cache.py：内存缓存 set_last/get_last
    - backend/core/utils/device_registry.py：读取 `backend/data/devices.yaml`，提供 `get_display_title()`

- 新增文件/接口
  - websocket_server：`async def send_to_device(device_id, payload)`（直达路由；自动去除 `to` 字段；`ui.render`→清洗+限频+缓存，`device.control`→阶段1仅支持 `net.banner`）
  - websocket_server：`async def deliver_last_render_snapshot(device_id, handler)`（设备注册后补投“最后一次渲染”）
  - render_schema：`clean_render_payload(device_id, payload)`（只允许 `body.kind: text|list`，UTF-8 安全；忽略未知字段；注入标题）
  - render_sender：`send_render(conn_or_device_id, payload)`、`send_control(conn_or_device_id, action="net.banner", **kw)`（限频≥500ms/设备；成功后 `set_last`）
  - last_render_cache：`set_last/get_last`
  - device_registry：`get_display_title(device_id)`（返回“工牌{badge} · {owner}”，未注册返回 None）

- 行为/协议（阶段1）
  - 任意已连接客户端可发送顶层 `ui.render` / `device.control`，当携带 `to:["<device-id>", ...]` 时：
    - 标准化目标ID（小写、去空格/引号）
    - 删除 `to` 字段后分别投递到每个在线设备；不在线仅日志，不回执给发起方
  - 设备上行 `{type:"ui.ack"|"ui.error"}`：仅透传到服务端日志（不回送发起方）
  - 设备注册成功后：若存在 `last_render_cache`，立即补投一次
  - 渲染清洗：仅支持 `body.kind in [text|list]`；列表≤8行；忽略未知字段
  - 标题注入：若设备已在 `backend/data/devices.yaml` 注册，则覆盖为“工牌{badge} · {owner}”；未注册只记录日志，不在 UI 显示设备标识
  - 限频：每设备≥500ms（≤2 QPS），命中限频丢弃旧帧并记录日志

- 测试指引（后端侧联调）
  - 文本渲染：
    ```json
    { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat","header":{},"body":{"kind":"text","text":"Hello 渲染测试"},"footer":{"hint":"后端→设备 OK"} }
    ```
  - 列表渲染：
    ```json
    { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-002","page":"dialog.chat","header":{},"body":{"kind":"list","items":["第一行","第二行","第三行"]},"footer":{"hint":"最多显示8行"} }
    ```
  - 顶部横幅：
    ```json
    { "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner","text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
    ```

## 编辑内容04 后端直达转发白名单与补投日志（阶段1）
编辑人 -w
- 变更内容 
    - backend/core/websocket_server.py：`send_to_device` 兼容字符串载荷（自动解析 JSON）；补投 last_render 日志改为 `[REDELIVER] device=.. id=..`
    - backend/core/handle/textHandle.py：顶层 `ui.render`/`device.control` 转发加入白名单校验（仅 text|list / net.banner），不通过记 `[DROP_BY_MODE]`；设备上行 `ui.ack/ui.error` 记录耗时（若含 ts）

- 白名单与净化
  - 顶层直达消息：`ui.render` 仅允许 `body.kind in [text,list]`；`device.control` 仅允许 `action==net.banner`
  - 通过服务端 `send_to_device` 下发（内部仍会触发清洗与限频），未通过直接丢弃并日志 `[DROP_BY_MODE]`

- 兼容性
  - 维持既有协议不变，发起方无需调整；阶段1 不回发起方任何回执
  - 设备 ACK/ERROR 统一落日志，若带 `ts` 追加 `elapsedMs`

## 编辑内容05 移除设备上线补发“最后一次渲染”
编辑人 -w
- 变更内容
  - backend/core/websocket_server.py：删除注册时的 last_render 补投调用与实现，后端不再自动补发“上一屏”。
- 原因与影响
  - 原因：阶段1聚焦最小闭环；上线补发非必需且可能引起误会。
  - 影响：设备上线后由编排端决定是否主动下发渲染指令；不影响既有转发、白名单、限频与标题注入逻辑。

## 编辑内容06 硬件稳定性修复与渲染链路加固
编辑人 -w
- 变更内容（硬件侧汇总）
  - hardware/main/application.cc：
    - JSON 指令处理巩固：`OnIncomingJson` 保持仅处理 `ui.render` 与 `device.control(action==net.banner)`，并支持 `peer.payload` 透传等价处理；渲染成功/失败分别回 `{type:"ui.ack"}` 与 `{type:"ui.error"}`；统一日志 `[RENDER_RX] / [RENDER_OK] / [RENDER_ERR]`。
    - 主事件循环解耦：重负载 JSON 解析与渲染调用均通过 `Schedule` 投递到主循环执行，WebSocket 接收线程仅复制字符串，降低栈占用与并发风险。
    - 音频循环防饿死/看门狗：`AudioLoop` 改为固定节拍 `vTaskDelayUntil`（周期 2ms），并确保 `period>=1 tick` 以避免 `tasks.c:1476 (( xTimeIncrement > 0U ))` 断言；在无数据/早退分支处统一 `vTaskDelay(1ms)` 主动让步；将 `audio_loop` 任务优先级降至 4，避免长期占用 CPU 触发 WDT。
    - 唤醒并发防护：欢迎页唤醒仅切换至“渲染测试页（等待后端指令…）”，不建立语音会话；`wake_word_detect_.StopDetection()` 后增加 `vTaskDelay(20ms)`；通过原子标志 `wwd_suspended_` 抑制 `OnAudioInput` 路径并在适当处让步。
    - 时钟/页面互斥：欢迎态才更新时钟；渲染页由显示驱动切换为交互态，避免被时钟覆盖。
    - 其他：`STATE` 日志打印使用枚举名；`Unknown device state: 1` 为默认分支提示（对功能无影响）。
  - hardware/main/protocols/websocket_protocol.cc：
    - 设备标识路由：`OpenAudioChannel()` 在 URL 追加 `?device-id=<mac小写>&client-id=<uuid>` 并设置对应请求头，确保后端稳定识别与路由到设备。
    - 接收线程瘦身：仅对 `hello` 就地解析设事件位；其余 JSON 复制原文并投递主循环中解析与分发，显著降低接收线程栈压力；`ParseServerHello` 在异常 `transport` 下亦设置事件位，避免超时阻塞。
  - hardware/main/protocols/protocol.h/.cc：新增 `bool SendJson(const std::string& json)`，复用底层 `SendText` 统一回执发送。
  - hardware/main/display/eink_display_st7306.h/.cc：新增最小渲染接口 `RenderSimplePage(...)` 与 `ShowTopBanner(...)`；渲染时切换 `current_state_ = STATE_INTERACTIVE_UI`，阻止欢迎页时钟覆盖渲染结果。
    - 文本绘制修复：渲染页正文与列表由 `u8g2_->print(...)` 改为 `u8g2_->drawUTF8(...)`，并显式 `setForegroundColor(ST7306_COLOR_BLACK)` / `setBackgroundColor(ST7306_COLOR_WHITE)`，修复“日志 OK 但屏幕无字/白字白底”。
    - 顶部横幅修复：`ShowTopBanner` 文本绘制由 `print(...)` 改为 `drawUTF8(...)`，并确保前景为白色以适配红底，修复“红条显示但无文字/长文无显示”。
    - 顶部横幅增强：支持单行自适应与两行布局（优先 16 号粗体，超宽自动降到 14 号；仍超宽则按 UTF‑8 字符边界拆分为两行），末行自动加省略号，杜绝“末尾丢字”。
  - hardware/main/display/eink_render_engine.h/.cc：渲染引擎独立化（整屏刷新、≥500ms 节流、UTF‑8 安全截断、列表 ≤8 行、横幅 3s 自动恢复上次渲染）。
  - hardware/main/display/eink/u8g2_for_st73xx_impl.cpp：修正默认字体颜色为前景黑/背景白，避免默认状态下出现白底白字导致内容不可见。
  - hardware/main/audio_processing/wake_word_detect.cc：`GetFeedSize()` 增加空指针判定（`afe_iface_`/`afe_data_`），未初始化时安全返回 512；规避并发窗口空引用导致的崩溃/栈溢出征兆。
  - hardware/main/CMakeLists.txt：新增 `display/eink_render_engine.cc` 编译项。
  - hardware/sdkconfig.defaults.esp32s3：`CONFIG_PTHREAD_TASK_STACK_SIZE_DEFAULT=8192`，缓解第三方线程栈不足问题（结合接收线程瘦身后可稳定运行）。

- 新增/修改文件（硬件）
  - 新增：`hardware/main/display/eink_render_engine.h`、`hardware/main/display/eink_render_engine.cc`
  - 修改：`hardware/main/application.cc`、`hardware/main/CMakeLists.txt`
  - 修改：`hardware/main/display/eink_display_st7306.h`、`hardware/main/display/eink_display_st7306.cc`
  - 修改：`hardware/main/display/eink/u8g2_for_st73xx_impl.cpp`
  - 修改：`hardware/main/protocols/protocol.h`、`hardware/main/protocols/protocol.cc`
  - 修改：`hardware/main/protocols/websocket_protocol.cc`
  - 修改：`hardware/main/audio_processing/wake_word_detect.cc`
  - 修改：`hardware/sdkconfig.defaults.esp32s3`

- 日志与可观测性
  - 渲染链路：`[RENDER_RX] type/page/id`、`[RENDER_OK] id`、`[RENDER_ERR] code`
  - 通道与采样：`Opening control channel for render engine...`、`Resampling audio from X to Y`
  - WDT/断言：通过固定节拍与分支让步处理，预期不再出现 `task_wdt` 与 `xTaskDelayUntil` 断言。

- 行为与阶段边界（阶段1）
  - 不实现：`listen.start/stop`、分页/滚动/局部刷新、主题系统（后续阶段再启用）。
  - 唤醒后进入“渲染测试页（等待后端指令…）”，不建立语音通道、不上报音频。

 - 实测
  - 设备可以正常启动、联网、欢迎页与唤醒后切入“渲染测试页”;
  - 通过meet001给设备发送Raw JSON后硬件日志无 `task_wdt`、无 `xTaskDelayUntil` 断言，且出现成对 `[RENDER_RX]` → `[RENDER_OK]`,但是屏幕上没有刷新或者渲染任何内容

## 编辑内容07 万能UI合并与唤醒入口切换（阶段1收尾）
编辑人 - p

- 变更内容 
  - hardware/main/display/eink_display_st7306.h/.cc：
    - Universal Frame 定稿：`RenderSimplePage(...)` 渲染顶部状态栏（模式缩写 C1/M1/C2 + 子页标题、时间、Wi‑Fi、电量）、中部正文（text/list，UTF‑8 绘制）、底部操作/提示栏。
    - 文本渲染：正文与列表一律使用 `u8g2->drawUTF8(...)`，并显式 `setForegroundColor(ST7306_COLOR_BLACK)` / `setBackgroundColor(ST7306_COLOR_WHITE)`，避免白底白字。
    - Meeting 默认提示：当 `footerHint` 为空且推断为 M1 时，底部提示默认显示“结束会议”。
    - `DrawActionBar` 新增可选 `custom_hint` 参数，保持对旧调用的向后兼容。
  - hardware/main/application.cc：
    - 唤醒后入口从“渲染测试页（等待后端指令…）”切换为本地“万能UI”（`universal.home`），不建立语音会话、不上报音频；停止唤醒词检测并切到 Idle。
    - 万能UI默认内容：`headerTitle="对话模式"`（状态栏推断为 C1），正文为引导语，`footerHint="说 \"开始聊天\" 进入对话"`。

- 新增/修改文件（硬件）
  - 修改：`hardware/main/display/eink_display_st7306.h`、`hardware/main/display/eink_display_st7306.cc`
  - 修改：`hardware/main/application.cc`

- 行为与阶段边界
  - 唤醒后直接显示本地万能UI；后端仍可通过 `ui.render` 覆盖渲染。阶段1 仍不启用分页/滚动/局部刷新。

- 测试指引（硬件侧）
  - 从欢迎页说唤醒词 → 出现万能UI：状态栏显示“C1 对话模式”、时间、Wi‑Fi、电量；正文与底部提示展示正确。
  - 发送 `ui.render`（text/list）验证渲染与 ACK；发送 `device.control(net.banner)` 验证 3s 顶部横幅并自动恢复原页面。

- 兼容性
  - 渲染协议与日志格式不变；旧的 `DrawActionBar(...)` 调用保持生效。

## 编辑内容08 后端统一日志口径（SEND/ACK/DROP/FREEZE/REDELIVER）
编辑人 -w
- 变更内容 
  - backend/core/websocket_server.py：在 `send_to_device` 打印 `[SEND]`，包含 `type/id/to/mode/page|action/qps`；`ui.render` 的 qps 依据发送器返回状态（ok/limited）
  - backend/core/orchestration/render_sender.py：
    - 限频丢帧：`[DROP_INVALID] type=ui.render reason=rate-limited interval=<ms> device=<id>`
    - 清洗失败：`[DROP_INVALID] type=ui.render reason=schema-invalid device=<id>`
    - 返回 `(ok|False, status)` 供 `[SEND]` 标记 qps
    - 预留 `[FREEZE]` 日志位（阶段1不触发逻辑）
  - backend/core/orchestration/render_schema.py：
    - 非法载荷/缺字段/不支持的 body.kind：统一打印 `[DROP_INVALID]`，附 `missing/expected/kind` 等键值
  - backend/core/handle/textHandle.py：
    - 收到 `ui.ack/ui.error`：统一打印 `[ACK] id=<id> device=<device> elapsedMs=<ms> code?<error>`
    - 白名单不通过：`[DROP_BY_MODE] type=<type> reason=not-allowed-in-mode mode=<mode> detail=<body.kind|action>`

- 行为说明
  - SEND：发送前统一打点；`ui.render`/`device.control` 两分支均覆盖
  - ACK：设备回执（包含 error 也计入），若带 `ts` 记录耗时
  - DROP：
    - `DROP_BY_MODE` 白名单不通过（阶段1仅 text|list、net.banner）
    - `DROP_INVALID` 清洗失败/字段缺失/限频
  - FREEZE：阶段1仅保留日志示例，不触发封禁
  - REDELIVER：仅当编排端显式补投时打印（后端已取消自动补投）

```

- 已在后端落地统一日志口径：
  - SEND: `websocket_server.send_to_device` 打印 `[SEND] type=<...> id=<...> to=<...> mode=<...> page|action=<...> qps=ok|limited`（qps 来自发送器返回状态）
  - ACK: `textHandle` 收到 `ui.ack/ui.error` 打印 `[ACK] id=<id> device=<device> elapsedMs=<ms> code?=<err>`（如带 ts 则输出耗时）
  - DROP_BY_MODE: `textHandle` 白名单不通过打印 `[DROP_BY_MODE] type=<type> reason=not-allowed-in-mode mode=<mode> detail=<body.kind|action>`
  - DROP_INVALID:
    - `render_schema` 载荷/字段/不支持的 kind：`[DROP_INVALID] type=ui.render reason=schema-invalid ...`
    - `render_sender` 限频：`[DROP_INVALID] type=ui.render reason=rate-limited interval=<ms> device=<id>`
    - `send_control` 不支持的动作：`[DROP_INVALID] type=device.control reason=unsupported-action action=<...> device=<id>`
  - FREEZE: `render_sender` 预留日志位（阶段1不触发）
  - REDELIVER: 仅编排端显式补投时打印；后端已取消自动补投

- 我已将“编辑内容08 后端统一日志口径”追加到 `collaboration/log.md`，并验证修改通过 lints。

---

**User**

用高中能听懂的方式告诉我08更新后端实现了什么功能?

---

**Cursor**

### 1. 需求分析与方案设计
- 你的需求：用通俗的话说明“编辑内容08”这次后端做了什么。
- 方案：把后端的关键动作都用统一的日志格式打点，便于快速排查问题和还原现场。

### 2. 代码实现
- SEND（准备发送）
  - 在把消息发到设备前记一条日志，包含发什么、给谁、当前模式、是渲染哪一页或什么动作、有没有触发限频。
  - 例子：  
    - [SEND] type=ui.render id=d1-002 to=94:a9:90:07:9d:88 mode=testing page=dialog.chat body=list qps=ok  
    - [SEND] type=device.control id=d1-003 to=94:a9:90:07:9d:88 mode=testing action=net.banner

- ACK（设备回执）
  - 设备回复“已收到/执行”或“出错”都会记一条，带上消息 id、设备号，若有时间戳还能算出耗时。
  - 例子：  
    - [ACK] id=d1-002 device=94:a9:90:07:9d:88 elapsedMs=215  
    - 出错会多一个 code 字段：[ACK] id=d1-005 device=... elapsedMs=120 code=INVALID_PAYLOAD

- DROP（两类丢弃）
  - DROP_BY_MODE（白名单不允许）：比如渲染体裁不是 text/list，或控制动作不是 net.banner，就直接丢弃并标明原因、当前模式、细节。
    - 例子：[DROP_BY_MODE] type=ui.render reason=not-allowed-in-mode mode=testing detail=logs
  - DROP_INVALID（内容非法/缺字段/限频）：清洗失败、字段缺失、动作不支持、限频触发等，都会标明具体原因。
    - 例子：  
      - [DROP_INVALID] type=ui.render reason=schema-invalid missing=page device=...  
      - [DROP_INVALID] type=ui.render reason=rate-limited interval=180 device=...  
      - [DROP_INVALID] type=device.control reason=unsupported-action action=beep device=...

- FREEZE（封禁占位）
  - 只预留日志样式，不启用逻辑（阶段1不封禁）。未来用于“多次失败临时冻结设备”这类场景。

- REDELIVER（补投）
  - 仅当“编排端显式补投”时打印（后端已取消自动补投），方便追踪补投时机。
  - 例子：[REDELIVER] device=... id=wel-001 page=welcome

### 3. 设计原因与取舍
- 统一口径：所有关键动作都“同一种格式”打印，便于人和机器（告警/检索）快速定位问题。
- 直观排障：一眼看到“发了什么、给谁、耗时多少、为什么被丢掉、是否限频”，问题定位更快。
- 渐进增强：FREEZE 先占位、REDELIVER改为显式触发，避免阶段1引入过多运行时复杂度。

---

**User**

# 已知内容
项目架构和实施原则请参考bulid.md , 现在是阶段2的开始, 你负责后端部分 后端部分代码是backend 注意硬件部分已经完成了自己的工作,只等待后端开发和更新了;

## 阶段2目标（对话最小闭环）
完整跑通“上电→欢迎→对话模式”全流程（参考全流程演示.md L9-L13@全流程演示.md ），后端主导模式，硬件/测试页只执行与回ACK。

## 当前问题
现在状况是这样的,就是硬件唤醒之后,能往后端传输并且后端asr了,但是后端没有返回,请查看日志,并告诉我后端应该怎么对接?

## 日志如下


---

**Cursor**

### 1. 需求分析与方案设计
- 现象：日志里已经看到握手/ASR/LLM链路正常（如“大模型收到用户消息: 能听见我说话吗？”），但没有任何 [SEND] 打点，说明后端没有向设备下发 `ui.render`/`device.control`。硬件只执行与回 ACK，不会自发 UI，必须由后端主动推。
- 阶段2目标（对话最小闭环）：后端在三个时机主动下发 UI 帧，驱动“上电→欢迎→对话模式”。
  - 设备连接/hello 后：发欢迎页
  - 唤醒/进入对话时：发对话页提示
  - ASR+LLM结束时：发最终回答页（可在计算中先发“思考中…”占位）

### 2. 对接要点（落点与示例）
- 在下述三个函数里“调用一次渲染函数”即可打通。推荐用已提供的发送器，保证限频/清洗/标题注入都正确：
  - 方案A（同连接直发，最简）：在 `ConnectionHandler` 内调用
    - 调用方式：`await core.orchestration.render_sender.send_render(self, payload)`
  - 方案B（统一路由，跨连接/跨会话）：在任意入口调用
    - 调用方式：`await self.server.send_to_device(device_id, payload_with_to_removed)` 或顶层构造带 `to:["device-id"]` 的外部消息

- 具体落点与示例
  - 1) 设备握手/hello 后 → 发欢迎页（`handle_hello` 里追加）
    ```python
    await send_render(conn, {
      "type": "ui.render",
      "id": "wel-001",
      "page": "welcome",
      "header": {},  # 标题会在清洗阶段注入“工牌{badge} · {owner}”
      "body": { "kind": "text", "text": "连接成功" },
      "footer": { "hint": "说“开始聊天”进入对话" }
    })
    ```
  - 2) 唤醒/进入对话 → 发对话页提示（`handle_listen_detect` 中识别到唤醒或进入对话分支时追加）
    ```python
    await send_render(conn, {
      "type": "ui.render",
      "id": "dlg-001",
      "page": "dialog.chat",
      "header": {},
      "body": { "kind": "text", "text": "请说出您的问题…" },
      "footer": { "hint": "我在听" }
    })
    ```
  - 3) ASR 最终文本 + LLM 回复 → 两次渲染（`ConnectionHandler.chat` 内追加）
    - 开始推理时（占位）：  
      ```python
      await send_render(self, {
        "type":"ui.render","id":"dlg-thinking",
        "page":"dialog.chat","header":{},
        "body":{"kind":"text","text":"正在思考…"}
      })
      ```
    - 生成完成后（最终回答展示）：  
      ```python
      await send_render(self, {
        "type":"ui.render","id":"dlg-final",
        "page":"dialog.chat","header":{},
        "body":{"kind":"text","text": final_answer_text},
        "footer":{"hint":"说“开始聊天”继续"}
      })
      ```
    - 提示：上述 `send_render(self, payload)` 会自动限频（≥500ms）、净化（仅 text/list）并注入“工牌{badge} · {owner}”。

- 校验日志
  - 成功发送前会看到类似：
    - [SEND] type=ui.render id=dlg-final to=94:a9:90:07:9d:88 mode=chat page=dialog.chat body=text qps=ok
  - 设备回 ACK：
    - [ACK] id=dlg-final device=94:a9:90:07:9d:88 elapsedMs=…

### 3. 设计理由与取舍
- 后端主导：硬件阶段2只执行与回 ACK，所有 UI 必须由后端显式下发，保证“对话最小闭环”能控可测。
- 低侵入接入：只在三处（hello、唤醒/进入对话、LLM完成）各加一条渲染下发即可跑通；其余能力（净化/限频/标题）由发送器统一处理。
- 可演进：后续可把“对话页”升级为列表（多轮日志/要点），或在对话模式切换时追加 `device.control(net.banner)` 提示；当前保持极简以稳定闭环。

```python
    await send_render(conn, {
      "type": "ui.render",
      "id": "wel-001",
      "page": "welcome",
      "header": {},  # 标题会在清洗阶段注入“工牌{badge} · {owner}”
      "body": { "kind": "text", "text": "连接成功" },
      "footer": { "hint": "说“开始聊天”进入对话" }
    })
```

```python
    await send_render(conn, {
      "type": "ui.render",
      "id": "dlg-001",
      "page": "dialog.chat",
      "header": {},
      "body": { "kind": "text", "text": "请说出您的问题…" },
      "footer": { "hint": "我在听" }
    })
```

```python
      await send_render(self, {
        "type":"ui.render","id":"dlg-thinking",
        "page":"dialog.chat","header":{},
        "body":{"kind":"text","text":"正在思考…"}
      })
```

```python
      await send_render(self, {
        "type":"ui.render","id":"dlg-final",
        "page":"dialog.chat","header":{},
        "body":{"kind":"text","text": final_answer_text},
        "footer":{"hint":"说“开始聊天”继续"}
      })
```

---

**User**

不对,“在设备连接/hello 后：发欢迎页”这个逻辑是错误的,因为硬件本身的开机动画和欢迎页面是预设好的,和渲染引擎无关,应该确认唤醒之后,才能发送渲染; 请更新需求,重建逻辑

---

**Cursor**

我将把对接逻辑更新为“仅在唤醒/开始拾音后下发渲染”，在 `textHandle.py`：
- 引入发送器导入；
- 在 `handle_listen` 的 state == "start" 时下发“请说出您的问题…”；
- 在 `handle_listen_detect` 的唤醒词分支改为下发渲染，不再触发聊天或TTS。
随后我会运行 lints 确认无错误。

```python
import json
import asyncio
import time
from typing import Dict, Callable, Any
from core.handle.abortHandle import handleAbortMessage
from core.handle.helloHandle import handleHelloMessage
from core.handle.mcpHandle import handle_mcp_message
from core.handle.peerHandle import handle_peer_message
from core.handle.meeting_handle import handle_meeting_message, finalize_meeting_and_send_summary
from core.handle.coding_handle import handle_coding_message
from core.handle.workflow_handle import handle_workflow_message
from core.utils.util import remove_punctuation_and_length, filter_sensitive_info
from core.handle.receiveAudioHandle import startToChat, handleAudioMessage
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.iotHandle import handleIotDescriptors, handleIotStatus
from core.handle.reportHandle import enqueue_asr_report
from core.utils.tasks_store import get_task_store
from config.logger import truncate_for_log
from core.orchestration.render_sender import send_render, send_control

TAG = __name__


async def handle_hello(conn, msg_json: Dict[str, Any]) -> None:
    """处理 hello 消息"""
    await handleHelloMessage(conn, msg_json)


async def handle_abort(conn, msg_json: Dict[str, Any]) -> None:
    """处理 abort 消息"""
    await handleAbortMessage(conn)


# 序号解析与直达意图分类（detect 与 STT 复用）
def _parse_target_index(text: str):
    """解析序号：第N个/第N条/任务一/工作一/数字/task N/first/second/third。返回1-based或None。"""
    try:
        t = (text or "").lower().strip()
        if not t:
            return None
        # 英文序数词
        ord_en = {
            "first":1,"second":2,"third":3,"fourth":4,"fifth":5,
            "sixth":6,"seventh":7,"eighth":8,"ninth":9,"tenth":10
        }
        for k,v in ord_en.items():
            if k in t:
                return v
        import re
        # task N / 第N个 / 第N条 / 第N
        m = re.search(r"(?:task|第|条|个)\s*(\d+)", t)
        if m:
            n = int(m.group(1))
            return n if n>0 else None
        # 任务一/工作一/第十
        ord_cn = {"一":1,"二":2,"两":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
        for k,v in ord_cn.items():
            if f"任务{k}" in t or f"工作{k}" in t or f"第{k}" in t:
                return v
        # 裸数字
        m2 = re.search(r"\b(\d{1,2})\b", t)
        if m2:
            n = int(m2.group(1))
            return n if n>0 else None
    except Exception:
        return None
    return None


async def handle_listen(conn, msg_json: Dict[str, Any]) -> None:
    """处理 listen 消息"""
    if "mode" in msg_json:
        conn.client_listen_mode = msg_json["mode"]
        conn.logger.bind(tag=TAG).debug(f"客户端拾音模式：{conn.client_listen_mode}")
    
    state = msg_json.get("state")
    if state == "start":
        # 最小去抖：忽略距上次同类事件 <300ms 的重复 start
        now_ms = int(time.time() * 1000)
        last_ms = int(getattr(conn, "_last_listen_start_ms", 0) or 0)
        if now_ms - last_ms < 300:
            return
        conn._last_listen_start_ms = now_ms
        
        conn.client_have_voice = True
        conn.client_voice_stop = False
        # 记录设备侧边界最新时间，用于回退策略判断
        conn._last_listen_event_ms = now_ms
        # 阶段2：唤醒/开始拾音后由后端主导下发对话页提示
        try:
            await send_render(conn, {
                "type": "ui.render",
                "id": "dlg-listen-start",
                "page": "dialog.chat",
                "header": {},
                "body": {"kind": "text", "text": "请说出您的问题…"},
                "footer": {"hint": "我在听"}
            })
        except Exception:
            pass
        
    elif state == "stop":
        # 最小去抖：忽略距上次同类事件 <300ms 的重复 stop
        now_ms = int(time.time() * 1000)
        last_ms = int(getattr(conn, "_last_listen_stop_ms", 0) or 0)
        if now_ms - last_ms < 300:
            return
        conn._last_listen_stop_ms = now_ms

        conn.client_have_voice = True
        conn.client_voice_stop = True
        conn._last_listen_event_ms = now_ms

        # 通知流式ASR“本段结束”，促使尽快产出最终结果（保留兜底）
        try:
            if getattr(conn, "asr", None) is not None and hasattr(conn.asr, "on_client_listen_stop"):
                maybe = conn.asr.on_client_listen_stop(conn)
                if asyncio.iscoroutine(maybe):
                    await maybe
        except Exception:
            pass

        # 兼容旧流程：仍保留 b"" 触发兜底
        if len(conn.asr_audio) > 0:
            await handleAudioMessage(conn, b"")
            
    elif state == "detect":
        conn.client_have_voice = False
        conn.asr_audio.clear()
        
        if "text" in msg_json:
            await handle_listen_detect(conn, msg_json)


async def handle_listen_detect(conn, msg_json: Dict[str, Any]) -> None:
    """处理 listen detect 消息的文本识别部分"""
    original_text = msg_json["text"]
    filtered_len, filtered_text = remove_punctuation_and_length(original_text)
    
    # 模式切换（进入工作模式）意图识别
    normalized = str(original_text or "").strip().lower()
    mode_switch_keywords = [
        "进入工作模式", "工作模式", "切到工作模式", "切换到工作模式",
        "workflow mode", "working mode", "switch to working mode", "enter working mode",
    ]
    if any(k.lower() in normalized for k in mode_switch_keywords):
        # 下发带意图标注的 STT
        await conn.send_json({
            "type": "stt",
            "text": original_text,
            "intent": "mode_switch",
            "target_mode": "working",
            "session_id": getattr(conn, "session_id", ""),
        })
        
        # 复用现有 mode 流程
        await handle_mode(conn, {"type": "mode", "state": "start", "mode": "working"})
        return
    
    # 识别是否是唤醒词
    is_wakeup_words = filtered_text in conn.config.get("wakeup_words")
    enable_greeting = conn.config.get("enable_greeting", True)
    
    if is_wakeup_words:
        # 阶段2：确认唤醒后仅下发渲染提示，由后端主导，不直接进入聊天或TTS
        conn.just_woken_up = True
        try:
            await send_render(conn, {
                "type": "ui.render",
                "id": "dlg-ready",
                "page": "dialog.chat",
                "header": {},
                "body": {"kind": "text", "text": "我在，准备好聆听您的问题。"},
                "footer": {"hint": "开始说话或按键开始"}
            })
        except Exception:
            pass
    else:
        # 语音指令直达（工作模式）
        if getattr(conn, "current_mode", None) == "working":
            if await handle_working_voice_command(conn, original_text):
                return
        
        # 默认走常规对话
        enqueue_asr_report(conn, original_text, [])
        await startToChat(conn, original_text)


async def handle_working_voice_command(conn, text: str) -> bool:
    """处理工作模式的语音指令，返回是否已处理"""
    normalized = str(text or "").strip().lower()
    
    # 同义词扩充，允许“工作/任务”混用
    assign_kw   = ["认领任务","领取任务","我来做","assign to me","claim task","接收","接受","接手","接单","接收工作","接受工作","接手工作"]
    complete_kw = ["完成任务","标记完成","做完了","mark done","complete task","搞定了","已完成","完成工作","办完工作"]
    refresh_kw  = ["刷新列表","刷新任务","拉取任务","刷新","update list","pull","更新列表"]
    
    intent = None
    if any(k.lower() in normalized for k in assign_kw):
        intent = "assign"
    elif any(k.lower() in normalized for k in complete_kw):
        intent = "complete"
    elif any(k.lower() in normalized for k in refresh_kw):
        intent = "refresh"
    
    # 统一序号解析：第N个/任务一/工作一/数字/task N/first/second/third
    index = _parse_target_index(normalized)
    
    if intent is None:
        return False
    
    # 发送轻量意图回包
    await conn.send_json({
        "type": "workflow",
        "event": "command",
        "intent": intent,
    })
    
    # 执行具体指令
    store = get_task_store()
    group_key = (getattr(conn, "device_id", "") or "")[:8]
    # 诊断日志
    try:
        tasks_open_for_log = [t for t in (store.list_by_group(group_key) or []) if (t.get("status") or "open") == "open"]
        target_id_log = None
        if index and 1 <= index <= len(tasks_open_for_log):
            target_id_log = tasks_open_for_log[index - 1].get("id")
        conn.logger.bind(tag=TAG).info(f"working_voice_intent: intent={intent} n={index} open_count={len(tasks_open_for_log)} target_id={target_id_log}")
    except Exception:
        pass
    
    if intent == "refresh":
        tasks = store.list_by_group(group_key)
        envelope = {"type": "workflow", "event": "update", "tasks": tasks}
        await conn.send_json(envelope)
        return True
    
    # 认领/完成：取最近一个可操作任务
    tasks = store.list_by_group(group_key) or []
    target_id = None
    
    if intent == "assign":
        tasks_open = [t for t in tasks if (t.get("status") or "open") == "open"]
        if index and tasks_open and 1 <= index <= len(tasks_open):
            target_id = tasks_open[index - 1].get("id")
        else:
            for t in tasks:
                if t.get("status") == "open" and (not t.get("owner") or t.get("owner") != getattr(conn, "device_id", None)):
                    target_id = t.get("id")
                    break
            if target_id is None and tasks:
                target_id = tasks[0].get("id")
        if target_id:
            await handle_workflow_message(conn, {"type": "workflow", "event": "assign", "id": target_id})
            return True
            
    elif intent == "complete":
        tasks_open = [t for t in tasks if (t.get("status") or "open") == "open"]
        if index and tasks_open and 1 <= index <= len(tasks_open):
            target_id = tasks_open[index - 1].get("id")
        else:
            for t in tasks:
                if t.get("status") == "open":
                    target_id = t.get("id")
                    break
        if target_id:
            await handle_workflow_message(conn, {"type": "workflow", "event": "complete", "ids": [target_id]})
            return True
    
    return False


async def handle_iot(conn, msg_json: Dict[str, Any]) -> None:
    """处理 IoT 消息"""
    if "descriptors" in msg_json:
        asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
    if "states" in msg_json:
        asyncio.create_task(handleIotStatus(conn, msg_json["states"]))


async def handle_mcp(conn, msg_json: Dict[str, Any]) -> None:
    """处理 MCP 消息"""
    if "payload" in msg_json:
        asyncio.create_task(handle_mcp_message(conn, conn.mcp_client, msg_json["payload"]))


async def handle_meeting(conn, msg_json: Dict[str, Any]) -> None:
    """处理会议消息"""
    if msg_json.get("phase") == "finalize":
        # 立即回执
        conn.logger.bind(tag=TAG).info("finalize request")
        ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
        pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
        await conn.send_json({
            "type": "meeting",
            "phase": "finalize",
            "sessionId": getattr(conn, "session_id", ""),
            "startedAt": ack_started_at,
            "pendingCount": pending_count,
        })
        conn.logger.bind(tag=TAG).info("send ack")
        
        # 标记 finalize 中
        setattr(conn, "meeting_finalizing", True)
        
        # 停止会中定时任务
        try:
            from core.handle.meeting_handle import stop_meeting_timers
            stop_meeting_timers(conn)
            conn.logger.bind(tag=TAG).info("stop timers done")
        except Exception:
            conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
        
        # 关闭/重置 ASR 流式连接
        try:
            if getattr(conn, "asr", None) is not None:
                if hasattr(conn.asr, "stop_ws_connection"):
                    conn.asr.stop_ws_connection()
                import inspect
                if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                    asyncio.create_task(conn.asr.close())
        except Exception:
            pass
        
        # 异步生成并下发最终纪要
        asyncio.create_task(finalize_meeting_and_send_summary(conn))
    else:
        asyncio.create_task(handle_meeting_message(conn, msg_json))


async def handle_coding(conn, msg_json: Dict[str, Any]) -> None:
    """处理编码消息"""
    asyncio.create_task(handle_coding_message(conn, msg_json))


async def handle_workflow(conn, msg_json: Dict[str, Any]) -> None:
    """处理工作流消息"""
    asyncio.create_task(handle_workflow_message(conn, msg_json))
    # 接受 workflow.update 以落库任务（便于种子任务注入）
    if msg_json.get("event") == "update":
        try:
            store = get_task_store()
            group_key = (getattr(conn, "device_id", "") or "")[:8]
            for t in (msg_json.get("tasks") or []):
                try:
                    store.upsert(group_key, t)
                except Exception:
                    pass
        except Exception:
            pass


async def handle_config_update(conn, msg_json: Dict[str, Any]) -> None:
    """处理配置更新消息（兼容旧版）"""
    try:
        cfg_keys = list((msg_json.get("config") or {}).keys())
        conn.logger.bind(tag=TAG).info(f"收到兼容 config_update（忽略实际更新）：keys={cfg_keys}")
    except Exception:
        conn.logger.bind(tag=TAG).info("收到兼容 config_update（忽略实际更新）")
    
    await conn.send_json({"type": "config_update", "status": "ok", "noop": True})


async def handle_mode(conn, msg_json: Dict[str, Any]) -> None:
    """处理模式切换消息"""
    state = msg_json.get("state")
    mode = msg_json.get("mode")
    
    if state not in ["start", "end"] or mode not in ["meeting", "coding", "working"]:
        return
    
    if state == "start":
        # 幂等：若已处于该模式则直接回执
        if getattr(conn, "current_mode", None) == mode:
            await conn.send_json({
                "type": "mode",
                "status": "ok",
                "state": "start",
                "mode": mode
            })
            return
        
        conn.current_mode = mode
        
        if mode == "meeting":
            await handle_meeting_mode_start(conn)
        elif mode == "working":
            await handle_working_mode_start(conn)
        elif mode == "coding":
            await handle_coding_mode_start(conn)
    
    elif state == "end":
        if conn.current_mode == mode:
            conn.current_mode = None
            # 清理相关状态
            if mode == "meeting":
                conn.meeting_segments.clear()
                conn.meeting_start_ts = 0
            elif mode == "coding":
                conn.coding_stream_running = False
                conn.coding_phase_name = ""
        
        await conn.send_json({
            "type": "mode",
            "status": "ok",
            "state": "end",
            "mode": mode
        })


async def handle_meeting_mode_start(conn) -> None:
    """处理会议模式启动"""
    conn.meeting_segments.clear()
    conn.meeting_start_ts = time.time() * 1000
    conn.meeting_last_snippet_ts = 0.0
    conn.meeting_last_snippet_index = 0
    
    # 播放进入会议提示音
    await conn.send_json({
        "type": "tts",
        "state": "start",
        "url": "config/assets/evening.wav",
        "text": "已进入会议模式"
    })
    await conn.send_json({
        "type": "tts",
        "state": "stop"
    })
    
    # 会议模式优先设备侧VAD
    try:
        srv = getattr(conn, "server", None)
        base_cfg = getattr(srv, "config", None) if srv else None
        if isinstance(base_cfg, dict):
            meeting_cfg = base_cfg.get("meeting", {})
        else:
            meeting_cfg = conn.config.get("meeting", {})
    except Exception:
        meeting_cfg = conn.config.get("meeting", {})
    
    if bool(meeting_cfg.get("prefer_device_vad", True)):
        conn.client_listen_mode = "manual"
        conn.logger.bind(tag=TAG).info("会议模式已启用设备侧VAD优先")
    
    # 尝试加载活跃会中状态
    try:
        from core.handle.meeting_handle import load_active_state_if_any, start_meeting_timers
        await load_active_state_if_any(conn)
        start_meeting_timers(conn)
    except Exception:
        pass
    
    await conn.send_json({
        "type": "mode",
        "status": "ok",
        "state": "start",
        "mode": "meeting"
    })


async def handle_working_mode_start(conn) -> None:
    """处理工作模式启动"""
    # 发送一次任务列表
    store = get_task_store()
    group_key = (getattr(conn, "device_id", "") or "")[:8]
    tasks = store.list_by_group(group_key)
    await conn.send_json({
        "type": "workflow",
        "event": "update",
        "tasks": tasks
    })
    
    await conn.send_json({
        "type": "mode",
        "status": "ok",
        "state": "start",
        "mode": "working"
    })


async def handle_coding_mode_start(conn) -> None:
    """处理编码模式启动"""
    conn.coding_stream_running = False
    conn.coding_phase_name = ""
    
    await conn.send_json({
        "type": "mode",
        "status": "ok",
        "state": "start",
        "mode": "coding"
    })


async def handle_peer(conn, msg_json: Dict[str, Any]) -> None:
    """处理 peer 消息"""
    try:
        # 透传顶层路由字段 to 给处理器，避免在 handler 内部引用未定义的变量
        to_list = msg_json.get("to", []) or []
        category = msg_json.get("category")  # 可选，主要用于快捷路径；不参与 schema 校验
        payload = msg_json.get("payload") or {}
        asyncio.create_task(handle_peer_message(conn, category, payload, to_list))
    except Exception:
        asyncio.create_task(handle_peer_message(conn, None, {}, []))


# 消息处理路由表
MESSAGE_HANDLERS: Dict[str, Callable] = {
    "hello": handle_hello,
    "abort": handle_abort,
    "listen": handle_listen,
    "iot": handle_iot,
    "mcp": handle_mcp,
    "meeting": handle_meeting,
    "coding": handle_coding,
    "workflow": handle_workflow,
    "config_update": handle_config_update,
    "mode": handle_mode,
    "peer": handle_peer,
}


async def handleTextMessage(conn, message):
    """处理文本消息的主入口"""
    try:
        msg_json = json.loads(message)
        
        # 处理整数消息（回显）
        if isinstance(msg_json, int):
            try:
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message if isinstance(message, str) else str(message)
            conn.logger.bind(tag=TAG).info(f"收到文本消息：{safe_msg}")
            await conn.send_text(message)
            return
        
        # 获取消息类型
        msg_type = msg_json.get("type")
        if not msg_type:
            conn.logger.bind(tag=TAG).warning(f"收到未知类型消息：{truncate_for_log(message)}")
            return
        
        # 设备上行 ACK/ERROR 统一 [ACK] 打点（阶段1不回发起方）
        if msg_type in ("ui.ack", "ui.error"):
            try:
                ts = msg_json.get("ts")
                elapsed = None
                if isinstance(ts, (int, float)):
                    try:
                        now_ms = int(time.time() * 1000)
                        elapsed = now_ms - int(ts)
                    except Exception:
                        elapsed = None
                _id = msg_json.get("id")
                code = msg_json.get("code") if msg_type == "ui.error" else None
                base = f"[ACK] id={_id} device={getattr(conn, 'device_id', None)}"
                if elapsed is not None:
                    base += f" elapsedMs={elapsed}"
                if code is not None:
                    base += f" code={code}"
                conn.logger.bind(tag=TAG).info(base)
            except Exception:
                conn.logger.bind(tag=TAG).info("[ACK] malformed")
            return

        # 消息转发：ui.render / device.control（热修，不改协议）
        if msg_type in ("ui.render", "device.control") and isinstance(msg_json.get("to"), list):
            to_list = [
                str(x).strip().strip('"').strip("'").lower()
                for x in (msg_json.get("to") or [])
                if str(x).strip() != ""
            ]
            if len(to_list) == 0:
                conn.logger.bind(tag=TAG).info("转发忽略：to 为空")
                return
            # 白名单校验：阶段1 仅允许 ui.render(text|list) 与 device.control(net.banner)
            allow = False
            if msg_type == "ui.render":
                body_kind = None
                try:
                    body = msg_json.get("body") or {}
                    body_kind = (body.get("kind") or "").strip().lower()
                except Exception:
                    body_kind = None
                allow = body_kind in ("text", "list")
            elif msg_type == "device.control":
                allow = (msg_json.get("action") == "net.banner")

            if not allow:
                mode = getattr(conn, "current_mode", None)
                detail = (msg_json.get("body") or {}).get("kind") if msg_type == "ui.render" else msg_json.get("action")
                conn.logger.bind(tag=TAG).info(
                    f"[DROP_BY_MODE] type={msg_type} reason=not-allowed-in-mode mode={mode} detail={detail}"
                )
                return

            # 并发转发到各在线设备；不在线仅日志；不回执
            async def _forward_one(did: str):
                try:
                    server = getattr(conn, "server", None)
                    if server is None or not hasattr(server, "send_to_device"):
                        return
                    ok = await server.send_to_device(did, msg_json)
                    if not ok:
                        conn.logger.bind(tag=TAG).info(f"设备不在线或发送失败：{did}")
                except Exception:
                    pass

            await asyncio.gather(*[_forward_one(d) for d in to_list])
            return

        # 记录消息日志
        try:
            if msg_type in ["hello", "listen", "iot", "mcp"]:
                safe_msg = truncate_for_log(message)
            elif msg_type in ["meeting", "coding", "workflow"]:
                safe_msg = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            else:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到{msg_type}消息：{safe_msg}")
        except Exception:
            conn.logger.bind(tag=TAG).info(f"收到{msg_type}消息")
        
        # 查找并执行对应的处理器
        handler = MESSAGE_HANDLERS.get(msg_type)
        if handler:
            await handler(conn, msg_json)
        else:
            conn.logger.bind(tag=TAG).warning(f"未知消息类型：{msg_type}")
            
    except json.JSONDecodeError:
        conn.logger.bind(tag=TAG).error(f"JSON解析失败：{truncate_for_log(message)}")
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"处理文本消息异常：{e}")

```

- 已改为“仅唤醒/开始拾音后才下发渲染”：
  - `handle_listen(state=="start")`：下发对话提示页“请说出您的问题…”
  - `handle_listen_detect` 检测到唤醒词时：只下发“准备聆听”的对话页，不触发聊天/TTS
- 未动硬件欢迎页逻辑；后端不再在连接/hello 时发送任何渲染。

---

**User**

逻辑还是错误的 我在硬件的欢迎页面 使用meet001发送了渲染指令({ "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat",
  "header":{"title":"(可留空, 由后端注入)"},
  "body":{"kind":"text","text":"Hello 渲染测试"},
  "footer":{"hint":"后端→设备 OK"} }) 硬件还是执行了渲染这个操作 

---

**Cursor**

```python
import json
import asyncio
import time
from typing import Dict, Callable, Any
from core.handle.abortHandle import handleAbortMessage
from core.handle.helloHandle import handleHelloMessage
from core.handle.mcpHandle import handle_mcp_message
from core.handle.peerHandle import handle_peer_message
from core.handle.meeting_handle import handle_meeting_message, finalize_meeting_and_send_summary
from core.handle.coding_handle import handle_coding_message
from core.handle.workflow_handle import handle_workflow_message
from core.utils.util import remove_punctuation_and_length, filter_sensitive_info
from core.handle.receiveAudioHandle import startToChat, handleAudioMessage
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.iotHandle import handleIotDescriptors, handleIotStatus
from core.handle.reportHandle import enqueue_asr_report
from core.utils.tasks_store import get_task_store
from config.logger import truncate_for_log
from core.orchestration.render_sender import send_render, send_control

TAG = __name__


async def handle_hello(conn, msg_json: Dict[str, Any]) -> None:
    """处理 hello 消息"""
    await handleHelloMessage(conn, msg_json)


async def handle_abort(conn, msg_json: Dict[str, Any]) -> None:
    """处理 abort 消息"""
    await handleAbortMessage(conn)


# 序号解析与直达意图分类（detect 与 STT 复用）
def _parse_target_index(text: str):
    """解析序号：第N个/第N条/任务一/工作一/数字/task N/first/second/third。返回1-based或None。"""
    try:
        t = (text or "").lower().strip()
        if not t:
            return None
        # 英文序数词
        ord_en = {
            "first":1,"second":2,"third":3,"fourth":4,"fifth":5,
            "sixth":6,"seventh":7,"eighth":8,"ninth":9,"tenth":10
        }
        for k,v in ord_en.items():
            if k in t:
                return v
        import re
        # task N / 第N个 / 第N条 / 第N
        m = re.search(r"(?:task|第|条|个)\s*(\d+)", t)
        if m:
            n = int(m.group(1))
            return n if n>0 else None
        # 任务一/工作一/第十
        ord_cn = {"一":1,"二":2,"两":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
        for k,v in ord_cn.items():
            if f"任务{k}" in t or f"工作{k}" in t or f"第{k}" in t:
                return v
        # 裸数字
        m2 = re.search(r"\b(\d{1,2})\b", t)
        if m2:
            n = int(m2.group(1))
            return n if n>0 else None
    except Exception:
        return None
    return None


async def handle_listen(conn, msg_json: Dict[str, Any]) -> None:
    """处理 listen 消息"""
    if "mode" in msg_json:
        conn.client_listen_mode = msg_json["mode"]
        conn.logger.bind(tag=TAG).debug(f"客户端拾音模式：{conn.client_listen_mode}")
    
    state = msg_json.get("state")
    if state == "start":
        # 最小去抖：忽略距上次同类事件 <300ms 的重复 start
        now_ms = int(time.time() * 1000)
        last_ms = int(getattr(conn, "_last_listen_start_ms", 0) or 0)
        if now_ms - last_ms < 300:
            return
        conn._last_listen_start_ms = now_ms
        
        # 阶段2：进入对话准备态
        try:
            conn.current_mode = "dialog.preparing"
        except Exception:
            pass

        conn.client_have_voice = True
        conn.client_voice_stop = False
        # 记录设备侧边界最新时间，用于回退策略判断
        conn._last_listen_event_ms = now_ms
        # 阶段2：唤醒/开始拾音后由后端主导下发对话页提示
        try:
            await send_render(conn, {
                "type": "ui.render",
                "id": "dlg-listen-start",
                "page": "dialog.chat",
                "header": {},
                "body": {"kind": "text", "text": "请说出您的问题…"},
                "footer": {"hint": "我在听"}
            })
        except Exception:
            pass
        
    elif state == "stop":
        # 最小去抖：忽略距上次同类事件 <300ms 的重复 stop
        now_ms = int(time.time() * 1000)
        last_ms = int(getattr(conn, "_last_listen_stop_ms", 0) or 0)
        if now_ms - last_ms < 300:
            return
        conn._last_listen_stop_ms = now_ms

        conn.client_have_voice = True
        conn.client_voice_stop = True
        conn._last_listen_event_ms = now_ms

        # 通知流式ASR“本段结束”，促使尽快产出最终结果（保留兜底）
        try:
            if getattr(conn, "asr", None) is not None and hasattr(conn.asr, "on_client_listen_stop"):
                maybe = conn.asr.on_client_listen_stop(conn)
                if asyncio.iscoroutine(maybe):
                    await maybe
        except Exception:
            pass

        # 兼容旧流程：仍保留 b"" 触发兜底
        if len(conn.asr_audio) > 0:
            await handleAudioMessage(conn, b"")
            
    elif state == "detect":
        conn.client_have_voice = False
        conn.asr_audio.clear()
        
        if "text" in msg_json:
            await handle_listen_detect(conn, msg_json)


async def handle_listen_detect(conn, msg_json: Dict[str, Any]) -> None:
    """处理 listen detect 消息的文本识别部分"""
    original_text = msg_json["text"]
    filtered_len, filtered_text = remove_punctuation_and_length(original_text)
    
    # 模式切换（进入工作模式）意图识别
    normalized = str(original_text or "").strip().lower()
    mode_switch_keywords = [
        "进入工作模式", "工作模式", "切到工作模式", "切换到工作模式",
        "workflow mode", "working mode", "switch to working mode", "enter working mode",
    ]
    if any(k.lower() in normalized for k in mode_switch_keywords):
        # 下发带意图标注的 STT
        await conn.send_json({
            "type": "stt",
            "text": original_text,
            "intent": "mode_switch",
            "target_mode": "working",
            "session_id": getattr(conn, "session_id", ""),
        })
        
        # 复用现有 mode 流程
        await handle_mode(conn, {"type": "mode", "state": "start", "mode": "working"})
        return
    
    # 识别是否是唤醒词
    is_wakeup_words = filtered_text in conn.config.get("wakeup_words")
    enable_greeting = conn.config.get("enable_greeting", True)
    
    if is_wakeup_words:
        # 阶段2：确认唤醒后仅下发渲染提示，由后端主导，不直接进入聊天或TTS
        conn.just_woken_up = True
        try:
            await send_render(conn, {
                "type": "ui.render",
                "id": "dlg-ready",
                "page": "dialog.chat",
                "header": {},
                "body": {"kind": "text", "text": "我在，准备好聆听您的问题。"},
                "footer": {"hint": "开始说话或按键开始"}
            })
        except Exception:
            pass
    else:
        # 语音指令直达（工作模式）
        if getattr(conn, "current_mode", None) == "working":
            if await handle_working_voice_command(conn, original_text):
                return
        
        # 默认走常规对话
        enqueue_asr_report(conn, original_text, [])
        await startToChat(conn, original_text)


async def handle_working_voice_command(conn, text: str) -> bool:
    """处理工作模式的语音指令，返回是否已处理"""
    normalized = str(text or "").strip().lower()
    
    # 同义词扩充，允许“工作/任务”混用
    assign_kw   = ["认领任务","领取任务","我来做","assign to me","claim task","接收","接受","接手","接单","接收工作","接受工作","接手工作"]
    complete_kw = ["完成任务","标记完成","做完了","mark done","complete task","搞定了","已完成","完成工作","办完工作"]
    refresh_kw  = ["刷新列表","刷新任务","拉取任务","刷新","update list","pull","更新列表"]
    
    intent = None
    if any(k.lower() in normalized for k in assign_kw):
        intent = "assign"
    elif any(k.lower() in normalized for k in complete_kw):
        intent = "complete"
    elif any(k.lower() in normalized for k in refresh_kw):
        intent = "refresh"
    
    # 统一序号解析：第N个/任务一/工作一/数字/task N/first/second/third
    index = _parse_target_index(normalized)
    
    if intent is None:
        return False
    
    # 发送轻量意图回包
    await conn.send_json({
        "type": "workflow",
        "event": "command",
        "intent": intent,
    })
    
    # 执行具体指令
    store = get_task_store()
    group_key = (getattr(conn, "device_id", "") or "")[:8]
    # 诊断日志
    try:
        tasks_open_for_log = [t for t in (store.list_by_group(group_key) or []) if (t.get("status") or "open") == "open"]
        target_id_log = None
        if index and 1 <= index <= len(tasks_open_for_log):
            target_id_log = tasks_open_for_log[index - 1].get("id")
        conn.logger.bind(tag=TAG).info(f"working_voice_intent: intent={intent} n={index} open_count={len(tasks_open_for_log)} target_id={target_id_log}")
    except Exception:
        pass
    
    if intent == "refresh":
        tasks = store.list_by_group(group_key)
        envelope = {"type": "workflow", "event": "update", "tasks": tasks}
        await conn.send_json(envelope)
        return True
    
    # 认领/完成：取最近一个可操作任务
    tasks = store.list_by_group(group_key) or []
    target_id = None
    
    if intent == "assign":
        tasks_open = [t for t in tasks if (t.get("status") or "open") == "open"]
        if index and tasks_open and 1 <= index <= len(tasks_open):
            target_id = tasks_open[index - 1].get("id")
        else:
            for t in tasks:
                if t.get("status") == "open" and (not t.get("owner") or t.get("owner") != getattr(conn, "device_id", None)):
                    target_id = t.get("id")
                    break
            if target_id is None and tasks:
                target_id = tasks[0].get("id")
        if target_id:
            await handle_workflow_message(conn, {"type": "workflow", "event": "assign", "id": target_id})
            return True
            
    elif intent == "complete":
        tasks_open = [t for t in tasks if (t.get("status") or "open") == "open"]
        if index and tasks_open and 1 <= index <= len(tasks_open):
            target_id = tasks_open[index - 1].get("id")
        else:
            for t in tasks:
                if t.get("status") == "open":
                    target_id = t.get("id")
                    break
        if target_id:
            await handle_workflow_message(conn, {"type": "workflow", "event": "complete", "ids": [target_id]})
            return True
    
    return False


async def handle_iot(conn, msg_json: Dict[str, Any]) -> None:
    """处理 IoT 消息"""
    if "descriptors" in msg_json:
        asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
    if "states" in msg_json:
        asyncio.create_task(handleIotStatus(conn, msg_json["states"]))


async def handle_mcp(conn, msg_json: Dict[str, Any]) -> None:
    """处理 MCP 消息"""
    if "payload" in msg_json:
        asyncio.create_task(handle_mcp_message(conn, conn.mcp_client, msg_json["payload"]))


async def handle_meeting(conn, msg_json: Dict[str, Any]) -> None:
    """处理会议消息"""
    if msg_json.get("phase") == "finalize":
        # 立即回执
        conn.logger.bind(tag=TAG).info("finalize request")
        ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
        pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
        await conn.send_json({
            "type": "meeting",
            "phase": "finalize",
            "sessionId": getattr(conn, "session_id", ""),
            "startedAt": ack_started_at,
            "pendingCount": pending_count,
        })
        conn.logger.bind(tag=TAG).info("send ack")
        
        # 标记 finalize 中
        setattr(conn, "meeting_finalizing", True)
        
        # 停止会中定时任务
        try:
            from core.handle.meeting_handle import stop_meeting_timers
            stop_meeting_timers(conn)
            conn.logger.bind(tag=TAG).info("stop timers done")
        except Exception:
            conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
        
        # 关闭/重置 ASR 流式连接
        try:
            if getattr(conn, "asr", None) is not None:
                if hasattr(conn.asr, "stop_ws_connection"):
                    conn.asr.stop_ws_connection()
                import inspect
                if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                    asyncio.create_task(conn.asr.close())
        except Exception:
            pass
        
        # 异步生成并下发最终纪要
        asyncio.create_task(finalize_meeting_and_send_summary(conn))
    else:
        asyncio.create_task(handle_meeting_message(conn, msg_json))


async def handle_coding(conn, msg_json: Dict[str, Any]) -> None:
    """处理编码消息"""
    asyncio.create_task(handle_coding_message(conn, msg_json))


async def handle_workflow(conn, msg_json: Dict[str, Any]) -> None:
    """处理工作流消息"""
    asyncio.create_task(handle_workflow_message(conn, msg_json))
    # 接受 workflow.update 以落库任务（便于种子任务注入）
    if msg_json.get("event") == "update":
        try:
            store = get_task_store()
            group_key = (getattr(conn, "device_id", "") or "")[:8]
            for t in (msg_json.get("tasks") or []):
                try:
                    store.upsert(group_key, t)
                except Exception:
                    pass
        except Exception:
            pass


async def handle_config_update(conn, msg_json: Dict[str, Any]) -> None:
    """处理配置更新消息（兼容旧版）"""
    try:
        cfg_keys = list((msg_json.get("config") or {}).keys())
        conn.logger.bind(tag=TAG).info(f"收到兼容 config_update（忽略实际更新）：keys={cfg_keys}")
    except Exception:
        conn.logger.bind(tag=TAG).info("收到兼容 config_update（忽略实际更新）")
    
    await conn.send_json({"type": "config_update", "status": "ok", "noop": True})


async def handle_mode(conn, msg_json: Dict[str, Any]) -> None:
    """处理模式切换消息"""
    state = msg_json.get("state")
    mode = msg_json.get("mode")
    
    if state not in ["start", "end"] or mode not in ["meeting", "coding", "working"]:
        return
    
    if state == "start":
        # 幂等：若已处于该模式则直接回执
        if getattr(conn, "current_mode", None) == mode:
            await conn.send_json({
                "type": "mode",
                "status": "ok",
                "state": "start",
                "mode": mode
            })
            return
        
        conn.current_mode = mode
        
        if mode == "meeting":
            await handle_meeting_mode_start(conn)
        elif mode == "working":
            await handle_working_mode_start(conn)
        elif mode == "coding":
            await handle_coding_mode_start(conn)
    
    elif state == "end":
        if conn.current_mode == mode:
            conn.current_mode = None
            # 清理相关状态
            if mode == "meeting":
                conn.meeting_segments.clear()
                conn.meeting_start_ts = 0
            elif mode == "coding":
                conn.coding_stream_running = False
                conn.coding_phase_name = ""
        
        await conn.send_json({
            "type": "mode",
            "status": "ok",
            "state": "end",
            "mode": mode
        })


async def handle_meeting_mode_start(conn) -> None:
    """处理会议模式启动"""
    conn.meeting_segments.clear()
    conn.meeting_start_ts = time.time() * 1000
    conn.meeting_last_snippet_ts = 0.0
    conn.meeting_last_snippet_index = 0
    
    # 播放进入会议提示音
    await conn.send_json({
        "type": "tts",
        "state": "start",
        "url": "config/assets/evening.wav",
        "text": "已进入会议模式"
    })
    await conn.send_json({
        "type": "tts",
        "state": "stop"
    })
    
    # 会议模式优先设备侧VAD
    try:
        srv = getattr(conn, "server", None)
        base_cfg = getattr(srv, "config", None) if srv else None
        if isinstance(base_cfg, dict):
            meeting_cfg = base_cfg.get("meeting", {})
        else:
            meeting_cfg = conn.config.get("meeting", {})
    except Exception:
        meeting_cfg = conn.config.get("meeting", {})
    
    if bool(meeting_cfg.get("prefer_device_vad", True)):
        conn.client_listen_mode = "manual"
        conn.logger.bind(tag=TAG).info("会议模式已启用设备侧VAD优先")
    
    # 尝试加载活跃会中状态
    try:
        from core.handle.meeting_handle import load_active_state_if_any, start_meeting_timers
        await load_active_state_if_any(conn)
        start_meeting_timers(conn)
    except Exception:
        pass
    
    await conn.send_json({
        "type": "mode",
        "status": "ok",
        "state": "start",
        "mode": "meeting"
    })


async def handle_working_mode_start(conn) -> None:
    """处理工作模式启动"""
    # 发送一次任务列表
    store = get_task_store()
    group_key = (getattr(conn, "device_id", "") or "")[:8]
    tasks = store.list_by_group(group_key)
    await conn.send_json({
        "type": "workflow",
        "event": "update",
        "tasks": tasks
    })
    
    await conn.send_json({
        "type": "mode",
        "status": "ok",
        "state": "start",
        "mode": "working"
    })


async def handle_coding_mode_start(conn) -> None:
    """处理编码模式启动"""
    conn.coding_stream_running = False
    conn.coding_phase_name = ""
    
    await conn.send_json({
        "type": "mode",
        "status": "ok",
        "state": "start",
        "mode": "coding"
    })


async def handle_peer(conn, msg_json: Dict[str, Any]) -> None:
    """处理 peer 消息"""
    try:
        # 透传顶层路由字段 to 给处理器，避免在 handler 内部引用未定义的变量
        to_list = msg_json.get("to", []) or []
        category = msg_json.get("category")  # 可选，主要用于快捷路径；不参与 schema 校验
        payload = msg_json.get("payload") or {}
        asyncio.create_task(handle_peer_message(conn, category, payload, to_list))
    except Exception:
        asyncio.create_task(handle_peer_message(conn, None, {}, []))


# 消息处理路由表
MESSAGE_HANDLERS: Dict[str, Callable] = {
    "hello": handle_hello,
    "abort": handle_abort,
    "listen": handle_listen,
    "iot": handle_iot,
    "mcp": handle_mcp,
    "meeting": handle_meeting,
    "coding": handle_coding,
    "workflow": handle_workflow,
    "config_update": handle_config_update,
    "mode": handle_mode,
    "peer": handle_peer,
}


async def handleTextMessage(conn, message):
    """处理文本消息的主入口"""
    try:
        msg_json = json.loads(message)
        
        # 处理整数消息（回显）
        if isinstance(msg_json, int):
            try:
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message if isinstance(message, str) else str(message)
            conn.logger.bind(tag=TAG).info(f"收到文本消息：{safe_msg}")
            await conn.send_text(message)
            return
        
        # 获取消息类型
        msg_type = msg_json.get("type")
        if not msg_type:
            conn.logger.bind(tag=TAG).warning(f"收到未知类型消息：{truncate_for_log(message)}")
            return
        
        # 设备上行 ACK/ERROR 统一 [ACK] 打点（阶段1不回发起方）
        if msg_type in ("ui.ack", "ui.error"):
            try:
                ts = msg_json.get("ts")
                elapsed = None
                if isinstance(ts, (int, float)):
                    try:
                        now_ms = int(time.time() * 1000)
                        elapsed = now_ms - int(ts)
                    except Exception:
                        elapsed = None
                _id = msg_json.get("id")
                code = msg_json.get("code") if msg_type == "ui.error" else None
                base = f"[ACK] id={_id} device={getattr(conn, 'device_id', None)}"
                if elapsed is not None:
                    base += f" elapsedMs={elapsed}"
                if code is not None:
                    base += f" code={code}"
                conn.logger.bind(tag=TAG).info(base)
            except Exception:
                conn.logger.bind(tag=TAG).info("[ACK] malformed")
            return

        # 消息转发：ui.render / device.control（热修，不改协议）
        if msg_type in ("ui.render", "device.control") and isinstance(msg_json.get("to"), list):
            to_list = [
                str(x).strip().strip('"').strip("'").lower()
                for x in (msg_json.get("to") or [])
                if str(x).strip() != ""
            ]
            if len(to_list) == 0:
                conn.logger.bind(tag=TAG).info("转发忽略：to 为空")
                return
            # 白名单校验：阶段1 仅允许 ui.render(text|list) 与 device.control(net.banner)
            allow = False
            if msg_type == "ui.render":
                body_kind = None
                try:
                    body = msg_json.get("body") or {}
                    body_kind = (body.get("kind") or "").strip().lower()
                except Exception:
                    body_kind = None
                allow = body_kind in ("text", "list")
            elif msg_type == "device.control":
                allow = (msg_json.get("action") == "net.banner")

            if not allow:
                mode = getattr(conn, "current_mode", None)
                detail = (msg_json.get("body") or {}).get("kind") if msg_type == "ui.render" else msg_json.get("action")
                conn.logger.bind(tag=TAG).info(
                    f"[DROP_BY_MODE] type={msg_type} reason=not-allowed-in-mode mode={mode} detail={detail}"
                )
                return

            # 进一步：按目标设备模式做白名单（阶段2：仅 dialog.preparing/active 放行，且 ui.render 仅 dialog.chat）
            def _allowed_by_target_mode(target_mode: str | None, payload: dict) -> bool:
                if target_mode not in ("dialog.preparing", "dialog.active"):
                    return False
                t = (payload.get("type") or "").strip().lower()
                if t == "ui.render":
                    page = (payload.get("page") or "").strip()
                    return page == "dialog.chat"
                if t == "device.control":
                    act = (payload.get("action") or "").strip()
                    return act in ("net.banner", "play.tone")
                return False

            # 并发转发到各在线设备；不在线仅日志；不回执
            async def _forward_one(did: str):
                try:
                    server = getattr(conn, "server", None)
                    if server is None or not hasattr(server, "send_to_device"):
                        return
                    # 目标设备模式校验
                    target_handler = None
                    try:
                        if hasattr(server, "get_device_handler"):
                            target_handler = server.get_device_handler(did)
                    except Exception:
                        target_handler = None
                    if target_handler is None:
                        conn.logger.bind(tag=TAG).info(f"设备不在线或发送失败：{did}")
                        return
                    target_mode = getattr(target_handler, "current_mode", None)
                    if not _allowed_by_target_mode(target_mode, msg_json):
                        detail = (msg_json.get("body") or {}).get("kind") if msg_type == "ui.render" else msg_json.get("action")
                        conn.logger.bind(tag=TAG).info(
                            f"[DROP_BY_MODE] type={msg_type} reason=not-allowed-in-mode mode={target_mode} detail={detail}"
                        )
                        return
                    ok = await server.send_to_device(did, msg_json)
                    if not ok:
                        conn.logger.bind(tag=TAG).info(f"设备不在线或发送失败：{did}")
                except Exception:
                    pass

            await asyncio.gather(*[_forward_one(d) for d in to_list])
            return

        # 记录消息日志
        try:
            if msg_type in ["hello", "listen", "iot", "mcp"]:
                safe_msg = truncate_for_log(message)
            elif msg_type in ["meeting", "coding", "workflow"]:
                safe_msg = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            else:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到{msg_type}消息：{safe_msg}")
        except Exception:
            conn.logger.bind(tag=TAG).info(f"收到{msg_type}消息")
        
        # 查找并执行对应的处理器
        handler = MESSAGE_HANDLERS.get(msg_type)
        if handler:
            await handler(conn, msg_json)
        else:
            conn.logger.bind(tag=TAG).warning(f"未知消息类型：{msg_type}")
            
    except json.JSONDecodeError:
        conn.logger.bind(tag=TAG).error(f"JSON解析失败：{truncate_for_log(message)}")
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"处理文本消息异常：{e}")

```

- 你说得对：欢迎页是硬件本地的，不能在欢迎页就允许渲染。为此我做了两层收敛：
  - 在后端连接侧，只有当设备进入对话相关模式时才放行渲染。
  - 在消息转发处，按“目标设备的当前模式”做白名单过滤。

- 已更新的后端行为（关键点）：
  - 进入拾音 start 时，将设备 `current_mode` 标记为 `dialog.preparing`，此后才允许渲染对话页。
  - 顶层直达转发时，除已有的类型白名单外，再检查“目标设备的模式”：
    - 仅当目标设备 `current_mode ∈ {dialog.preparing, dialog.active}` 才放行；
    - 且 `ui.render` 仅允许 `page == "dialog.chat"`；
    - `device.control` 仅允许 `net.banner`、`play.tone`（为阶段2留的提示音通道准备）。
  - 不满足条件的渲染，统一打印：
    - `[DROP_BY_MODE] type=<...> reason=not-allowed-in-mode mode=<目标设备当前模式> detail=<body.kind|action>`

- 结果：
  - 在欢迎页（设备还没进入对话模式）发送 `ui.render` 将被后端拒绝并日志为 `[DROP_BY_MODE]`；
  - 唤醒/开始拾音后，才会放行对话页渲染（对齐阶段2“对话最小闭环”）。

---

**User**

查看日志 是不是成功了? 我在硬件欢迎页面的时候使用meet001发送了一条渲染指令,在唤醒后又发送了一条

---

**Cursor**

### 1. 需求分析与方案设计
- 你想确认：在“欢迎页时发送的渲染是否被拦截、唤醒后再发是否放行并收到 ACK”。

### 2. 代码实现
- 从你提供的日志看，行为符合预期：
  - 欢迎页阶段被拦截（当前模式为 None）：
    - [DROP_BY_MODE] type=ui.render reason=not-allowed-in-mode mode=None detail=text
    - 重复一次同样的 DROP，说明欢迎页的两次尝试都被拒绝
  - 唤醒/开始拾音后（进入 dialog.preparing）：
    - [SEND] type=ui.render id=d1-001 to=94:a9:90:07:9d:88 mode=dialog.preparing page=dialog.chat body=text qps=ok
    - [ACK] id=d1-001 device=94:a9:90:07:9d:88
  - 同时，后端在 listen.start 时下发的提示页也有 ACK：
    - [ACK] id=dlg-listen-start device=94:a9:90:07:9d:88

### 3. 设计取舍与结论
- 结论：成功。欢迎页阶段的渲染被白名单规则阻断；唤醒后（dialog.preparing）渲染被放行并收到设备 ACK，完全符合“仅唤醒后可渲染”的阶段2对接要求。

---

**User**

非常不错,总结刚刚w做的更新,并在log.md@log.md 新增编辑内容10 编辑人是w (参考之前的log格式);

---

**Cursor**

```markdown
## 协同工作日志记录

8.22

## 编辑内容1 框架更新 确定渲染协议契约（v1）
编辑人 -w
- 变更内容 build.md prompt.md 全流程演示.md

## 编辑内容02 硬件引擎接入 UI 渲染最小闭环（阶段1）
编辑人 -w
- 变更内容 
    - hardware/main 增加 display/eink_render_engine.*；
    - 接入 application.cc OnIncomingJson 处理 ui.render 与 device.control(net.banner)；
    - 新增 Protocol::SendJson；唤醒后进入渲染测试页（等待后端指令…）；更新 CMakeLists.txt 编译新引擎；
    - 日志输出 [RENDER_RX]/[RENDER_OK]/[RENDER_ERR]

- 新增文件/接口
  - hardware/main/display/eink_render_engine.h/.cc：新增 `EinkRenderEngine`
    - 接口：`void Init(EinkDisplayST7306* display)`；`bool Render(const RenderPayload& payload)`；`void ShowNetBanner(const std::string& text, int duration_ms=3000)`
    - 数据结构：`RenderPayload{ page, headerTitle, bodyKind(TEXT|LIST), bodyText, bodyList(≤8), footerHint }`
    - 能力：整屏刷新、≥500ms合并节流（后台任务）、UTF‑8安全截断（title≤96B、正文≤120B、footer≤96B）、列表最多8行
  - hardware/main/display/eink_display_st7306.h/.cc：增加最小渲染辅助
    - `bool RenderSimplePage(title, bodyIsList, bodyText, bodyList, footerHint)` 整屏渲染并切换 `STATE_INTERACTIVE_UI`，避免欢迎/名片页时钟覆盖
    - `void ShowTopBanner(text)` 顶部红条白字横幅（3s 由引擎恢复上次渲染）

- application 接入
  - 初始化引擎：在 `Start()` 中对 `EinkDisplayST7306` 调用 `g_eink_render_engine.Init(...)`
  - 打开控制通道：`Opening control channel for render engine...`（保证能接收 JSON 指令）
  - OnIncomingJson 仅保留渲染相关分支：
    - `type=="ui.render"`：解析 header.title / body.kind in [text|list] / body.text / body.items / footer.hint / id?；调用 `EinkRenderEngine::Render(payload)`；回 `{type:"ui.ack",status:"ok",id}`；错误回 `{type:"ui.error",code:"INVALID_PAYLOAD",id?}`
    - `type=="device.control" && action=="net.banner"`：显示顶部横幅3s；含 id 回 ACK
    - `type=="peer"`（透传）：当 `payload.type` 为 `ui.render|device.control` 时等价处理（便于后端经 peer 转发）
  - 唤醒流程（阶段1）：欢迎态唤醒仅渲染固定“渲染测试页（等待后端指令…）”，不建立语音会话、不上报音频；停止唤醒词检测，置 Idle
  - 日志：`[RENDER_RX] type/page/id`、`[RENDER_OK] id`、`[RENDER_ERR] code`

- 协议/网络
  - `protocols/protocol.h/.cc`：新增 `bool SendJson(const std::string& json)` 复用底层 `SendText` 用于回 ACK/错误
  - `protocols/websocket_protocol.cc`：连接 URL 追加查询参数 `?device-id=<mac小写>&client-id=<uuid>`，确保后端正确路由设备（后端日志显示握手解析 device-id）

- 构建/依赖
  - `hardware/main/CMakeLists.txt`：新增源文件 `display/eink_render_engine.cc`

- 显示行为变化
  - 欢迎页→时钟更新只在 `STATE_WELCOME/STATE_CARD_DISPLAY` 下执行；渲染页切到 `STATE_INTERACTIVE_UI` 后不再被时钟覆盖
  - 横幅 3 秒后自动恢复上次渲染内容 (“临时提醒/公告”，对当前页面非侵入式覆盖展示，约 3 秒后自动回到原页面。)

- 测试指引（硬件侧联调）
  - 首选：后端直发顶层 `ui.render` / `device.control`，按 `device-id` 路由到设备（可在消息中带 `to:["<device-id>"]` 或后端通过握手 `device-id` 直接匹配路由）
  - 可选（过渡，不推荐）：`peer` 透传渲染，仅用于后端尚未实现直达路由时的应急联调

## 编辑内容03 后端渲染路由与发送接入（阶段1）
编辑人 -w
- 变更内容 
    - backend/core/websocket_server.py：新增设备直达发送与补投；注册流程补投 last_render
    - backend/core/handle/textHandle.py：统一入口实现 `ui.render` / `device.control` 转发与 ACK/ERROR 日志
    - backend/core/orchestration/render_schema.py：渲染负载轻量清洗（仅 text|list，忽略未知字段）并注入标题
    - backend/core/orchestration/render_sender.py：发送器（每设备≤2 QPS 限频、成功后缓存 last_render）
    - backend/core/utils/last_render_cache.py：内存缓存 set_last/get_last
    - backend/core/utils/device_registry.py：读取 `backend/data/devices.yaml`，提供 `get_display_title()`

- 新增文件/接口
  - websocket_server：`async def send_to_device(device_id, payload)`（直达路由；自动去除 `to` 字段；`ui.render`→清洗+限频+缓存，`device.control`→阶段1仅支持 `net.banner`）
  - websocket_server：`async def deliver_last_render_snapshot(device_id, handler)`（设备注册后补投“最后一次渲染”）
  - render_schema：`clean_render_payload(device_id, payload)`（只允许 `body.kind: text|list`，UTF-8 安全；忽略未知字段；注入标题）
  - render_sender：`send_render(conn_or_device_id, payload)`、`send_control(conn_or_device_id, action="net.banner", **kw)`（限频≥500ms/设备；成功后 `set_last`）
  - last_render_cache：`set_last/get_last`
  - device_registry：`get_display_title(device_id)`（返回“工牌{badge} · {owner}”，未注册返回 None）

- 行为/协议（阶段1）
  - 任意已连接客户端可发送顶层 `ui.render` / `device.control`，当携带 `to:["<device-id>", ...]` 时：
    - 标准化目标ID（小写、去空格/引号）
    - 删除 `to` 字段后分别投递到每个在线设备；不在线仅日志，不回执给发起方
  - 设备上行 `{type:"ui.ack"|"ui.error"}`：仅透传到服务端日志（不回送发起方）
  - 设备注册成功后：若存在 `last_render_cache`，立即补投一次
  - 渲染清洗：仅支持 `body.kind in [text|list]`；列表≤8行；忽略未知字段
  - 标题注入：若设备已在 `backend/data/devices.yaml` 注册，则覆盖为“工牌{badge} · {owner}”；未注册只记录日志，不在 UI 显示设备标识
  - 限频：每设备≥500ms（≤2 QPS），命中限频丢弃旧帧并记录日志

- 测试指引（后端侧联调）
  - 文本渲染：
    ```json
    { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-001","page":"dialog.chat","header":{},"body":{"kind":"text","text":"Hello 渲染测试"},"footer":{"hint":"后端→设备 OK"} }
    ```
  - 列表渲染：
    ```json
    { "type":"ui.render","to":["94:a9:90:07:9d:88"],"id":"d1-002","page":"dialog.chat","header":{},"body":{"kind":"list","items":["第一行","第二行","第三行"]},"footer":{"hint":"最多显示8行"} }
    ```
  - 顶部横幅：
    ```json
    { "type":"device.control","to":["94:a9:90:07:9d:88"],"id":"d1-003","action":"net.banner","text":"网络已连接 · 可开始测试","level":"info","duration_ms":3000 }
    ```

## 编辑内容04 后端直达转发白名单与补投日志（阶段1）
编辑人 -w
- 变更内容 
    - backend/core/websocket_server.py：`send_to_device` 兼容字符串载荷（自动解析 JSON）；补投 last_render 日志改为 `[REDELIVER] device=.. id=..`
    - backend/core/handle/textHandle.py：顶层 `ui.render`/`device.control` 转发加入白名单校验（仅 text|list / net.banner），不通过记 `[DROP_BY_MODE]`；设备上行 `ui.ack/ui.error` 记录耗时（若含 ts）

- 白名单与净化
  - 顶层直达消息：`ui.render` 仅允许 `body.kind in [text,list]`；`device.control` 仅允许 `action==net.banner`
  - 通过服务端 `send_to_device` 下发（内部仍会触发清洗与限频），未通过直接丢弃并日志 `[DROP_BY_MODE]`

- 兼容性
  - 维持既有协议不变，发起方无需调整；阶段1 不回发起方任何回执
  - 设备 ACK/ERROR 统一落日志，若带 `ts` 追加 `elapsedMs`

## 编辑内容05 移除设备上线补发“最后一次渲染”
编辑人 -w
- 变更内容
  - backend/core/websocket_server.py：删除注册时的 last_render 补投调用与实现，后端不再自动补发“上一屏”。
- 原因与影响
  - 原因：阶段1聚焦最小闭环；上线补发非必需且可能引起误会。
  - 影响：设备上线后由编排端决定是否主动下发渲染指令；不影响既有转发、白名单、限频与标题注入逻辑。

## 编辑内容06 硬件稳定性修复与渲染链路加固
编辑人 -w
- 变更内容（硬件侧汇总）
  - hardware/main/application.cc：
    - JSON 指令处理巩固：`OnIncomingJson` 保持仅处理 `ui.render` 与 `device.control(action==net.banner)`，并支持 `peer.payload` 透传等价处理；渲染成功/失败分别回 `{type:"ui.ack"}` 与 `{type:"ui.error"}`；统一日志 `[RENDER_RX] / [RENDER_OK] / [RENDER_ERR]`。
    - 主事件循环解耦：重负载 JSON 解析与渲染调用均通过 `Schedule` 投递到主循环执行，WebSocket 接收线程仅复制字符串，降低栈占用与并发风险。
    - 音频循环防饿死/看门狗：`AudioLoop` 改为固定节拍 `vTaskDelayUntil`（周期 2ms），并确保 `period>=1 tick` 以避免 `tasks.c:1476 (( xTimeIncrement > 0U ))` 断言；在无数据/早退分支处统一 `vTaskDelay(1ms)` 主动让步；将 `audio_loop` 任务优先级降至 4，避免长期占用 CPU 触发 WDT。
    - 唤醒并发防护：欢迎页唤醒仅切换至“渲染测试页（等待后端指令…）”，不建立语音会话；`wake_word_detect_.StopDetection()` 后增加 `vTaskDelay(20ms)`；通过原子标志 `wwd_suspended_` 抑制 `OnAudioInput` 路径并在适当处让步。
    - 时钟/页面互斥：欢迎态才更新时钟；渲染页由显示驱动切换为交互态，避免被时钟覆盖。
    - 其他：`STATE` 日志打印使用枚举名；`Unknown device state: 1` 为默认分支提示（对功能无影响）。
  - hardware/main/protocols/websocket_protocol.cc：
    - 设备标识路由：`OpenAudioChannel()` 在 URL 追加 `?device-id=<mac小写>&client-id=<uuid>` 并设置对应请求头，确保后端稳定识别与路由到设备。
    - 接收线程瘦身：仅对 `hello` 就地解析设事件位；其余 JSON 复制原文并投递主循环中解析与分发，显著降低接收线程栈压力；`ParseServerHello` 在异常 `transport` 下亦设置事件位，避免超时阻塞。
  - hardware/main/protocols/protocol.h/.cc：新增 `bool SendJson(const std::string& json)`，复用底层 `SendText` 统一回执发送。
  - hardware/main/display/eink_display_st7306.h/.cc：新增最小渲染接口 `RenderSimplePage(...)` 与 `ShowTopBanner(...)`；渲染时切换 `current_state_ = STATE_INTERACTIVE_UI`，阻止欢迎页时钟覆盖渲染结果。
    - 文本绘制修复：渲染页正文与列表由 `u8g2_->print(...)` 改为 `u8g2_->drawUTF8(...)`，并显式 `setForegroundColor(ST7306_COLOR_BLACK)` / `setBackgroundColor(ST7306_COLOR_WHITE)`，修复“日志 OK 但屏幕无字/白字白底”。
    - 顶部横幅修复：`ShowTopBanner` 文本绘制由 `print(...)` 改为 `drawUTF8(...)`，并确保前景为白色以适配红底，修复“红条显示但无文字/长文无显示”。
    - 顶部横幅增强：支持单行自适应与两行布局（优先 16 号粗体，超宽自动降到 14 号；仍超宽则按 UTF‑8 字符边界拆分为两行），末行自动加省略号，杜绝“末尾丢字”。
  - hardware/main/display/eink_render_engine.h/.cc：渲染引擎独立化（整屏刷新、≥500ms 节流、UTF‑8 安全截断、列表 ≤8 行、横幅 3s 自动恢复上次渲染）。
  - hardware/main/display/eink/u8g2_for_st73xx_impl.cpp：修正默认字体颜色为前景黑/背景白，避免默认状态下出现白底白字导致内容不可见。
  - hardware/main/audio_processing/wake_word_detect.cc：`GetFeedSize()` 增加空指针判定（`afe_iface_`/`afe_data_`），未初始化时安全返回 512；规避并发窗口空引用导致的崩溃/栈溢出征兆。
  - hardware/main/CMakeLists.txt：新增 `display/eink_render_engine.cc` 编译项。
  - hardware/sdkconfig.defaults.esp32s3：`CONFIG_PTHREAD_TASK_STACK_SIZE_DEFAULT=8192`，缓解第三方线程栈不足问题（结合接收线程瘦身后可稳定运行）。

- 新增/修改文件（硬件）
  - 新增：`hardware/main/display/eink_render_engine.h`、`hardware/main/display/eink_render_engine.cc`
  - 修改：`hardware/main/application.cc`、`hardware/main/CMakeLists.txt`
  - 修改：`hardware/main/display/eink_display_st7306.h`、`hardware/main/display/eink_display_st7306.cc`
  - 修改：`hardware/main/display/eink/u8g2_for_st73xx_impl.cpp`
  - 修改：`hardware/main/protocols/protocol.h`、`hardware/main/protocols/protocol.cc`
  - 修改：`hardware/main/protocols/websocket_protocol.cc`
  - 修改：`hardware/main/audio_processing/wake_word_detect.cc`
  - 修改：`hardware/sdkconfig.defaults.esp32s3`

- 日志与可观测性
  - 渲染链路：`[RENDER_RX] type/page/id`、`[RENDER_OK] id`、`[RENDER_ERR] code`
  - 通道与采样：`Opening control channel for render engine...`、`Resampling audio from X to Y`
  - WDT/断言：通过固定节拍与分支让步处理，预期不再出现 `task_wdt` 与 `xTaskDelayUntil` 断言。

- 行为与阶段边界（阶段1）
  - 不实现：`listen.start/stop`、分页/滚动/局部刷新、主题系统（后续阶段再启用）。
  - 唤醒后进入“渲染测试页（等待后端指令…）”，不建立语音通道、不上报音频。

 - 实测
  - 设备可以正常启动、联网、欢迎页与唤醒后切入“渲染测试页”;
  - 通过meet001给设备发送Raw JSON后硬件日志无 `task_wdt`、无 `xTaskDelayUntil` 断言，且出现成对 `[RENDER_RX]` → `[RENDER_OK]`,但是屏幕上没有刷新或者渲染任何内容

## 编辑内容07 万能UI合并与唤醒入口切换（阶段1收尾）
编辑人 - p

- 变更内容 
  - hardware/main/display/eink_display_st7306.h/.cc：
    - Universal Frame 定稿：`RenderSimplePage(...)` 渲染顶部状态栏（模式缩写 C1/M1/C2 + 子页标题、时间、Wi‑Fi、电量）、中部正文（text/list，UTF‑8 绘制）、底部操作/提示栏。
    - 文本渲染：正文与列表一律使用 `u8g2->drawUTF8(...)`，并显式 `setForegroundColor(ST7306_COLOR_BLACK)` / `setBackgroundColor(ST7306_COLOR_WHITE)`，避免白底白字。
    - Meeting 默认提示：当 `footerHint` 为空且推断为 M1 时，底部提示默认显示“结束会议”。
    - `DrawActionBar` 新增可选 `custom_hint` 参数，保持对旧调用的向后兼容。
  - hardware/main/application.cc：
    - 唤醒后入口从“渲染测试页（等待后端指令…）”切换为本地“万能UI”（`universal.home`），不建立语音会话、不上报音频；停止唤醒词检测并切到 Idle。
    - 万能UI默认内容：`headerTitle="对话模式"`（状态栏推断为 C1），正文为引导语，`footerHint="说 \"开始聊天\" 进入对话"`。

- 新增/修改文件（硬件）
  - 修改：`hardware/main/display/eink_display_st7306.h`、`hardware/main/display/eink_display_st7306.cc`
  - 修改：`hardware/main/application.cc`

- 行为与阶段边界
  - 唤醒后直接显示本地万能UI；后端仍可通过 `ui.render` 覆盖渲染。阶段1 仍不启用分页/滚动/局部刷新。

- 测试指引（硬件侧）
  - 从欢迎页说唤醒词 → 出现万能UI：状态栏显示“C1 对话模式”、时间、Wi‑Fi、电量；正文与底部提示展示正确。
  - 发送 `ui.render`（text/list）验证渲染与 ACK；发送 `device.control(net.banner)` 验证 3s 顶部横幅并自动恢复原页面。

- 兼容性
  - 渲染协议与日志格式不变；旧的 `DrawActionBar(...)` 调用保持生效。


## 编辑内容08 后端统一日志口径（SEND/ACK/DROP/FREEZE/REDELIVER）
编辑人 -w
- 变更内容 
  - backend/core/websocket_server.py：在 `send_to_device` 打印 `[SEND]`，包含 `type/id/to/mode/page|action/qps`；`ui.render` 的 qps 依据发送器返回状态（ok/limited）
  - backend/core/orchestration/render_sender.py：
    - 限频丢帧：`[DROP_INVALID] type=ui.render reason=rate-limited interval=<ms> device=<id>`
    - 清洗失败：`[DROP_INVALID] type=ui.render reason=schema-invalid device=<id>`
    - 返回 `(ok|False, status)` 供 `[SEND]` 标记 qps
    - 预留 `[FREEZE]` 日志位（阶段1不触发逻辑）
  - backend/core/orchestration/render_schema.py：
    - 非法载荷/缺字段/不支持的 body.kind：统一打印 `[DROP_INVALID]`，附 `missing/expected/kind` 等键值
  - backend/core/handle/textHandle.py：
    - 收到 `ui.ack/ui.error`：统一打印 `[ACK] id=<id> device=<device> elapsedMs=<ms> code?<error>`
    - 白名单不通过：`[DROP_BY_MODE] type=<type> reason=not-allowed-in-mode mode=<mode> detail=<body.kind|action>`

- 行为说明
  - SEND：发送前统一打点；`ui.render`/`device.control` 两分支均覆盖
  - ACK：设备回执（包含 error 也计入），若带 `ts` 记录耗时
  - DROP：
    - `DROP_BY_MODE` 白名单不通过（阶段1仅 text|list、net.banner）
    - `DROP_INVALID` 清洗失败/字段缺失/限频
  - FREEZE：阶段1仅保留日志示例，不触发封禁
  - REDELIVER：仅当编排端显式补投时打印（后端已取消自动补投）

## 编辑内容09 音频会话模式调整回退（对齐后端处理）
编辑人 - p

- 变更内容 
  - 恢复“实时对话”的音频处理链路：
     在 hardware/main/application.cc 的唤醒回调中（Welcome/Idle 两种状态）：
    渲染本地万能UI后，恢复音频输入循环并进入会话：
    调用 ResumeAudioLoop();
    调用 ToggleChatState();（打开控制/音频通道并进入 Listening/Realtime 取决于配置）
    保留了停止唤醒词检测与20ms让步，避免并发竞态。
    不改动后端判断逻辑，硬件不做“结束会议”等业务判断。
  - 唤醒回调（Welcome/Idle）：
    渲染本地万能UI后，不再调用 ToggleChatState，而是：
    ResumeAudioLoop()（恢复喂入开关）
    StartListening()（直接走已存在的控制通道发送 start-listening，避免二次 OpenAudioChannel）
    保留且顺序化：停止唤醒词检测 → 20ms 让步 → SetDeviceState(Idle) → Resume/StartListening，降低并发窗口风险。。

- 原因说明
  - 错误 TcpTransport: Receive failed: -1 / WS disconnected

- 回归测试
  - 无 TcpTransport -1/WS 重连环路；单次 listen.start 收敛
    对话链路可用（上行/下行音频正常），UI 稳定显示
    关键埋点齐全，可回溯问题根因

## 编辑内容10 阶段2对话闭环接入（唤醒后才允许渲染）
编辑人 - w

- 变更内容
  - backend/core/handle/textHandle.py：
    - 调整渲染触发时机：仅“唤醒/开始拾音”后由后端下发渲染；欢迎页阶段一律拦截。
    - 在 `handle_listen(state=="start")` 将目标设备 `current_mode=dialog.preparing`，并发送对话提示页（id=dlg-listen-start，“请说出您的问题…”）。
    - 在 `handle_listen_detect` 检测到唤醒词时，仅发送“准备聆听”提示页（id=dlg-ready），不直接进入聊天/TTS。
    - 顶层直达转发增加“目标设备模式白名单”：仅当目标设备 `mode ∈ {dialog.preparing, dialog.active}` 才放行；
      - `ui.render` 仅允许 `page==dialog.chat`；
      - `device.control` 仅允许 `net.banner | play.tone`；
      - 不满足打印 `[DROP_BY_MODE] type=.. mode=<target_mode> detail=<kind|action>`。
  - backend/core/websocket_server.py：保留统一 `[SEND]` 打点（含 type/id/to/mode/page|action/qps）
  - backend/core/orchestration/render_schema.py / render_sender.py：保留 `[DROP_INVALID]`（schema/限频等）与限频状态返回，供 `[SEND]` 标记 qps。

- 行为与验证
  - 欢迎页阶段：来自 meet001 的 `ui.render(text)` 被拦截，日志示例：
    - `[DROP_BY_MODE] type=ui.render reason=not-allowed-in-mode mode=None detail=text`
  - 唤醒后（listen.start → dialog.preparing）：
    - 后端发送对话页或外部渲染指令均被放行，例如：
      - `[SEND] type=ui.render id=d1-001 to=94:a9:90:07:9d:88 mode=dialog.preparing page=dialog.chat body=text qps=ok`
      - `[ACK] id=d1-001 device=94:a9:90:07:9d:88`
    - 后端提示页也收到 ACK：`[ACK] id=dlg-listen-start device=...`

- 阶段边界
  - 仅对话相关模式放行渲染；欢迎页不接受远程渲染，避免与硬件本地欢迎 UI 冲突。
  - 其它日志统一口径（SEND/ACK/DROP_INVALID/DROP_BY_MODE），便于排障与审计。
```

- 我已在 `collaboration/log.md` 增加“编辑内容10 阶段2对话闭环接入（唤醒后才允许渲染）”，记录本次后端改动与验证结论。
- 要点：欢迎页一律拦截渲染；listen.start 后转入 `dialog.preparing` 并发对话提示页；仅在对话相关模式放行 `dialog.chat` 渲染与 `net.banner|play.tone` 控制；日志口径统一（SEND/ACK/DROP_BY_MODE/DROP_INVALID）。

---

**User**

# 已知内容
项目架构和实施原则请参考bulid.md@build.md  , 现在是阶段2,你负责后端部分 后端部分代码是backend 注意硬件部分已经完成了自己的工作,只等待后端开发和更新了;

# 具体任务1 状态机字段与跳转（ConnectionHandler 内存即可）
     - 新增并维护 `currentMode`（默认为 connected(idle)）。
     - 事件接入：`mode.start(dialog)` / `listen.start` → set dialog.preparing；`listen.detect` → 保持 preparing 并发送“准备聆听”提示页；编排切换 → set dialog.active。
# 具体任务2 事件编排与渲染
     - dialog.preparing：下发“建立连接/请稍候”（`ui.render:text`，id=dlg-listen-start）+ `device.control: play.tone`；收到 `listen.detect` 时下发“准备聆听”（id=dlg-ready）。
     - dialog.active：下发“开始对话”（`ui.render:text`）。
# 具体任务3 直达 to 白名单（textHandle 转发入口）
     - 仅当“目标设备”的 `currentMode ∈ {dialog.preparing, dialog.active}` 时放行：`ui.render(page==dialog.chat)` 与 `device.control(net.banner|play.tone)`；否则 `[DROP_BY_MODE]`。
# 具体任务4 对话链路（最小闭环）
     - ASR：接入现有 provider，拿到识别文本（允许分段/最终）。
     - LLM：将识别文本交给 LLM，生成回复文本。
     - TTS：将回复文本合成语音，按帧下发到设备播放；无 TTS 时可先仅下发 `ui.render:text`。

# 具体任务5 在确认完成上述任务1,2,3,4后,总结刚刚w做的更新,并在log.md 新增编辑内容01 编辑人是w (参考之前的log格式);

---

**Cursor**

```python
import os
import sys
import copy
import json
import uuid
import time
import queue
import asyncio
import threading
import traceback
from config.logger import truncate_for_log
import subprocess
import websockets
from core.handle.mcpHandle import call_mcp_tool
from core.utils.util import (
    extract_json_from_string,
    check_vad_update,
    check_asr_update,
    filter_sensitive_info,
)
from typing import Dict, Any
from core.mcp.manager import MCPManager
from core.utils.modules_initialize import (
    initialize_modules,
    initialize_tts,
    initialize_asr,
)
from core.handle.reportHandle import report
from core.providers.tts.default import DefaultTTS
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Message, Dialogue
from core.providers.asr.dto.dto import InterfaceType
from core.handle.textHandle import handleTextMessage
from core.handle.functionHandler import FunctionHandler
from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import Action, ActionResponse
from core.auth import AuthMiddleware, AuthenticationError
from config.config_loader import get_private_config_from_api
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging, build_module_string, update_module_string
from config.manage_api_client import DeviceNotFoundException, DeviceBindException


TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        server=None,
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # 保存server实例的引用

        self.auth = AuthMiddleware(config)
        self.need_bind = False
        self.bind_code = None
        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.client_ip_info = {}
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"

        # 客户端状态相关
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"
        # 监听状态机：idle -> listening -> finalizing -> idle
        self.listen_state = "idle"
        self._listen_state_timer = None
        self._last_listen_event_ms = 0

        # 线程任务相关
        self.loop = asyncio.get_event_loop()
        self.stop_event = threading.Event()
        # 缩减线程池，降低上下文切换与内存占用
        try:
            meeting_cfg = self.config.get("meeting", {}) if isinstance(self.config, dict) else {}
            # 固化 W3：线程池默认 2，可被 meeting.threadpool_max_workers 覆盖
            default_workers = 2
            max_workers = int(meeting_cfg.get("threadpool_max_workers", default_workers))
            if max_workers < 1:
                max_workers = default_workers
        except Exception:
            max_workers = 2
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 添加上报线程池
        self.report_queue = queue.Queue()
        self.report_thread = None
        # 未来可以通过修改此处，调节asr的上报和tts的上报，目前默认都开启
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

        # 依赖的组件
        self.vad = None
        self.asr = None
        self.tts = None
        self._asr = _asr
        self._vad = _vad
        self.llm = _llm
        self.memory = _memory
        self.intent = _intent

        # vad相关变量
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0.0
        self.client_no_voice_last_time = 0.0
        self.client_voice_stop = False
        self.client_voice_frame_count = 0

        # asr相关变量
        # 因为实际部署时可能会用到公共的本地ASR，不能把变量暴露给公共ASR
        # 所以涉及到ASR的变量，需要在这里定义，属于connection的私有变量
        self.asr_audio = []
        self.asr_audio_queue = queue.Queue()

        # llm相关变量
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # tts相关变量
        self.sentence_id = None

        # iot相关变量
        self.iot_descriptors = {}
        self.func_handler = None

        # 模式状态（meeting/coding/working/dialog）
        # 阶段2默认进入 connected.idle，欢迎页不允许渲染
        self.current_mode = "connected.idle"
        # 会议模式相关缓存
        self.meeting_segments = []  # [{"ts": int(ms), "text": str}]
        self.meeting_start_ts = 0.0
        self.meeting_last_snippet_ts = 0.0
        self.meeting_last_snippet_index = 0
        # 会议片段节流与幂等状态
        self.meeting_recent_texts = {}
        self.meeting_pending_texts = []
        self.meeting_last_emit_ms = 0.0
        self.meeting_finalized = False
        # 编码模式日志流运行标志/阶段名（用于 stop/clear/phase 扩展）
        self.coding_stream_running = False
        self.coding_phase_name = ""

        self.cmd_exit = self.config["exit_commands"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        # 是否在聊天结束后关闭连接
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"

        self.timeout_task = None
        # 放宽默认空闲阈值：默认 600s + 60s 兜底；允许配置覆盖
        try:
            base_idle = int(self.config.get("close_connection_no_voice_time", 600))
        except Exception:
            base_idle = 600
        self.timeout_seconds = base_idle + 60  # 第一层之外的兜底关闭

        # {"mcp":true} 表示启用MCP功能
        self.features = None

        # LLM 按模式实例缓存（随连接释放）
        self._llm_cache = {}

    def _get_base_config(self) -> Dict[str, Any]:
        try:
            srv = getattr(self, "server", None)
            base_cfg = getattr(srv, "config", None) if srv else None
            if isinstance(base_cfg, dict):
                return base_cfg
        except Exception:
            pass
        return self.config if isinstance(self.config, dict) else {}

    def get_llm_for(self, purpose: str):
        """按用途/模式返回 LLM 实例，懒加载并缓存。

        purpose 可取："chat" | "meeting" | "coding" | "working" | "intent" | "memory"
        """
        try:
            key = str(purpose or "chat").lower()
        except Exception:
            key = "chat"

        # 缓存命中
        if key in self._llm_cache and self._llm_cache[key] is not None:
            return self._llm_cache[key]

        base_cfg = self._get_base_config()
        # 读取映射
        mapping = {}
        try:
            mapping = base_cfg.get("llm_by_mode", {}) or {}
        except Exception:
            mapping = {}

        mapping_val = mapping.get(key, None)
        if mapping_val is None:
            # 用途未配置专用 LLM，回退 default 并记录告警
            try:
                self.logger.bind(tag=TAG).warning(
                    f"get_llm_for: 未找到用途 {key} 的 llm_by_mode 配置，回退到 default"
                )
            except Exception:
                pass
            mapping_val = mapping.get("default")

        alias = None
        overrides = None
        if isinstance(mapping_val, dict):
            # 支持 { alias: xxx, overrides: { model_name: '...' } } 或直接平铺覆盖字段
            alias = mapping_val.get("alias") or mapping_val.get("name") or mapping_val.get("module") or mapping_val.get("llm")
            overrides = mapping_val.get("overrides")
            if overrides is None:
                # 将除别名键外的其余键视为覆盖
                tmp = dict(mapping_val)
                for k in ["alias", "name", "module", "llm", "overrides"]:
                    tmp.pop(k, None)
                overrides = tmp if len(tmp) > 0 else None
        elif isinstance(mapping_val, str) and len(mapping_val) > 0:
            alias = mapping_val

        # 回退默认 alias
        try:
            if alias is None:
                alias = self.config["selected_module"]["LLM"]
        except Exception:
            alias = None

        # 若无覆盖且别名等于当前默认，直接复用
        try:
            current_default_alias = self.config["selected_module"]["LLM"]
            if (overrides is None or len(overrides) == 0) and alias == current_default_alias and getattr(self, "llm", None) is not None:
                self._llm_cache[key] = self.llm
                return self.llm
        except Exception:
            pass

        # 统一委托 server 级共享工厂；失败回退默认 LLM
        try:
            srv = getattr(self, "server", None)
            if srv and hasattr(srv, "get_or_create_llm") and callable(getattr(srv, "get_or_create_llm")) and alias:
                instance = srv.get_or_create_llm(alias, overrides)
                if instance is not None:
                    self._llm_cache[key] = instance
                    return instance
            # 回退默认
            self._llm_cache[key] = self.llm
            return self.llm
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"get_llm_for 失败({key}): {e}，回退默认LLM")
            self._llm_cache[key] = self.llm
            return self.llm

    async def handle_connection(self, ws, path=None):
        try:
            # 获取并验证headers（兼容 websockets 库的属性命名）
            try:
                raw_headers = getattr(ws, "request_headers", {})
                # 统一小写键，便于后续从 headers 获取 authorization/device-id
                headers_lower = {}
                try:
                    # 优先使用 items() 以兼容 websockets 的 Headers 类型
                    for k, v in raw_headers.items():
                        headers_lower[str(k).lower()] = v
                except Exception:
                    try:
                        headers_lower = {str(k).lower(): v for k, v in dict(raw_headers).items()}
                    except Exception:
                        headers_lower = {}
                self.headers = headers_lower
            except Exception:
                self.headers = {}

            # 统一调用服务器封装的握手解析；其次尝试 Header；最后回退自动分配
            device_id_from_query = None
            client_id_from_query = None
            raw_path_from_server = None
            try:
                server_obj = getattr(self, "server", None)
                if server_obj and hasattr(server_obj, "parse_ids_from_handshake"):
                    d, c, rawp = server_obj.parse_ids_from_handshake(ws, path)
                    device_id_from_query = d
                    client_id_from_query = c
                    raw_path_from_server = rawp
            except Exception:
                pass

            # 从 Header 兜底解析（包含非规范写法）
            def _normalize_id(v):
                try:
                    if v is None:
                        return None
                    vv = str(v).strip().strip('"').strip("'")
                    return vv.lower() if vv else None
                except Exception:
                    return None
            header_device_id = _normalize_id(
                self.headers.get("device-id")
                or self.headers.get("device_id")
                or self.headers.get("x-device-id")
                or self.headers.get("x-device_id")
            )
            header_client_id = _normalize_id(
                self.headers.get("client-id")
                or self.headers.get("client_id")
                or self.headers.get("x-client-id")
                or self.headers.get("x-client_id")
            )

            # 赋值优先级：Query > Header > 回退
            chosen_device_id = device_id_from_query or header_device_id or header_client_id
            chosen_client_id = client_id_from_query or header_client_id or chosen_device_id

            if chosen_device_id:
                self.headers["device-id"] = chosen_device_id
                if chosen_client_id:
                    self.headers["client-id"] = chosen_client_id
                # 打印来源与解析快照（包含原始 path 片段便于定位异常客户端）
                try:
                    raw_paths_snapshot = []
                    if isinstance(raw_path_from_server, str) and raw_path_from_server:
                        raw_paths_snapshot.append(raw_path_from_server[:256])
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                        for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                            val = getattr(ws, attr, "")
                            if isinstance(val, str) and val:
                                raw_paths_snapshot.append(val[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    src = "query" if device_id_from_query else "header"
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={src}, rawPaths={truncate_for_log(str(raw_paths_snapshot))})"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).info(
                        f"握手解析 device-id: {self.headers.get('device-id')} (source={'query' if device_id_from_query else 'header'})"
                    )
            else:
                # 容错：仍未取到则自动分配，保证连接可用；同时输出诊断快照
                auto_device_id = f"auto-{uuid.uuid4().hex[:8]}"
                self.headers["device-id"] = auto_device_id
                self.headers["client-id"] = auto_device_id
                try:
                    raw_paths_snapshot = []
                    try:
                        raw_ws_path = getattr(ws, "path", "")
                        if raw_ws_path:
                            raw_paths_snapshot.append(raw_ws_path[:256])
                    except Exception:
                        pass
                    if isinstance(path, str) and path:
                        raw_paths_snapshot.insert(0, path[:256])
                    header_keys = list(self.headers.keys())
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}; rawPaths={truncate_for_log(str(raw_paths_snapshot))}, headerKeys={truncate_for_log(str(header_keys))}"
                    )
                except Exception:
                    self.logger.bind(tag=TAG).warning(
                        f"未从握手中获取 device-id，已回退自动分配 device-id={auto_device_id}"
                    )
            # 获取客户端ip地址
            try:
                remote = getattr(ws, "remote_address", None)
                if isinstance(remote, tuple) and len(remote) >= 1:
                    self.client_ip = remote[0]
                else:
                    self.client_ip = str(remote) if remote is not None else ""
            except Exception:
                self.client_ip = ""
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            # 进行认证
            await self.auth.authenticate(self.headers)

            # 认证通过,继续处理
            self.websocket = ws
            self.device_id = self.headers.get("device-id", None)
            # 在 server 上注册设备路由（自动断开旧连接）
            if self.server and self.device_id:
                ok = await self.server.register_device_handler(self.device_id, self)
                if ok is False:
                    self.logger.bind(tag=TAG).error(f"设备注册失败: {self.device_id}")
                    await ws.send("设备注册失败")
                    await self.close(ws)
                    return

            # 启动超时检查任务
            self.timeout_task = asyncio.create_task(self._check_timeout())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id
            await self.websocket.send(json.dumps(self.welcome_msg))

            # 获取差异化配置
            self._initialize_private_config()
            # 异步初始化
            self.executor.submit(self._initialize_components)

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("客户端断开连接")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            try:
                safe_e = truncate_for_log(str(e))
                safe_tb = truncate_for_log(stack_trace)
            except Exception:
                safe_e = str(e)
                safe_tb = stack_trace
            self.logger.bind(tag=TAG).error(f"Connection error: {safe_e}-{safe_tb}")
            return
        finally:
            try:
                # 注销设备路由映射
                if self.server and self.device_id:
                    await self.server.unregister_device_handler(self.device_id, self)
            finally:
                await self._save_and_close(ws)

    async def _save_and_close(self, ws):
        """保存记忆并关闭连接"""
        try:
            if self.memory:
                # 使用线程池异步保存记忆
                def save_memory_task():
                    try:
                        # 创建新事件循环（避免与主循环冲突）
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            self.memory.save_memory(self.dialogue.dialogue)
                        )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
                    finally:
                        loop.close()

                # 启动线程保存记忆，不等待完成
                threading.Thread(target=save_memory_task, daemon=True).start()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
        finally:
            # 立即关闭连接，不等待记忆保存完成
            await self.close(ws)

    def reset_timeout(self):
        """重置超时计时器"""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._check_timeout())

    async def _route_message(self, message):
        """消息路由"""
        # 重置超时计时器
        self.reset_timeout()

        if isinstance(message, str):
            # 轻量 ping/keepalive：收到后仅重置计时器并忽略
            try:
                import json as _json
                try:
                    obj = _json.loads(message)
                except Exception:
                    obj = None
                if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
                    try:
                        # 可选：立即回 pong
                        await self.websocket.send(_json.dumps({"type": "pong"}))
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            if self.vad is None:
                return
            if self.asr is None:
                return
            self.asr_audio_queue.put(message)

    async def handle_restart(self, message):
        """处理服务器重启请求"""
        try:

            self.logger.bind(tag=TAG).info("收到服务器重启指令，准备执行...")

            # 发送确认响应
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "服务器重启中...",
                        "content": {"action": "restart"},
                    }
                )
            )

            # 异步执行重启操作
            def restart_server():
                """实际执行重启的方法"""
                time.sleep(1)
                self.logger.bind(tag=TAG).info("执行服务器重启...")
                # 后台重启：避免继承TTY，全部重定向，保证 nohup/backgroud 模式不被SIGTTIN挂起
                with open(os.devnull, "rb", buffering=0) as devnull_in, \
                     open(os.devnull, "ab", buffering=0) as devnull_out, \
                     open(os.devnull, "ab", buffering=0) as devnull_err:
                    subprocess.Popen(
                        [sys.executable, "app.py"],
                        stdin=devnull_in,
                        stdout=devnull_out,
                        stderr=devnull_err,
                        start_new_session=True,
                        close_fds=True,
                    )
                os._exit(0)

            # 使用线程执行重启避免阻塞事件循环
            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"重启失败: {str(e)}")
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    }
                )
            )

    def _initialize_components(self):
        try:
            self.selected_module_str = build_module_string(
                self.config.get("selected_module", {})
            )
            update_module_string(self.selected_module_str)
            """初始化组件"""
            if self.config.get("prompt") is not None:
                self.prompt = self.config["prompt"]
                self.change_system_prompt(self.prompt)
                self.logger.bind(tag=TAG).info(
                    f"初始化组件: prompt成功 {self.prompt[:50]}..."
                )

            """初始化本地组件"""
            if self.vad is None:
                self.vad = self._vad
            if self.asr is None:
                self.asr = self._initialize_asr()
            # 打开语音识别通道
            asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)

            if self.tts is None:
                self.tts = self._initialize_tts()
            # 会议模式可禁用 TTS 通道（懒启动）
            disable_tts = False
            try:
                srv = getattr(self, "server", None)
                base_cfg = getattr(srv, "config", None) if srv else None
                if isinstance(base_cfg, dict):
                    meeting_cfg2 = base_cfg.get("meeting", {})
                else:
                    meeting_cfg2 = self.config.get("meeting", {})
                disable_tts = bool(meeting_cfg2.get("disable_tts", False))
            except Exception:
                disable_tts = False
            if not disable_tts:
                asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)

            """加载记忆"""
            self._initialize_memory()
            """加载意图识别"""
            self._initialize_intent()
            """初始化上报线程"""
            self._init_report_threads()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"实例化组件失败: {e}")

    def _init_report_threads(self):
        """初始化ASR和TTS上报线程"""
        if not self.read_config_from_api or self.need_bind:
            return
        if self.chat_history_conf == 0:
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(
                target=self._report_worker, daemon=True
            )
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("TTS上报线程已启动")

    def _initialize_tts(self):
        """初始化TTS"""
        tts = None
        if not self.need_bind:
            tts = initialize_tts(self.config)

        if tts is None:
            tts = DefaultTTS(self.config, delete_audio_file=True)

        return tts

    def _initialize_asr(self):
        """初始化ASR"""
        if self._asr.interface_type == InterfaceType.LOCAL:
            # 如果公共ASR是本地服务，则直接返回
            # 因为本地一个实例ASR，可以被多个连接共享
            asr = self._asr
        else:
            # 如果公共ASR是远程服务，则初始化一个新实例
            # 因为远程ASR，涉及到websocket连接和接收线程，需要每个连接一个实例
            asr = initialize_asr(self.config)

        return asr

    def _initialize_private_config(self):
        """如果是从配置文件获取，则进行二次实例化"""
        if not self.read_config_from_api:
            return
        """从接口获取差异化的配置进行二次实例化，非全量重新实例化"""
        try:
            begin_time = time.time()
            private_config = get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} 秒，获取差异化配置成功: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            private_config = {}

        init_llm, init_tts, init_memory, init_intent = (
            False,
            False,
            False,
            False,
        )

        init_vad = check_vad_update(self.common_config, private_config)
        init_asr = check_asr_update(self.common_config, private_config)

        if init_vad:
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if init_asr:
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            model_intent = private_config.get("selected_module", {}).get("Intent", {})
            self.config["selected_module"]["Intent"] = model_intent
            # 加载插件配置
            if model_intent != "Intent_nointent":
                plugin_from_server = private_config.get("plugins", {})
                for plugin, config_str in plugin_from_server.items():
                    plugin_from_server[plugin] = json.loads(config_str)
                self.config["plugins"] = plugin_from_server
                self.config["Intent"][self.config["selected_module"]["Intent"]][
                    "functions"
                ] = plugin_from_server.keys()
        if private_config.get("prompt", None) is not None:
            self.config["prompt"] = private_config["prompt"]
        if private_config.get("summaryMemory", None) is not None:
            self.config["summaryMemory"] = private_config["summaryMemory"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(private_config["device_max_output_size"])
        if private_config.get("chat_history_conf", None) is not None:
            self.chat_history_conf = int(private_config["chat_history_conf"])
        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                init_tts,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        if self.memory is None:
            return
        """初始化记忆模块"""
        # 按模式选择记忆总结 LLM（可被 llm_by_mode.memory 覆盖）
        chosen_llm = self.llm
        try:
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                selected = self.get_llm_for("memory")
                if selected is not None:
                    chosen_llm = selected
        except Exception:
            pass

        self.memory.init_memory(
            role_id=self.device_id,
            llm=chosen_llm,
            summary_memory=self.config.get("summaryMemory", None),
            save_to_file=not self.read_config_from_api,
        )

        # 获取记忆总结配置
        memory_config = self.config["Memory"]
        memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
            "type"
        ]
        # 如果使用 nomen，直接返回
        if memory_type == "nomem":
            return
        # 使用 mem_local_short 模式
        elif memory_type == "mem_local_short":
            memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
                "llm"
            ]
            if memory_llm_name and memory_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                memory_llm_config = self.config["LLM"][memory_llm_name]
                memory_llm_type = memory_llm_config.get("type", memory_llm_name)
                memory_llm = llm_utils.create_instance(
                    memory_llm_type, memory_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为记忆总结创建了专用LLM: {memory_llm_name}, 类型: {memory_llm_type}"
                )
                self.memory.set_llm(memory_llm)
            else:
                # 否则使用主LLM
                self.memory.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

    def _initialize_intent(self):
        if self.intent is None:
            return
        self.intent_type = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ]["type"]
        if self.intent_type == "function_call" or self.intent_type == "intent_llm":
            self.load_function_plugin = True
        """初始化意图识别模块"""
        # 获取意图识别配置
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # 如果使用 nointent，直接返回
        if intent_type == "nointent":
            return
        # 使用 intent_llm 模式
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get("type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为意图识别创建了专用LLM: {intent_llm_name}, 类型: {intent_llm_type}"
                )
                # 按模式选择意图识别 LLM（可被 llm_by_mode.intent 覆盖）
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(intent_llm)
                    else:
                        self.intent.set_llm(intent_llm)
                except Exception:
                    self.intent.set_llm(intent_llm)
            else:
                # 否则使用主LLM
                try:
                    if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                        selected = self.get_llm_for("intent")
                        if selected is not None:
                            self.intent.set_llm(selected)
                        else:
                            self.intent.set_llm(self.llm)
                    else:
                        self.intent.set_llm(self.llm)
                except Exception:
                    self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

        """加载插件"""
        self.func_handler = FunctionHandler(self)
        self.mcp_manager = MCPManager(self)

        """加载MCP工具"""
        asyncio.run_coroutine_threadsafe(
            self.mcp_manager.initialize_servers(), self.loop
        )

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        # 更新系统prompt至上下文
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query, tool_call=False):
        try:
            safe_query = truncate_for_log(query)
        except Exception:
            safe_query = query
        self.logger.bind(tag=TAG).info(f"大模型收到用户消息: {safe_query}")
        self.llm_finish_task = False

        if not tool_call:
            self.dialogue.put(Message(role="user", content=query))

        # Define intent functions
        functions = None
        if self.intent_type == "function_call" and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        if hasattr(self, "mcp_client"):
            mcp_tools = self.mcp_client.get_available_tools()
            if mcp_tools is not None and len(mcp_tools) > 0:
                if functions is None:
                    functions = []
                functions.extend(mcp_tools)
        response_message = []

        try:
            # 使用带记忆的对话
            memory_str = None
            if self.memory is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self.memory.query_memory(query), self.loop
                )
                memory_str = future.result()

            self.sentence_id = str(uuid.uuid4().hex)


            # 按当前模式选择 LLM（默认chat；coding/working 切换对应别名）
            purpose = self.current_mode or "chat"
            active_llm = self.llm
            if hasattr(self, "get_llm_for") and callable(self.get_llm_for):
                try:
                    active_llm = self.get_llm_for(purpose) or self.llm
                except Exception:
                    active_llm = self.llm

            if self.intent_type == "function_call" and functions is not None:
                # 使用支持functions的streaming接口
                llm_responses = active_llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                    functions=functions,
                )
            else:
                llm_responses = active_llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        # 处理流式响应
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        text_index = 0
        self.client_abort = False
        for response in llm_responses:
            if self.client_abort:
                break
            if self.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None
                if content is not None and len(content) > 0:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    # print("content_arguments", content_arguments)
                    tool_call_flag = True

                if tools_call is not None and len(tools_call) > 0:
                    tool_call_flag = True
                    if tools_call[0].id is not None:
                        function_id = tools_call[0].id
                    if tools_call[0].function.name is not None:
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments is not None:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response
            if content is not None and len(content) > 0:
                if not tool_call_flag:
                    response_message.append(content)
                    if text_index == 0:
                        self.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=self.sentence_id,
                                sentence_type=SentenceType.FIRST,
                                content_type=ContentType.ACTION,
                            )
                        )
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=self.sentence_id,
                            sentence_type=SentenceType.MIDDLE,
                            content_type=ContentType.TEXT,
                            content_detail=content,
                        )
                    )
                    text_index += 1
        # 处理function call
        if tool_call_flag:
            bHasError = False
            if function_id is None:
                a = extract_json_from_string(content_arguments)
                if a is not None:
                    try:
                        content_arguments_json = json.loads(a)
                        function_name = content_arguments_json["name"]
                        function_arguments = json.dumps(
                            content_arguments_json["arguments"], ensure_ascii=False
                        )
                        function_id = str(uuid.uuid4().hex)
                    except Exception as e:
                        bHasError = True
                        response_message.append(a)
                else:
                    bHasError = True
                    response_message.append(content_arguments)
                if bHasError:
                    self.logger.bind(tag=TAG).error(
                        f"function call error: {content_arguments}"
                    )
            if not bHasError:
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                # 处理Server端MCP工具调用
                if self.mcp_manager.is_mcp_tool(function_name):
                    result = self._handle_mcp_tool_call(function_call_data)
                elif hasattr(self, "mcp_client") and self.mcp_client.has_tool(
                    function_name
                ):
                    # 如果是小智端MCP工具调用
                    self.logger.bind(tag=TAG).debug(
                        f"调用小智端MCP工具: {function_name}, 参数: {function_arguments}"
                    )
                    try:
                        result = asyncio.run_coroutine_threadsafe(
                            call_mcp_tool(
                                self, self.mcp_client, function_name, function_arguments
                            ),
                            self.loop,
                        ).result()
                        self.logger.bind(tag=TAG).debug(f"MCP工具调用结果: {result}")

                        resultJson = None
                        if isinstance(result, str):
                            try:
                                resultJson = json.loads(result)
                            except Exception as e:
                                self.logger.bind(tag=TAG).error(
                                    f"解析MCP工具返回结果失败: {e}"
                                )

                        # 视觉大模型不经过二次LLM处理
                        if (
                            resultJson is not None
                            and isinstance(resultJson, dict)
                            and "action" in resultJson
                        ):
                            result = ActionResponse(
                                action=Action[resultJson["action"]],
                                result=None,
                                response=resultJson.get("response", ""),
                            )
                        else:
                            result = ActionResponse(
                                action=Action.REQLLM, result=result, response=""
                            )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"MCP工具调用失败: {e}")
                        result = ActionResponse(
                            action=Action.REQLLM, result="MCP工具调用失败", response=""
                        )
                else:
                    # 处理系统函数
                    result = self.func_handler.handle_llm_function_call(
                        self, function_call_data
                    )
                self._handle_function_result(result, function_call_data)

        # 存储对话内容
        if len(response_message) > 0:
            self.dialogue.put(
                Message(role="assistant", content="".join(response_message))
            )
        if text_index > 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
        self.llm_finish_task = True
        self.logger.bind(tag=TAG).debug(
            json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False)
        )

        return True

