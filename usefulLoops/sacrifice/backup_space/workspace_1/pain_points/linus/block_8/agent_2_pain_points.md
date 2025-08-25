# Pain Points from Block 8 - Backend WebSocket Server Development

## Issue: Websocket Message Send Method Inconsistency
The code had scattered `websocket.send()` and `websocket.send_json()` calls with different error handling patterns, causing compatibility issues across different websocket library versions.

**Solution:**
Added unified `send_json()` and `send_text()` methods to ConnectionHandler that automatically handle the send_json availability and fallback to string serialization:
```python
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
```

---

## Issue: Device ID Parsing Fragmented Across Multiple Files
Device ID and client ID parsing logic was duplicated between WebSocketServer._http_response and ConnectionHandler.handle_connection with complex reflection-based attribute access for different websocket versions.

**Solution:**
Created centralized `parse_ids_from_handshake()` helper function that unifies parsing logic and handles various websocket library attribute names:
```python
def parse_ids_from_handshake(path_or_conn) -> tuple[str | None, str | None, str | None]:
    """Parse device-id and client-id from a path string or connection-like object.
    Returns: (device_id, client_id, raw_path)
    """
    raw_path = _extract_raw_path(path_or_conn)
    # ... unified parsing logic
```

---

## Issue: Event Loop Binding During Construction
The code was using `get_event_loop()` in constructor which could fail or return wrong loop when no running loop exists.

**Solution:**
Bind event loop at connection start using `get_running_loop()`:
```python
async def handle_connection(self, ws, path=None):
    try:
        # 绑定当前运行事件循环供跨线程调度使用
        self.loop = asyncio.get_running_loop()
```

---

## Issue: Delayed Snapshot Task Creation Error
Incorrect asyncio task creation with tuple instead of coroutine caused delayed snapshots to fail:
```python
# Wrong:
asyncio.create_task((asyncio.sleep(...),))
```

**Solution:**
Created proper async function for delayed snapshot:
```python
async def _delayed_snapshot():
    try:
        await asyncio.sleep(delay_ms/1000.0)
        await _send_snapshot()
    except Exception:
        pass
asyncio.create_task(_delayed_snapshot())
```

---

## Issue: LLM Instance Management Complexity
Multiple places creating LLM instances with duplicate configuration merging logic, causing memory waste and configuration inconsistencies.

**Solution:**
Implemented shared LLM registry with fingerprint-based caching:
```python
def get_or_create_llm(self, alias: str, overrides: dict | None = None):
    """按别名与可选覆盖创建/复用共享 LLM 实例。"""
    key = f"{alias}::{json.dumps(overrides, sort_keys=True)}"
    if key in self.llm_registry:
        return self.llm_registry[key]
    # ... create and cache instance
```

---

## Issue: Meeting Mode Finalize Race Conditions
Multiple finalize requests could cause duplicate summary generation and timer conflicts.

**Solution:**
Added mutex lock and idempotent flag for meeting finalization:
```python
# 在 meeting_handle.py
async with conn.meeting_finalize_lock:
    if getattr(conn, "meeting_finalized", False):
        # 复发上次 summary 并带 idempotent:true
        return
    conn.meeting_finalized = True
    # ... perform finalization once
```

---

## Issue: ASR Stream Not Closing Properly on Listen Stop
When device sends `listen.stop`, the streaming ASR wouldn't finalize the current segment quickly, causing delayed or lost transcriptions.

**Solution:**
Added notification mechanism to ASR on listen stop:
```python
# In textHandle.py
if msg_json["state"] == "stop":
    # 通知流式ASR"本段结束"，促使尽快产出最终结果
    if getattr(conn, "asr", None) is not None and hasattr(conn.asr, "on_client_listen_stop"):
        maybe = conn.asr.on_client_listen_stop(conn)
        if asyncio.iscoroutine(maybe):
            await maybe
```

---

## Issue: Working Mode Only Works Once
After entering working mode, subsequent voice commands wouldn't be processed because listen mode wasn't properly maintained.

**Solution:**
Explicitly start listening when entering working mode and refresh listen event timestamp:
```python
elif mode == "working":
    # 进入工作模式后显式开启拾音（manual）
    conn.client_listen_mode = "manual"
    conn._last_listen_event_ms = int(time.time() * 1000)
    await conn.websocket.send(json.dumps({
        "type": "listen",
        "state": "start",
        "mode": "manual",
    }))
```

---

## Issue: Workflow Snapshot Timing Conflicts
Multiple triggers (register, hello, mode_start) could send workflow snapshots in quick succession causing UI flicker.

**Solution:**
Added 1.5s debounce between snapshots from different sources:
```python
if state == "start" and mode == "working":
    # 去抖：避免与注册/hello触发的快照在极短时间内重复
    now_ms = int(time.time() * 1000)
    last_ms = int(getattr(conn, "_last_workflow_snapshot_ms", 0) or 0)
    if now_ms - last_ms >= 1500:
        # ... send snapshot
        conn._last_workflow_snapshot_ms = now_ms
```

---

## Issue: Coding Insight Flooding Logs with Large JSON
LLM responses for coding insights were being logged in full, causing log flooding and potential BlockingIOError.

