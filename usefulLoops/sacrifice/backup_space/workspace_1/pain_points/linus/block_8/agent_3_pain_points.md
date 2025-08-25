# Pain Points from Block 8 - Linus Conversation

## Issue: Delayed WebSocket Snapshot Task Creation Error
The initial implementation used incorrect syntax for creating delayed snapshot tasks, causing the snapshot to be sent immediately rather than after the configured delay.

**Solution:**
Changed from `asyncio.create_task((asyncio.sleep(...),))` to a proper async function `_delayed_snapshot()` that first awaits the sleep, then calls `_send_snapshot()`. This ensures test mode snapshots are sent only once after the configured delay.

---

## Issue: Event Loop Binding During Construction
Event loop was being bound during ConnectionHandler construction using `get_event_loop()`, which could fail when no running loop exists or cause cross-loop scheduling issues.

**Solution:**
Moved event loop binding to the `handle_connection()` entry point using `asyncio.get_running_loop()`, ensuring the loop is properly bound to the running coroutine context.

---

## Issue: Scattered WebSocket Send Logic
WebSocket sending logic was scattered throughout the codebase with multiple try/except blocks handling `send_json` attribute errors and fallbacks to string serialization.

**Solution:**
Created unified `ConnectionHandler.send_json()` and `send_text()` methods that centrally handle `send_json` missing attribute fallback to string serialization, reducing boilerplate code and centralizing error handling.

---

## Issue: Duplicate Heartbeat Processing
Heartbeat messages (ping/keepalive) were being processed in multiple places - both in `_route_message` and in `handleTextMessage`, causing duplicate processing and unnecessary logs.

**Solution:**
Removed duplicate heartbeat handling from `handleTextMessage`, keeping only the single processing point in `_route_message` that intercepts and responds with `pong`.

---

## Issue: BlockingIOError with Long Log Messages  
Extended log messages containing JSON payloads were causing `BlockingIOError` exceptions and blocking the logging system.

**Solution:**
- Implemented truncation patcher `_build_trunc_patcher()` for both console and file sinks
- Set default `log.max_message_length` to 2000 characters
- Changed coding insights to output only statistical summary lines instead of full JSON: `[Coding Insight] final=... insights=... jsonSHA=... elapsedMs=...`

---

## Issue: LLM Instance Duplication
Multiple LLM instances were being created for the same configuration, wasting memory and initialization time.

**Solution:**
- Implemented `WebSocketServer.get_or_create_llm()` with a shared registry using fingerprint keys (alias + overrides)
- Modified `ConnectionHandler.get_llm_for()` to delegate to server's shared factory
- Cache instances by purpose (chat/meeting/coding/working/intent/memory) to enable reuse across connections

---

## Issue: Meeting Finalize Concurrency Issues
Concurrent finalize requests could trigger multiple summary calculations and cause race conditions.

**Solution:**
- Added connection-level mutex lock `meeting_finalize_lock = asyncio.Lock()`
- Implemented idempotency - first finalize computes, subsequent ones return cached result with `idempotent:true` flag
- All send/broadcast paths now swallow connection closed exceptions

---

## Issue: ASR Stream Not Finalizing on Listen Stop
When `listen.stop` was received, ASR streams weren't immediately producing final transcription results, causing text loss.

**Solution:**
- Added `on_client_listen_stop()` callback in ASR providers
- Implemented sending "last frame" marker in `doubao_stream.py` using `generate_last_audio_default_header()` with empty payload to force server-side definitive results

---

## Issue: Working Mode Voice Commands Not Direct
In working mode, voice commands for task operations required going through full intent recognition, adding unnecessary latency.

**Solution:**
Implemented direct command parsing in `receiveAudioHandle.py` when `current_mode=="working"`:
- Parse commands like "刷新/认领/完成" with optional ordinals
- Execute business logic directly and return response
- Fall back to intent recognition only for unmatched commands

---

## Issue: Meeting Summary Generation Latency
Meeting finalization was taking too long due to large token limits and unoptimized transcript processing.

**Solution:**
- Reduced default `max_tokens` to 800 (summary) and 400 (checkpoint)
- Implemented transcript trimming to 4000 characters (tail-priority)
- Added progress events (`prepare/llm_start/llm_done/done`) with timing metrics
- Enhanced logging with `LLM raw len=.., json len=.., sha8=.., elapsedMs=..`

---

## Issue: Handshake ID Parsing Logic Duplication
Device ID and client ID parsing logic was duplicated and scattered across `WebSocketServer._http_response` and `ConnectionHandler.handle_connection`.

**Solution:**
Created unified `parse_ids_from_handshake()` function that:
- Handles various websockets version attributes
- Normalizes IDs (strips quotes, lowercases, handles empty strings)
- Maintains `_handshake_cache` for fallback lookup
- Provides consistent error handling and logging

