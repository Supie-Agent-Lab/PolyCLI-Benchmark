# Merged Pain Points Analysis - Block 3

## Critical Issues (Service-Breaking)

### Issue: Complete WebSocket Connection Failure - Service Not Listening
WebSocket connections were completely non-functional. The OTA page kept spinning indefinitely, browser WS test pages couldn't connect, hardware couldn't connect, and the server had almost no new log output. The entire WebSocket/OTA chain was unreachable.

**Root Causes (by impact):**

1. **WebSocket upgrade callback API misuse**
   - Used wrong callback signature for `websockets.serve(process_request=...)`
   - Incorrectly treated `request_headers` as an object with `.headers` attribute
   - Called non-existent `websocket.respond()` method

2. **Connection object attribute confusion (aiohttp vs websockets)**
   - Code was using `ws.request.headers` and `ws.request.path` to read request information
   - Should have used `request_headers` and `path` directly for websockets library

3. **OTA WebSocket path inconsistency**
   - OTA handler returned `/xiaozhi/v1/` while test pages, documentation, and backend modules were using `/supie/v1/`

4. **FFmpeg hard dependency blocking startup**
   - `backend/app.py::main` called `check_ffmpeg_installed()` which threw an exception and terminated the process when ffmpeg was missing
   - Service never started listening

5. **Configuration inconsistencies**
   - Port mismatches (8000 vs 8004)
   - IP binding issues (`127.0.0.1` vs `0.0.0.0`)

**Solution:**
Multiple fixes were applied:
```python
# Fixed WebSocket upgrade callback to conform to library specifications:
def _http_response(path, request_headers):
    if is_websocket_upgrade:
        return None  # Let websockets handle the upgrade
    else:
        return (status, headers, body)  # Return HTTP response tuple

# Aligned connection object access to websockets library conventions
# Changed from ws.request.headers to request_headers
# Changed from ws.request.path to path parameter
```
- Unified WebSocket path to `/supie/v1/` across all components
- Downgraded ffmpeg check from hard requirement to warning level
- Standardized configuration:
```yaml
server:
  ip: 0.0.0.0  # Listen on all interfaces
  port: 8004   # Unified WebSocket port
  http_port: 8003  # HTTP/OTA port
  advertise_ip: <lan-ip>  # Consistent LAN IP for logs
  websocket: ws://<lan-ip>:8004/supie/v1/  # Full URL
```

---

### Issue: WebSocket Connection Immediately Closing After Success
Browser connections would succeed then immediately close with code 1000, backend reported "cannot get request path" multiple times, preventing device-id parsing.

**Root Cause:**
websockets v14.2 passes `path` as second parameter to handler callback, but old implementation only read from `ws.path`, which was empty in some environments.

**Solution:**
Made path handling compatible with library callback pattern:
```python
# File: backend/core/websocket_server.py
async def _handle_connection(self, websocket, path):
    # Pass path parameter down
    await ConnectionHandler.handle_connection(websocket, path)

# File: backend/core/connection.py
async def handle_connection(ws, path):
    # Use passed path parameter first, fallback to ws.path
    # Auto-assign device-id if both are empty
    if not path and hasattr(ws, 'path'):
        path = ws.path
    if not path:
        device_id = f"auto-{random_8_chars}"  # With warning
```

---

### Issue: Port Binding Failures Silent
Service appeared to run but wasn't actually listening when port was already in use or permissions were insufficient.

**Root Cause:**
No pre-check for port availability before attempting to start WebSocket server.

**Solution:**
Added port pre-binding check with explicit error reporting:
```python
# File: backend/core/websocket_server.py
# Pre-bind socket with SO_REUSEADDR to check availability
# Immediate ERROR log and exit if port unavailable
# Added wait_started() for explicit startup confirmation
```

---

## High Severity Issues (Feature-Breaking)

### Issue: LLM Configuration Format Error
AI relay (peer messaging) failed with 404 errors (`Invalid URL (POST /v1/models/chat/completions)`) or JSON parsing failures (`LLM_OUTPUT_NOT_JSON`).

**Root Cause:**
`LLM.gptLLM` configuration used `url:` pointing to `/v1/models` instead of the expected `base_url: https://api.openai.com/v1` format.

**Solution:**
Fixed configuration format in `backend/data/.config.yaml`:
```yaml
LLM:
  gptLLM:
    type: openai
    model_name: gpt-4.1-nano
    base_url: https://api.openai.com/v1  # Changed from url: to base_url:
    api_key: <your_key>
```

---

### Issue: JSON Extraction from LLM Output Unreliable
LLM responses for meeting summaries often failed JSON parsing, resulting in empty bullet points or summary generation failures.

**Root Cause:**
Direct JSON parsing without fallback mechanisms for malformed LLM output.

**Solution:**
Implemented robust JSON extraction with fallbacks:
```python
# File: backend/core/handle/meeting_handle.py
# Try direct JSON parsing first
# Fallback to bracket extraction if direct parsing fails
# Return empty list if all extraction methods fail
# Added deduplication and limiting to 6 bullets
# Ultimate fallback: Return empty bullets list with complete skeleton structure
```
Added strict JSON output constraints in system prompts and graceful degradation.

---

