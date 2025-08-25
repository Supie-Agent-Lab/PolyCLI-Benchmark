# Pain Points from Block 6

## Issue: VAD Detection Count Attribute Error
The system was experiencing persistent errors with VAD (Voice Activity Detection) processing, with logs continuously showing: `VAD处理异常: 'ConnectionHandler' object has no attribute '_vad_detection_count'`. This error occurred repeatedly during packet counting operations.

**Root Cause:**
In `backend/core/providers/vad/silero.py::VADProvider.is_vad()`, the `_vad_detection_count` was only initialized when `client_voice_frame_count` was missing. When a connection object already had `client_voice_frame_count` created but had never created `_vad_detection_count`, subsequent attempts to increment with `conn._vad_detection_count += 1` triggered an `AttributeError`.

**Solution:**
Separated the initialization of `_vad_detection_count` from `client_voice_frame_count` to ensure it always exists independently:

```python
# 初始化帧计数器
if not hasattr(conn, "client_voice_frame_count"):
    conn.client_voice_frame_count = 0
# 确保 _vad_detection_count 一定存在（避免 AttributeError）
if not hasattr(conn, "_vad_detection_count"):
    conn._vad_detection_count = 0
```

---

## Issue: Meeting Mode Performance Issues with TTS/LLM
Meeting mode was experiencing performance problems due to unnecessary TTS (Text-To-Speech) and LLM (Large Language Model) processing during meeting snippets, causing resource waste and latency.

**Solution:**
Implemented bypass mechanisms for TTS/LLM in meeting mode:
- Modified `backend/core/handle/receiveAudioHandle.py` to only inject `meeting.snippet` when in meeting mode
- Added configuration `meeting.disable_chat_on_snippet` (default true) to prevent triggering LLM on snippets
- Added `meeting.disable_tts` option to skip TTS audio transmission
- In `backend/core/handle/sendAudioHandle.py`, when `meeting.disable_tts==true`, only send `tts start/stop` placeholders without actual audio frames

---

## Issue: Thread Pool Resource Exhaustion
The connection-level ThreadPoolExecutor was using 5 threads per connection, causing resource issues at scale.

**Solution:**
Reduced thread pool size and made it configurable:
- Changed default ThreadPoolExecutor size from 5 to 2 in `backend/core/connection.py`
- Added `meeting.threadpool_max_workers` configuration option for override
- Implemented lazy initialization: skip opening TTS channel when `meeting.disable_tts==true`

---

## Issue: Concurrent Meeting Finalization Race Conditions
Multiple concurrent calls to finalize a meeting could cause duplicate processing and inconsistent state, potentially generating multiple summaries or corrupting meeting data.

**Solution:**
Implemented connection-level mutex lock and idempotency:
- Added `meeting_finalize_lock` mutex in `backend/core/handle/meeting_handle.py`
- First finalize call executes normally
- Concurrent calls return cached summary with `idempotent:true` flag
- Duration calculation fixed to use `start → max(lastSnippet, now)` to avoid 00:00:00 or incorrect short durations

---

## Issue: Meeting Timer Cleanup Not Idempotent
Calling `stop_meeting_timers()` multiple times could cause errors or undefined behavior due to attempting to cancel already-canceled timers.

**Solution:**
Made timer cleanup idempotent in `backend/core/handle/meeting_handle.py`:
- Clear task references after cancellation
- Set `meeting_timers_stopped` flag to track state
- Second calls become no-ops, preventing errors

---

## Issue: Transcript API Parameter Validation Missing
The transcript API could receive invalid parameters causing crashes or unexpected behavior, especially with out-of-bounds pagination values.

**Solution:**
Added parameter validation in `backend/core/http_server.py`:
- Enforce `offset>=0` and `1<=limit<=500`
- When parameters are out of bounds, return empty `items` array but maintain correct `total` count
- Prevents crashes while providing meaningful responses

---

## Issue: Meeting API Lack of Authentication
Meeting query endpoints were publicly accessible without any authentication, potentially exposing sensitive meeting data.

**Solution:**
Implemented optional read-only authentication for meeting APIs:
- Added `server.meeting_api_token` configuration option
- Support three authentication methods:
  - `Authorization: Bearer <token>`
  - `X-API-Token: <token>`
  - Query parameter: `?token=<token>`
- Return 401 Unauthorized on failed authentication
- Only applies to `/supie/meetings/*` endpoints

---

## Issue: Inconsistent API Response Format
Meeting query APIs had inconsistent response structures making client integration difficult and error handling complex.

**Solution:**
Standardized API response format in `backend/core/http_server.py`:
- Success responses: `{"success":true,"data":...}`
- Error responses: `{"success":false,"error":"..."}`
- Added CORS headers for `GET /supie/meetings/recent`, `/supie/meetings/{sessionId}`, and `/supie/meetings/{sessionId}/transcript`
- Support OPTIONS preflight requests

---

## Issue: Device-side VAD Not Prioritized
Server-side VAD was being used even when device-side VAD was available, causing unnecessary server processing and potential accuracy issues.

**Solution:**
Implemented device-side VAD preference in `backend/core/handle/textHandle.py`:
- Added `meeting.prefer_device_vad` configuration (default true)
- When entering meeting mode, set `client_listen_mode` to `manual` to signal frontend/hardware to bracket voice segments with `listen start/stop`
- Restore to `auto` mode when exiting meeting mode

---

## Issue: LLM Model Selection Inflexibility
System was using the same LLM model for all purposes (chat, meeting summaries, intent recognition, memory), leading to inefficient resource usage and suboptimal results for different tasks.

**Solution:**
Implemented purpose-based LLM selection in `backend/core/connection.py`:
- Added `get_llm_for(purpose)` method to select appropriate LLM based on use case
- Lazy loading and caching of LLM instances in `self._llm_cache`
- Configuration through `llm_by_mode` mapping different purposes to specific models:
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
- Modified all LLM usage points to use appropriate model selection

---

## Issue: Hot Config Updates Not Applied to Running Timers
Changes to `meeting.transcript_push_interval_ms` configuration were not taking effect until service restart, making it impossible to adjust push intervals dynamically.

**Solution:**
Implemented hot-reload for timer intervals:
- Current cycle continues with fixed `meeting_push_interval_ms_current`
- Next cycle reads updated configuration value
- Added logging: `next interval=...ms` to confirm new interval application
- Changes take effect after current cycle completes