---

## Issue: Coding Insight Debounce Too High
Static debounce of 1200ms was causing unnecessary delays in generating coding insights.

**Solution:**
- Clamped debounce lower limit to ≥300ms
- Added immediate triggering for error/step/phase events
- Passed smaller `max_tokens=512` to LLM calls for faster response
- Maintained error/traceback immediate triggering

---

## Issue: Mode Switch Not Idempotent
Receiving the same `mode.start(X)` multiple times would trigger duplicate initialization logic.

**Solution:**
Added idempotency check - if already in the requested mode, immediately return `status:"ok"` and skip reinitialization of TTS prompts, timers, and snapshot broadcasts.

---

## Issue: Workflow Snapshot Timing Collisions  
Workflow snapshots triggered from register/hello/mode_start could arrive within milliseconds of each other, causing UI flicker.

**Solution:**
- Added 1.5s debounce for working mode start snapshots
- Tracked `_last_workflow_snapshot_ms` to prevent duplicate sends
- Unified logging format: `[Workflow] op=snapshot source=... group=... to=... count=...`

---

## Issue: Connection Timeout Without Warning
Connections would close after idle timeout without giving users a chance to keep the connection alive.

**Solution:**
- Send `timeout_warning` message 10 seconds before closing
- Allow any message received during buffer period to cancel closure via `reset_timeout()`
- Extended default idle threshold to 600s + 60s buffer

---

## Issue: Resource Cleanup Incomplete
Connection resources (tasks, threads, LLM instances) weren't being properly cleaned up on close.

**Solution:**
Enhanced `ConnectionHandler.close()` to:
- Cancel `timeout_task` and `coding_insight_task`
- Shutdown thread pool with `cancel_futures=True` (Python 3.9+)
- Clear `_llm_cache` dictionary
- Gracefully close asr/tts/llm resources if they implement `close()`
- Clean up MCP manager resources

---

## Issue: Thread Pool Excessive for Light Workloads
Default thread pool size was too large, causing unnecessary context switching and memory usage.

**Solution:**
- Reduced default `max_workers` to 2
- Made configurable via `meeting.threadpool_max_workers`
- Validated minimum of 1 worker to prevent invalid configuration

---

## Issue: Peer Category Validation Too Strict
Peer messages with uppercase or trailing whitespace in `category` field were being rejected.

**Solution:**
Normalized `category` with `strip().lower()` before validation to handle case variations and whitespace gracefully.

---

## Issue: VAD Silence Duration Calculation Wrong
VAD silence duration was being calculated incorrectly, showing negative or huge values in logs.

**Solution:**
Fixed calculation to use `now_ms - silence_start_ms` consistently across all VAD implementations, ensuring accurate silence duration reporting.

---

## Issue: Working Mode Not Listening After Entry
Entering working mode didn't automatically enable audio capture, requiring manual intervention.

**Solution:**
When entering working mode (`mode.start(working)`):
- Immediately send `{"type":"listen","state":"start","mode":"manual"}`  
- Set `client_listen_mode=manual`
- Update `_last_listen_event_ms` to ensure continued voice interaction

---

## Issue: OAuth2/JWT Authentication Missing
System lacked proper authentication mechanisms beyond static tokens.

**Solution:**
Implemented comprehensive auth in `backend/core/auth.py`:
- JWT validation with configurable algorithms, audience, issuer
- OAuth2 introspection support
- Mixed mode allowing multiple auth methods
- Device whitelist fallback (lowercase normalized)
- Preserved static token compatibility

---

## Issue: Offline Message Storage Not Persistent
Offline messages were stored in memory only, losing data on restart.

**Solution:**
- Created SQLite backend in `offline_store_sqlite.py` with indexed schema
- Modified `offline_queue.py` to prioritize SQLite, fallback to JSON
- Implemented per-device limit of 100 messages
- Added TTL expiration logic for old messages

---

## Issue: Giant handleTextMessage Function
`handleTextMessage` exceeded 500 lines with multiple nested responsibilities, making it hard to maintain.

**Solution:**
Proposed routing table refactor:
```python
HANDLERS = {
    "hello": handle_hello,
    "abort": handle_abort,
    "listen": handle_listen,
    "mode": handle_mode,
    # ... etc
}
```
Each handler maintains single responsibility with <100 lines per function.

---

## Issue: ASR State Machine Using Patches
Device listen start/stop and server VAD fallback were mixed with conditional branches and temporary states like `just_woken_up`.

**Solution:**
Proposed finite state machine with states: `Idle -> Listening -> Finalizing -> Idle`
- Device events only change state and update `_last_listen_event_ms`
- VAD provides fallback only when no device boundary received within timeout
- Removed scattered `have_voice` special cases and patches