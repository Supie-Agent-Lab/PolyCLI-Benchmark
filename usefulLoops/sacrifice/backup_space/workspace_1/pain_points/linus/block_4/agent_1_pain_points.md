# Pain Points and Solutions - Block 4

## Issue: Device ID parsing priority and consistency problems
The handshake logic initially had unclear parsing priority for device-id/client-id, causing inconsistent device registration and routing failures when device IDs had different case formats.

**Solution:**
Implemented clear parsing priority in `backend/core/connection.py`:
- First priority: URL Query parameters (`device-id/client-id`)
- Second priority: Headers (supporting variants like `device-id|device_id|x-device-id`)
- Last resort: Auto-generated ID (`auto-xxxx`)
- Added `_normalize_id()` function to standardize IDs (lowercase, trim whitespace/quotes) ensuring consistent matching between registration and routing

---

## Issue: Meeting text deduplication and throttling
Meeting snippets were accumulating duplicate text entries within short time windows, causing redundant processing and inflated meeting summaries.

**Solution:**
In `backend/core/handle/meeting_handle.py`:
- Maintained connection-level caches: `meeting_recent_texts/meeting_pending_texts`
- Implemented 1-minute deduplication window for repeated text
- Added 12-second throttling to batch merge snippets into `meeting_segments` (satisfying 10-15s requirement)
- Made `finalize` idempotent - repeated triggers reuse last summary instead of reprocessing

---

## Issue: Peer messages lost when target devices offline
Messages sent to offline devices were silently dropped, causing data loss and requiring manual retransmission when devices came back online.

**Solution:**
Created lightweight offline queue system:
- `backend/core/utils/offline_queue.py`: JSON-based queue (`backend/data/offline_peer_queue.json`)
- Queue limits: 100 messages per device, 3-day TTL
- Auto-enqueue on delivery failure with `enqueued` field in sender receipt
- Auto-flush and deliver queued messages when device registers (comes online)
- Added delivery statistics logging: `sent/dropped` counts

---

## Issue: Auth whitelist case sensitivity
Device authentication failed when MAC addresses in whitelist had different case than provided device IDs, causing legitimate devices to be rejected.

**Solution:**
In `backend/core/auth.py`:
- Convert all `allowed_devices` to lowercase during initialization
- Normalize incoming `headers['device-id']` to lowercase before comparison
- Ensures case-insensitive matching for MAC addresses in whitelist

---

## Issue: WebSocket handshake data loss across library versions
Different websockets library versions stored path/request data in different attributes, causing handshake parsing failures and device registration issues.

**Solution:**
Implemented handshake caching fallback in `backend/core/websocket_server.py`:
- Extract path from multiple possible attributes during HTTP upgrade: `path/request_uri/raw_request_uri/request_path/raw_path`
- Cache parsed device-id/client-id in `_handshake_cache[id(conn)]`
- Connection phase reads from cache if direct parsing fails
- Added diagnostic logging: `HTTP upgrade request path=...` and `rawPaths/headerKeys` snapshots

---

## Issue: Workflow task updates causing data overwrites
Field-level updates to workflow tasks were replacing entire task objects, causing concurrent updates from different clients to overwrite each other's changes.

**Solution:**
Enhanced workflow handling in `backend/core/handle/workflow_handle.py`:
- Implemented field-level merging for `event:"update"` - only update provided fields
- Added `upsert_fields()` in task store for partial updates
- Preserved unmodified fields during updates
- Example: Client A updates `status:'done'`, Client B updates `title:'renamed'` - both changes preserved

---

## Issue: Workflow broadcasts crossing group boundaries
All workflow updates were broadcast to all connected devices, causing unnecessary updates and potential data leakage between unrelated device groups.

**Solution:**
Implemented group-based workflow isolation:
- Calculate `groupKey=conn.device_id[:8]` for device grouping
- Store tasks with group association in `backend/core/utils/tasks_store.py`
- Broadcast only to devices in same group
- Added `list_by_group()` for filtered task retrieval
- Support group override via message `groupKey` field

---

## Issue: Schema validation too strict for partial updates
The workflow schema required all fields for update operations, preventing field-level updates and causing validation failures for legitimate partial updates.

