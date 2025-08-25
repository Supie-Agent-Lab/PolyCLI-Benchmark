# Pain Points Analysis - Linus Block 3

## Issue: WebSocket Connection Complete Failure - No Service Listening
OTA page kept spinning indefinitely, browser WS test pages couldn't connect, hardware couldn't connect, and server produced almost no new logs. The entire WebSocket/OTA chain was unreachable.

**Solution:**
Multiple critical issues were identified and fixed:
1. **WebSocket upgrade callback API misuse**: Fixed `websockets.serve(process_request=...)` callback signature to return `None` for upgrade requests and `(status, headers, body)` for HTTP requests. Removed calls to non-existent `websocket.respond()`.
2. **Connection object attribute confusion**: Changed from incorrect `ws.request.headers / ws.request.path` to correct `request_headers / path` for websockets library.
3. **Path inconsistency**: Unified OTA WebSocket path from `/xiaozhi/v1/` to `/supie/v1/` to match test pages and documentation.
4. **FFmpeg hard blocking**: Changed from throwing exception when ffmpeg not installed to warning only, preventing service startup failure.
5. **Port and IP configuration mismatches**: Standardized to `server.ip=0.0.0.0`, `server.port=8004`, `server.http_port=8003`.

---

## Issue: LLM Configuration Causing AI Relay Failures
Logs showed 404 errors (`Invalid URL (POST /v1/models/chat/completions)`) or `LLM_OUTPUT_NOT_JSON` when using AI relay functionality.

**Solution:**
Fixed LLM configuration in `backend/data/.config.yaml`:
```yaml
LLM:
  gptLLM:
    type: openai
    model_name: gpt-4.1-nano
    base_url: https://api.openai.com/v1  # Changed from url: to base_url:
    api_key: <your_key>
```
The adapter expected `base_url: https://api.openai.com/v1` but was configured with `url:` pointing to `/v1/models`.

---

## Issue: WebSocket Connection Immediately Closes After Success
Browser connections showed "connected successfully then immediately closed (code=1000)", backend repeatedly reported "cannot get request path".

**Solution:**
Fixed path parameter handling in WebSocket handler:
- Modified `WebSocketServer._handle_connection(self, websocket, path)` to receive and pass down the `path` parameter
- Updated `ConnectionHandler.handle_connection(ws, path)` to prioritize the passed `path` parameter, fallback to `ws.path`, and auto-generate `auto-<8-digit>` device-id if both are empty
- Added proper path extraction from websockets v14.2 callback structure

---

## Issue: Meeting Mode Memory Unbounded Growth
Meeting segments accumulated indefinitely in memory without cleanup, causing potential memory exhaustion.

**Solution:**
Implemented proper cleanup and limiting:
- Clear meeting cache after finalize in `finalize_meeting_and_send_summary(conn)`
- Added deduplication and limiting to maximum 6 bullets in meeting summary
- Added fields `bulletsLength` and `sourceSegments` for observability
- Ensured `meeting_segments` cleared on both `mode.end(meeting)` and `meeting.finalize`

---

## Issue: JSON Extraction from LLM Output Unreliable
LLM responses for meeting summaries couldn't be reliably parsed as JSON, causing summary generation failures.

**Solution:**
Implemented robust JSON extraction with fallback:
```python
# Primary: Direct JSON parsing
# Fallback: Extract content between brackets
# Ultimate fallback: Return empty bullets list with complete skeleton structure
```
Added strict JSON output constraints in system prompts and graceful degradation when LLM fails.

---

## Issue: Device ID Spoofing and Duplicate Connections
Multiple connections with same device-id could cause routing confusion and security issues.

**Solution:**
Added duplicate device ID detection in `backend/core/websocket_server.py`:
- Check for existing device ID during registration
- Reject new connections with duplicate IDs
- Immediately close connection on rejection to prevent spoofing
- Log warning messages for debugging

---

## Issue: Concurrent Task Store Write Conflicts
Multiple devices updating tasks simultaneously could cause data corruption in the JSON file storage.

**Solution:**
Implemented thread-safe operations in `backend/core/utils/tasks_store.py`:
- All file operations (save/load) performed within locks
- Basic schema validation during load phase
- Atomic write operations to prevent partial updates
- Added error handling for corrupt data recovery

---

## Issue: Port Already in Use Silent Failure
Service appeared to start but wasn't actually listening when port was already occupied.

**Solution:**
Added port pre-check before startup:
- Socket pre-binding test with SO_REUSEADDR
- Immediate ERROR log and exit on port unavailable or permission denied
- Added explicit `wait_started()` method in WebSocketServer
- Main app waits for startup completion before proceeding

---

## Issue: Peer Messaging Without Authorization Control
No ACL/whitelist/rate limiting for peer-to-peer messaging, creating security vulnerability.

**Solution:**
Implemented ACL and rate limiting:
```yaml
peer:
  enabled: true
  allow_all: false
  allow_broadcast: false
  allowlist:
    - "002"
```
- ACL check before LLM processing
- Unauthorized targets added to `failed` list in response
- Simple rate limiting for broadcast (≥5s per device)
- Added `UNAUTHORIZED` error code

---

## Issue: Schema Validation Incomplete
Malformed messages could bypass validation and cause unexpected behavior.

**Solution:**
Extended schema validation in `backend/core/utils/schema.py`:
- Added comprehensive enum validation for coding events: `start|stop|clear|phase|log|step`
- Added workflow events validation: `update|complete`
- Enforced required fields checking
- Return `SCHEMA_INVALID` error code for validation failures

---

## Issue: Service Stats Broadcasting Missing Degradation
When psutil unavailable, server stats broadcasting would fail completely.

**Solution:**
Implemented graceful degradation:
- Check psutil availability at startup
- When unavailable, send stats without CPU/memory fields
- Continue sending device count and online list
- Log warning but don't block service operation

---

## Issue: Non-Atomic Mode State Transitions
Mode switching between meeting/coding/working states wasn't atomic, causing inconsistent state.

**Solution:**
Unified state management in `backend/core/handle/textHandle.py`:
- Initialize meeting cache and timestamp in `mode.start(meeting)`
- Trigger finalize uniformly in `mode.end(meeting)`
- Ensure all related fields initialized in `connection.py`
- Added idempotency checks to prevent duplicate operations

---

## Issue: Coding Mode Lacking Observable Progress
No feedback during coding operations, making it unclear if system was working.

**Solution:**
Implemented simulated log streaming:
- Added `coding_stream_running` flag at connection level
- Simulated log stream sends 6-8 lines every 0.5s with mixed `info|warn|error` levels
- Added events: `start` (begin stream), `stop` (halt immediately), `clear` (send clear screen event), `step` (sync step with log), `phase` (phase transition with log)
- Auto-reset after stream completion

---

## Issue: Testing Environment CSP Restrictions
Browser environment might have CSP restrictions preventing external WebSocket connections.

**Solution:**
Provided alternative testing methods:
- Use local `file://` HTML pages to bypass CSP
- Provide enhanced test pages with subscription and disconnect buttons
- Document use of tools like Postman/WsCat for testing
- Added comprehensive test cases in `test/ws_001.html` and `test/ws_002.html`