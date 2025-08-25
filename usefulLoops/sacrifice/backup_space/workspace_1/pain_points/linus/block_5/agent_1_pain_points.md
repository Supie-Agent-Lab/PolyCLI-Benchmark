# Pain Points Analysis - Block 5

## Issue: Duplicate Device ID Connection Handling
The system was rejecting new connections when a device tried to reconnect with the same device ID, causing issues during network interruptions.

**Solution:**
Modified `backend/core/websocket_server.py` and `backend/core/connection.py` to implement a "kick old, accept new" strategy:
- When duplicate device ID detected, actively disconnect old connection
- Send system message to old connection: `{"type": "system", "message": "设备被新连接替换，即将断开"}`
- Accept new connection immediately
- Added exception handling to ensure new connection succeeds even if old connection cleanup fails

---

## Issue: MCP Configuration File Missing Warnings
The system was generating misleading warning logs when MCP configuration file didn't exist, even though this was a valid state.

**Solution:**
Modified `backend/core/mcp/manager.py`:
- Downgraded log level from `warning` to `info`, then to `debug`
- Added safety check for `func_handler` existence before initializing MCP services
- Automatically created empty config file `data/.mcp_server_settings.json` with content `{"mcpServers": {}}`
- Added static marker to avoid repeated warning outputs
- Created example configuration file `.mcp_server_settings.json.example` for reference

---

## Issue: LLM Service Unavailability Causing Meeting Summary Failures
When LLM service was unavailable, the entire meeting summary generation would fail, leaving no record of the meeting.

**Solution:**
Modified `backend/core/handle/meeting_handle.py`:
- Added LLM availability check before calling: check if `conn.llm` exists
- When LLM unavailable, generate default summary: `["会议内容已记录", "LLM服务暂时不可用", "请稍后重试"]`
- Fixed indentation issue in exception handling
- Enhanced logging to record raw LLM response for debugging

---

## Issue: Transcript Messages Not Being Pushed
Transcript messages weren't being sent properly, even when segments were empty, causing client-side issues.

**Solution:**
Modified `backend/core/handle/meeting_handle.py`:
- Ensured transcript messages always sent, even with empty segments
- Added `totalSegments` field for complete segment count
- Added logging: `发送transcript: segments=N, total=N`
- Fixed broadcast logic to ensure other devices receive transcript

---

## Issue: Long Meeting Storage Performance
Long meetings with hundreds of segments were causing performance issues when loading and storing data.

**Solution:**
Implemented sharding mechanism in `backend/core/handle/meeting_handle.py`:
- Created `index.json` index file tracking last 100 meetings with metadata
- Automatic sharding when segments exceed 100 items
- Each shard file stores 100 segments in `meetings/segments/` directory
- Main file keeps only first 50 segments as preview with `preview: true` flag
- Added `totalCount` and `shardCount` for efficient loading
- Added `_update_meeting_index()` function for index management

---

## Issue: Opus Audio Decoder Corruption
The Opus decoder was encountering "corrupted stream" errors causing audio processing failures.

**Solution:**
Enhanced error handling in `backend/core/providers/vad/silero.py`:
- Added packet statistics logging every 100 packets
- Implemented detailed Opus decode error logging with packet number and size
- Created automatic decoder reset mechanism on "corrupted stream" detection
- Added VAD detection status logging every 50 detections
- Implemented error recovery with decoder reset events logged for troubleshooting

---

## Issue: Meeting Transcript Push Loop Not Starting
Meeting transcript push tasks weren't being properly managed, causing missing real-time updates.

**Solution:**
Implemented task management in `backend/core/handle/meeting_handle.py`:
- Created `_run_transcript_push_loop` async task with 12-second default interval
- Added `start_meeting_timers` for unified timer management
- Added `stop_meeting_timers` to properly stop tasks on meeting end
- Automatic task start when receiving first snippet
- Push message format: `phase="transcript"` with accumulated content
- Auto-clear pending queue after push and merge to main cache

---

## Issue: Transcript Push Interval Not Configurable at Runtime
The transcript push interval was hardcoded and couldn't be changed without restart.

**Solution:**
Made interval hot-reloadable in `backend/core/handle/meeting_handle.py`:
- `transcript_push_interval_ms` now read from `server.config.meeting` (fallback to `conn.config.meeting`)
- Configuration changes take effect on next cycle after `update_config`
- Added logging to show next cycle duration for observability

---

## Issue: Webhook Failures Without Retry
Webhook notifications were failing permanently on temporary network issues.

**Solution:**
Added retry mechanism in `backend/core/handle/meeting_handle.py`:
- Implemented `_send_webhook()` with 2-5 second random backoff single retry
- Failures only generate warning logs, don't affect main flow
- Used `asyncio.create_task` for async sending with 5-second timeout protection

---

## Issue: LLM Prompt Template Quality
LLM was generating poor quality meeting summaries with unclear field categorization.

**Solution:**
Rewrote prompt templates in `backend/core/handle/meeting_handle.py`:
- Added detailed field descriptions:
  - decisions: "已达成的决定、确定的方案或共识"
  - actions: "需要执行的具体任务，包含负责人"
  - risks: "提到的问题、挑战、风险或担忧"
  - nextSteps: "下一步计划、后续安排或待办事项"
- Added processing principles:
  - "仔细分析会议内容，提取相应信息填充各字段"
  - "如某字段无相关内容，必须返回空数组[]，不要编造"
- Adjusted word limits: title max 30 chars, other fields 20-40 chars per item

---

## Issue: Transcript Pagination for Large Meetings
No way to efficiently retrieve transcript segments for long meetings with hundreds of entries.

**Solution:**
Implemented pagination API in `backend/core/http_server.py`:
- Added `GET /supie/meetings/{sessionId}/transcript?offset=0&limit=100`
- Supports reading from main file and shards sequentially
- Returns `{ items, total, offset, limit }` with limit range 1-500
- Compatible with both preview structure (`preview:true,totalCount,segments[]`) and full list storage formats
- Intelligent shard detection with `hasShards` flag in detail API

---

## Issue: Test Reports Lacking Performance Metrics
Test reports didn't include actual meeting performance metrics from logs.

**Solution:**
Enhanced test reporting in `test/run_all_tests.py`:
- Added `extract_meeting_metrics_from_log()` function
- Extracts `[Meeting Metrics]` lines from logs
- Parses segmentsCount, checkpointCount, llmElapsedMs metrics
- Supports multiple log path searching
- Added "Performance Metrics" section to test report
- Includes LLM timing, empty skeleton status, industry/scenario info