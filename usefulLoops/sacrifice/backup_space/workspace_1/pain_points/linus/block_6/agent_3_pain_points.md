# Pain Points from Block 6

## Issue: AttributeError - Missing _vad_detection_count attribute
VAD processing was throwing continuous errors in the logs: `VAD处理异常: 'ConnectionHandler' object has no attribute '_vad_detection_count'`. This error occurred repeatedly during packet counting increments, causing the VAD (Voice Activity Detection) system to fail.

**Root Cause:**
In `backend/core/providers/vad/silero.py::VADProvider.is_vad()`, the `_vad_detection_count` attribute was only initialized when `client_voice_frame_count` was missing. When a connection object already had `client_voice_frame_count` created but never had `_vad_detection_count` initialized, subsequent attempts to increment with `conn._vad_detection_count += 1` triggered an AttributeError.

**Solution:**
Separated the initialization of `_vad_detection_count` from `client_voice_frame_count` to ensure it always exists independently:

```python
# Initialize frame counter
if not hasattr(conn, "client_voice_frame_count"):
    conn.client_voice_frame_count = 0
# Ensure _vad_detection_count always exists (avoid AttributeError)
if not hasattr(conn, "_vad_detection_count"):
    conn._vad_detection_count = 0
```

---

## Issue: Performance bottleneck with excessive thread pool size
The system was using a thread pool with 5 workers per connection, which was excessive for meeting mode operations and caused unnecessary resource consumption.

**Solution:**
Reduced the connection-level ThreadPoolExecutor from 5 to 2 workers and made it configurable:
- Changed default from 5 → 2 workers
- Added support for `meeting.threadpool_max_workers` configuration to override the default
- Implemented lazy initialization - when `meeting.disable_tts==true`, skip opening TTS channels during initialization

---

## Issue: Unnecessary TTS/LLM processing in meeting mode
Meeting mode was triggering full TTS (Text-to-Speech) and LLM (Large Language Model) processing even when only transcription was needed, causing performance issues and unnecessary API calls.

**Solution:**
Implemented bypass mechanisms for meeting mode:
- Modified `startToChat` in `backend/core/handle/receiveAudioHandle.py` to only inject `meeting.snippet` when in meeting mode
- Added `meeting.disable_chat_on_snippet` config (default true) to prevent triggering conversational LLM
- Added `meeting.disable_tts` config to skip TTS processing entirely
- When TTS is disabled, only send `tts start/stop` placeholders without audio frames or expressions

---

## Issue: Concurrent finalize operations causing duplicate processing
Multiple concurrent calls to finalize meeting summaries could result in duplicate processing and generation of summaries.

**Solution:**
Implemented connection-level mutex lock and idempotency:
- Added `meeting_finalize_lock` mutex at connection level
- First finalize call processes normally
- Concurrent calls return the cached summary with `idempotent:true` flag
- Prevents duplicate API calls and processing overhead

---

## Issue: Incorrect meeting duration calculation
Meeting duration was showing as 00:00:00 or incorrectly short durations due to improper timestamp calculation.

**Solution:**
Fixed duration calculation logic:
- Changed to calculate duration as `start → max(lastSnippet, now)`
- Ensures minimum reasonable duration even if snippets are missing
- Avoids edge cases with zero or negative durations

---

## Issue: Inefficient VAD processing with server-side detection
Server-side VAD processing was causing delays and inefficiencies, especially when devices had their own VAD capabilities.

**Solution:**
Implemented device-side VAD preference:
- Added `meeting.prefer_device_vad` config (default true)
- When entering meeting mode, sets `client_listen_mode` to `manual`
- Prompts frontend/hardware to bracket voice segments with `listen start/stop`
- Reverts to `auto` mode when exiting meeting mode

---

## Issue: Missing authentication and CORS support for meeting query APIs
Meeting query endpoints were exposed without authentication and lacked proper CORS headers, creating security vulnerabilities and cross-origin access issues.

**Solution:**
Implemented unified authentication and CORS support:
- Added optional `server.meeting_api_token` configuration
- Supports three authentication methods: `Authorization: Bearer`, `X-API-Token` header, and `?token=` query parameter
- Returns 401 on authentication failure
- Added proper CORS headers for GET/OPTIONS on `/supie/meetings/*` endpoints
- Unified response structure: success returns `{"success":true,"data":...}`, errors return `{"success":false,"error":"..."}`

---

## Issue: Invalid pagination parameters causing API errors
The transcript API could receive invalid pagination parameters (negative offsets, excessive limits) causing unexpected behavior.

**Solution:**
Added parameter validation:
- Enforced `offset>=0` and `1<=limit<=500`
- When parameters are out of bounds, returns empty `items` array while maintaining correct `total` count
- Prevents database query errors and excessive resource consumption

---

## Issue: Hot-reload of transcript push intervals not taking effect
Changes to `meeting.transcript_push_interval_ms` configuration were not being applied to active push cycles.

**Solution:**
Implemented proper interval update mechanism:
- Current cycle maintains fixed `meeting_push_interval_ms_current` value
- Configuration changes only affect the next cycle
- Added logging to show `next interval=...ms` for visibility
- Ensures predictable behavior without interrupting active cycles

---

## Issue: Inefficient LLM usage across different modes
All modes were using the same LLM model regardless of requirements, causing unnecessary costs for simple tasks and potential performance issues for complex ones.

**Solution:**
Implemented mode-specific LLM selection:
- Added `get_llm_for(purpose)` method to select appropriate LLM based on use case
- Configuration through `llm_by_mode` mapping different purposes to specific models
- Lazy loading and caching of LLM instances at connection level
- Cleanup of `_llm_cache` on connection close
- Example configuration separating fast models for chat/intent and powerful models for meeting summaries:
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