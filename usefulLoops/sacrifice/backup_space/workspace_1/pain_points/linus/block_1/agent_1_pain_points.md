# Pain Points from Linus Block 1 Conversation

## Issue: Incorrect async task creation with tuple
**File:** backend/core/websocket_server.py:460-463

The code incorrectly wrapped `asyncio.sleep()` in a tuple when creating an async task, causing the sleep to not actually execute:
```python
asyncio.create_task((asyncio.sleep(delay_ms/1000.0),))
asyncio.create_task(_send_snapshot())
```

**Solution:**
Create a single coroutine that handles both the delay and snapshot:
```python
async def _delayed_snapshot():
    await asyncio.sleep(delay_ms/1000.0)
    await _send_snapshot()

asyncio.create_task(_delayed_snapshot())
```

---

## Issue: Unsafe event loop acquisition in constructor
**File:** backend/core/connection.py:90-96

Using `asyncio.get_event_loop()` in the constructor is unreliable in modern asyncio as it may return wrong loop when no running loop exists:
```python
self.loop = asyncio.get_event_loop()
```

**Solution:**
Get the running loop in the actual async context:
```python
# In handle_connection() at start:
self.loop = asyncio.get_running_loop()
```

---

## Issue: Repeated send_json fallback boilerplate
**Files:** Multiple locations including backend/core/websocket_server.py:386-407

The code repeatedly tries `send_json` and falls back to string serialization throughout the codebase:
```python
try:
    await handler.websocket.send_json(env)
except AttributeError:
    await handler.websocket.send(json.dumps(env, ensure_ascii=False))
```

**Solution:**
Create unified Transport layer methods in ConnectionHandler:
```python
async def send_json(self, payload: dict) -> None:
    try:
        await self.websocket.send_json(payload)
    except AttributeError:
        await self.websocket.send(json.dumps(payload, ensure_ascii=False))

async def send_text(self, text: str) -> None:
    await self.websocket.send(text)
```

---

## Issue: Duplicate heartbeat handling
**Files:** backend/core/connection.py:576-590 and backend/core/handle/textHandle.py:501-508

Heartbeat (ping/keepalive) messages were being handled in two different places, creating redundancy.

**Solution:**
Keep heartbeat handling only in `_route_message`, remove duplicate logic from `handleTextMessage`.

---

## Issue: Monolithic routing function with deep nesting
**File:** backend/core/handle/textHandle.py:21-500+

The `handleTextMessage` function exceeded 500 lines with multiple responsibilities (heartbeat, mode switching, meetings, workflows, MCP, IoT, direct commands) and deep nesting levels.

**Solution:**
Refactor to routing table pattern:
```python
HANDLERS = {
    "hello": handle_hello,
    "abort": handle_abort,
    "listen": handle_listen,
    # ...
}

async def handleTextMessage(conn, message):
    msg_json = json.loads(message)
    msg_type = msg_json.get("type")
    
    handler = HANDLERS.get(msg_type)
    if handler:
        await handler(conn, msg_json)
```

---

## Issue: Complex ASR segmentation with patch-like conditions
**File:** backend/core/providers/asr/base.py:58-73

Voice segmentation logic mixed device boundaries and VAD fallback with multiple if/else patches and temporary states like `just_woken_up`:
```python
if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
    have_voice = audio_have_voice
else:
    # Multiple conditions and fallback logic
    if last_listen_ms <= 0 or (now_ms - last_listen_ms) > fallback_ms:
        have_voice = audio_have_voice
    else:
        have_voice = conn.client_have_voice
```

**Solution:**
Implement finite state machine:
- States: `Idle -> Listening -> Finalizing -> Idle`
- Device `listen` events only change state and timestamp
- VAD acts only as timeout fallback when no device boundary received
- Remove scattered `have_voice` special cases and patches

---

## Issue: Duplicate LLM instance creation logic
**Files:** WebSocketServer and ConnectionHandler

Both server and connection handler had separate logic for merging overrides and creating LLM instances, causing potential cache inconsistencies.

**Solution:**
Delegate all LLM creation to server's shared factory:
```python
# In ConnectionHandler.get_llm_for:
return self.server.get_or_create_llm(alias, overrides)
# Fall back to self.llm only on cache miss
```

---

## Issue: Scattered WebSocket version compatibility handling
**Files:** WebSocketServer._http_response and ConnectionHandler.handle_connection

Device/client ID parsing logic was scattered with reflection-based attribute access for different websockets versions.

**Solution:**
Extract to single function with unit tests:
```python
def parse_ids_from_handshake(ws, path) -> tuple[str, str, str]:
    # Unified error handling, normalization (remove quotes, lowercase)
    # Single place for version compatibility
    # Maintain handshake cache
    return device_id, client_id, raw_path
```

---

## Issue: Missing error handling standardization
Throughout the codebase, send operations had inconsistent try/except patterns - some swallowing exceptions, others printing full stack traces.

**Solution:**
Unified error handling in Transport layer:
- Classify errors (warn/error levels)
- Silent/reduce noise for expected network exceptions
- Never throw exceptions that would terminate entire connection
- Single point of error logging and metrics

---

## Issue: Working mode TTS suppression default behavior
The system had default TTS suppression in working mode (`working.disable_tts`), which needed to be preserved to maintain backward compatibility.

**Solution:**
Maintained the existing default behavior while documenting it clearly as part of the "Never break userspace" principle. The behavior was already correctly implemented in `sendAudioHandle` and aligned with device-side logic.