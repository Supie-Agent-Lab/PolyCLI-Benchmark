# Pain Points from Block 3 - Backend WebSocket Implementation

## Issue: LLM Configuration Causing AI Relay Failures
The LLM configuration was incorrectly set up, causing 404 errors and JSON parsing failures in the AI relay feature.

**Error Messages:**
- `Invalid URL (POST /v1/models/chat/completions)` 
- `LLM_OUTPUT_NOT_JSON`

**Root Cause:**
The `LLM.gptLLM` was using `url:` field pointing to `/v1/models`, but the adapter expected `base_url: https://api.openai.com/v1`.

**Solution:**
Fixed configuration in `backend/data/.config.yaml`:
```yaml
LLM:
  gptLLM:
    type: openai
    model_name: gpt-4.1-nano
    base_url: https://api.openai.com/v1
    api_key: <your_key>
```

---

## Issue: Complete WebSocket Connection Failure
The entire WebSocket and OTA chain was unreachable - OTA page showed infinite loading, browser WS test pages couldn't connect, hardware couldn't connect, and server had minimal log output.

**Root Causes (by impact):**

1. **WebSocket upgrade callback API misuse**
   - Used incorrect callback signature with `websockets.serve(process_request=...)`
   - Mistakenly treated `request_headers` as object with `.headers` attribute
   - Called non-existent `websocket.respond()` method

2. **Connection object attribute confusion (aiohttp vs websockets)**
   - Used `ws.request.headers / ws.request.path` to read request info
   - Should have used `request_headers / path` for websockets library

3. **OTA returning inconsistent WS path**
   - OTA returned `/xiaozhi/v1/` while test pages/docs/backend used `/supie/v1/`

4. **Hard dependency on ffmpeg blocking startup**
   - Missing ffmpeg threw exception terminating the process
   - Service never started listening

5. **Configuration inconsistencies and device ID conflicts**
   - Port mismatches (8000/8004)
   - IP binding issues (`127.0.0.1` vs `0.0.0.0`)

**Solution:**
Multiple fixes were applied:
- Fixed WebSocket upgrade callback to use proper library signature: upgrade requests return `None`, HTTP returns `(status, headers, body)`
- Aligned connection object reading to websockets library: use `request_headers / path`
- Unified OTA WS path to `/supie/v1/`
- Degraded ffmpeg from hard requirement to warning
- Standardized configuration: `server.ip=0.0.0.0`, `server.port=8004`, `server.http_port=8003`

---

## Issue: Connection Immediately Closing After Success
Browser connections would succeed then immediately close with code 1000, backend reported "unable to get request path" multiple times.

**Root Cause:**
websockets v14.2 passes `path` as second parameter to handler callback, but old implementation only read from `ws.path`, which was empty in some environments, causing failure to parse `device-id` and premature closure.

**Solution:**
Made path handling compatible:
- `WebSocketServer._handle_connection(self, websocket, path)` receives and passes down `path`
- `ConnectionHandler.handle_connection(ws, path)` prioritizes parameter `path`, falls back to `ws.path`
- Auto-assigns `auto-<8-digit>` device-id if no path available (with warning)

Added startup validation:
- Explicit `wait_started()` method
- Port pre-detection with socket pre-binding check (SO_REUSEADDR)
- Immediate ERROR and exit on port occupied/permission denied

---

## Issue: Meeting Mode Memory Unbounded Growth
Meeting segments were accumulated in memory without cleanup, potentially causing unbounded memory growth during long meetings.

**Solution:**
- Clear meeting cache after finalize with `finalize_meeting_and_send_summary(conn)`
- Limit meeting summary bullets to maximum 6 items with deduplication
- Added cleanup in `mode.end(meeting)` trigger

---

## Issue: JSON Extraction from LLM Output Unreliable
LLM responses for meeting summaries sometimes returned non-JSON or malformed JSON, breaking the summary generation.

**Solution:**
Implemented fallback JSON extraction strategy:
- Direct parsing attempt first
- Bracket extraction fallback (find content between `{` and `}`)
- Graceful degradation to empty bullets list if all extraction fails
- Summary skeleton remains valid even with empty bullets

---

## Issue: Device ID Spoofing and Duplicate Connections
Multiple connections could use the same device ID, potentially causing routing confusion and security issues.

**Solution:**
- Added duplicate device ID detection in `backend/core/websocket_server.py`
- Reject new connections with duplicate IDs
- Connection immediately closes upon rejection to prevent spoofing

---

## Issue: Workflow Concurrent Write Conflicts
Multiple devices updating tasks concurrently could cause data corruption in the task store.

**Solution:**
- All file I/O operations wrapped in locks in `backend/core/utils/tasks_store.py`
- Basic schema validation during load phase
- Thread-safe add/update/complete operations

---

## Issue: Broadcast Without Rate Limiting
Broadcast messages had no frequency restrictions, potentially allowing abuse.

**Solution:**
- Added simple rate limiting for broadcast: minimum 5 seconds between broadcasts per device
- ACL interception before LLM processing
- Unauthorized targets included in `failed` receipt

---

## Issue: Incomplete Schema Validation
Schema validation was partial, allowing malformed messages to pass through and cause downstream errors.

**Solution:**
Extended validation in `backend/core/utils/schema.py`:
- Added complete enums for coding events: `start|stop|clear|phase|log|step`
- Added workflow events: `update|complete`
- Enforced required fields validation
- Return `SCHEMA_INVALID` error code for malformed messages

---

## Issue: Non-Atomic Mode State Switching
Mode transitions weren't atomic, potentially leaving system in inconsistent state during meeting mode switches.

**Solution:**
- Initialize meeting cache and timestamps atomically in `mode.start(meeting)`
- Unified finalize trigger in `mode.end(meeting)`
- Ensure all related fields initialized in `connection.py`

---

## Issue: CSP Restrictions in Browser Environment
Browser Content Security Policy could restrict WebSocket connections to external servers, breaking test pages.

**Solution:**
- Documented need to use local `file://` HTML or tools like Postman/WsCat
- Provided enhanced test pages that work with `file://` protocol