# Merged Pain Points Analysis - Block 5

## Critical Issues (System Failures)

### Issue: Duplicate Device ID Connection Handling
When a device with the same ID tried to reconnect (e.g., after network interruption), the system would reject the new connection because the old connection was still registered, even though it was effectively dead. This caused issues during network interruptions.

**Solution:**
Modified `backend/core/websocket_server.py` and `backend/core/connection.py` to implement a "kick old, welcome new" strategy:
- When duplicate device ID is detected, proactively disconnect the old connection
- Send system message to old connection: `{"type": "system", "message": "设备被新连接替换，即将断开"}`
- Accept the new connection immediately after closing old one
- Added exception handling to ensure new connection succeeds even if old connection cleanup fails

---

### Issue: LLM Service Unavailability Causing Meeting Summary Failures
When LLM service was unavailable or failed, the entire meeting finalization process would fail, leaving users without any summary or record of the meeting.

**Solution:**
Enhanced `backend/core/handle/meeting_handle.py` with fallback mechanism:
- Added LLM availability check before invocation: check if `conn.llm` exists
- When LLM unavailable, generate default summary: `["会议内容已记录", "LLM服务暂时不可用", "请稍后重试"]`
- Fixed indentation issues in exception handling to ensure proper fallback
- Enhanced logging to capture raw LLM responses for debugging

---

### Issue: Opus Audio Decoder Stream Corruption
The Opus decoder was encountering "corrupted stream" errors causing audio processing failures and VAD detection issues.

**Solution:**
Enhanced error recovery in `backend/core/providers/vad/silero.py`:
- Added packet statistics logging every 100 packets
- Implemented corrupted stream detection with auto-reset mechanism
- Added detailed error logging with packet number and size
- VAD detection status logging every 50 detections
- Automatic decoder reset on corruption detection with event logging for troubleshooting

---

## High Priority Issues (Data & Performance)

### Issue: Long Meeting Storage Performance
Large meetings with hundreds of segments were causing memory issues, slow API responses, and performance problems when loading/saving data.

**Solution:**
Implemented sharding and indexing system in `backend/core/handle/meeting_handle.py`:
- Created `index.json` index file tracking last 100 meetings with metadata
- Auto-shard when segments exceed 100 items:
  - Each shard file stores 100 segments in `meetings/segments/` directory
  - Main file keeps only first 50 segments as preview with `preview: true` flag
  - Track `totalCount` and `shardCount` for efficient loading
- Index includes: sessionId, deviceId, title, timestamps, bullets count, segments count
- Added `_update_meeting_index()` function for index management

---

### Issue: Transcript API Pagination for Large Meetings
No way to efficiently retrieve transcript segments for long meetings without loading entire file, causing timeouts and memory issues for meetings with thousands of segments.

**Solution:**
Implemented pagination API in `backend/core/http_server.py`:
```
GET /supie/meetings/{sessionId}/transcript?offset=0&limit=100
```
- Supports reading from both main file and shards sequentially
- Returns structured response: `{ items, total, offset, limit }`
- Limit range validation: 1-500 items per request
- Compatible with both preview structure (`preview:true,totalCount,segments[]`) and full list storage formats
- Intelligent shard detection with `hasShards` flag in detail API

---

### Issue: Meeting Transcript Real-time Updates Missing
Users couldn't see real-time transcript updates during meetings; transcript messages weren't being pushed to clients, even when segments were being processed. Empty segments would cause the entire transcript push to fail.

**Solution:**
Implemented comprehensive transcript push system in `backend/core/handle/meeting_handle.py`:
- Created `_run_transcript_push_loop` async task with 12-second default interval
- Ensured transcript messages always send, even with empty segments array
- Added `totalSegments` field for complete segment count statistics
- Enhanced logging: `发送transcript: segments=N, total=N`
- Fixed broadcast logic to ensure all connected devices receive transcript updates
- Push format: `phase="transcript"` with accumulated content
- Auto-clear pending queue after each push and merge to main cache
- Unified timer management with `start_meeting_timers` and `stop_meeting_timers`
- Automatic task start when receiving first snippet

---

## Medium Priority Issues (Quality & Reliability)

