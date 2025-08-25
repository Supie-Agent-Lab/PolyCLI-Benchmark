# Merged Pain Points from Block 8 - Backend WebSocket Server Development

## Critical Issues - System Stability & Core Functionality

### Issue: Working Mode Lost Audio After First Interaction
When entering working mode, the device could only process one voice interaction before becoming unresponsive to further voice commands.

**Solution:**
Upon receiving `{"type":"mode","state":"start","mode":"working"}`, immediately send `{"type":"listen","state":"start","mode":"manual"}` and set `client_listen_mode=manual` with `_last_listen_event_ms` refresh to ensure continuous voice interaction capability. Added in `backend/core/handle/textHandle.py`.

---

### Issue: BlockingIOError from Excessive Logging
Long JSON logs from coding insights were causing `BlockingIOError` and blocking the application.

**Solution:**
1. Output only statistical summary lines instead of full JSON: `[Coding Insight] final=.. insights=.. risks=.. actions=.. nextSteps=.. jsonSHA=.. elapsedMs=..`
2. Enable `patcher=_build_trunc_patcher()` for console and file sinks with `log.max_message_length` (default 2000) truncation
3. Implemented truncation patcher:
```python
def _build_trunc_patcher():
    def patcher(record):
        max_len = config.get("log.max_message_length", 2000)
        if len(record["message"]) > max_len:
            # 头尾保留+中间省略
            record["message"] = record["message"][:max_len//2] + "..." + record["message"][-max_len//2:]
    return patcher
```
4. Keep `enqueue=True`, `rotation=10MB`, `retention=30 days` for async handling

---

### Issue: Event Loop Binding During Construction
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

### Issue: Delayed Snapshot Task Creation Error
`asyncio.create_task((asyncio.sleep(...),))` was incorrectly passing tuple instead of coroutine.

**Solution:**
Changed to proper `_delayed_snapshot()` coroutine:
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

## High Priority - Performance & Resource Management

### Issue: LLM Instance Duplication Across Connections
Multiple connections were creating duplicate LLM instances, wasting memory and causing initialization delays.

**Solution:**
Implemented shared LLM registry in `WebSocketServer` with fingerprint-based caching:
```python
def get_or_create_llm(self, alias: str, overrides: dict | None = None):
    """按别名与可选覆盖创建/复用共享 LLM 实例。"""
    key = f"{alias}::{json.dumps(overrides, sort_keys=True)}"
    if key in self.llm_registry:
        return self.llm_registry[key]
    # ... create and cache instance
```
`ConnectionHandler.get_llm_for(purpose)` now delegates to server's shared factory, ensuring single instance per configuration.

---

### Issue: Meeting Finalize Race Conditions
Concurrent finalize requests were causing duplicate summary generation and processing errors.

**Solution:**
Added connection-level mutex lock and idempotent flag:
```python
# 在 meeting_handle.py
async with conn.meeting_finalize_lock:
    if getattr(conn, "meeting_finalized", False):
        # 复发上次 summary 并带 idempotent:true
        return
    conn.meeting_finalized = True
    # ... perform finalization once
```
All send/broadcast paths wrapped with connection close exception handling.

---

### Issue: Resource Cleanup Incomplete
Connection close wasn't properly canceling async tasks and cleaning up resources, leading to memory leaks.

**Solution:**
Enhanced `ConnectionHandler.close()` to:
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
    # 清理 LLM 缓存
    if hasattr(self, "_llm_cache") and isinstance(self._llm_cache, dict):
        self._llm_cache.clear()
    # 关闭 asr/tts/llm 资源
    for resource in [self.asr, self.tts, self.llm]:
        if resource and hasattr(resource, "close"):
            resource.close()
