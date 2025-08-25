```markdown
# Technical Knowledge Base

## 1. Critical AsyncIO and Event Loop Fixes

### Event Loop Acquisition Bug (P0)
**Location**: `backend/core/connection.py:90-96`, `backend/core/connection.py:714`
**Error**: Using `asyncio.get_event_loop()` in constructor fails in modern Python
**Solution**:
```python
# WRONG - in constructor
self.loop = asyncio.get_event_loop()

# CORRECT - in coroutine context  
async def handle_connection(self, ws, path):
    self.loop = asyncio.get_running_loop()
```

### Create Task Tuple Bug (P0)
**Location**: `backend/core/websocket_server.py:460-463`
**Error**: Wrapping coroutine in tuple prevents execution
**Solution**:
```python
# WRONG - coroutine never runs
asyncio.create_task((asyncio.sleep(delay_ms/1000.0),))

# CORRECT
async def _delayed_snapshot():
    await asyncio.sleep(delay_ms/1000.0)
    await _send_snapshot()
asyncio.create_task(_delayed_snapshot())
```

## 2. WebSocket Connection Management

### Connection Establishment Sequence
**Device ID Resolution Priority**:
1. URL Query parameters (`device-id`, `device_id`)
2. Headers (`device-id`, `device_id`, `x-device-id`)  
3. Auto-generation (`auto-{uuid[:8]}`)

**Normalization Process**:
```python
def _normalize_id(value):
    return value.strip().strip('"').strip("'").lower()
```

### Duplicate Connection Handling
**Location**: `backend/core/websocket_server.py:register_device_handler`
**Strategy**: Dual-channel transition with 1.5s delay
```python
# Send warning to old connection
await existed.send_json({
    "type": "system",
    "message": "检测到新连接，当前通道将于约1.5秒后关闭"
})
# Delayed close
await asyncio.sleep(1.5)
await old_handler.close()
```

### WebSocket Upgrade Callback Fix
**Problem**: "连不上、一直转圈" (can't connect, endless loading)
**Location**: `backend/core/websocket_server.py::_http_response`
**Solution**:
```python
def _http_response(self, path, request_headers):
    # WebSocket upgrade - MUST return None
    if "upgrade" in connection_header and upgrade_header == "websocket":
        return None
    # HTTP response - return tuple
    return 200, headers, body
```

## 3. Performance Optimizations

### Thread Pool Optimization
- **Original**: 5 threads per connection
- **Optimized**: 2 threads (60% memory reduction)
- **Configuration**: `meeting.threadpool_max_workers: 2`

### Unified Message Sending
**Location**: `backend/core/connection.py`
```python
async def send_json(self, payload: dict) -> None:
    try:
        await self.websocket.send_json(payload)
    except AttributeError:
        await self.websocket.send(json.dumps(payload, ensure_ascii=False))
```

### Logger Optimization (Prevents BlockingIOError)
```python
logger.add(
    sys.stdout,
    enqueue=True,  # Async queue prevents blocking
    backtrace=False,
    diagnose=False,
    max_message_length=2000
)
```

## 4. Meeting Mode Architecture

### Critical Configuration
```yaml
meeting:
  disable_tts: true
  disable_chat_on_snippet: true
  transcript_push_interval_ms: 5000
  prefer_device_vad: true
  min_duration_ms: 5000
  threadpool_max_workers: 2
```

### Meeting Finalization Sequence
1. **Immediate ACK**: Send confirmation with sessionId
2. **Stop timers**: Cancel all meeting tasks
3. **Generate summary**: Call LLM with idempotency
4. **Atomic storage**: Use temp file + os.replace

### ASR Reset Bug
**Problem**: Second meeting fails - ASR connection not reset
**Fix**: Explicitly call `conn.asr.stop_ws_connection()` on meeting end

## 5. LLM Model Selection by Context

### Configuration Pattern
```yaml
LLM:
  ChatGLM_Flashx:
    type: openai
    base_url: https://open.bigmodel.cn/api/paas/v4/
    model_name: glm-4-flashx-250414
  ChatGLM_45:
    type: openai
    base_url: https://open.bigmodel.cn/api/paas/v4/
    model_name: glm-4.5

llm_by_mode:
  default: ChatGLM_Flashx
  chat: ChatGLM_Flashx
  meeting: ChatGLM_45
  coding: ChatGLM_45
  intent: ChatGLM_Flashx
