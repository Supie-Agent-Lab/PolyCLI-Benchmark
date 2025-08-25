# Consolidated Pain Points from Block 7 - Backend System Development

## Critical Issue: BlockingIOError in Logging System
High-frequency logging operations were causing BlockingIOError exceptions, particularly during coding mode operations with long messages or exception stacks, blocking the main process flow and causing system instability.

**Solution:**
Implemented comprehensive asynchronous logging with queue-based output and message truncation:
```python
# backend/config/logger.py
# Added enqueue=True for async queue processing on console and file sinks
# Added patcher to truncate messages to max_message_length=2000
# Disabled backtrace/diagnose to reduce deep stack diagnostic overhead
# Created truncate_for_log() utility for pre-truncation at entry points
# Per-message truncation (≤512 chars) for coding logs specifically
```

---

## Critical Issue: Second Meeting Session ASR Not Initializing
When entering meeting mode for a second time, the ASR service wasn't reconnecting properly. The device would continue streaming audio but no "正在连接ASR服务..." message appeared in logs and no speech recognition occurred despite continuous audio streaming.

**Solution:**
Explicitly reset ASR connection and resources when meeting ends:
```python
# backend/core/handle/textHandle.py
# In both meeting.finalize and mode.end(meeting) flows:
conn.asr.stop_ws_connection()  # Explicitly close ASR stream
# If async close() is implemented, trigger it in background
# Ensures clean state and proper resource release for next meeting session
```

---

## Critical Issue: Meeting Finalization Still Accepting New Content
After triggering meeting finalization, new transcript/snippet messages were still being processed and added, causing the meeting content to continue growing during summary generation and creating UI confusion with "ending but still adding content" state.

**Solution:**
Implemented triple-layer protection with immediate acknowledgment:
```python
# backend/core/handle/textHandle.py
# 1. Send immediate ACK: {"type":"meeting","phase":"finalize"} for UI feedback
# 2. Immediately set meeting_finalizing=true on finalize request
# 3. Stop all meeting timers (transcript/summary push)

# backend/core/handle/meeting_handle.py
# In handle_meeting_message() top:
if meeting_finalizing or meeting_finalized:
    return {"status": "ok"}  # Ignore new snippets/transcripts
```

---

## Critical Issue: Working Mode Voice Interaction Complete Deadlock
In working mode, voice input was being incorrectly intercepted, causing a functional deadlock where devices couldn't interact with the backend at all, preventing any subsequent device-backend interaction.

**Solution:**
Fixed voice routing and added proactive initialization:
```python
# backend/core/handle/receiveAudioHandle.py
# Removed working mode from bypass conditions in startToChat
# Before: if mode in ['meeting', 'working']: return
# After: if mode == 'meeting': return  # Only meeting mode bypasses standard flow
# Working mode voice input now correctly enters intent recognition

# backend/core/handle/textHandle.py
# On mode.start(working), immediately send:
{"type": "listen", "action": "start"}  # Ensures device enters listening state
```

---

## Major Issue: Idle Connection Timeout Too Aggressive
Connections were being closed after just 2 minutes of silence, interrupting legitimate long pauses in meetings or working sessions. This was especially problematic during normal conversation pauses.

**Solution:**
Implemented comprehensive multi-layer timeout strategy with mode awareness:
```python
# backend/core/connection.py
# Default timeout raised from 120s to 600s (10 minutes) + 60s buffer
# Meeting/working modes get 3x multiplier (30+ minutes)
# Added grace period warning 15s before closing
# Support for keepalive/ping messages: {"type":"ping"|"keepalive"} to reset timeout
# Added system.timeout_warning with 10s buffer for last-chance activity
# Cancellation on activity: Any message during grace period cancels closure
```

---

## Major Issue: Concurrent Finalize Requests Causing Duplicate Processing
Multiple finalize requests could trigger parallel summary generation, causing race conditions, duplicate work, and inconsistent state.

**Solution:**
Implemented idempotent finalization with atomic state management:
```python
# First finalize generates summary
# Subsequent requests return cached result with idempotent:true flag
# Atomic state management with meeting_finalizing and meeting_finalized flags
# Immediate ACK sent before processing: {"type":"meeting","phase":"finalize"}
```

---

## Major Issue: Meeting Summary Missing Required Fields Causing Client Crashes
Meeting summaries could have missing or incomplete fields (decisions, risks, etc.), causing client-side parsing errors and crashes.

**Solution:**
Enforced strict 7-field schema with comprehensive fallbacks:
```python
# Always return: title/duration/bullets/decisions/actions/risks/nextSteps
# When snippets exist: deduplicate and limit bullets (≤6), other fields (≤4 each)
# When no snippets: output empty skeleton with all fields present
# Empty fields default to [] not null
# Duration minimum 5000ms for short meetings, based on start→now
# Duplicate finalize requests return cached result with idempotent:true flag
```

---

## Major Issue: Webhook Requests Missing Security and Reliability
Webhooks lacked signature verification for security and had no retry mechanism for transient failures, potentially affecting meeting finalization flow.

**Solution:**
Added HMAC-SHA256 signing and resilient delivery with exponential backoff:
```python
# backend/core/handle/meeting_handle.py
# Added X-Meeting-Signature header with HMAC-SHA256(secret, body)
# 5s timeout with one retry after 2-5s random backoff
# Failures logged as ERROR but don't block meeting flow or summary/archive
# Config: meeting.webhook.secret for signing key
# Observable metrics: ok|retry_ok|fail counts with body_len and sha256(8)
```

---

## Issue: Index and Shard Files Growing Unbounded
Meeting files and segments were never cleaned up, causing storage to grow indefinitely and accumulate orphaned files.

