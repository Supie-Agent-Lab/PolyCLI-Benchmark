# Pain Points Extracted from Block 7

## Issue: BlockingIOError During High-Frequency Logging
The system encountered BlockingIOError exceptions when handling high volumes of log output, particularly during coding mode operations.

**Solution:**
Implemented asynchronous logging with queue buffering and message truncation:
- Added `enqueue: true` to all logger sinks (console and file) to enable async queue processing
- Disabled `backtrace/diagnose` to reduce deep stack diagnostic overhead
- Implemented message truncation with `patcher` (max 2000 chars by default)
- Added per-message truncation (≤512 chars) for coding logs specifically
```python
# In logger.py
add(enqueue=True, backtrace=False, diagnose=False)
# Added patcher for truncation
patcher=lambda record: truncate_message(record, max_message_length)
```

---

## Issue: Second Meeting Session Failed to Initialize ASR
When entering meeting mode for the second time, the system would continuously push audio stream but ASR service wouldn't initialize, showing no "正在连接ASR服务..." logs and resulting in no speech recognition.

**Solution:**
Explicitly reset ASR resources when ending a meeting:
```python
# In textHandle.py during meeting.finalize and mode.end(meeting)
conn.asr.stop_ws_connection()
# If async close() is implemented, trigger it in background
```
This ensures the previous meeting's ASR streaming connection and internal state are properly released before the next session.

---

## Issue: Meeting Finalization Continued Receiving New Snippets
After triggering meeting finalization, the system would still accept and process new transcript/snippet messages, causing the meeting content to continue growing during summary generation.

**Solution:**
Implemented dual-layer protection:
1. Immediate stop of timers and set finalization flag:
```python
# On receiving finalize request
stop_meeting_timers()  # Stop transcript/summary periodic tasks
meeting_finalizing = True
```
2. Reject new snippets during finalization:
```python
# In handle_meeting_message()
if meeting_finalizing or meeting_finalized:
    return {"status": "ok"}  # Ignore new snippet/transcript
```

---

## Issue: Meeting Summary Missing Required Fields
Meeting summaries could have missing or incomplete fields, causing client-side parsing issues.

**Solution:**
Enforced strict 7-field structure with fallback values:
- Always include: `title/duration/bullets/decisions/actions/risks/nextSteps`
- When snippets exist: deduplicate and limit bullets (≤6), other fields (≤4 each)
- When no snippets: output empty skeleton with all fields present, duration based on `start→now`
- Duplicate finalize requests return cached result with `idempotent:true` flag

---

## Issue: Working Mode Voice Interaction Deadlock
In working mode, voice input was incorrectly intercepted, preventing any subsequent device-backend interaction and causing functional deadlock.

**Solution:**
Removed special handling for `working` mode in voice processing:
```python
# In receiveAudioHandle.py startToChat()
# Before: if mode in ['meeting', 'working']: return
# After: if mode == 'meeting': return  # Only meeting mode bypasses standard flow
```
Now only `meeting` mode bypasses standard dialogue flow, while `working` mode correctly enters intent recognition and command processing.

---

## Issue: Long Silent Periods Causing Premature Connection Closure
Connections were being closed too aggressively during silent periods, especially problematic in meeting/working modes.

**Solution:**
Implemented multi-layer timeout strategy:
1. Increased base timeout from 120s to 600s (10 minutes)
2. Mode-specific multipliers: 3x timeout for meeting/working modes
3. Pre-warning system: Send warning 15s before closure with grace period
4. Keepalive support: Accept `{"type":"ping"|"keepalive"}` to reset timeout
5. Cancellation on activity: Any message during grace period cancels closure

---

## Issue: Workflow Cross-Group Updates Being Rejected
System was rejecting workflow updates when task.groupKey differed from sender's default group, preventing legitimate cross-group task assignments.

**Solution:**
Allowed cross-group updates with targeted broadcasting:
```python
# Priority: task.groupKey > top-level groupKey > sender's default group
target_group = task.get('groupKey') or groupKey or device_group[:8]
# Track affected groups for precise broadcasting
changed_groups.add(target_group)
# Only broadcast to affected groups, not all online devices
```

---

## Issue: Excessive Meeting Detail Preview Data
Meeting detail API could return hundreds of lines in transcriptPreview, overwhelming clients.

**Solution:**
Added preview parameter with strict limits:
```python
# GET /supie/meetings/{sessionId}?preview=N
# N clamped to range 1..20, default 5
transcriptPreview = transcript_lines[:preview_count]
```

---

## Issue: VAD Silent Period Logging Incorrect
VAD silence logs were printing raw timestamps instead of actual silence duration, making diagnosis difficult.

**Solution:**
Fixed calculation to show actual duration:
```python
# Before: logger.info(f"silence detected: {silence_start_ms}")
# After: logger.info(f"silence detected: {now_ms - silence_start_ms}ms")
```

---

## Issue: Webhook Failures Affecting Main Business Flow
Webhook sending failures could potentially block or delay meeting finalization and storage.

**Solution:**
Implemented resilient webhook handling:
- 5s timeout with single retry (2-5s random backoff)
- Failures only log ERROR, never affect summary delivery or storage
- Added HMAC-SHA256 signature for security (`X-Meeting-Signature` header)
- Result counting for observability: `ok|retry_ok|fail` with body_len and sha256(8)

---

## Issue: Coding Mode Insights Showing Raw Logs Instead of Analysis
LLM-generated insights were returning raw log echoes rather than refined analysis.

**Solution:**
Enhanced prompt engineering and fallback logic:
- Strict system prompt forbidding raw log echo, requiring pure JSON output
- Event-based context injection with `lastEvent` for focused analysis
- Signal extraction for specific issues (failed tests, OOM, timeouts, build errors)
- Heuristic fallback when LLM returns empty/weak results
- Field completion ensuring risks/actions/nextSteps are never empty

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

## Issue: Workflow Snapshot Not Automatically Sent on Connection
Devices had to manually request workflow list after connecting, causing UI delays.

**Solution:**
Proactive snapshot broadcasting on key events:
- Send workflow.update snapshot immediately after device registration
- Send snapshot when entering working mode (`mode.start(working)`)
- Send snapshot after each hello message
- Group-based unicast ensuring devices only see their group's tasks