```

---

### Issue: SQLite Offline Queue Performance
JSON file-based offline queue couldn't handle 50 QPS concurrent operations.

**Solution:**
Implemented SQLite storage with:
- Table: `offline_queue(device_id TEXT, payload TEXT, queued_at INTEGER, ttl_ms INTEGER)`
- Indexes for fast lookup
- Fallback to JSON on SQLite failure
- 100 message per-device limit with TTL expiration

---

### Issue: Thread Pool Size Excessive
Default thread pool with too many workers causing context switching overhead.

**Solution:**
Reduced default `ThreadPoolExecutor` workers to 2, configurable via `meeting.threadpool_max_workers`. This reduced memory usage and context switching while maintaining performance.

---

## Medium Priority - User Experience & Reliability

### Issue: Delayed ASR Final Text on Listen Stop
When `listen.stop` was received, ASR would take too long to produce final transcription, causing text loss.

**Solution:**
On `listen.stop`, call `conn.asr.on_client_listen_stop(conn)` to send "last frame" marker:
```python
# In textHandle.py
if msg_json["state"] == "stop":
    # 通知流式ASR"本段结束"，促使尽快产出最终结果
    if getattr(conn, "asr", None) is not None and hasattr(conn.asr, "on_client_listen_stop"):
        maybe = conn.asr.on_client_listen_stop(conn)
        if asyncio.iscoroutine(maybe):
            await maybe
```
Implementation in `backend/core/providers/asr/doubao_stream.py` sends `generate_last_audio_default_header()` + empty payload.

---

### Issue: Workflow Snapshot Jitter on Mode Start
When starting working mode, multiple workflow snapshots were being sent in rapid succession, causing UI flickering.

**Solution:**
Added 1.5s debounce for `workflow.update` snapshots:
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

### Issue: Working Mode Direct Commands Not Working
Voice commands like "refresh tasks" or "complete task" required full LLM processing in working mode.

**Solution:**
Added direct command parsing in working mode for:
```python
if getattr(conn, "current_mode", None) == "working":
    assign_kw = ["认领任务", "领取任务", "我来做", "assign to me"]
    complete_kw = ["完成任务", "标记完成", "做完了", "mark done"]
    refresh_kw = ["刷新列表", "刷新任务", "拉取任务", "refresh"]
    # ... parse intent and execute directly
    if intent == "assign":
        await handle_workflow_message(conn, {"type": "workflow", "event": "assign", "id": target_id})
        return
```
These bypass LLM and directly execute workflow operations.

---

### Issue: Meeting LLM Token Limits Causing Truncation
Long meeting transcripts were being truncated mid-summary due to token limits.

**Solution:**
1. Reduced default `max_tokens`: 800 for summary, 400 for checkpoint
2. Set `summary_transcript_max_chars` to 4000 (tail-priority truncation)
3. Added LLM logging with `raw len`, `json len`, `sha8` for truncation diagnosis
4. Added progress events (`prepare/llm_start/llm_done/done`) with timing metrics

---

### Issue: Meeting Transcript Real-time Visibility
Meeting transcriptions weren't visible in real-time, only appearing in final summary.

**Solution:**
After each `handle_voice_stop()` STT result, immediately broadcast:
```json
{"type":"audio","event":"transcription","text":"...","ts":...,"session_id":"..."}
```
while preserving existing `meeting.snippet` injection for compatibility.

---

### Issue: Connection Timeout Without Warning
Connections would close after idle timeout without giving users a chance to keep the connection alive.

**Solution:**
- Send `timeout_warning` message 10 seconds before closing
- Allow any message received during buffer period to cancel closure via `reset_timeout()`
- Extended default idle threshold to 600s + 60s buffer

---

### Issue: Mode Switch Idempotency Missing
Repeated `mode.start(X)` messages were triggering duplicate initialization logic.

**Solution:**
Check if already in requested mode; if so, return `status:"ok"` immediately:
```python
if state == "start":
    # 幂等：若已处于该模式则直接回执并跳过重复初始化
    if getattr(conn, "current_mode", None) == mode:
        await conn.websocket.send(json.dumps({"type":"mode","status":"ok"}))
        return
    conn.current_mode = mode
