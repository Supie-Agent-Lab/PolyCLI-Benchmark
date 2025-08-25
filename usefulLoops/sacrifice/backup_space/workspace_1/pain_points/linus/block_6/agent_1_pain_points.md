# Pain Points from Block 6

## Issue: AttributeError - VAD Detection Count Not Initialized
The system was throwing repeated errors: `VAD处理异常: 'ConnectionHandler' object has no attribute '_vad_detection_count'` when processing VAD (Voice Activity Detection) packets, causing the packet counting mechanism to fail.

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

## Issue: Performance Degradation from Excessive Thread Pool Size
The connection-level ThreadPoolExecutor was configured with 5 threads, causing unnecessary resource consumption especially in meeting mode where TTS/LLM operations were bypassed.

**Solution:**
Reduced the thread pool from 5 to 2 threads and made it configurable via `meeting.threadpool_max_workers`. Added lazy initialization to skip opening TTS channels when `meeting.disable_tts==true`:

- File: `backend/core/connection.py`
- Changed default ThreadPoolExecutor from 5 → 2
- Added configuration override support via `meeting.threadpool_max_workers`
- Implemented lazy initialization for TTS channels when disabled

---

## Issue: Concurrent Finalize Operations Causing Duplicate Processing
Multiple concurrent finalize operations on meeting summaries could result in duplicate processing and resource waste, particularly when multiple triggers attempted to finalize the same meeting simultaneously.

**Solution:**
Implemented a connection-level mutex lock with idempotency checking:

- File: `backend/core/handle/meeting_handle.py`
- Added `meeting_finalize_lock` mutex for connection-level synchronization
- First finalize executes normally, subsequent concurrent attempts return cached summary with `idempotent:true` flag
- Prevents duplicate LLM calls and processing

---

## Issue: Incorrect Meeting Duration Calculation
Meeting duration was showing as `00:00:00` or unrealistically short durations due to incorrect timestamp calculation logic.

**Solution:**
Fixed duration calculation to use `start → max(lastSnippet, now)` for estimation:

- File: `backend/core/handle/meeting_handle.py`
- Changed duration calculation to consider the maximum of last snippet timestamp and current time
- Ensures minimum reasonable duration even for meetings with sparse snippets

---

## Issue: Timer Tasks Not Properly Cleaned Up on Stop
Meeting transcript push timers were not being properly cleaned up, causing potential memory leaks and duplicate executions when timers were stopped and restarted.

**Solution:**
Implemented idempotent timer stopping with proper cleanup:

- File: `backend/core/handle/meeting_handle.py`
- Added `meeting_timers_stopped` flag to track stop state
- Clear task references after cancellation in `stop_meeting_timers()`
- Made the function idempotent - second calls return immediately without side effects

---

## Issue: Configuration Hot Reload Not Affecting Current Timer Intervals
When `meeting.transcript_push_interval_ms` was updated via hot reload, the current running timer would continue with the old interval indefinitely.

**Solution:**
Implemented interval caching to affect only the next cycle:

- File: `backend/core/handle/meeting_handle.py`
- Current cycle uses fixed `meeting_push_interval_ms_current`
- Configuration changes apply to next timer cycle
- Added logging: `next interval=...ms` to track when new intervals take effect

---

## Issue: Missing CORS Headers on Meeting Query APIs
Meeting query endpoints (`/supie/meetings/*`) were missing CORS headers, preventing cross-origin requests from web clients.

**Solution:**
Added unified CORS support for all meeting query endpoints:

- File: `backend/core/http_server.py`
- Added CORS headers for `GET /supie/meetings/recent`, `/supie/meetings/{sessionId}`, `/supie/meetings/{sessionId}/transcript`
- Implemented OPTIONS preflight handling for all endpoints
- Unified response structure: `{"success":true,"data":...}` for success, `{"success":false,"error":"..."}` for errors

---

## Issue: Invalid Pagination Parameters Causing API Errors
The transcript API would crash or return incorrect results when provided with invalid pagination parameters (negative offset, zero/excessive limit).

**Solution:**
Implemented parameter validation with graceful handling:

- File: `backend/core/http_server.py`
- Added validation: `offset>=0`, `1<=limit<=500`
- Out-of-bounds requests return empty `items` while preserving correct `total` count
- Prevents crashes and provides predictable API behavior

---

## Issue: Lack of Authentication on Meeting Query APIs
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

## Issue: Inefficient LLM Usage Across Different Modes
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