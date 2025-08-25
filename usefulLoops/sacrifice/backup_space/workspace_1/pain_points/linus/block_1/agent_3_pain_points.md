# Pain Points Analysis - Linus Block 1

## Issue: Incorrect async task creation with tuple
The code incorrectly passed a coroutine inside a tuple to `asyncio.create_task()`, which resulted in the sleep not actually being awaited. This was found in the test mode snapshot delay functionality.

**Location:** `backend/core/websocket_server.py:460-463`

**Original problematic code:**
```python
asyncio.create_task((asyncio.sleep(delay_ms/1000.0),))
asyncio.create_task(_send_snapshot())
```

**Solution:**
Create a unified coroutine that handles both the delay and snapshot sending:
```python
async def _delayed_snapshot(): 
    await asyncio.sleep(delay_ms/1000.0)
    await _send_snapshot()

asyncio.create_task(_delayed_snapshot())
```

---

## Issue: Event loop retrieval in constructor timing problem
Using `asyncio.get_event_loop()` in the constructor is unreliable in modern asyncio runtime model. When there's no running loop, it may retrieve an incorrect loop reference.

**Location:** `backend/core/connection.py:90-96`

**Original problematic code:**
```python
# In constructor
self.loop = asyncio.get_event_loop()
```

**Solution:**
Retrieve the event loop in the async context when it's actually running:
```python
# In handle_connection() at the beginning
self.loop = asyncio.get_running_loop()
```

---

## Issue: Duplicated send_json fallback pattern everywhere
The codebase has repetitive try/except blocks for `send_json` with fallback to `send(json.dumps(...))` scattered throughout. This creates maintenance burden and inconsistent error handling.

**Location:** Multiple locations including `backend/core/websocket_server.py:386-407`

**Original problematic pattern:**
```python
try:
    await handler.websocket.send_json(env)
except AttributeError:
    await handler.websocket.send(json.dumps(env, ensure_ascii=False))
```

**Solution:**
Create unified Transport layer methods in `ConnectionHandler`:
```python
async def send_json(self, payload: dict) -> None:
    try:
        await self.websocket.send_json(payload)
    except AttributeError:
        await self.websocket.send(json.dumps(payload, ensure_ascii=False))

async def send_text(self, text: str) -> None:
    await self.websocket.send(text)

async def send_envelope(self, type: str, **fields) -> None:
    await self.send_json({"type": type, **fields})
```

---

## Issue: Duplicate heartbeat handling in multiple locations
Heartbeat messages (ping/keepalive) were being processed in two different places, creating redundancy and potential for divergent behavior.

**Locations:** 
- `backend/core/connection.py:576-590` (_route_message)
- `backend/core/handle/textHandle.py:501-508` (handleTextMessage)

**Solution:**
Keep heartbeat handling only in `_route_message` and remove the duplicate logic from `handleTextMessage`. This ensures single-point processing of heartbeat messages.

---

## Issue: Monolithic router function with excessive responsibilities
The `handleTextMessage` function exceeded 500 lines and handled too many responsibilities (heartbeat, mode switching, meetings, workflows, MCP, IoT, direct commands, etc.), with deep nesting levels.

**Location:** `backend/core/handle/textHandle.py:21-528+`

**Solution:**
Refactor using a routing table pattern:
```python
HANDLERS = {
    "hello": handle_hello,
    "abort": handle_abort,
    "listen": handle_listen,
    "mode": handle_mode,
    "meeting": handle_meeting,
    # etc...
}

async def handleTextMessage(conn, message):
    msg_json = json.loads(message)
    msg_type = msg_json.get("type")
    
    handler = HANDLERS.get(msg_type)
    if handler:
        await handler(conn, msg_json)
    else:
        # handle unknown type
```

---

## Issue: Complex ASR segmentation with scattered if/else patches
Voice segmentation logic mixed device boundaries with VAD fallback in multiple if/else branches, including temporary patches like `just_woken_up`.

**Location:** `backend/core/providers/asr/base.py:58-73`

**Original problematic code:**
```python
if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
    have_voice = audio_have_voice
else:
    # Device boundary priority with server VAD fallback
    if last_listen_ms <= 0 or (now_ms - last_listen_ms) > fallback_ms:
        have_voice = audio_have_voice
    else:
        have_voice = conn.client_have_voice
```

**Solution:**
Implement a finite state machine for voice segmentation:
- States: `Idle -> Listening -> Finalizing -> Idle`
- Device `listen` events only change state and update timestamp
- VAD only acts as timeout fallback when device boundary not received within fallback_ms
- Remove scattered `have_voice` special cases and `just_woken_up` patches

---

## Issue: Handshake parsing scattered across multiple locations
Device ID and client ID parsing logic was duplicated in `WebSocketServer._http_response` and `ConnectionHandler.handle_connection`, with fragile reflection-based access to different websockets version attributes.

**Solution:**
Extract to a single function:
```python
def parse_ids_from_handshake(ws, path) -> tuple[str, str, str]:
    """
    Parse device_id, client_id, and raw_path from WebSocket handshake.
    Handles multiple websockets versions and maintains compatibility.
    Returns: (device_id, client_id, raw_path)
    """
    # Unified parsing logic with proper error handling
    # Maintains _handshake_cache for consistency
```

---

## Issue: Duplicate LLM instance creation logic
Both `WebSocketServer.get_or_create_llm` and `ConnectionHandler.get_llm_for` had separate logic for merging overrides and creating instances, leading to potential cache inconsistencies.

**Solution:**
Have `get_llm_for` always delegate to the server's shared factory:
- Pass `alias+overrides` fingerprint to server factory
- Only fallback to `self.llm` when no match found
- Remove local instantiation branches to avoid configuration hot-reload and cache inconsistencies

---

## Issue: Missing auto device-id assignment protection
When device-id couldn't be retrieved from headers/query/path, the system auto-assigns one for fault tolerance, but this logic needed better isolation and testing.

**Location:** `backend/core/connection.py:450-471`

**Solution:**
Keep the fault-tolerant auto-assignment (following "Never break userspace" principle) but:
- Extract to a dedicated function
- Add comprehensive unit test coverage
- Maintain diagnostic logging for troubleshooting