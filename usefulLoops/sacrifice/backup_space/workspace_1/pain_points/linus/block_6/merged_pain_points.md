# Pain Points from Block 6

## Critical Issues

### 1. AttributeError - VAD Detection Count Not Initialized
The system was throwing repeated errors: `VAD处理异常: 'ConnectionHandler' object has no attribute '_vad_detection_count'` when processing VAD (Voice Activity Detection) packets, causing the packet counting mechanism to fail completely.

**Root Cause:**
In `backend/core/providers/vad/silero.py::VADProvider.is_vad()`, the `_vad_detection_count` attribute was only initialized when `client_voice_frame_count` was missing. When a connection object already had `client_voice_frame_count` but had never created `_vad_detection_count`, the subsequent increment operation `conn._vad_detection_count += 1` would trigger an AttributeError.

**Solution:**
Separated the initialization logic to ensure `_vad_detection_count` is always initialized independently:

```python
# Initialize frame counter
if not hasattr(conn, "client_voice_frame_count"):
    conn.client_voice_frame_count = 0
# Ensure _vad_detection_count always exists (avoid AttributeError)
if not hasattr(conn, "_vad_detection_count"):
    conn._vad_detection_count = 0
```

---

### 2. Concurrent Meeting Finalization Race Conditions
Multiple concurrent calls to finalize a meeting could cause duplicate processing and inconsistent state, potentially generating multiple summaries or corrupting meeting data.

**Solution:**
Implemented connection-level mutex lock with idempotency checking:
- File: `backend/core/handle/meeting_handle.py`
- Added `meeting_finalize_lock` mutex for connection-level synchronization
- First finalize executes normally, subsequent concurrent attempts return cached summary with `idempotent:true` flag
- Prevents duplicate LLM calls and processing

---

## Performance Issues

### 3. Performance Degradation from Excessive Thread Pool Size
The connection-level ThreadPoolExecutor was configured with 5 threads, causing unnecessary resource consumption especially in meeting mode where TTS/LLM operations were bypassed.

**Solution:**
Reduced the thread pool from 5 to 2 threads and made it configurable via `meeting.threadpool_max_workers`:
- File: `backend/core/connection.py`
- Changed default ThreadPoolExecutor from 5 → 2
- Added configuration override support via `meeting.threadpool_max_workers`
- Implemented lazy initialization for TTS channels when disabled

---

### 4. Unnecessary TTS/LLM Processing in Meeting Mode
Meeting mode was experiencing performance problems due to unnecessary TTS (Text-To-Speech) and LLM (Large Language Model) processing during meeting snippets, causing resource waste and latency.

**Solution:**
Implemented bypass mechanisms for TTS/LLM in meeting mode:
- Modified `backend/core/handle/receiveAudioHandle.py` to only inject `meeting.snippet` when in meeting mode
- Added configuration `meeting.disable_chat_on_snippet` (default true) to prevent triggering LLM on snippets
- Added `meeting.disable_tts` option to skip TTS audio transmission
- In `backend/core/handle/sendAudioHandle.py`, when `meeting.disable_tts==true`, only send `tts start/stop` placeholders without actual audio frames

---

### 5. Inefficient LLM Usage Across Different Modes
All modes (chat, meeting, coding, etc.) were using the same LLM model, leading to suboptimal performance and cost - using expensive models for simple tasks and vice versa.

**Solution:**
Implemented per-mode LLM selection with lazy loading and caching:
- File: `backend/core/connection.py`
- Added `get_llm_for(purpose)` method to select appropriate LLM based on mode
- Lazy loading and connection-level caching of LLM instances
- Configuration via `llm_by_mode` mapping in config:

```yaml
llm_by_mode:
  default: ChatGLM_Flashx
  chat:    ChatGLM_Flashx
  meeting: ChatGLM_45
  coding:  ChatGLM_45
  working: ChatGLM_45
  intent:  ChatGLM_Flashx
  memory:  ChatGLM_45
```

