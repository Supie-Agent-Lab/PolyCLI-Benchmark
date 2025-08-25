# Pain Points from Block 7 - WebSocket Backend Development

## Issue: BlockingIOError with Long Log Messages
The logging system was experiencing BlockingIOError when writing long messages or exception stacks to console/file, causing the main process to block.

**Solution:**
Implemented asynchronous logging with message truncation:
- Enabled `enqueue: true` for both console and file sinks to use async queue
- Disabled `backtrace/diagnose` to reduce deep stack diagnostic overhead  
- Added patcher with `max_message_length=2000` for safe truncation
- Created `truncate_for_log()` utility for pre-truncation at entry points

---

## Issue: Second Meeting Session ASR Not Initializing
When entering meeting mode for the second time, the device would continue streaming audio but ASR service wouldn't initialize, resulting in no speech recognition. Logs were missing "正在连接ASR服务..." messages.

**Solution:**
Added explicit ASR resource cleanup on meeting end:
- Call `conn.asr.stop_ws_connection()` in both `meeting.finalize` and `mode.end(meeting)` flows
- Trigger async `close()` if implemented to release ASR streaming connections and internal state
- Ensures clean state for next meeting session

---

## Issue: Meeting Finalize Delay and Continued Updates
After triggering meeting finalize, devices would still receive transcript/snippet updates during summary generation, causing UI confusion with "ending but still adding content" state.

**Solution:**
Implemented immediate acknowledgment and boundary enforcement:
- Send immediate confirmation packet `{"type":"meeting","phase":"finalize"}` for UI to show "总结中..."
- Immediately call `stop_meeting_timers()` to halt transcript/snippet push tasks
- Set `meeting_finalizing=true` flag to reject new snippets during finalization
- Double-insurance: Check flags at `handle_meeting_message()` entry to drop post-finalize messages

---

## Issue: Working Mode Voice Interaction Dead Lock
In working mode (`working`), voice input was incorrectly intercepted, preventing any subsequent device-backend interaction and causing functional deadlock.

**Solution:**
Fixed voice routing in working mode:
- Removed special handling of `working` mode in `startToChat` function
- Only `meeting` mode now bypasses standard conversation flow
- Working mode voice input correctly enters intent recognition and command processing
- Added proactive `listen start` command after `mode.start(working)` to ensure immediate listening state

---

## Issue: Idle Connection Premature Disconnection
Connections were being closed too aggressively during normal pauses in conversation, especially problematic in meeting/working modes with long silent periods.

**Solution:**
Implemented multi-layer timeout strategy:
- Increased default timeout from 120s to 600s (+ 60s buffer = 660s total)
- Mode-specific multipliers: 3x timeout for meeting/working modes
- Added keepalive support for `{"type":"ping"|"keepalive"}` messages to reset timeout
- Pre-warning system: Send warning 15s before timeout with grace period for recovery
- Added `system.timeout_warning` with 10s buffer for last-chance activity

---

## Issue: Webhook Failures Affecting Main Business Flow
Webhook delivery failures could potentially impact meeting summary generation and archival processes.

**Solution:**
Implemented resilient webhook delivery:
- 5s timeout with single retry using random backoff (2-5s)
- Failures only log ERROR without affecting summary/archive flow
- Added HMAC-SHA256 signature verification via `X-Meeting-Signature` header
- Observable metrics: ok|retry_ok|fail counts with body_len and sha256(8) for diagnostics

---

## Issue: Index and Shard Files Accumulation
Meeting files and segment shards were accumulating indefinitely, causing storage issues.

**Solution:**
Implemented automatic cleanup strategy:
- Maintain only latest 100 meetings in `index.json`
- Clean up expired `<sessionId>.json` files outside retention set
- Remove orphaned shard files from `meetings/segments/` directory
- Fault-tolerant cleanup that doesn't block main flow

---

## Issue: Concurrent/Duplicate Finalize Requests
Multiple finalize requests could cause duplicate processing and inconsistent state.

**Solution:**
Implemented idempotent finalize handling:
- First finalize generates summary, subsequent ones reuse cached result
- Return `idempotent:true` flag for duplicate requests
- Atomic state management with `meeting_finalizing` and `meeting_finalized` flags

---

## Issue: Cross-Group Task Updates Rejected
Workflow tasks couldn't be assigned across device groups, limiting task distribution capabilities.

**Solution:**
Enabled cross-group updates with controlled broadcasting:
- Priority chain: `task.groupKey` > top-level `groupKey` > sender's default group
- Allow cross-group upsert when task contains explicit `groupKey`
- Track `changed_groups` for targeted broadcasting only to affected groups
- Sender receives their own group snapshot for consistency

---

## Issue: VAD Silent Period Logging Inaccuracy
VAD silence logs were printing raw timestamps instead of actual silence duration, hindering diagnostics.

**Solution:**
Fixed silence duration calculation:
- Correctly compute `now_ms - silence_start_ms` for actual duration
- Updated log format to show meaningful silence period in milliseconds

---

## Issue: Meeting Transcript Push Latency
Default 12-second transcript push interval was too slow for real-time collaboration needs.

**Solution:**
Optimized push timing with configurable intervals:
- Changed check cycle to 0.5s for faster response
- Default `transcript_push_interval_ms` reduced to 5000ms
- Configurable range clamped to 3000-15000ms
- Maintains "fixed for current cycle, hot-reload for next" strategy

---

## Issue: Configuration Hot Reload Not Affecting Active Connections
After updating configuration via `update_config`, existing connections continued using cached LLM instances and old settings.

**Solution:**
Implemented cache invalidation on config update:
- Clear `_llm_cache` on connection close
- Iterate all active connections to clear caches after successful `update_config`
- Meeting transcript push intervals take effect on next cycle with logging

---

## Issue: Coding Mode Insights Quality
Raw log echoing in insights instead of actionable intelligence, making the feature less useful.

**Solution:**
Enhanced insight generation with signal extraction:
- Strict prompt engineering to forbid raw log echoing
- Extract signals: failed tests, import errors, OOM, timeouts, network issues, build errors, lint warnings
- Generate specific risks/actions/nextSteps based on signals
- Inject context stats: errorCount, warnCount, lastStep, buildSuccess, testsFailed
- Heuristic fallback for weak LLM responses
- Field completion with minimal viable suggestions when empty

---

## Issue: Device-Side Boundary Updates Not Refreshing
In manual listen mode, missing device boundaries caused prolonged silence windows and empty recognition results.

**Solution:**
Implemented boundary fallback with refresh:
- Track `_last_listen_event_ms` for device listen start/stop events
- Fallback to server VAD after `meeting.manual_listen_fallback_ms` (default 5000ms) without boundaries
- Refresh timestamp on boundary receipt for accurate segment detection
- 300ms debounce on listen start/stop to reduce boundary jitter

---

## Issue: Atomic File Writing Corruption Risk
Potential for corrupted JSON files during crashes or interruptions.

**Solution:**
Implemented atomic write operations:
- `_safe_write_json()` using temp file + `os.replace` for atomic replacement
- `_safe_append_line()` for safe log appending
- Applied to main files, `index.json`, and shard files
- Graceful loading with extended field preservation