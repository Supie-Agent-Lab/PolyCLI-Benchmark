# Pain Points Extracted from Block 8

## Issue: Working Mode Lost Audio After First Interaction
When entering working mode, the device could only process one voice interaction before becoming unresponsive to further voice commands.

**Solution:**
Upon receiving `{"type":"mode","state":"start","mode":"working"}`, immediately send `{"type":"listen","state":"start","mode":"manual"}` and set `client_listen_mode=manual` with `_last_listen_event_ms` refresh to ensure continuous voice interaction capability. Added in `backend/core/handle/textHandle.py`.

---

## Issue: Workflow Snapshot Jitter on Mode Start
When starting working mode, multiple workflow snapshots were being sent in rapid succession, causing UI flickering.

**Solution:**
Added 1.5s debounce for `workflow.update` snapshots triggered by `mode.start(working)` to avoid overlapping with registration/hello snapshots. Tracks `_last_workflow_snapshot_ms` to prevent duplicate sends within 1500ms window.

---

## Issue: BlockingIOError from Excessive Logging
Long JSON logs from coding insights were causing `BlockingIOError` and blocking the application.

**Solution:**
1. Output only statistical summary lines instead of full JSON: `[Coding Insight] final=.. insights=.. risks=.. actions=.. nextSteps=.. jsonSHA=.. elapsedMs=..`
2. Enable `patcher=_build_trunc_patcher()` for console and file sinks with `log.max_message_length` (default 2000) truncation
3. Keep `enqueue=True`, `rotation=10MB`, `retention=30 days` for async handling

---

## Issue: LLM Instance Duplication Across Connections
Multiple connections were creating duplicate LLM instances, wasting memory and causing initialization delays.

**Solution:**
Implemented shared LLM registry in `WebSocketServer` with `get_or_create_llm(alias, overrides)` using fingerprint keys (`alias::json(overrides)`). `ConnectionHandler.get_llm_for(purpose)` now delegates to server's shared factory, ensuring single instance per configuration.

---

## Issue: Meeting Finalize Race Conditions
Concurrent finalize requests were causing duplicate summary generation and processing errors.

**Solution:**
Added connection-level mutex lock `meeting_finalize_lock = asyncio.Lock()`. First finalize computes summary, subsequent calls return cached result with `idempotent:true` flag. All send/broadcast paths wrapped with connection close exception handling.

---

## Issue: Delayed ASR Final Text on Listen Stop
When `listen.stop` was received, ASR would take too long to produce final transcription, causing text loss.

**Solution:**
On `listen.stop`, call `conn.asr.on_client_listen_stop(conn)` to send "last frame" marker (`generate_last_audio_default_header()` + empty payload) to prompt immediate definitive results from streaming ASR. Added to `backend/core/providers/asr/doubao_stream.py`.

---

## Issue: Device ID Parsing Fragility
Device ID extraction from websocket handshake was scattered and brittle across different websockets library versions.

**Solution:**
Created unified `parse_ids_from_handshake(path_or_conn)` function that:
1. Tries multiple attribute names (`path`, `request_uri`, `raw_path`, etc.)
2. Normalizes IDs (strip quotes, lowercase, handle empty)
3. Maintains `_handshake_cache` by connection object ID for fallback
4. Returns tuple `(device_id, client_id, raw_path)`

---

## Issue: Async Task Scheduling Without Event Loop
Creating tasks before event loop was running caused "no running event loop" errors.

**Solution:**
Bind `self.loop = asyncio.get_running_loop()` in `handle_connection()` entry point instead of constructor. Use `asyncio.run_coroutine_threadsafe(..., self.loop)` for cross-thread scheduling.

---

## Issue: Delayed Snapshot Task Creation Error
`asyncio.create_task((asyncio.sleep(...),))` was incorrectly passing tuple instead of coroutine.

**Solution:**
Changed to proper `_delayed_snapshot()` coroutine:
```python
async def _delayed_snapshot():
    await asyncio.sleep(delay_ms/1000.0)
    await _send_snapshot()
asyncio.create_task(_delayed_snapshot())
```

---

## Issue: Inconsistent Message Sending Methods
Mixed use of `websocket.send_json()`, `websocket.send()`, and string serialization causing errors and duplication.

**Solution:**
Added unified `ConnectionHandler.send_json()/send_text()` methods that:
1. Handle `send_json` missing with string fallback
2. Centralize exception handling
3. Ensure consistent JSON serialization with `ensure_ascii=False`

---

## Issue: Duplicate Heartbeat Processing
Heartbeat (`ping`/`keepalive`) messages were being processed in multiple places causing redundancy.