**Solution:**
Log only statistics instead of full JSON:
```python
# 统计日志行：仅输出统计，不直写完整 JSON
self.logger.info(f"[Coding Insight] final=.. insights={len(insights)} risks={len(risks)} jsonSHA={sha} elapsedMs={elapsed}")
```

---

## Issue: Long Log Messages Causing BlockingIOError
Extremely long log messages could block the logging system and cause I/O errors.

**Solution:**
Added truncation patcher to loguru:
```python
def _build_trunc_patcher():
    def patcher(record):
        max_len = config.get("log.max_message_length", 2000)
        if len(record["message"]) > max_len:
            # 头尾保留+中间省略
            record["message"] = record["message"][:max_len//2] + "..." + record["message"][-max_len//2:]
    return patcher
```

---

## Issue: Resource Cleanup Incomplete
Connection close wasn't properly canceling async tasks and cleaning up resources, leading to memory leaks.

**Solution:**
Enhanced close() method with comprehensive cleanup:
```python
async def close(self, ws=None):
    # 取消超时任务
    if self.timeout_task:
        self.timeout_task.cancel()
    # 取消编码洞察定时任务
    if hasattr(self, "coding_insight_task") and self.coding_insight_task:
        self.coding_insight_task.cancel()
    # 关闭线程池
    if self.executor:
        self.executor.shutdown(wait=False, cancel_futures=True)
```

---

## Issue: Mode Switch Duplication
Receiving the same `mode.start` message multiple times would reinitialize everything causing redundant operations.

**Solution:**
Added idempotent check for mode switching:
```python
if state == "start":
    # 幂等：若已处于该模式则直接回执并跳过重复初始化
    if getattr(conn, "current_mode", None) == mode:
        await conn.websocket.send(json.dumps({"type":"mode","status":"ok"}))
        return
    conn.current_mode = mode
```

---

## Issue: Heartbeat Processing Duplication
Ping/keepalive messages were being handled in multiple places causing duplicate processing.

**Solution:**
Centralized heartbeat handling in `_route_message`:
```python
# In _route_message
if isinstance(obj, dict) and obj.get("type") in ("ping", "keepalive"):
    await self.websocket.send(json.dumps({"type": "pong"}))
    return
# Removed duplicate handling from handleTextMessage
```

---

## Issue: Meeting Summary Token Limits Causing Truncation
Long meeting transcripts would get truncated in LLM responses due to excessive token usage.

**Solution:**
Reduced default max_tokens and added transcript trimming:
```python
# 默认 max_tokens 下调
max_tokens = 800  # summary
checkpoint_max_tokens = 400  # checkpoint
summary_transcript_max_chars = 4000  # 裁剪输入
```

---

## Issue: Peer Message Category Validation Too Strict
Messages with uppercase category or trailing whitespace would fail validation unnecessarily.

**Solution:**
Normalize category before validation:
```python
# In peerHandle.py
category = (msg_json.get("category", "") or "").strip().lower()
# Now validation is case-insensitive
```

---

## Issue: Complex Giant Router in handleTextMessage
The handleTextMessage function was over 500 lines with deeply nested if/else branches for different message types, making it hard to maintain and extend.

**Solution:**
While the complete refactoring to route table wasn't shown in the edits, the issue was identified and planned for modularization with a handler registry pattern:
```python
HANDLERS = {
    "hello": handle_hello,
    "abort": handle_abort,
    "listen": handle_listen,
    # ... etc
}
```

---

## Issue: Working Mode Direct Commands Not Working
Voice commands in working mode (refresh/assign/complete) weren't being processed correctly.

**Solution:**
Added direct command parsing in working mode before regular chat processing:
```python
if getattr(conn, "current_mode", None) == "working":
    assign_kw = ["认领任务", "领取任务", "我来做"]
    complete_kw = ["完成任务", "标记完成", "做完了"]
    refresh_kw = ["刷新列表", "刷新任务", "拉取任务"]
    # ... parse intent and execute directly
    if intent == "assign":
        await handle_workflow_message(conn, {"type": "workflow", "event": "assign", "id": target_id})
        return
```

---

## Issue: Configuration Hot Reload Not Clearing LLM Cache
After configuration updates, connections would still use old LLM instances from cache.

**Solution:**
Clear LLM cache on all connections during config update:
```python
for handler in list(self.active_connections):
    if hasattr(handler, "_llm_cache") and isinstance(handler._llm_cache, dict):
        handler._llm_cache.clear()
```

---

## Issue: Offline Message Delivery Statistics Not Tracked
When delivering offline messages, the original senders weren't notified about successful redelivery.

**Solution:**
Added sender aggregation and redelivery notifications:
```python
# 聚合发起方统计
sender_counts = defaultdict(int)
for env in pending:
    origin = env.get("from")
    if origin:
        sender_counts[origin] += 1
# 给各发起方回执补投统计
for origin_id, cnt in sender_counts.items():
    origin_handler = self.device_handlers.get(origin_id)
    if origin_handler:
        await origin_handler.send_json({
            "type": "peer",
            "event": "redelivered",
            "to": device_id,
            "count": cnt
        })
```