```

---

### Issue: Coding Insight Debounce Too High
Static 1200ms debounce was causing noticeable delays in insight generation.

**Solution:**
1. Clamp debounce minimum to ≥300ms
2. Pass smaller `max_tokens=512` to LLM for faster responses
3. Keep immediate trigger for error/step/phase events

---

## Code Quality & Maintenance Issues

### Issue: Inconsistent Message Sending Methods
Mixed use of `websocket.send_json()`, `websocket.send()`, and string serialization causing errors and duplication.

**Solution:**
Added unified `ConnectionHandler.send_json()/send_text()` methods:
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

### Issue: Device ID Parsing Fragility
Device ID extraction from websocket handshake was scattered and brittle across different websockets library versions.

**Solution:**
Created unified `parse_ids_from_handshake(path_or_conn)` function that:
1. Tries multiple attribute names (`path`, `request_uri`, `raw_path`, etc.)
2. Normalizes IDs (strip quotes, lowercase, handle empty)
3. Maintains `_handshake_cache` by connection object ID for fallback
4. Returns tuple `(device_id, client_id, raw_path)`

---

### Issue: Giant handleTextMessage Function
`handleTextMessage` exceeded 500 lines with multiple nested responsibilities, making it hard to maintain.

**Solution:**
Proposed routing table refactor:
```python
HANDLERS = {
    "hello": handle_hello,
    "abort": handle_abort,
    "listen": handle_listen,
    "mode": handle_mode,
    # ... etc
}
```
Each handler maintains single responsibility with <100 lines per function.

---

### Issue: Duplicate Heartbeat Processing
Heartbeat (`ping`/`keepalive`) messages were being processed in multiple places causing redundancy.

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

## Validation & Error Handling Improvements

### Issue: Peer Category Validation Too Strict
Messages with category field having different case or trailing whitespace were being rejected.

**Solution:**
Apply `strip().lower()` normalization to `category` field before validation to handle case variations and whitespace.

---

### Issue: Schema Validation Error Messages Unhelpful
Schema validation failures didn't indicate which fields were missing or invalid.

**Solution:**
Enhanced error messages to include specific missing fields:
- `missing: title,duration` for missing required fields
- `items must be array of {tag,text}: missing one of tag/text` for array validation
This allows frontend to make minimal corrections.

---

### Issue: VAD Silence Duration Calculation Error
VAD silence duration was being calculated incorrectly, showing wrong idle times.

**Solution:**
Fixed calculation to use `now_ms - silence_start_ms` consistently across VAD implementations. This provides accurate silence duration for timeout decisions.

---

### Issue: Coding Prompt Returning Raw Logs
LLM was echoing back raw log content instead of generating insights.

**Solution:**
Rewrote system prompt to strictly enforce:
- Output only JSON, no code fences or explanatory text
- Fixed four keys: `{insights, risks, actions, nextSteps}`
- Language consistency and deduplication
- Explicit prohibition of raw log/stack echoing
Still preserve bracket extraction + `json.loads` + key fallback for parsing resilience.

---

## Additional Enhancements

### Issue: Workflow Owner Missing Friendly Names
Task assignments showed raw device IDs instead of readable names.

**Solution:**
Added `_resolve_device_alias_from_config()` to map device IDs to friendly aliases from `workflow.device_alias` or top-level `device_alias` config. Default to `alias|device-id` format when not explicitly provided.

---

### Issue: OAuth2/JWT Authentication Missing
System lacked proper authentication mechanisms beyond static tokens.

**Solution:**
Implemented comprehensive auth in `backend/core/auth.py`:
- JWT validation with configurable algorithms, audience, issuer
- OAuth2 introspection support
- Mixed mode allowing multiple auth methods
- Device whitelist fallback (lowercase normalized)
- Preserved static token compatibility

---

### Issue: Offline Message Delivery Statistics Not Tracked
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

---

### Issue: Configuration Hot Reload Not Clearing LLM Cache
After configuration updates, connections would still use old LLM instances from cache.

**Solution:**
Clear LLM cache on all connections during config update:
```python
for handler in list(self.active_connections):
    if hasattr(handler, "_llm_cache") and isinstance(handler._llm_cache, dict):
        handler._llm_cache.clear()
```

---

### Issue: ASR State Machine Using Patches
Device listen start/stop and server VAD fallback were mixed with conditional branches and temporary states like `just_woken_up`.

**Solution:**
Proposed finite state machine with states: `Idle -> Listening -> Finalizing -> Idle`
- Device events only change state and update `_last_listen_event_ms`
- VAD provides fallback only when no device boundary received within timeout
- Removed scattered `have_voice` special cases and patches