**Solution:**
Implemented automatic cleanup strategy with fault tolerance:
```python
# Keep only most recent 100 meetings in index.json
# Clean up main files: <sessionId>.json not in retention set
# Clean up shards: meetings/segments/<sessionId>_shard_K.json
# Remove orphaned shard files from meetings/segments/ directory
# Cleanup is fault-tolerant and non-blocking
```

---

## Issue: Config Updates Not Taking Effect in Active Connections
Configuration changes required reconnection to take effect, with existing connections continuing to use cached LLM instances and old settings, causing confusion and requiring manual restarts.

**Solution:**
Implemented cache invalidation and hot reload:
```python
# backend/core/websocket_server.py
# On update_config success:
for conn in active_connections:
    conn._llm_cache.clear()  # Clear cached LLM instances
# Clear _llm_cache on connection close
# Transcript push interval takes effect next cycle
# Log shows: "next interval=...ms" for transparency
```

---

## Issue: Workflow Cross-Group Operations Limited
Workflow updates weren't broadcasting properly to other devices in the same group, and couldn't assign tasks to devices in different groups, limiting workflow flexibility.

**Solution:**
Implemented comprehensive group-based broadcasting with cross-group support:
```python
# backend/core/handle/workflow_handle.py
# Device grouping by device-id[:8] prefix
# On registration/mode entry: auto-push workflow snapshot
# Priority: task.groupKey > top-level groupKey > sender's default
# Allow cross-group upsert when task contains explicit groupKey
# Track changed_groups for targeted broadcasting
# Only affected groups receive updates
# Added idempotent handling for assign/complete operations
# Group-based unicast ensuring devices only see their group's tasks
```

---

## Issue: Coding Mode Raw Logs Being Sent as Insights
LLM was returning raw log lines instead of processed insights, providing no actionable intelligence and making the feature useless.

**Solution:**
Enhanced prompt engineering with signal extraction and fallback logic:
```python
# backend/core/handle/coding_handle.py
# Extract signals: test failures, import errors, OOM, timeouts, network issues
# Extract signals: build errors, lint warnings
# Strict JSON-only output, forbid raw log echoing
# Event-based context injection with lastEvent for focused analysis
# Context stats: errorCount, warnCount, lastStep, buildSuccess, testsFailed
# Heuristic fallback when LLM returns weak results
# Field completion ensuring risks/actions/nextSteps are never empty
# Generate specific risks/actions/nextSteps based on signals
```

---

## Issue: VAD Silent Period Logging Shows Raw Timestamps
VAD (Voice Activity Detection) logs were printing raw timestamps rather than actual silence duration, making debugging and diagnostics difficult.

**Solution:**
Fixed the calculation to show actual silence duration:
```python
# backend/core/providers/vad/silero.py
# Changed from logging raw timestamp to:
silence_duration = now_ms - silence_start_ms
# Now logs actual silence duration in milliseconds
# Updated log format: f"silence detected: {silence_duration}ms"
```

---

## Issue: Device-Side Boundary Updates and Listen Event Jitter
In manual listen mode, missing device boundaries caused prolonged silence windows and empty recognition results. Rapid start/stop events were causing audio boundary instability.

**Solution:**
Implemented boundary fallback with debouncing:
```python
# Track _last_listen_event_ms for device listen start/stop events
# Fallback to server VAD after meeting.manual_listen_fallback_ms (default 5000ms)
# Refresh timestamp on boundary receipt for accurate segment detection
# 300ms debounce on listen start/stop to reduce boundary jitter
# Prevents rapid toggling from causing instability
# Smooths out network jitter effects
```

---

## Issue: Meeting Detail API Returning Excessive Preview Data
The meeting detail endpoint was returning up to 394 lines of preview in transcriptPreview, overwhelming clients with unnecessary data.

**Solution:**
Implemented preview limiting with configurable cap:
```python
# backend/core/http_server.py
# GET /supie/meetings/{sessionId}?preview=N
# Default 5 items, max 20, auto-clamp to valid range [1..20]
# Strict truncation of transcriptPreview array
transcriptPreview = transcript_lines[:preview_count]
```

---

## Issue: Meeting Transcript Push Latency
Default 12-second transcript push interval was too slow for real-time collaboration needs.

**Solution:**
Optimized push timing with configurable intervals:
```python
# Changed check cycle to 0.5s for faster response
# Default transcript_push_interval_ms reduced to 5000ms
# Configurable range clamped to 3000-15000ms
# Maintains "fixed for current cycle, hot-reload for next" strategy
```

---

## Issue: Device Reconnection Causing Voice Transcription Interruption
When devices reconnected with same ID, immediate disconnection of old connection caused voice transcription to break.

**Solution:**
Implemented dual-channel transition:
```python
# In websocket_server.py
# Delay old connection closure by ~1.5s
# Allow dual-channel period ≤2s for smooth transition
# Enable ping/pong keepalive (ping_interval=20, ping_timeout=50)
```

---

## Issue: Old Config Update Format Causing Unknown Type Errors
Legacy `type=config_update` messages were falling into unknown type handler, generating noise in logs.

**Solution:**
Added compatibility handler for legacy format:
```python
# backend/core/handle/textHandle.py
# Recognize type=config_update
# Return {type:"config_update",status:"ok",noop:true}
# Log as informational, not error
```

---

## Issue: Atomic File Writes Not Guaranteed
File writes could be corrupted if process was killed mid-write, causing potential data loss and corrupted JSON files.

**Solution:**
Implemented atomic write operations with safety guarantees:
```python
# backend/core/handle/meeting_handle.py
# _safe_write_json() using temp file + os.replace for atomic replacement
# _safe_append_line() for safe log appending
# Write to temp file first
# Use os.replace() for atomic swap
# Applies to: index.json, main files, shards
# metrics.log uses safe append mode
# Graceful loading with extended field preservation
```