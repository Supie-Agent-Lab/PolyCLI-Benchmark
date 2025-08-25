
**Cursor**

我要开始实现 P0 的四项修改：修复延时快照的异步调度、在连接协程内绑定事件循环、增加统一发送封装并替换主要调用点、移除重复心跳处理。接下来我会编辑相关文件。

我要执行一组并行编辑：修复 WS 延时快照调度、为连接增加统一发送封装并替换主要调用点、在连接协程内绑定事件循环、移除重复的心跳处理分支。随后我会更新 log-w.md，新增“编辑84 by w”的记录。

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
            # 诊断：记录升级请求的原始 path（含 query）与关键头部
            try:
                # websockets 不同版本下，这里的第一个参数可能是 str（带 query 的 path），也可能是连接对象
                raw_path_str = None
                conn_obj = None
                if isinstance(path, str):
                    raw_path_str = path
                else:
                    conn_obj = path
                    # 猜测属性链提取原始 path
                    for attr in ("path", "request_uri", "raw_request_uri", "request_path", "raw_path"):
                        try:
                            val = getattr(conn_obj, attr, None)
                            if isinstance(val, str) and val:
                                raw_path_str = val
                                break
                        except Exception:
                            continue
                    # 深一层：可能存在 request 对象
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

                self.logger.bind(tag=TAG).info(
                    f"HTTP upgrade request path={raw_path_str if raw_path_str is not None else path}"
                )

                # 将解析到的 device-id/client-id 暂存，供后续 handler 兜底读取
                try:
                    if raw_path_str and conn_obj is not None:
                        parsed = urlparse(raw_path_str)
                        qs = parse_qs(parsed.query or "")
                        device_vals = qs.get("device-id") or qs.get("device_id")
                        client_vals = qs.get("client-id") or qs.get("client_id")
                        if device_vals:
                            device_id = (device_vals[0] or "").strip().strip('"').strip("'").lower()
                            client_id = (client_vals[0] if client_vals else device_id)
                            client_id = (client_id or "").strip().strip('"').strip("'").lower()
                            self._handshake_cache[id(conn_obj)] = {
                                "raw_path": raw_path_str,
                                "device-id": device_id,
                                "client-id": client_id,
                            }
                except Exception:
                    pass
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

    async def register_device_handler(self, device_id: str, handler: ConnectionHandler) -> bool:
        """注册设备与连接处理器的映射；若已存在同名设备，则断开旧连接并接受新连接。

        Returns:
            bool: True 注册成功；False 注册失败。
        """
        try:
            async with self.device_handlers_lock:
                existed = self.device_handlers.get(device_id)
                if existed is not None and existed is not handler:
                    self.logger.bind(tag=TAG).warning(
                        f"检测到重复连接，启用双通道过渡(≤2s)并接受新连接: device={device_id}"
                    )
                    # 双通道过渡：先提示旧连接，延迟 ~1.5s 再关闭，降低听写中断概率
                    try:
                        if existed.websocket:
                            try:
                                await existed.websocket.send(json.dumps({
                                    "type": "system",
                                    "message": "检测到新连接，当前通道将于约1.5秒后关闭以切换到新通道"
                                }, ensure_ascii=False))
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
                        # 即使计划失败，也继续注册新连接
                self.device_handlers[device_id] = handler
            self.logger.bind(tag=TAG).info(f"注册设备路由: {device_id}")
            # 注册后广播一次在线快照
            await self.broadcast_server_stats()
            # 上线补投递：尝试取出离线队列并逐条发送
            try:
                pending, dropped = pop_offline_for_device(device_id)
                if pending:
                    # 统计按发起方聚合的补投条数
                    try:
                        from collections import defaultdict
                        sender_counts = defaultdict(int)
                    except Exception:
                        sender_counts = {}
                    sent = 0
                    for env in pending:
                        try:
                            if handler and handler.websocket:
                                await handler.websocket.send_json(env)
                            else:
                                import json
                                await handler.websocket.send(json.dumps(env, ensure_ascii=False))
                            sent += 1
                            # 聚合发起方统计
                            try:
                                origin = env.get("from")
                                if isinstance(origin, str) and len(origin) > 0:
                                    key = origin.strip().lower()
                                    if isinstance(sender_counts, dict):
                                        sender_counts[key] = sender_counts.get(key, 0) + 1
                                    else:
                                        sender_counts[key] += 1
                            except Exception:
                                pass
                        except AttributeError:
                            import json
                            await handler.websocket.send(json.dumps(env, ensure_ascii=False))
                            sent += 1
                        except Exception:
                            continue
                    self.logger.bind(tag=TAG).info(
                        f"离线补投递: device={device_id}, sent={sent}, dropped={dropped}"
                    )
                    # 给各发起方回执补投统计
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
                                            await origin_handler.websocket.send_json(payload)
                                        except AttributeError:
                                            import json
                                            await origin_handler.websocket.send(json.dumps(payload, ensure_ascii=False))
                                except Exception:
                                    continue
                    except Exception:
                        pass
            except Exception:
                pass
            # 上线即单播一次工作流快照（按分组），可通过开关/延迟避免测试噪声
            try:
                try:
                    group_key = str(device_id)[:8]
                except Exception:
                    group_key = "default"
                tasks = get_task_store().list_by_group(group_key)
                if tasks is not None:
                    # 读取测试模式与延迟配置
                    try:
                        wf_cfg = (self.config.get("workflow", {}) or {}) if isinstance(self.config, dict) else {}
                        test_mode = bool(wf_cfg.get("test_mode", False))
                        delay_ms = int(wf_cfg.get("snapshot_on_register_delay_ms", 0))
                    except Exception:
                        test_mode = False; delay_ms = 0
                    async def _send_snapshot():
                        envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                        try:
                            await handler.websocket.send_json(envelope)
                        except AttributeError:
                            import json
                            await handler.websocket.send(json.dumps(envelope, ensure_ascii=False))
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
                    if handler and handler.websocket:
                        await handler.websocket.send_json(payload)  # 优先使用 send_json
                except AttributeError:
                    # 兼容 websockets，使用字符串发送
                    import json

                    await handler.websocket.send(json.dumps(payload, ensure_ascii=False))
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