### Issue: Poor LLM Summary Quality - Incorrect Field Population
LLM was generating poor quality summaries with mixed-up content in wrong fields (e.g., decisions appearing in risks, actions without owners), empty arrays, or generic content.

**Solution:**
Rewrote prompt templates in `backend/core/handle/meeting_handle.py`:
- Added detailed field descriptions and extraction methods:
  - decisions: "已达成的决定、确定的方案或共识"
  - actions: "需要执行的具体任务，包含负责人"
  - risks: "提到的问题、挑战、风险或担忧"
  - nextSteps: "下一步计划、后续安排或待办事项"
- Added processing principles:
  - "仔细分析会议内容，提取相应信息填充各字段"
  - "如某字段无相关内容，必须返回空数组[]，不要编造"
- Adjusted word limits: title max 30 chars, other fields 20-40 chars per item

---

### Issue: Webhook Delivery Failures Without Retry
Webhook notifications were failing permanently on temporary network issues, losing important meeting completion notifications.

**Solution:**
Implemented retry mechanism in `backend/core/handle/meeting_handle.py`:
- Added `_send_webhook()` with single retry attempt
- 2-5 second random backoff between attempts
- Async sending using `asyncio.create_task` to avoid blocking main flow
- 5-second timeout protection
- Failures only log warnings, don't affect main process
- Webhook payload includes: sessionId, deviceId, summary, metrics, durationMs

---

### Issue: JSON Parsing Failures in LLM Responses
LLM responses weren't always valid JSON, causing parsing failures with no graceful degradation.

**Solution:**
Fixed exception handling in `backend/core/handle/meeting_handle.py`:
- Corrected indentation of try-catch blocks
- Added proper fallback when JSON parsing fails
- Enhanced logging to capture raw LLM response before parsing attempt

---

## Low Priority Issues (Developer Experience)

### Issue: MCP Configuration File Warning Spam
The system was generating excessive/misleading warning logs when MCP configuration file didn't exist, even though this was a valid state for systems not using MCP features.

**Solution:**
Progressive improvements in `backend/core/mcp/manager.py`:
1. First attempt: Lowered log level from `warning` to `info`
2. Second attempt: Further reduced from `info` to `debug`
3. Final solution: Auto-create empty config file `data/.mcp_server_settings.json` with content `{"mcpServers": {}}`
4. Added static marker to prevent duplicate warning outputs
5. Added safety check for `func_handler` existence before initializing MCP services
6. Created example configuration file `.mcp_server_settings.json.example` for reference

---

### Issue: Dynamic Configuration Not Taking Effect
Changes to transcript push intervals and other meeting configurations required full service restart, causing disruption.

**Solution:**
Implemented hot configuration reload in `backend/core/handle/meeting_handle.py`:
- `transcript_push_interval_ms` reads from `server.config.meeting` first (fallback to `conn.config.meeting`)
- Configuration changes via `update_config` take effect on next cycle
- Added logging to show next cycle duration for observability
- No service restart needed for interval adjustments

---

### Issue: Test Metrics Not Visible in Reports
Meeting performance metrics were buried in logs, making it hard to assess quality or diagnose performance problems.

**Solution:**
Enhanced testing and reporting in `test/run_all_tests.py`:
- Added `extract_meeting_metrics_from_log()` function to parse `[Meeting Metrics]` lines
- Extracts comprehensive metrics:
  - segmentsCount, checkpointCount, llmElapsedMs
  - emptyBullets, bulletsLength, industry, scenario
  - Empty skeleton status
- Test report generates `test/results/summary.md` with:
  - Meeting basic metrics
  - Quality metrics and empty skeleton rate
  - Assertion results summary
  - Performance indicators section
  - LLM timing statistics
- Supports multiple log path searching
- Includes assertions for field completeness and quality thresholds

---

### Issue: Peer Message Rate Limiting Too Restrictive
Broadcast messages were limited to once per 5 seconds, causing legitimate use cases to fail.

**Solution:**
Enhanced rate limiting in `backend/core/handle/peerHandle.py`:
- Regular messages: 5 per second (unchanged)
- Broadcast messages: relaxed from 5 seconds to 10 seconds between broadcasts
- Added remaining wait time in error messages
- Added `max_targets` config to limit single message target count (default 10)
- Enhanced ACL permission checking with detailed logs