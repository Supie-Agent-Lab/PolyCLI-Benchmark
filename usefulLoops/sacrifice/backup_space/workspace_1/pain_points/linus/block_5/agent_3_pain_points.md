# Pain Points Analysis - Block 5

## Issue: Duplicate Device ID Connection Handling
When a device with the same ID tried to reconnect (e.g., after network interruption), the system would reject the new connection because the old connection was still registered, even though it was effectively dead.

**Solution:**
Modified `backend/core/websocket_server.py` and `backend/core/connection.py` to implement a "kick old, welcome new" strategy:
- When duplicate device ID is detected, proactively disconnect the old connection
- Send system message to old connection: `{"type": "system", "message": "设备被新连接替换，即将断开"}`
- Accept the new connection immediately
- Added exception handling to prevent old connection cleanup failures from blocking new connections

---

## Issue: MCP Configuration File Warning Spam
The system was generating excessive warning logs when MCP configuration file was missing, even though this was a normal scenario for systems not using MCP features.

**Solution:**
Progressive improvements in `backend/core/mcp/manager.py`:
1. First attempt: Lowered log level from `warning` to `info`
2. Second attempt: Further reduced from `info` to `debug`
3. Final solution: Auto-create empty configuration file `data/.mcp_server_settings.json` with content `{"mcpServers": {}}` to eliminate warnings entirely
4. Added static marker to prevent duplicate warning outputs

---

## Issue: LLM Service Unavailability Causing Meeting Summary Failures
When LLM service was unavailable or failed, the entire meeting finalization would fail, leaving users without any summary.

**Solution:**
Enhanced `backend/core/handle/meeting_handle.py` with fallback mechanism:
- Added LLM availability check before calling: `if not conn.llm`
- Generate default summary when LLM unavailable: `["会议内容已记录", "LLM服务暂时不可用", "请稍后重试"]`
- Fixed indentation issues in exception handling to ensure proper fallback
- Added raw LLM response logging for debugging

---

## Issue: Transcript Message Not Being Pushed
Meeting transcript messages were not being sent to connected clients, even when segments existed. Empty segments would cause the entire transcript push to fail.

**Solution:**
Fixed in `backend/core/handle/meeting_handle.py`:
- Ensured transcript messages are always sent, even with empty segments array
- Added `totalSegments` field for complete segment count statistics
- Enhanced logging: `发送transcript: segments=N, total=N`
- Fixed broadcast logic to ensure all connected devices receive transcript

---

## Issue: Long Meeting Storage Performance
Large meetings with hundreds of segments were causing memory issues and slow API responses when loading the full meeting data.

**Solution:**
Implemented sharding and indexing system in `backend/core/handle/meeting_handle.py`:
- Created `index.json` to maintain metadata for last 100 meetings
- Auto-shard segments when exceeding 100 entries:
  - Each shard stores 100 segments in `meetings/segments/` directory
  - Main file keeps first 50 as preview with `preview: true` flag
  - Track `totalCount` and `shardCount` for efficient loading
- Added `_update_meeting_index()` function for index management

---

## Issue: Opus Audio Decoder Stream Corruption
Opus decoder was encountering "corrupted stream" errors, causing audio processing failures and VAD detection issues.

**Solution:**
Enhanced error handling in `backend/core/providers/vad/silero.py`:
- Added packet statistics logging every 100 packets
- Implemented corrupted stream detection with auto-reset mechanism
- Added detailed error logging with packet sequence and size
- VAD detection status logging every 50 detections
- Automatic decoder reset on corruption detection

---

## Issue: Meeting Transcript Real-time Updates Missing
Users couldn't see real-time transcript updates during meetings; they had to wait until meeting end to see any content.

**Solution:**
Implemented transcript push loop in `backend/core/handle/meeting_handle.py`:
- Created `_run_transcript_push_loop` async task
- Default 12-second push interval (configurable via `transcript_push_interval_ms`)
- Push format: `phase="transcript"` with accumulated content
- Auto-clear pending queue after each push
- Unified timer management with `start_meeting_timers` and `stop_meeting_timers`

---

## Issue: Poor LLM Summary Quality - Incorrect Field Population
LLM was generating poor quality summaries with mixed-up content in wrong fields (e.g., decisions appearing in risks, actions without owners).

**Solution:**
Rewrote default system prompts in `backend/core/handle/meeting_handle.py`:
- Provided detailed field descriptions and extraction methods:
  - decisions: "已达成的决定、确定的方案或共识"
  - actions: "需要执行的具体任务，包含负责人"
  - risks: "提到的问题、挑战、风险或担忧"
  - nextSteps: "下一步计划、后续安排或待办事项"
- Added explicit instructions: "如某字段无相关内容，必须返回空数组[]，不要编造"
- Adjusted word limits: title ≤30 chars, other fields 20-40 chars per item

---

## Issue: Webhook Delivery Failures Due to Network Issues
Webhook notifications would fail permanently on first network error, losing important meeting completion notifications.

**Solution:**
Added retry mechanism in `backend/core/handle/meeting_handle.py`:
- Implemented `_send_webhook()` with single retry attempt
- Added 2-5 second random backoff between attempts
- Failure handling: log warning but don't block main flow
- Used `asyncio.create_task` for async non-blocking sends

---

## Issue: Missing Pagination for Large Transcript Data
API couldn't efficiently serve large transcript data, causing timeouts and memory issues for meetings with thousands of segments.

**Solution:**
Implemented pagination API in `backend/core/http_server.py`:
- New endpoint: `GET /supie/meetings/{sessionId}/transcript?offset=0&limit=100`
- Supports both main file and shards with sequential reading
- Returns structured response: `{ items, total, offset, limit }`
- Limit range validation: 1-500 items per request
- Compatible with both preview and full segment storage formats

---

## Issue: Configuration Changes Requiring Service Restart
Changes to transcript push intervals and other meeting configurations required full service restart, causing disruption.

**Solution:**
Implemented hot configuration reload in `backend/core/handle/meeting_handle.py`:
- `transcript_push_interval_ms` reads from `server.config.meeting` with fallback
- Configuration changes via `update_config` take effect on next cycle
- Added logging to show new interval after each push cycle
- No service restart needed for interval adjustments

---

## Issue: Incomplete Test Coverage for Meeting Quality
No visibility into meeting processing metrics, making it hard to diagnose quality issues or performance problems.

**Solution:**
Enhanced testing and metrics in multiple files:
1. Added comprehensive metrics collection in `backend/core/handle/meeting_handle.py`:
   - `segmentsCount`, `checkpointCount`, `llmElapsedMs`
   - `emptyBullets`, `bulletsLength`, `industry`, `scenario`
   - Output format: `[Meeting Metrics] segmentsCount=N, checkpointCount=N...`

2. Created `extract_meeting_metrics_from_log()` in `test/run_all_tests.py`:
   - Extracts metrics from log files
   - Generates performance report in `test/results/summary.md`
   - Includes assertions for field completeness and quality thresholds