```

```python
*** Begin Patch
*** Update File: /Users/tlovo/code_ai/Badge-ai/backend/core/connection.py
@@
-        # 线程任务相关
-        self.loop = asyncio.get_event_loop()
+        # 线程任务相关（在 handle_connection 内绑定运行中的事件循环）
+        self.loop = None
         self.stop_event = threading.Event()
@@
     async def handle_connection(self, ws, path=None):
         try:
+            # 绑定当前运行事件循环供跨线程调度使用
+            try:
+                self.loop = asyncio.get_running_loop()
+            except Exception:
+                self.loop = asyncio.get_event_loop()
@@
             self.logger.bind(tag=TAG).info(
                 f"{self.client_ip} conn - Headers: {self.headers}"
             )
@@
             self.welcome_msg = self.config["xiaozhi"]
             self.welcome_msg["session_id"] = self.session_id
-            await self.websocket.send(json.dumps(self.welcome_msg))
+            await self.send_json(self.welcome_msg)
@@
             self.timeout_task = asyncio.create_task(self._check_timeout())
*** End Patch
```

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

        # 模式状态（meeting/coding/working）
        self.current_mode = None
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

        # 构造/复用实例（合并覆盖）：优先使用 server 级共享注册表
        try:
            from core.utils import llm as llm_utils
            base_conf = None
            if alias:
                base_conf = copy.deepcopy(self.config.get("LLM", {}).get(alias))
                # 若连接级配置未包含该别名，尝试从服务器级配置读取（支持热更）
                if not base_conf:
                    try:
                        srv = getattr(self, "server", None)
                        srv_cfg = getattr(srv, "config", None) if srv else None
                        if isinstance(srv_cfg, dict):
                            base_conf = copy.deepcopy(srv_cfg.get("LLM", {}).get(alias))
                    except Exception:
                        pass
            if not base_conf:
                # 回退：无对应配置则复用默认，并给出一次告警
                try:
                    self.logger.bind(tag=TAG).warning(
                        f"get_llm_for: llm_by_mode[{key}] 别名未命中(alias={alias}), 回退默认LLM"
                    )
                except Exception:
                    pass
                self._llm_cache[key] = self.llm
                return self.llm
            # 若 server 提供共享注册表，优先复用
            try:
                srv = getattr(self, "server", None)
                if srv and hasattr(srv, "get_or_create_llm") and callable(getattr(srv, "get_or_create_llm")):
                    instance = srv.get_or_create_llm(alias, overrides)
                else:
                    # 直接合并覆盖并创建独立实例
                    if overrides and isinstance(overrides, dict):
                        for k, v in overrides.items():
                            base_conf[k] = v
                    llm_type = base_conf.get("type", alias)
                    instance = llm_utils.create_instance(llm_type, base_conf)
            except Exception:
                if overrides and isinstance(overrides, dict):
                    for k, v in overrides.items():
                        base_conf[k] = v
                llm_type = base_conf.get("type", alias)
                instance = llm_utils.create_instance(llm_type, base_conf)
            self._llm_cache[key] = instance
            return instance
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

            # 优先从 URL 查询参数解析 device-id/client-id；其次尝试 Header；最后回退
            from urllib.parse import parse_qs, urlparse

            def _normalize_id(value: str | None) -> str | None:
                if value is None:
                    return None
                try:
                    v = str(value).strip().strip('"').strip("'")
                    if v == "":
                        return None
                    return v.lower()
                except Exception:
                    return None

            device_id_from_query = None
            client_id_from_query = None
            try:
                candidate_paths = []
                if isinstance(path, str) and len(path) > 0:
                    candidate_paths.append(path)
                ws_path = getattr(ws, "path", "")
                if isinstance(ws_path, str) and len(ws_path) > 0 and ws_path not in candidate_paths:
                    candidate_paths.append(ws_path)
                # 兼容不同版本 websockets 的属性命名，尽量获取带 query 的原始 URI
                for attr in ["request_uri", "raw_request_uri", "request_path", "raw_path"]:
                    try:
                        val = getattr(ws, attr, "")
                        if isinstance(val, str) and len(val) > 0 and val not in candidate_paths:
                            candidate_paths.append(val)
                    except Exception:
                        pass
                # 从候选 path 中解析 query 参数
                for p in candidate_paths:
                    try:
                        parsed_url = urlparse(p)
                        raw_query = parsed_url.query or ""
                        if not raw_query:
                            # 兼容某些环境仅传递了 "?a=b" 作为 path 的情况
                            if "?" in p and p.endswith("?") is False:
                                raw_query = p.split("?", 1)[1]
                        if not raw_query:
                            continue
                        query_params = parse_qs(raw_query, keep_blank_values=False)
                        device_vals = query_params.get("device-id") or query_params.get("device_id")
                        client_vals = query_params.get("client-id") or query_params.get("client_id")
                        if device_vals and len(device_vals) > 0:
                            device_id_from_query = _normalize_id(device_vals[0])
                            # client-id 缺省时复用 device-id
                            client_id_from_query = _normalize_id(client_vals[0]) if client_vals else device_id_from_query
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            # 兜底：从 server 的握手缓存读取（适配 websockets 传参差异）
            try:
                server_obj = getattr(self, "server", None)
                if (device_id_from_query is None) and server_obj is not None:
                    cache = getattr(server_obj, "_handshake_cache", None)
                    if isinstance(cache, dict):
                        # 按连接对象 id 存储
                        cached = cache.get(id(ws))
                        if isinstance(cached, dict):
                            did = cached.get("device-id")
                            cid = cached.get("client-id") or did
                            device_id_from_query = _normalize_id(did)
                            client_id_from_query = _normalize_id(cid)
            except Exception:
                pass

            # 从 Header 兜底解析（包含非规范写法）
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

    def _handle_mcp_tool_call(self, function_call_data):
        function_arguments = function_call_data["arguments"]
        function_name = function_call_data["name"]
        try:
            args_dict = function_arguments
            if isinstance(function_arguments, str):
                try:
                    args_dict = json.loads(function_arguments)
                except json.JSONDecodeError:
                    self.logger.bind(tag=TAG).error(
                        f"无法解析 function_arguments: {function_arguments}"
                    )
                    return ActionResponse(
                        action=Action.REQLLM, result="参数解析失败", response=""
                    )

            tool_result = asyncio.run_coroutine_threadsafe(
                self.mcp_manager.execute_tool(function_name, args_dict), self.loop
            ).result()
            # meta=None content=[TextContent(type='text', text='北京当前天气:\n温度: 21°C\n天气: 晴\n湿度: 6%\n风向: 西北 风\n风力等级: 5级', annotations=None)] isError=False
            content_text = ""
            if tool_result is not None and tool_result.content is not None:
                for content in tool_result.content:
                    content_type = content.type
                    if content_type == "text":
                        content_text = content.text
                    elif content_type == "image":
                        pass

            if len(content_text) > 0:
                return ActionResponse(
                    action=Action.REQLLM, result=content_text, response=""
                )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
            return ActionResponse(
                action=Action.REQLLM, result="工具调用出错", response=""
            )

        return ActionResponse(action=Action.REQLLM, result="工具调用出错", response="")

    def _handle_function_result(self, result, function_call_data):
        if result.action == Action.RESPONSE:  # 直接回复前端
            text = result.response
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                "id": function_id,
                                "function": {
                                    "arguments": function_arguments,
                                    "name": function_name,
                                },
                                "type": "function",
                                "index": 0,
                            }
                        ],
                    )
                )

                self.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=(
                            str(uuid.uuid4()) if function_id is None else function_id
                        ),
                        content=text,
                    )
                )
                self.chat(text, tool_call=True)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.result
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _report_worker(self):
        """聊天记录上报工作线程"""
        while not self.stop_event.is_set():
            try:
                # 从队列获取数据，设置超时以便定期检查停止事件
                item = self.report_queue.get(timeout=1)
                if item is None:  # 检测毒丸对象
                    break
                type, text, audio_data, report_time = item
                try:
                    # 检查线程池状态
                    if self.executor is None:
                        continue
                    # 提交任务到线程池
                    self.executor.submit(
                        self._process_report, type, text, audio_data, report_time
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"聊天记录上报线程异常: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"聊天记录上报工作线程异常: {e}")

        self.logger.bind(tag=TAG).info("聊天记录上报线程已退出")

    def _process_report(self, type, text, audio_data, report_time):
        """处理上报任务"""
        try:
            # 执行上报（传入二进制数据）
            report(self, type, text, audio_data, report_time)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"上报处理异常: {e}")
        finally:
            # 标记任务完成
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.logger.bind(tag=TAG).debug(f"清除服务端讲话状态")

    async def close(self, ws=None):
        """资源清理方法"""
        try:
            # 取消超时任务
            if self.timeout_task:
                self.timeout_task.cancel()
                self.timeout_task = None

            # 取消编码洞察定时任务
            try:
                if hasattr(self, "coding_insight_task") and self.coding_insight_task and not self.coding_insight_task.done():
                    self.coding_insight_task.cancel()
            except Exception:
                pass

            # 清理MCP资源
            if hasattr(self, "mcp_manager") and self.mcp_manager:
                await self.mcp_manager.cleanup_all()

            # 触发停止事件
            if self.stop_event:
                self.stop_event.set()

            # 清空任务队列
            self.clear_queues()

            # 关闭WebSocket连接
            if ws:
                await ws.close()
            elif self.websocket:
                await self.websocket.close()

            # 最后关闭线程池（避免阻塞）
            if self.executor:
                try:
                    # Python 3.9+ 支持 cancel_futures
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    self.executor.shutdown(wait=False)
                self.executor = None

            # 清理 LLM 实例缓存
            try:
                if hasattr(self, "_llm_cache") and isinstance(self._llm_cache, dict):
                    self._llm_cache.clear()
            except Exception:
                pass

            # 关闭 asr/tts/llm 资源
            try:
                if hasattr(self, "asr") and hasattr(self.asr, "close") and callable(getattr(self.asr, "close")):
                    maybe_close = self.asr.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "tts") and hasattr(self.tts, "close") and callable(getattr(self.tts, "close")):
                    maybe_close = self.tts.close()
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass
            try:
                if hasattr(self, "llm") and hasattr(self.llm, "close") and callable(getattr(self.llm, "close")):
                    maybe_close = self.llm.close()  # 供应商可选实现
                    if asyncio.iscoroutine(maybe_close):
                        await maybe_close
            except Exception:
                pass

            self.logger.bind(tag=TAG).info("连接资源已释放")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"关闭连接时出错: {e}")

    def clear_queues(self):
        """清空所有任务队列"""
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"开始清理: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

            # 使用非阻塞方式清空队列
            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            self.logger.bind(tag=TAG).debug(
                f"清理结束: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_vad_states(self):
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0
        self.client_voice_stop = False
        self.logger.bind(tag=TAG).debug("VAD states reset.")

    async def send_text(self, text: str) -> None:
        """统一文本发送包装。"""
        try:
            if self.websocket:
                await self.websocket.send(text)
        except Exception:
            pass

    async def send_json(self, payload: dict) -> None:
        """统一 JSON 发送包装，自动兼容 send_json 缺失并回退字符串。"""
        try:
            if self.websocket is None:
                return
            try:
                await self.websocket.send_json(payload)
            except AttributeError:
                import json as _json
                await self.websocket.send(_json.dumps(payload, ensure_ascii=False))
        except Exception:
            # 发送错误不应中断主流程
            pass

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Use the existing chat method
            self.chat(text)

            # After chat is complete, close the connection
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """检查连接超时"""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(self.timeout_seconds)
                if not self.stop_event.is_set():
                    # 在关闭前先发送提示并提供缓冲期（与无声层策略一致）
                    try:
                        await self.websocket.send(json.dumps({
                            "type": "system",
                            "event": "timeout_warning",
                            "message": "连接将因长时间空闲而关闭，如需继续请发送任意消息。"
                        }))
                    except Exception:
                        pass
                    # 给予 10 秒缓冲，若期间收到任何消息，reset_timeout 会取消下一轮关闭
                    try:
                        await asyncio.sleep(10)
                    except Exception:
                        pass
                    if self.stop_event.is_set():
                        break
                    self.logger.bind(tag=TAG).info("连接超时，准备关闭")
                    await self.close(self.websocket)
                    break
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"超时检查任务出错: {e}")

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
            # 诊断：记录升级请求的原始 path（含 query）与关键头部
            try:
                # websockets 不同版本下，这里的第一个参数可能是 str（带 query 的 path），也可能是连接对象
                raw_path_str = None
                conn_obj = None
                if isinstance(path, str):
                    raw_path_str = path
                else:
                    conn_obj = path
                    # 猜测属性链提取原始 path
                    for attr in ("path", "request_uri", "raw_request_uri", "request_path", "raw_path"):
                        try:
                            val = getattr(conn_obj, attr, None)
                            if isinstance(val, str) and val:
                                raw_path_str = val
                                break
                        except Exception:
                            continue
                    # 深一层：可能存在 request 对象
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

                self.logger.bind(tag=TAG).info(
                    f"HTTP upgrade request path={raw_path_str if raw_path_str is not None else path}"
                )

                # 将解析到的 device-id/client-id 暂存，供后续 handler 兜底读取
                try:
                    if raw_path_str and conn_obj is not None:
                        parsed = urlparse(raw_path_str)
                        qs = parse_qs(parsed.query or "")
                        device_vals = qs.get("device-id") or qs.get("device_id")
                        client_vals = qs.get("client-id") or qs.get("client_id")
                        if device_vals:
                            device_id = (device_vals[0] or "").strip().strip('"').strip("'").lower()
                            client_id = (client_vals[0] if client_vals else device_id)
                            client_id = (client_id or "").strip().strip('"').strip("'").lower()
                            self._handshake_cache[id(conn_obj)] = {
                                "raw_path": raw_path_str,
                                "device-id": device_id,
                                "client-id": client_id,
                            }
                except Exception:
                    pass
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

    async def register_device_handler(self, device_id: str, handler: ConnectionHandler) -> bool:
        """注册设备与连接处理器的映射；若已存在同名设备，则断开旧连接并接受新连接。

        Returns:
            bool: True 注册成功；False 注册失败。
        """
        try:
            async with self.device_handlers_lock:
                existed = self.device_handlers.get(device_id)
                if existed is not None and existed is not handler:
                    self.logger.bind(tag=TAG).warning(
                        f"检测到重复连接，启用双通道过渡(≤2s)并接受新连接: device={device_id}"
                    )
                    # 双通道过渡：先提示旧连接，延迟 ~1.5s 再关闭，降低听写中断概率
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
                        # 即使计划失败，也继续注册新连接
                self.device_handlers[device_id] = handler
            self.logger.bind(tag=TAG).info(f"注册设备路由: {device_id}")
            # 注册后广播一次在线快照
            await self.broadcast_server_stats()
            # 上线补投递：尝试取出离线队列并逐条发送
            try:
                pending, dropped = pop_offline_for_device(device_id)
                if pending:
                    # 统计按发起方聚合的补投条数
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
                            # 聚合发起方统计
                            try:
                                origin = env.get("from")
                                if isinstance(origin, str) and len(origin) > 0:
                                    key = origin.strip().lower()
                                    if isinstance(sender_counts, dict):
                                        sender_counts[key] = sender_counts.get(key, 0) + 1
                                    else:
                                        sender_counts[key] += 1
                            except Exception:
                                pass
                        except AttributeError:
                            import json
                            await handler.send_json(env)
                            sent += 1
                        except Exception:
                            continue
                    self.logger.bind(tag=TAG).info(
                        f"离线补投递: device={device_id}, sent={sent}, dropped={dropped}"
                    )
                    # 给各发起方回执补投统计
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
            # 上线即单播一次工作流快照（按分组），可通过开关/延迟避免测试噪声
            try:
                try:
                    group_key = str(device_id)[:8]
                except Exception:
                    group_key = "default"
                tasks = get_task_store().list_by_group(group_key)
                if tasks is not None:
                    # 读取测试模式与延迟配置
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

```