```

### LLM Instance Management
```python
def get_llm_for(self, purpose: str):
    if purpose in self._llm_cache:
        return self._llm_cache[purpose]
    
    alias = self.config.get("llm_by_mode", {}).get(purpose, "default")
    instance = self.server.get_or_create_llm(alias, overrides)
    self._llm_cache[purpose] = instance
    return instance
```

## 6. VAD (Voice Activity Detection) Fixes

### AttributeError Fix
**Location**: `backend/core/providers/vad/silero.py`
**Error**: `'ConnectionHandler' object has no attribute '_vad_detection_count'`
**Solution**:
```python
# Independent initialization
if not hasattr(conn, "_vad_detection_count"):
    conn._vad_detection_count = 0
```

### Device-side VAD Priority
```python
# Device boundaries take priority
if conn.client_listen_mode == "manual":
    # Use device listen start/stop events
    # Fallback to server VAD after 5000ms timeout
```

## 7. Workflow Task Management

### Group-based Isolation
```python
# Group key = first 8 chars of device ID
group_key = device_id[:8]

# Tasks isolated by group
def upsert_fields(group_key, task_id, partial):
    existing = self.tasks.get(task_id, {})
    existing.update(partial)
    existing["groupKey"] = group_key
```

### Idempotent Operations
```python
# Assign idempotency
if task.get("owner") == current_device:
    return {"status": "ok", "idempotent": True}

# Complete idempotency  
if task.get("status") == "done":
    return {"status": "ok", "idempotent": True}
```

## 8. Peer Messaging System

### ACL Implementation
```yaml
peer:
  enabled: true
  allow_all: false
  allow_broadcast: false
  allowlist: ["device-001", "device-002"]
  max_targets: 10
  rate_limit: 5  # per second
```

### Offline Queue
- JSON file: `backend/data/offline_peer_queue.json`
- Max 100 messages per device
- TTL: 3 days
- Auto-delivery on reconnection

## 9. Critical Bug Fixes and Solutions

### Port Binding Pre-check
```python
# Early detection of port conflicts
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
except OSError as e:
    self.logger.error(f"Port {port} already in use")
    raise
```

### Atomic File Operations
```python
def _safe_write_json(filepath, data):
    temp_path = f"{filepath}.tmp.{os.getpid()}"
    with open(temp_path, 'w') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(temp_path, filepath)  # Atomic
```

### Keepalive Configuration
```python
websockets.serve(
    handler,
    host="0.0.0.0",
    port=8004,
    ping_interval=20,
    ping_timeout=50,
    close_timeout=5
)
```

## 10. Meeting Storage and Sharding

- Index file: `backend/data/meetings/index.json` (last 100 meetings)
- Sharding: Auto-split at 100 segments
- Shard files: `meetings/segments/{sid}_shard_K.json`
- Webhook delivery with HMAC-SHA256 signature

## 11. Error Patterns and Resolutions

### WebSocket Library Compatibility
- Different versions use different attributes
- Path resolution: Try `path`, `request_uri`, `raw_request_uri`, `request_path`
- Headers access: Use `items()` for compatibility

### Configuration Hot-reload
```python
# Clear LLM cache on config update
for handler in self.active_connections:
    if hasattr(handler, "_llm_cache"):
        handler._llm_cache.clear()
```

### Timeout Management
- Base idle time: 600s
- Meeting/working mode: 3x multiplier
- Warning before close: 10-15s grace period

## 12. Working Mode Implementation

### Voice Command Recognition
```python
# Direct commands in working mode
assign_keywords = ["认领任务", "assign to me"]
complete_keywords = ["完成任务", "mark done"]
refresh_keywords = ["刷新列表", "refresh"]

# Auto-execute without TTS feedback
if intent == "assign":
    await handle_workflow_message(conn, {
        "type": "workflow",
        "event": "assign",
        "id": target_id
    })
```

### Mode Switching
```python
# Enter working mode and start listening
if mode == "working":
    await conn.send_json({
        "type": "listen",
        "state": "start",
        "mode": "manual"
    })
```

## 13. Coding Mode Insights

### Log Processing
```python
# Normalize and truncate logs
def _normalize_incoming_text(text):
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'```.*?```', '', text)
    return text[:512]

# Buffer for LLM insight generation
coding_logs_buffer = []  # Max 200 lines
```

### Insight Generation
- Debounce: 1200ms
- Error triggers immediate insight
- Fields: insights, risks, actions, nextSteps
- Max items per field: 5-6
```