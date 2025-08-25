# Pain Points from Block 7 - Backend System Development

## Issue: BlockingIOError in Logging System
High-frequency logging operations were causing BlockingIOError exceptions, blocking the main process flow and causing system instability.

**Solution:**
Implemented asynchronous logging with queue-based output and message truncation:
```python
# backend/config/logger.py
# Added enqueue=True for async logging
# Added patcher to truncate messages to max_message_length=2000
# Disabled backtrace/diagnose to reduce diagnostic overhead
```

---

## Issue: Second Meeting Session ASR Not Initializing
When entering meeting mode for a second time, the ASR service wasn't reconnecting properly. Logs showed no "正在连接ASR服务..." message and no recognition occurred despite continuous audio streaming.

**Solution:**
Explicitly reset ASR connection when meeting ends:
```python
# backend/core/handle/textHandle.py
# In meeting.finalize and mode.end(meeting) flow:
conn.asr.stop_ws_connection()  # Explicitly close ASR stream
# If async close() is implemented, trigger it in background
```

---

## Issue: VAD Silent Period Logging Shows Raw Timestamps Instead of Duration
VAD (Voice Activity Detection) logs were printing raw timestamps rather than actual silence duration, making debugging difficult.

**Solution:**
Fixed the calculation to show actual silence duration:
```python
# backend/core/providers/vad/silero.py
# Changed from logging raw timestamp to:
silence_duration = now_ms - silence_start_ms
# Now logs actual silence duration in milliseconds
```

---

## Issue: Working Mode Voice Interaction Completely Blocked
In working mode, voice input was being incorrectly intercepted, causing a functional deadlock where devices couldn't interact with the backend at all.

**Solution:**
Removed special handling for working mode that was blocking voice processing:
```python
# backend/core/handle/receiveAudioHandle.py
# Removed working mode from bypass conditions in startToChat
# Only meeting mode now bypasses standard dialogue flow
# Working mode voice input now correctly enters intent recognition
```

---

## Issue: Meeting Finalizing Still Accepting New Snippets
After triggering meeting finalization, new transcript snippets were still being processed and added, causing the meeting to continue growing during summary generation.

**Solution:**
Implemented double safeguards to block new content during finalization:
```python
# backend/core/handle/textHandle.py
# 1. Immediately set meeting_finalizing=true on finalize request
# 2. Stop all meeting timers (transcript/summary push)

# backend/core/handle/meeting_handle.py
# In handle_meeting_message() top:
if meeting_finalizing or meeting_finalized:
    return {"status": "ok"}  # Ignore new snippets
```

---

## Issue: Concurrent Finalize Requests Causing Duplicate Processing
Multiple finalize requests could trigger parallel summary generation, causing race conditions and duplicate work.

**Solution:**
Implemented idempotent finalization with immediate acknowledgment:
```python
# First finalize generates summary
# Subsequent requests return cached result with idempotent:true flag
# Immediate ACK sent before processing: {"type":"meeting","phase":"finalize"}
```

---

## Issue: Idle Connection Timeout Too Aggressive
Connections were being closed after just 2 minutes of silence, interrupting legitimate long pauses in meetings or working sessions.

**Solution:**
Implemented multi-layer timeout strategy with mode awareness:
```python
# backend/core/connection.py
# Default timeout raised from 120s to 600s (10 minutes)
# Meeting/working modes get 3x multiplier (30+ minutes)
# Added grace period warning 15s before closing
# Support for keepalive/ping messages to reset timeout
```

---

## Issue: Webhook Requests Missing Authentication and Retry Logic
Webhooks lacked signature verification for security and had no retry mechanism for transient failures.

**Solution:**
Added HMAC-SHA256 signing and exponential backoff retry:
```python
# backend/core/handle/meeting_handle.py
# Added X-Meeting-Signature header with HMAC-SHA256(secret, body)
# 5s timeout with one retry after 2-5s random backoff
# Failures logged but don't block meeting flow
# Config: meeting.webhook.secret for signing key
```

---

## Issue: Index and Shard Files Growing Unbounded
Meeting files and segments were never cleaned up, causing storage to grow indefinitely.