```python
import json
from core.handle.abortHandle import handleAbortMessage
from core.handle.helloHandle import handleHelloMessage
from core.handle.mcpHandle import handle_mcp_message
from core.handle.peerHandle import handle_peer_message
from core.handle.meeting_handle import handle_meeting_message
from core.handle.coding_handle import handle_coding_message
from core.handle.workflow_handle import handle_workflow_message
from core.utils.util import remove_punctuation_and_length, filter_sensitive_info
from core.handle.receiveAudioHandle import startToChat, handleAudioMessage
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.iotHandle import handleIotDescriptors, handleIotStatus
from core.handle.reportHandle import enqueue_asr_report
import asyncio
import time
from core.handle.meeting_handle import finalize_meeting_and_send_summary

TAG = __name__


async def handleTextMessage(conn, message):
    """处理文本消息"""
    try:
        msg_json = json.loads(message)
        if isinstance(msg_json, int):
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message if isinstance(message, str) else str(message)
            conn.logger.bind(tag=TAG).info(f"收到文本消息：{safe_msg}")
            await conn.websocket.send(message)
            return
        if msg_json["type"] == "hello":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到hello消息：{safe_msg}")
            await handleHelloMessage(conn, msg_json)
        elif msg_json["type"] == "abort":
            conn.logger.bind(tag=TAG).info(f"收到abort消息：{message}")
            await handleAbortMessage(conn)
        elif msg_json["type"] == "listen":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到listen消息：{safe_msg}")
            if "mode" in msg_json:
                conn.client_listen_mode = msg_json["mode"]
                conn.logger.bind(tag=TAG).debug(
                    f"客户端拾音模式：{conn.client_listen_mode}"
                )
            if msg_json["state"] == "start":
                # 最小去抖：忽略距上次同类事件 <300ms 的重复 start
                try:
                    import time as _t
                    now_ms = int(_t.time() * 1000)
                    last_ms = int(getattr(conn, "_last_listen_start_ms", 0) or 0)
                    if now_ms - last_ms < 300:
                        return
                    conn._last_listen_start_ms = now_ms
                except Exception:
                    pass
                conn.client_have_voice = True
                conn.client_voice_stop = False
                # 记录设备侧边界最新时间，用于回退策略判断
                try:
                    import time as _t
                    conn._last_listen_event_ms = int(_t.time() * 1000)
                except Exception:
                    pass
            elif msg_json["state"] == "stop":
                # 最小去抖：忽略距上次同类事件 <300ms 的重复 stop
                try:
                    import time as _t
                    now_ms = int(_t.time() * 1000)
                    last_ms = int(getattr(conn, "_last_listen_stop_ms", 0) or 0)
                    if now_ms - last_ms < 300:
                        return
                    conn._last_listen_stop_ms = now_ms
                except Exception:
                    pass
                conn.client_have_voice = True
                conn.client_voice_stop = True
                try:
                    import time as _t
                    conn._last_listen_event_ms = int(_t.time() * 1000)
                except Exception:
                    pass
                # 新增：通知流式ASR“本段结束”，促使尽快产出最终结果
                try:
                    if getattr(conn, "asr", None) is not None and hasattr(conn.asr, "on_client_listen_stop"):
                        maybe = conn.asr.on_client_listen_stop(conn)
                        if asyncio.iscoroutine(maybe):
                            await maybe
                except Exception:
                    pass
                if len(conn.asr_audio) > 0:
                    await handleAudioMessage(conn, b"")
            elif msg_json["state"] == "detect":
                conn.client_have_voice = False
                conn.asr_audio.clear()
                if "text" in msg_json:
                    original_text = msg_json["text"]  # 保留原始文本
                    filtered_len, filtered_text = remove_punctuation_and_length(
                        original_text
                    )

                    # 模式切换（进入工作模式）意图识别与回显/播报抑制
                    try:
                        normalized = str(original_text or "").strip().lower()
                        mode_switch_keywords = [
                            "进入工作模式",
                            "工作模式",
                            "切到工作模式",
                            "切换到工作模式",
                            "workflow mode",
                            "working mode",
                            "switch to working mode",
                            "enter working mode",
                        ]
                        if any(k.lower() in normalized for k in mode_switch_keywords):
                            # 下发带意图标注的 STT（不触发 TTS），并仅发送模式确认
                            try:
                                await conn.websocket.send(
                                    json.dumps(
                                        {
                                            "type": "stt",
                                            "text": original_text,
                                            "intent": "mode_switch",
                                            "target_mode": "working",
                                            "session_id": getattr(conn, "session_id", ""),
                                        },
                                        ensure_ascii=False,
                                    )
                                )
                            except Exception:
                                pass
                            # 复用现有 mode 流程，设置工作模式并触发一次快照单播
                            try:
                                await handleTextMessage(
                                    conn,
                                    json.dumps(
                                        {
                                            "type": "mode",
                                            "state": "start",
                                            "mode": "working",
                                        },
                                        ensure_ascii=False,
                                    ),
                                )
                            except Exception:
                                pass
                            return
                    except Exception:
                        pass

                    # 识别是否是唤醒词
                    is_wakeup_words = filtered_text in conn.config.get("wakeup_words")
                    # 是否开启唤醒词回复
                    enable_greeting = conn.config.get("enable_greeting", True)

                    if is_wakeup_words and not enable_greeting:
                        # 如果是唤醒词，且关闭了唤醒词回复，就不用回答
                        await send_stt_message(conn, original_text)
                        await send_tts_message(conn, "stop", None)
                        conn.client_is_speaking = False
                    elif is_wakeup_words:
                        conn.just_woken_up = True
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                        enqueue_asr_report(conn, "嘿，你好呀", [])
                        await startToChat(conn, "嘿，你好呀")
                    else:
                        # 语音指令直达（工作模式）：assign/complete/refresh
                        try:
                            normalized = str(original_text or "").strip().lower()
                            # 仅在工作模式才进行直达解析
                            if getattr(conn, "current_mode", None) == "working":
                                assign_kw = ["认领任务", "领取任务", "我来做", "assign to me", "claim task"]
                                complete_kw = ["完成任务", "标记完成", "做完了", "mark done", "complete task"]
                                refresh_kw = ["刷新列表", "刷新任务", "拉取任务", "refresh", "pull", "update list"]
                                intent = None
                                if any(k.lower() in normalized for k in assign_kw):
                                    intent = "assign"
                                elif any(k.lower() in normalized for k in complete_kw):
                                    intent = "complete"
                                elif any(k.lower() in normalized for k in refresh_kw):
                                    intent = "refresh"
                                if intent is not None:
                                    # 可选：回包一个轻量意图（无 TTS 回显）
                                    try:
                                        await conn.websocket.send(json.dumps({
                                            "type": "workflow",
                                            "event": "command",
                                            "intent": intent,
                                        }, ensure_ascii=False))
                                    except Exception:
                                        pass
                                    # 具体执行
                                    from core.utils.tasks_store import get_task_store
                                    store = get_task_store()
                                    group_key = (getattr(conn, "device_id", "") or "")[:8]
                                    # 在没有任务时，避免空数组频发：拉取一次并返回
                                    if intent == "refresh":
                                        tasks = store.list_by_group(group_key)
                                        envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                                        try:
                                            await conn.websocket.send_json(envelope)
                                        except AttributeError:
                                            await conn.websocket.send(json.dumps(envelope, ensure_ascii=False))
                                        return
                                    # 认领/完成：取最近一个可操作任务（open，owner为空/非我）
                                    tasks = store.list_by_group(group_key) or []
                                    target_id = None
                                    if intent == "assign":
                                        for t in tasks:
                                            if t.get("status") == "open" and (not t.get("owner") or t.get("owner") != getattr(conn, "device_id", None)):
                                                target_id = t.get("id")
                                                break
                                        if target_id is None and tasks:
                                            target_id = tasks[0].get("id")
                                        if target_id:
                                            # 构造 assign 消息并复用 handler（含幂等返回）
                                            await handle_workflow_message(conn, {"type": "workflow", "event": "assign", "id": target_id})
                                            return
                                    elif intent == "complete":
                                        for t in tasks:
                                            if t.get("status") == "open":
                                                target_id = t.get("id")
                                                break
                                        if target_id:
                                            await handle_workflow_message(conn, {"type": "workflow", "event": "complete", "ids": [target_id]})
                                            return
                        except Exception:
                            pass
                        # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）；默认走常规对话
                        enqueue_asr_report(conn, original_text, [])
                        await startToChat(conn, original_text)
        elif msg_json["type"] == "iot":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到iot消息：{safe_msg}")
            if "descriptors" in msg_json:
                asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
            if "states" in msg_json:
                asyncio.create_task(handleIotStatus(conn, msg_json["states"]))
        elif msg_json["type"] == "mcp":
            try:
                from config.logger import truncate_for_log
                safe_msg = truncate_for_log(message)
            except Exception:
                safe_msg = message
            conn.logger.bind(tag=TAG).info(f"收到mcp消息：{safe_msg}")
            if "payload" in msg_json:
                asyncio.create_task(
                    handle_mcp_message(conn, conn.mcp_client, msg_json["payload"])
                )
        elif msg_json["type"] == "meeting":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到meeting消息：{safe_detail}")
            if msg_json.get("phase") == "finalize":
                # W1: 立即回执 + 立即停止定时器（双保险）并打印三段连续日志
                try:
                    conn.logger.bind(tag=TAG).info("finalize request")
                    ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
                    pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
                    await conn.websocket.send(
                        json.dumps({
                            "type": "meeting",
                            "phase": "finalize",
                            "sessionId": getattr(conn, "session_id", ""),
                            "startedAt": ack_started_at,
                            "pendingCount": pending_count,
                        }, ensure_ascii=False)
                    )
                    conn.logger.bind(tag=TAG).info("send ack")
                except Exception:
                    pass
                # 标记 finalize 中，停止会中定时任务与推送，避免“结束中仍在增加片段”
                try:
                    setattr(conn, "meeting_finalizing", True)
                except Exception:
                    pass
                try:
                    from core.handle.meeting_handle import stop_meeting_timers
                    stop_meeting_timers(conn)
                    conn.logger.bind(tag=TAG).info("stop timers done")
                except Exception:
                    conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
                # 关闭/重置 ASR 流式连接，避免下次会议复用陈旧状态
                try:
                    if getattr(conn, "asr", None) is not None:
                        if hasattr(conn.asr, "stop_ws_connection"):
                            conn.asr.stop_ws_connection()
                        # 如实现了异步 close，则后台触发
                        import inspect
                        if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                            asyncio.create_task(conn.asr.close())
                except Exception:
                    pass
                # 异步生成并下发最终纪要
                asyncio.create_task(finalize_meeting_and_send_summary(conn))
            else:
                asyncio.create_task(handle_meeting_message(conn, msg_json))
        elif msg_json["type"] == "coding":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到coding消息：{safe_detail}")
            asyncio.create_task(handle_coding_message(conn, msg_json))
        elif msg_json["type"] == "workflow":
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到workflow消息：{safe_detail}")
            asyncio.create_task(handle_workflow_message(conn, msg_json))
        elif msg_json["type"] == "config_update":
            # 兼容旧式 config_update：仅提示并忽略（避免“未知类型”噪声）
            try:
                cfg_keys = list((msg_json.get("config") or {}).keys())
                conn.logger.bind(tag=TAG).info(f"收到兼容 config_update（忽略实际更新）：keys={cfg_keys}")
            except Exception:
                conn.logger.bind(tag=TAG).info("收到兼容 config_update（忽略实际更新）")
            try:
                await conn.websocket.send(json.dumps({"type": "config_update", "status": "ok", "noop": True}))
            except Exception:
                pass
        elif msg_json["type"] == "mode":
            # 模式切换骨架：start/end + mode
            conn.logger.bind(tag=TAG).info(f"收到mode消息：{message}")
            try:
                state = msg_json.get("state")
                mode = msg_json.get("mode")
                if state in ["start", "end"] and mode in ["meeting", "coding", "working"]:
                    # 仅更新会话级状态（后续根据 mode 影响处理策略）
                    if state == "start":
                        # 幂等：若已处于该模式则直接回执并跳过重复初始化
                        if getattr(conn, "current_mode", None) == mode:
                            try:
                                await conn.websocket.send(json.dumps({"type":"mode","status":"ok","state":"start","mode":mode}))
                            except Exception:
                                pass
                            return
                        conn.current_mode = mode
                        if mode == "meeting":
                            conn.meeting_segments.clear()
                            conn.meeting_start_ts = time.time() * 1000
                            conn.meeting_last_snippet_ts = 0.0
                            conn.meeting_last_snippet_index = 0
                            # 播放进入会议提示音（后端下发TTS音频 or 控制端提示）
                            try:
                                await conn.websocket.send(
                                    json.dumps({
                                        "type": "tts",
                                        "state": "start",
                                        "url": "config/assets/evening.wav",
                                        "text": "已进入会议模式"
                                    }, ensure_ascii=False)
                                )
                                # 立即发送 stop 以最小化占用（客户端可按需播放本地资源）
                                await conn.websocket.send(
                                    json.dumps({
                                        "type": "tts",
                                        "state": "stop"
                                    }, ensure_ascii=False)
                                )
                            except Exception:
                                pass
                            # 会议模式优先设备侧VAD（可选）
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
                                conn.logger.bind(tag=TAG).info("会议模式已启用设备侧VAD优先（listen start/stop 括起语音段）")
                            # 尝试加载活跃会中状态，实现断线续传
                            try:
                                from core.handle.meeting_handle import load_active_state_if_any, start_meeting_checkpoint_timer, start_meeting_timers
                                await load_active_state_if_any(conn)
                                # 启动会议相关定时任务（transcript 聚合 + checkpoint）
                                start_meeting_timers(conn)
                                start_meeting_checkpoint_timer(conn)
                            except Exception:
                                pass
                        elif mode == "working":
                            # 任务1-1：进入工作模式后显式开启拾音（manual），确保设备处于可听状态
                            try:
                                # 更新连接侧拾音模式与最近边界时间
                                conn.client_listen_mode = "manual"
                                try:
                                    import time as _t
                                    conn._last_listen_event_ms = int(_t.time() * 1000)
                                except Exception:
                                    pass
                                await conn.websocket.send(
                                    json.dumps(
                                        {
                                            "type": "listen",
                                            "state": "start",
                                            "mode": "manual",
                                        },
                                        ensure_ascii=False,
                                    )
                                )
                            except Exception:
                                pass
                    else:
                        conn.current_mode = None
                        # 退出会议模式时恢复自动拾音
                        if mode == "meeting":
                            conn.client_listen_mode = "auto"
                        if mode == "meeting":
                            # 退出 meeting 等价 finalize：立即回执确认并停止推送（同样打印三段日志）
                            try:
                                conn.logger.bind(tag=TAG).info("finalize request")
                                ack_started_at = int(getattr(conn, "meeting_start_ts", 0) or 0)
                                pending_count = len(getattr(conn, "meeting_pending_texts", []) or [])
                                await conn.websocket.send(json.dumps({
                                    "type": "meeting",
                                    "phase": "finalize",
                                    "sessionId": getattr(conn, "session_id", ""),
                                    "startedAt": ack_started_at,
                                    "pendingCount": pending_count,
                                }, ensure_ascii=False))
                                conn.logger.bind(tag=TAG).info("send ack")
                            except Exception:
                                pass
                            try:
                                setattr(conn, "meeting_finalizing", True)
                            except Exception:
                                pass
                            try:
                                from core.handle.meeting_handle import stop_meeting_timers
                                stop_meeting_timers(conn)
                                conn.logger.bind(tag=TAG).info("stop timers done")
                            except Exception:
                                conn.logger.bind(tag=TAG).warning("stop timers encountered error (ignored)")
                            # 关闭/重置 ASR 流式连接，避免下次会议复用陈旧状态
                            try:
                                if getattr(conn, "asr", None) is not None:
                                    if hasattr(conn.asr, "stop_ws_connection"):
                                        conn.asr.stop_ws_connection()
                                    import inspect
                                    if hasattr(conn.asr, "close") and inspect.iscoroutinefunction(conn.asr.close):
                                        asyncio.create_task(conn.asr.close())
                            except Exception:
                                pass
                            asyncio.create_task(finalize_meeting_and_send_summary(conn))
                    # 任务1：进入工作模式时单播一次分组任务快照
                    try:
                        if state == "start" and mode == "working":
                            # 去抖：避免与注册/hello触发的快照在极短时间内重复
                            import time as _t
                            now_ms = int(_t.time() * 1000)
                            last_ms = int(getattr(conn, "_last_workflow_snapshot_ms", 0) or 0)
                            if now_ms - last_ms >= 1500:
                                group_key = (getattr(conn, "device_id", "") or "")[:8]
                                if group_key:
                                    from core.utils.tasks_store import get_task_store
                                    tasks = get_task_store().list_by_group(group_key)
                                    envelope = {"type": "workflow", "event": "update", "tasks": tasks}
                                    try:
                                        await conn.websocket.send_json(envelope)
                                    except AttributeError:
                                        await conn.websocket.send(json.dumps(envelope, ensure_ascii=False))
                                    conn._last_workflow_snapshot_ms = now_ms
                                    conn.logger.bind(tag=TAG).info(f"[Workflow] op=snapshot source=mode_start group={group_key} to={getattr(conn,'device_id','')} count={len(tasks)}")
                    except Exception:
                        pass
                else:
                    await conn.websocket.send(
                        json.dumps({
                            "type": "mode",
                            "status": "error",
                            "message": "invalid state or mode"
                        })
                    )
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"处理mode消息异常: {e}")
        
        elif msg_json["type"] == "peer":
            # 板间通信骨架：仅校验并入队，后续由AI中转路由处理
            conn.logger.bind(tag=TAG).info(f"收到peer消息：{filter_sensitive_info(msg_json)}")
            try:
                to_list = msg_json.get("to", [])
                payload = msg_json.get("payload", {})
                if not isinstance(to_list, list) or not isinstance(payload, dict):
                    await conn.websocket.send(
                        json.dumps({"type": "peer", "status": "error", "message": "invalid to/payload"})
                    )
                    return
                # 调用AI中转路由（串行以保证顺序；如需提升吞吐可放线程池）
                await handle_peer_message(conn, to_list, payload)
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"处理peer消息异常: {e}")
        elif msg_json["type"] == "server":
            # 记录日志时过滤敏感信息
            try:
                from config.logger import truncate_for_log
                safe_detail = truncate_for_log(json.dumps(filter_sensitive_info(msg_json), ensure_ascii=False))
            except Exception:
                safe_detail = str(filter_sensitive_info(msg_json))
            conn.logger.bind(tag=TAG).info(f"收到服务器消息：{safe_detail}")
            # 如果配置是从API读取的，则需要验证secret
            if not conn.read_config_from_api:
                return
            # 获取post请求的secret
            post_secret = msg_json.get("content", {}).get("secret", "")
            secret = conn.config["manager-api"].get("secret", "")
            # 如果secret不匹配，则返回
            if post_secret != secret:
                await conn.websocket.send(
                    json.dumps(
                        {
                            "type": "server",
                            "status": "error",
                            "message": "服务器密钥验证失败",
                        }
                    )
                )
                return
            # 动态更新配置
            if msg_json["action"] == "update_config":
                try:
                    # 更新WebSocketServer的配置
                    if not conn.server:
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "无法获取服务器实例",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    if not await conn.server.update_config():
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "更新服务器配置失败",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    # 发送成功响应
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "success",
                                "message": "配置更新成功",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"更新配置失败: {str(e)}")
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "error",
                                "message": f"更新配置失败: {str(e)}",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
            # 重启服务器
            elif msg_json["action"] == "restart":
                await conn.handle_restart(msg_json)
        else:
            conn.logger.bind(tag=TAG).error(f"收到未知类型消息：{message}")
    except json.JSONDecodeError:
        await conn.websocket.send(message)

```

我刚完成了 P0 的代码 edits：修复了延时快照的调度、在连接协程内绑定事件循环、增加并应用统一发送封装、移除了重复心跳处理。现在我会检查是否有语法/风格问题，并读取 `log-w.md` 的末尾看日志格式，然后按“编辑84 by w”追加一条记录。

```markdown
## 协同工作日志记录

## 后端log

8.11