**Solution:**
Relaxed schema validation in `backend/core/utils/schema.py`:
- Made `title/priority/status` optional for `update` event
- Only validate fields when present (e.g., `priority` must be 0-3 only if provided)
- Added support for `delete` event with `ids` array
- Allow update with only `id` field for minimal changes

---

## Issue: Meeting audio-to-summary pipeline disconnected
Audio inputs through ASR weren't properly integrated with the meeting snippet processing pipeline, causing audio-based meetings to miss deduplication and throttling logic.

**Solution:**
Connected audio pipeline in `backend/core/handle/receiveAudioHandle.py`:
- Route ASR text through `handle_meeting_message` in meeting mode
- Package as `meeting.snippet` to reuse existing deduplication/throttling
- Ensure consistent processing path for both text and audio inputs

---

## Issue: LLM configuration errors hard to diagnose
LLM API failures (wrong URL, invalid key, model not found) produced cryptic errors without clear indication of root cause, making troubleshooting difficult.

**Solution:**
Enhanced LLM error handling in `backend/core/providers/llm/openai/openai.py` and `backend/core/handle/meeting_handle.py`:
- Added explicit diagnostic logging: base_url, api_key, model on errors
- Print system_prompt/user_prompt before LLM calls
- Log raw LLM response and parsed JSON
- Full traceback on exceptions
- Graceful degradation: return empty summary skeleton on LLM failure

---

## Issue: Meeting duration incorrectly calculated
Meeting summaries showed `00:00:00` duration when no segments present, not reflecting actual meeting time.

**Solution:**
Fixed duration calculation in `backend/core/handle/meeting_handle.py`:
- Calculate duration from `start_time → now` instead of fixed `00:00:00`
- Properly estimate duration even when no text segments captured
- Ensure duration reflects actual elapsed time

---

## Issue: Cross-device meeting/coding state not synchronized
Multiple devices in same session couldn't see each other's meeting snippets or coding status updates, requiring manual coordination.

**Solution:**
Implemented broadcast mechanism:
- `backend/core/handle/meeting_handle.py`: Broadcast `meeting.snippet/summary/transcript` after processing
- `backend/core/handle/coding_handle.py`: Broadcast coding events (`start/stop/clear/log/step/phase`)
- Added `from` field to identify message source
- Reused `server.get_broadcast_targets()` for efficient distribution

---

## Issue: Workflow group assignment too rigid
Devices could only write tasks to their own group (based on device ID prefix), preventing cross-group task assignment for legitimate use cases.

**Solution:**
Added group override support in `backend/core/handle/workflow_handle.py`:
- Priority order: `task.groupKey` > message `groupKey` > default device group
- Allow explicit group targeting while maintaining default isolation
- Example: Device `001` can write to group `94:a9:90:` by specifying `groupKey`

---

## Issue: Meeting summaries lacking structure
Meeting summaries were unstructured text blocks, making it difficult to extract actionable items like decisions, tasks, and risks programmatically.

**Solution:**
Structured summary format in `backend/core/handle/meeting_handle.py`:
- Enhanced LLM prompt for strict JSON output
- Added fields: `decisions/actions/risks/nextSteps`
- Implemented deduplication and length trimming per field
- Heuristic fallback when LLM fails to generate proper structure
- Extended schema in `backend/core/utils/schema.py` to validate new fields

---

## Issue: Speaker identification missing in transcripts
Meeting transcripts didn't identify who said what, making it difficult to attribute statements and follow conversation flow.

**Solution:**
Added speaker tracking:
- Schema extension: `meeting.items[].speakerId` field
- `backend/core/handle/receiveAudioHandle.py`: Derive `speakerId` from device-id
- Store speaker ID in segments and transcript
- Preserve speaker information through entire pipeline

---

## Issue: Long meetings losing context
Extended meetings would lose early context when generating final summary, and no intermediate checkpoints were available during the meeting.

**Solution:**
Implemented checkpoint system in `backend/core/handle/meeting_handle.py`:
- Active state persistence: `backend/data/meetings/active_{device_id}.json`
- Periodic checkpoints every 10 minutes (configurable via `checkpoint_interval_min`)
- Incremental summaries marked with `checkpoint:true`
- Resume capability after disconnection
- Final summary incorporates all checkpoints