# Pain Points Analysis - Linus Block 1

## Issue: Incorrect async task creation with tuple wrapping
In the test mode snapshot feature, asyncio.create_task was incorrectly called with a tuple containing the coroutine, causing the sleep to not actually execute.

**Location:** backend/core/websocket_server.py:460-463

**Original Code:**
```python
asyncio.create_task((asyncio.sleep(delay_ms/1000.0),))
asyncio.create_task(_send_snapshot())
```

**Solution:**
Create a wrapper coroutine that properly handles the delay:
```python
async def _delayed_snapshot():
    await asyncio.sleep(delay_ms/1000.0)
    await _send_snapshot()

asyncio.create_task(_delayed_snapshot())
```

---

## Issue: Event loop retrieval timing problem
Using `asyncio.get_event_loop()` in constructor is unreliable in modern asyncio, as it may get wrong loop when no event loop is running.

**Location:** backend/core/connection.py:90-96

**Original Code:**
```python
self.loop = asyncio.get_event_loop()
```

**Solution:**
Get the running loop within the async context:
```python
# In handle_connection() at start:
self.loop = asyncio.get_running_loop()
```

---

## Issue: Duplicate send_json fallback handling across codebase
Repetitive try/except blocks for websocket.send_json with string fallback scattered throughout the code, causing maintenance burden and potential inconsistencies.

**Location:** Multiple files, example at backend/core/websocket_server.py:386-407

**Pattern Found:**
```python
try:
    await handler.websocket.send_json(env)
except AttributeError:
    await handler.websocket.send(json.dumps(env, ensure_ascii=False))
```

**Solution:**
Create unified Transport layer in ConnectionHandler:
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

## Issue: Duplicate heartbeat handling in multiple locations
Ping/keepalive messages being processed in both _route_message and handleTextMessage, causing redundancy.

**Location:** 
- backend/core/connection.py:576-590 (_route_message)
- backend/core/handle/textHandle.py:501-508 (duplicate handling)

**Solution:**
Keep heartbeat handling only in _route_message, remove from handleTextMessage to maintain single responsibility.

---

## Issue: Massive monolithic routing function
handleTextMessage exceeds 500 lines with deep nesting, handling too many responsibilities (heartbeat, mode switching, meetings, workflows, MCP, IoT, direct commands).

**Location:** backend/core/handle/textHandle.py:21-28+

**Solution:**
Refactor using routing table pattern:
```python
HANDLERS = {
    "hello": handle_hello,
    "abort": handle_abort,
    "listen": handle_listen,
    "mode": handle_mode,
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

## Issue: Complex ASR segmentation with scattered if/else patches
Voice segmentation logic mixed between device boundaries and VAD fallback, with temporary patches like "just_woken_up" scattered across multiple conditionals.

**Location:** backend/core/providers/asr/base.py:58-73

**Original Pattern:**
```python
if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
    have_voice = audio_have_voice
else:
    # Multiple nested conditions for fallback logic
    if last_listen_ms <= 0 or (now_ms - last_listen_ms) > fallback_ms:
        have_voice = audio_have_voice
    else:
        have_voice = conn.client_have_voice
```

**Solution:**
Implement finite state machine for listen states:
- States: Idle → Listening → Finalizing → Idle
- Device listen events only change state and timestamp
- VAD acts as timeout fallback only
- Remove scattered have_voice special cases

---

## Issue: Handshake parsing logic scattered across multiple locations
Device-id/client-id parsing duplicated in WebSocketServer._http_response and ConnectionHandler.handle_connection with fragile reflection-based attribute access for websockets version compatibility.

**Solution:**
Extract to single function:
```python
def parse_ids_from_handshake(ws, path) -> tuple[str, str, str]:
    # Unified parsing logic with version compatibility
    # Centralized error handling and fallback
    # Maintain _handshake_cache
    return (device_id, client_id, raw_path)
```

---

## Issue: Duplicate LLM instance creation logic
Both WebSocketServer.get_or_create_llm and ConnectionHandler.get_llm_for have separate override merging and instance creation logic.

**Solution:**
ConnectionHandler.get_llm_for should always delegate to server's shared factory, passing alias+overrides fingerprint, only falling back to self.llm when no match found.

---

## Issue: Missing error standardization in message sending
Inconsistent error handling strategies across send operations - some swallow exceptions, others print full stack traces.

**Solution:**
Standardize in the Transport layer wrapper:
- Categorized error logging (warn/error levels)
- Silent/reduced noise for expected network exceptions
- Never throw exceptions that would terminate entire connection
- Centralized error statistics

---

## Issue: Auto device-id assignment buried in complex conditional
The fallback logic for missing device-id is functional but mixed with other parsing logic, making it hard to test and maintain.

**Location:** backend/core/connection.py:450-471

**Solution:**
Extract to dedicated function with proper unit test coverage while maintaining backwards compatibility (keeping the "never break userspace" principle).