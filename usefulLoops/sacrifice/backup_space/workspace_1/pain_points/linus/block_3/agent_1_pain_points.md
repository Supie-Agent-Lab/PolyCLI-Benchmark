# Pain Points Analysis - Block 3

## Issue: WebSocket Connection Failed - Library API Misuse
WebSocket connections were completely non-functional. The OTA page kept spinning indefinitely, browser WS test pages couldn't connect, hardware couldn't connect, and the server had almost no new log output.

**Root Cause:**
The WebSocket upgrade callback in `backend/core/websocket_server.py::_http_response` was using incorrect library API signatures and return values. Specifically:
- Used wrong callback signature for `websockets.serve(process_request=...)`
- Incorrectly treated `request_headers` as an object with `.headers` attribute
- Called non-existent `websocket.respond()` method

**Solution:**
Fixed the WebSocket upgrade callback to conform to library specifications:
```python
# Correct signature: upgrade requests return None, HTTP requests return (status, headers, body)
def _http_response(path, request_headers):
    if is_websocket_upgrade:
        return None  # Let websockets handle the upgrade
    else:
        return (status, headers, body)  # Return HTTP response tuple
```
Removed all calls to non-existent APIs.

---

## Issue: Connection Object Attribute Confusion
Mixed up attribute access patterns between aiohttp and websockets libraries, causing connection failures during handshake or first packet parsing.

**Root Cause:**
Code was using `ws.request.headers` and `ws.request.path` to read request information, but websockets objects should use `request_headers` and `path` directly.

**Solution:**
Aligned connection object access to websockets library conventions:
```python
# File: backend/core/connection.py::handle_connection
# Changed from ws.request.headers to request_headers
# Changed from ws.request.path to path parameter
```

---

## Issue: OTA WebSocket Path Inconsistency
OTA endpoint returned inconsistent WebSocket path, preventing devices from connecting properly.

**Root Cause:**
OTA handler returned `/xiaozhi/v1/` while test pages, documentation, and backend modules were using `/supie/v1/`.

**Solution:**
Unified WebSocket path across all components:
```python
# File: backend/core/api/ota_handler.py::_get_websocket_url
# Changed to return consistent path: /supie/v1/
```

---

## Issue: FFmpeg Hard Dependency Blocking Startup
Service failed to start when ffmpeg was not installed, showing no external listening and appearing as "can't connect, no new logs".

**Root Cause:**
`backend/app.py::main` called `check_ffmpeg_installed()` which threw an exception and terminated the process when ffmpeg was missing.

**Solution:**
Downgraded ffmpeg check from hard requirement to warning:
```python
# File: backend/app.py::main
# Changed ffmpeg check to warning level, allowing service to start without it
# Only fails when ffmpeg-dependent features are actually used
```

---

## Issue: Path Parameter Not Passed to Handler
WebSocket connections immediately closed after successful connection with "cannot get request path" errors.

**Root Cause:**
websockets (v14.2) passes `path` as second parameter to handler callback, but old implementation only read from `ws.path` which was empty in some environments, preventing device-id parsing.

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

## Issue: LLM Configuration Format Error
AI relay (peer messaging) failed with 404 errors or JSON parsing failures.

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

## Issue: Meeting Mode Memory Unbounded Growth
Meeting segments accumulated in memory without cleanup, potentially causing memory issues in long sessions.

**Root Cause:**
Meeting segments were continuously appended to `meeting_segments` without any cleanup mechanism after meeting finalization.

**Solution:**
Implemented proper cleanup after meeting finalization:
- Clear `meeting_segments` after generating summary
- Limit summary bullets to maximum 6 items with deduplication
- Added `finalize_meeting_and_send_summary()` to handle cleanup

---

## Issue: Device ID Spoofing Vulnerability
Multiple connections could register with the same device-id, allowing potential spoofing.

**Root Cause:**
No duplicate detection when registering device routes in `backend/core/websocket_server.py`.

**Solution:**
Added duplicate device-id detection:
```python
# File: backend/core/websocket_server.py
# Check for existing device-id during registration
# Reject new connection if device-id already exists
# Connection side receives rejection and closes immediately
```

---

## Issue: Workflow Concurrent Write Conflicts
Multiple devices updating tasks simultaneously could cause data corruption.

**Root Cause:**
File I/O operations in `backend/core/utils/tasks_store.py` weren't properly synchronized.

**Solution:**
Implemented proper locking for all file operations:
```python
# File: backend/core/utils/tasks_store.py
# All save/load operations now happen within locks
# Added basic schema validation during load phase
# Prevents data corruption from concurrent updates
```

---

## Issue: JSON Extraction from LLM Output Unreliable
LLM responses for meeting summaries often failed JSON parsing, resulting in empty bullet points.

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
```

---

## Issue: Peer Messaging No Authorization Control
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
Unauthorized targets are rejected and included in `failed` receipt.

---

## Issue: Broadcast Messages No Rate Limiting
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

## Issue: Port Binding Failures Silent
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

## Issue: Configuration Inconsistencies Across Components
Port numbers, IP addresses, and paths were inconsistent between configuration, test pages, and documentation (8000 vs 8004, 127.0.0.1 vs 0.0.0.0).

**Solution:**
Standardized configuration across all components:
```yaml
# backend/data/.config.yaml
server:
  ip: 0.0.0.0  # Listen on all interfaces
  port: 8004   # Unified WebSocket port
  http_port: 8003  # HTTP/OTA port
  advertise_ip: <lan-ip>  # Consistent LAN IP for logs
  websocket: ws://<lan-ip>:8004/supie/v1/  # Full URL
```
Updated all test pages and documentation to use port 8004 and path `/supie/v1/`.

---

## Issue: Schema Validation Incomplete
Incomplete validation allowed malformed messages to bypass security checks.

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
```

---

## Issue: Mode State Non-Atomic Switching
Mode transitions weren't atomic, potentially causing inconsistent state during switches.

**Root Cause:**
Mode state changes and associated cleanup operations weren't synchronized.

**Solution:**
Unified mode transition handling:
```python
# File: backend/core/handle/textHandle.py
# mode.start(meeting): Initialize meeting cache and timestamp atomically
# mode.end(meeting): Trigger finalize uniformly
# All related fields initialized in connection.py
```