- Automatic cleanup of LLM cache on connection close

---

### 6. Device-side VAD Not Prioritized
Server-side VAD was being used even when device-side VAD was available, causing unnecessary server processing and potential accuracy issues.

**Solution:**
Implemented device-side VAD preference in `backend/core/handle/textHandle.py`:
- Added `meeting.prefer_device_vad` configuration (default true)
- When entering meeting mode, set `client_listen_mode` to `manual` to signal frontend/hardware to bracket voice segments with `listen start/stop`
- Restore to `auto` mode when exiting meeting mode

---

## Security & API Issues

### 7. Lack of Authentication on Meeting Query APIs
Meeting query endpoints were publicly accessible without any authentication mechanism, potentially exposing sensitive meeting data.

**Solution:**
Implemented optional token-based authentication with multiple input methods:
- File: `backend/core/http_server.py`
- Added `server.meeting_api_token` configuration option
- Supports three authentication methods:
  - `Authorization: Bearer <token>`
  - `X-API-Token: <token>`
  - Query parameter: `?token=<token>`
- Returns 401 Unauthorized for failed authentication
- Only applies to `/supie/meetings/*` endpoints

---

### 8. Missing CORS Headers on Meeting Query APIs
Meeting query endpoints (`/supie/meetings/*`) were missing CORS headers, preventing cross-origin requests from web clients.

**Solution:**
Added unified CORS support for all meeting query endpoints:
- File: `backend/core/http_server.py`
- Added CORS headers for `GET /supie/meetings/recent`, `/supie/meetings/{sessionId}`, `/supie/meetings/{sessionId}/transcript`
- Implemented OPTIONS preflight handling for all endpoints
- Unified response structure: `{"success":true,"data":...}` for success, `{"success":false,"error":"..."}` for errors

---

### 9. Invalid Pagination Parameters Causing API Errors
The transcript API would crash or return incorrect results when provided with invalid pagination parameters (negative offset, zero/excessive limit).

**Solution:**
Implemented parameter validation with graceful handling:
- File: `backend/core/http_server.py`
- Added validation: `offset>=0`, `1<=limit<=500`
- Out-of-bounds requests return empty `items` while preserving correct `total` count
- Prevents crashes and provides predictable API behavior

---

## Data Integrity Issues

### 10. Incorrect Meeting Duration Calculation
Meeting duration was showing as `00:00:00` or unrealistically short durations due to incorrect timestamp calculation logic.

**Solution:**
Fixed duration calculation to use `start → max(lastSnippet, now)` for estimation:
- File: `backend/core/handle/meeting_handle.py`
- Changed duration calculation to consider the maximum of last snippet timestamp and current time
- Ensures minimum reasonable duration even for meetings with sparse snippets

---

## Resource Management Issues

### 11. Timer Tasks Not Properly Cleaned Up on Stop
Meeting transcript push timers were not being properly cleaned up, causing potential memory leaks and duplicate executions when timers were stopped and restarted.

**Solution:**
Implemented idempotent timer stopping with proper cleanup:
- File: `backend/core/handle/meeting_handle.py`
- Added `meeting_timers_stopped` flag to track stop state
- Clear task references after cancellation in `stop_meeting_timers()`
- Made the function idempotent - second calls return immediately without side effects

---

## Configuration & Hot-Reload Issues

### 12. Configuration Hot Reload Not Affecting Current Timer Intervals
When `meeting.transcript_push_interval_ms` was updated via hot reload, the current running timer would continue with the old interval indefinitely.

**Solution:**
Implemented interval caching to affect only the next cycle:
- File: `backend/core/handle/meeting_handle.py`
- Current cycle uses fixed `meeting_push_interval_ms_current`
- Configuration changes apply to next timer cycle
- Added logging: `next interval=...ms` to track when new intervals take effect