### Issue: Meeting Mode Memory Unbounded Growth
Meeting segments accumulated in memory without cleanup, potentially causing memory exhaustion in long sessions.

**Root Cause:**
Meeting segments were continuously appended to `meeting_segments` without any cleanup mechanism after meeting finalization.

**Solution:**
Implemented proper cleanup after meeting finalization:
- Clear `meeting_segments` after generating summary
- Limit summary bullets to maximum 6 items with deduplication
- Added `finalize_meeting_and_send_summary()` to handle cleanup
- Added fields `bulletsLength` and `sourceSegments` for observability
- Ensured cleanup on both `mode.end(meeting)` and `meeting.finalize`

---

## Security Issues

### Issue: Device ID Spoofing Vulnerability
Multiple connections could register with the same device-id, allowing potential spoofing and routing confusion.

**Root Cause:**
No duplicate detection when registering device routes in `backend/core/websocket_server.py`.

**Solution:**
Added duplicate device-id detection:
```python
# File: backend/core/websocket_server.py
# Check for existing device-id during registration
# Reject new connection if device-id already exists
# Connection side receives rejection and closes immediately
# Log warning messages for debugging
```

---

### Issue: Peer Messaging No Authorization Control
Peer messaging had no permission verification, allowing unrestricted device-to-device communication.

**Root Cause:**
Missing ACL (Access Control List) implementation for peer messaging targets.

**Solution:**
Added ACL pre-filtering with configuration support:
```yaml
# Configuration options:
peer:
  enabled: true
  allow_all: false  # Set true for debugging only
  allow_broadcast: false
  allowlist:
    - "002"  # Explicitly allowed target devices
```
- ACL check before LLM processing
- Unauthorized targets are rejected and included in `failed` receipt
- Added `UNAUTHORIZED` error code

---

### Issue: Broadcast Messages No Rate Limiting
Broadcast messages could be sent without any frequency restrictions, potentially causing spam.

**Root Cause:**
No rate limiting implementation for broadcast operations.

**Solution:**
Added simple rate limiting for broadcast:
```python
# File: backend/core/handle/peerHandle.py
# Minimum 5 seconds between broadcasts per device
# ACL filtering happens before LLM processing
# Unauthorized targets added to failed receipt
```

---

## Data Integrity Issues

### Issue: Workflow Concurrent Write Conflicts
Multiple devices updating tasks simultaneously could cause data corruption in the JSON file storage.

**Root Cause:**
File I/O operations in `backend/core/utils/tasks_store.py` weren't properly synchronized.

**Solution:**
Implemented proper locking for all file operations:
```python
# File: backend/core/utils/tasks_store.py
# All save/load operations now happen within locks
# Added basic schema validation during load phase
# Thread-safe add/update/complete operations
# Added error handling for corrupt data recovery
# Atomic write operations to prevent partial updates
```

---

### Issue: Non-Atomic Mode State Switching
Mode transitions weren't atomic, potentially leaving system in inconsistent state during meeting mode switches.

**Root Cause:**
Mode state changes and associated cleanup operations weren't synchronized.

**Solution:**
Unified mode transition handling:
```python
# File: backend/core/handle/textHandle.py
# mode.start(meeting): Initialize meeting cache and timestamp atomically
# mode.end(meeting): Trigger finalize uniformly
# All related fields initialized in connection.py
# Added idempotency checks to prevent duplicate operations
```

---

## Validation & Schema Issues

### Issue: Schema Validation Incomplete
Incomplete validation allowed malformed messages to bypass security checks and cause downstream errors.

**Root Cause:**
Missing validation for various event types and required fields in schema definitions.

**Solution:**
Extended schema validation coverage:
```python
# File: backend/core/utils/schema.py
# Added comprehensive validation for:
# - coding events: start|stop|clear|phase|log|step
# - workflow events: update|complete
# - All required fields now properly validated
# - Enum constraints enforced
# Return SCHEMA_INVALID error code for validation failures
```

---

## Observability & User Experience Issues

### Issue: Coding Mode Lacking Observable Progress
No feedback during coding operations, making it unclear if system was working.

**Solution:**
Implemented simulated log streaming:
- Added `coding_stream_running` flag at connection level
- Simulated log stream sends 6-8 lines every 0.5s with mixed `info|warn|error` levels
- Added events: `start` (begin stream), `stop` (halt immediately), `clear` (send clear screen event), `step` (sync step with log), `phase` (phase transition with log)
- Auto-reset after stream completion

---

### Issue: Service Stats Broadcasting Missing Degradation
When psutil unavailable, server stats broadcasting would fail completely.

**Solution:**
Implemented graceful degradation:
- Check psutil availability at startup
- When unavailable, send stats without CPU/memory fields
- Continue sending device count and online list
- Log warning but don't block service operation

---

## Testing Environment Issues

### Issue: CSP Restrictions in Browser Environment
Browser Content Security Policy could restrict WebSocket connections to external servers, breaking test pages.

**Solution:**
Provided alternative testing methods:
- Use local `file://` HTML pages to bypass CSP
- Provide enhanced test pages with subscription and disconnect buttons
- Document use of tools like Postman/WsCat for testing
- Added comprehensive test cases in `test/ws_001.html` and `test/ws_002.html`