**Solution:**
Implemented automatic cleanup strategy:
```python
# Keep only most recent 100 meetings in index.json
# Clean up main files: <sessionId>.json not in retention set
# Clean up shards: meetings/segments/<sessionId>_shard_K.json
# Cleanup is fault-tolerant and non-blocking
```

---

## Issue: Config Updates Not Taking Effect in Active Connections
Configuration changes required reconnection to take effect, causing confusion and requiring manual restarts.

**Solution:**
Implemented cache clearing on config update:
```python
# backend/core/websocket_server.py
# On update_config success:
for conn in active_connections:
    conn._llm_cache.clear()  # Clear cached LLM instances
# Transcript push interval takes effect next cycle
# Log shows: "next interval=...ms" for transparency
```

---

## Issue: Workflow Tasks Not Syncing Across Devices
Workflow updates weren't broadcasting properly to other devices in the same group.

**Solution:**
Implemented group-based broadcasting with snapshot push:
```python
# Device grouping by device-id[:8] prefix
# On registration/mode entry: auto-push workflow snapshot
# Updates broadcast only to same-group devices
# Added idempotent handling for assign/complete operations
```

---

## Issue: Cross-Group Task Assignment Blocked
Couldn't assign tasks to devices in different groups, limiting workflow flexibility.

**Solution:**
Allowed cross-group updates with explicit groupKey:
```python
# backend/core/handle/workflow_handle.py
# Priority: task.groupKey > top-level groupKey > sender's default
# Record changed_groups for targeted broadcasting
# Only affected groups receive updates
```

---

## Issue: Empty Summary Fields Causing Client Parsing Errors
Missing fields in meeting summaries (decisions, risks, etc.) caused client-side crashes.

**Solution:**
Enforced strict schema with empty array fallbacks:
```python
# Always return 7 fields: title/duration/bullets/decisions/actions/risks/nextSteps
# Empty fields default to [] not null
# Bullets limited to 6, other arrays to 4 items
# Duration minimum 5000ms for short meetings
```

---

## Issue: Coding Mode Raw Logs Being Sent as Insights
LLM was returning raw log lines instead of processed insights, providing no value.

**Solution:**
Enhanced prompt engineering and signal extraction:
```python
# backend/core/handle/coding_handle.py
# Extract signals: test failures, import errors, OOM, timeouts
# Strict JSON-only output, no log echoing
# Heuristic fallback when LLM returns weak results
# Auto-populate risks/actions/nextSteps if empty
```

---

## Issue: Device Not Starting Audio Capture in Working Mode
After entering working mode, devices weren't automatically starting audio capture, breaking interaction.

**Solution:**
Server actively triggers listening after mode switch:
```python
# backend/core/handle/textHandle.py
# On mode.start(working), immediately send:
{"type": "listen", "action": "start"}
# Ensures device enters listening state
```

---

## Issue: Listen Start/Stop Events Causing Boundary Jitter
Rapid start/stop events were causing audio boundary instability and recognition issues.

**Solution:**
Implemented 300ms debouncing for boundary events:
```python
# Minimum 300ms between listen start/stop transitions
# Prevents rapid toggling from causing instability
# Smooths out network jitter effects
```

---

## Issue: Old Config Update Format Causing Unknown Type Errors
Legacy `type=config_update` messages were falling into unknown type handler, generating noise.

**Solution:**
Added compatibility handler for legacy format:
```python
# backend/core/handle/textHandle.py
# Recognize type=config_update
# Return {type:"config_update",status:"ok",noop:true}
# Log as informational, not error
```

---

## Issue: Detail API Returning Excessive Preview Data
The meeting detail endpoint was returning up to 394 lines of preview, overwhelming clients.

**Solution:**
Implemented preview limiting with configurable cap:
```python
# backend/core/http_server.py
# GET /supie/meetings/{sessionId}?preview=N
# Default 5 items, max 20, auto-clamp to valid range
# Strict truncation of transcriptPreview array
```

---

## Issue: Atomic File Writes Not Guaranteed
File writes could be corrupted if process was killed mid-write, causing data loss.

**Solution:**
Implemented atomic write operations:
```python
# backend/core/handle/meeting_handle.py
# Write to temp file first
# Use os.replace() for atomic swap
# Applies to: index.json, main files, shards
# metrics.log uses safe append mode
```