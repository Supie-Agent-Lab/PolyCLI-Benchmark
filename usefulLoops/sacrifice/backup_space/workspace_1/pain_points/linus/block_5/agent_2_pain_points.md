# Pain Points from Block 5 - Agent 2

## Issue: Duplicate Device ID Connection Handling
When the same device ID attempted to reconnect, the old connection wasn't being properly closed, causing rejection issues during network interruptions.

**Solution:**
Modified `backend/core/websocket_server.py` and `backend/core/connection.py` to implement a "kick old, welcome new" strategy:
- When duplicate device ID detected, actively disconnect old connection
- Send system message to old connection: `{"type": "system", "message": "设备被新连接替换，即将断开"}`
- Accept new connection after closing old one
- Added exception handling to ensure new connection succeeds even if old connection cleanup fails

---

## Issue: MCP Configuration File Warning Spam
Missing MCP configuration file was generating warning-level logs repeatedly, misleading developers about actual issues.

**Solution:**
Multiple iterations to fix in `backend/core/mcp/manager.py`:
1. First attempt: Lowered log level from `warning` to `info`
2. Second attempt: Further lowered from `info` to `debug`
3. Final solution: Auto-create empty config file `data/.mcp_server_settings.json` with content `{"mcpServers": {}}` to eliminate warnings entirely
4. Added static flag to prevent duplicate warnings
5. Created example config file `.mcp_server_settings.json.example` for reference

---

## Issue: LLM Service Unavailability Causing Meeting Summary Failures
When LLM service was unavailable, the entire meeting finalization process would fail, leaving no summary at all.

**Solution:**
Enhanced `backend/core/handle/meeting_handle.py` with fallback mechanism:
- Added LLM availability check before invocation: check if `conn.llm` exists
- When LLM unavailable, generate default summary: `["会议内容已记录", "LLM服务暂时不可用", "请稍后重试"]`
- Fixed indentation issues in exception handling
- Enhanced logging to capture raw LLM responses for debugging

---

## Issue: Missing Transcript Messages Despite Meeting Progress
Transcript messages weren't being pushed to clients, even when segments were being processed.

**Solution:**
Fixed in `backend/core/handle/meeting_handle.py`:
- Ensured transcript messages always send, even with empty segments
- Added `totalSegments` field for complete segment count
- Enhanced logging: `发送transcript: segments=N, total=N`
- Fixed broadcast logic to ensure all connected devices receive transcript updates
- Implemented `_run_transcript_push_loop` async task with 12-second default interval

---

## Issue: JSON Parsing Failures in LLM Responses
LLM responses weren't always valid JSON, causing parsing failures and no graceful degradation.

**Solution:**
Fixed exception handling in `backend/core/handle/meeting_handle.py`:
- Corrected indentation of try-catch blocks
- Added proper fallback when JSON parsing fails
- Enhanced logging to capture raw LLM response before parsing attempt

---

## Issue: Long Meeting Storage Performance
Large meetings with hundreds of segments were causing performance issues when loading/saving.

**Solution:**
Implemented sharding mechanism in `backend/core/handle/meeting_handle.py`:
- Auto-shard when segments > 100
- Each shard stores 100 segments in `meetings/segments/` directory
- Main file keeps first 50 segments as preview with `preview: true` flag
- Added `totalCount` and `shardCount` metadata
- Created `index.json` for fast lookups of recent 100 meetings
- Index includes: sessionId, deviceId, title, timestamps, bullets count, segments count

---

## Issue: Transcript API Pagination for Large Meetings
No way to efficiently retrieve transcript segments for long meetings without loading entire file.

**Solution:**
Added pagination API in `backend/core/http_server.py`:
```
GET /supie/meetings/{sessionId}/transcript?offset=0&limit=100
```
- Supports reading from both main file and shards sequentially
- Returns `{ items, total, offset, limit }`
- Limit range: 1-500
- Compatible with both preview structure and complete list formats

---

## Issue: Poor Meeting Summary Quality - Empty or Generic Content
LLM was generating empty arrays or generic content for decisions, actions, risks, and nextSteps fields.

**Solution:**
Rewrote prompt templates in `backend/core/handle/meeting_handle.py`:
- Added detailed field explanations:
  - decisions: "已达成的决定、确定的方案或共识"
  - actions: "需要执行的具体任务，包含负责人"
  - risks: "提到的问题、挑战、风险或担忧"
  - nextSteps: "下一步计划、后续安排或待办事项"
- Added explicit instruction: "如某字段无相关内容，必须返回空数组[]，不要编造"
- Adjusted word limits: title ≤30 chars, other fields 20-40 chars per item

---

## Issue: Webhook Delivery Failures Without Retry
Webhook notifications were failing silently when target servers were temporarily unavailable.

**Solution:**
Implemented retry mechanism in `backend/core/handle/meeting_handle.py`:
- Added single retry with 2-5 second random backoff
- Async sending using `asyncio.create_task` to avoid blocking main flow
- 5-second timeout protection
- Failures only log warnings, don't affect main process
- Webhook payload includes: sessionId, deviceId, summary, metrics, durationMs

---

## Issue: Opus Audio Decoder Stream Corruption
"Corrupted stream" errors in Opus decoding were causing audio processing failures.

**Solution:**
Enhanced error recovery in `backend/core/providers/vad/silero.py`:
- Added packet statistics logging (every 100 packets)
- Implemented corrupted stream detection
- Auto-reset decoder when corruption detected
- Enhanced error logging with packet number and size
- Added VAD detection status logging (every 50 detections)

---

## Issue: Dynamic Configuration Not Taking Effect
Changes to transcript push intervals required service restart to take effect.

**Solution:**
Modified `backend/core/handle/meeting_handle.py`:
- `transcript_push_interval_ms` now reads from `server.config.meeting` first (fallback to `conn.config.meeting`)
- Configuration changes via `update_config` take effect on next push cycle
- Push completion logs show next cycle duration for observability

---

## Issue: Test Metrics Not Visible in Reports
Meeting performance metrics were buried in logs, making it hard to assess quality.

**Solution:**
Enhanced `test/run_all_tests.py`:
- Added `extract_meeting_metrics_from_log()` function to parse `[Meeting Metrics]` lines
- Extracts: segmentsCount, checkpointCount, llmElapsedMs, emptyBullets, bulletsLength
- Test report generates `test/results/summary.md` with:
  - Meeting basic metrics
  - Quality metrics and empty skeleton rate
  - Assertion results summary
  - Performance indicators section

---

## Issue: Peer Message Rate Limiting Too Restrictive
Broadcast messages were limited to once per 5 seconds, causing legitimate use cases to fail.

**Solution:**
Enhanced rate limiting in `backend/core/handle/peerHandle.py`:
- Regular messages: 5 per second (unchanged)
- Broadcast messages: relaxed from 5 seconds to 10 seconds between broadcasts
- Added remaining wait time in error messages
- Added `max_targets` config to limit single message target count (default 10)
- Enhanced ACL permission checking with detailed logs