**Solution:**
Removed duplicate handling from `handleTextMessage`, keeping only the `_route_message` interception with immediate `pong` response and timeout reset.

---

## Issue: Resource Leaks on Connection Close
Tasks, threads, and LLM instances weren't being properly cleaned up on connection termination.

**Solution:**
Enhanced `ConnectionHandler.close()` to:
1. Cancel `timeout_task` and `coding_insight_task`
2. Call `shutdown(cancel_futures=True)` on thread pool
3. Gracefully close `asr/tts/llm` if they implement `close()`
4. Clear `_llm_cache` dictionary

---

## Issue: Meeting LLM Token Limits Causing Truncation
Long meeting transcripts were being truncated mid-summary due to token limits.

**Solution:**
1. Reduced default `max_tokens`: 800 for summary, 400 for checkpoint
2. Set `summary_transcript_max_chars` to 4000 (tail-priority truncation)
3. Added LLM logging with `raw len`, `json len`, `sha8` for truncation diagnosis

---

## Issue: Peer Category Validation Too Strict
Messages with category field having different case or trailing whitespace were being rejected.

**Solution:**
Apply `strip().lower()` normalization to `category` field before validation to handle case variations and whitespace.

---

## Issue: Coding Insight Debounce Too High
Static 1200ms debounce was causing noticeable delays in insight generation.

**Solution:**
1. Clamp debounce minimum to ≥300ms
2. Pass smaller `max_tokens=512` to LLM for faster responses
3. Keep immediate trigger for error/step/phase events

---

## Issue: Mode Switch Idempotency Missing
Repeated `mode.start(X)` messages were triggering duplicate initialization logic.

**Solution:**
Check if already in requested mode; if so, return `status:"ok"` immediately and skip re-initialization (TTS prompts, timer starts, snapshot broadcasts).

---

## Issue: Workflow Owner Missing Friendly Names
Task assignments showed raw device IDs instead of readable names.

**Solution:**
Added `_resolve_device_alias_from_config()` to map device IDs to friendly aliases from `workflow.device_alias` or top-level `device_alias` config. Default to `alias|device-id` format when not explicitly provided.

---

## Issue: Working Mode Direct Commands Not Working
Voice commands like "refresh tasks" or "complete task" required full LLM processing in working mode.

**Solution:**
Added direct command parsing in working mode for:
- "认领任务/assign to me" → `intent: "assign"`
- "完成任务/mark done" → `intent: "complete"`  
- "刷新列表/refresh" → `intent: "refresh"`
These bypass LLM and directly execute workflow operations.

---

## Issue: SQLite Offline Queue Performance
JSON file-based offline queue couldn't handle 50 QPS concurrent operations.

**Solution:**
Implemented SQLite storage with:
- Table: `offline_queue(device_id TEXT, payload TEXT, queued_at INTEGER, ttl_ms INTEGER)`
- Indexes for fast lookup
- Fallback to JSON on SQLite failure
- 100 message per-device limit with TTL expiration

---

## Issue: Meeting Transcript Real-time Visibility
Meeting transcriptions weren't visible in real-time, only appearing in final summary.

**Solution:**
After each `handle_voice_stop()` STT result, immediately broadcast:
```json
{"type":"audio","event":"transcription","text":"...","ts":...,"session_id":"..."}
```
while preserving existing `meeting.snippet` injection for compatibility.

---

## Issue: Thread Pool Size Excessive
Default thread pool with too many workers causing context switching overhead.

**Solution:**
Reduced default `ThreadPoolExecutor` workers to 2, configurable via `meeting.threadpool_max_workers`. This reduced memory usage and context switching while maintaining performance.

---

## Issue: Schema Validation Error Messages Unhelpful
Schema validation failures didn't indicate which fields were missing or invalid.

**Solution:**
Enhanced error messages to include specific missing fields:
- `missing: title,duration` for missing required fields
- `items must be array of {tag,text}: missing one of tag/text` for array validation
This allows frontend to make minimal corrections.

---

## Issue: VAD Silence Duration Calculation Error
VAD silence duration was being calculated incorrectly, showing wrong idle times.

**Solution:**
Fixed calculation to use `now_ms - silence_start_ms` consistently across VAD implementations. This provides accurate silence duration for timeout decisions.

---

## Issue: Coding Prompt Returning Raw Logs
LLM was echoing back raw log content instead of generating insights.

**Solution:**
Rewrote system prompt to strictly enforce:
- Output only JSON, no code fences or explanatory text
- Fixed four keys: `{insights, risks, actions, nextSteps}`
- Language consistency and deduplication
- Explicit prohibition of raw log/stack echoing
Still preserve bracket extraction + `json.loads` + key fallback for parsing resilience.