# Pain Points and Solutions - Block 4 (Merged)

## Critical Infrastructure Issues

### Issue: Device ID parsing priority and consistency problems
The handshake logic initially had unclear parsing priority for device-id/client-id, causing inconsistent device registration and routing failures when device IDs had different case formats. Different websockets library versions stored path/request data in different attributes, causing handshake parsing failures.

**Solution:**
Implemented clear parsing priority in `backend/core/connection.py`:
- First priority: URL Query parameters (`device-id/client-id`)
- Second priority: Headers (supporting variants like `device-id|device_id|x-device-id`)
- Last resort: Auto-generated ID (`auto-xxxx`)
- Added `_normalize_id()` function to standardize IDs (lowercase, trim whitespace/quotes) ensuring consistent matching between registration and routing
- Enhanced logging to show source of ID (`source=query` or `source=header`)

Implemented handshake caching fallback in `backend/core/websocket_server.py`:
- Extract path from multiple possible attributes during HTTP upgrade: `path/request_uri/raw_request_uri/request_path/raw_path`
- Cache parsed device-id/client-id in `_handshake_cache[id(conn)]`
- Connection phase reads from cache if direct parsing fails
- Added diagnostic logging: `HTTP upgrade request path=...` and `rawPaths/headerKeys` snapshots

---

### Issue: Case sensitivity causing device matching failures
Device IDs with different cases (uppercase MAC from hardware vs lowercase in system) were not matching, causing routing failures for peer-to-peer messages. Authentication whitelist was case-sensitive, causing legitimate devices to be rejected.

**Solution:**
Standardized all device IDs to lowercase throughout the system:
- In `backend/core/connection.py`: Applied normalization during registration
- In `backend/core/handle/peerHandle.py`: Normalized `to` list elements before ACL and distribution
- In `backend/core/auth.py`: Convert `allowed_devices` to lowercase during initialization
- Preserved `broadcast` constant while normalizing actual device IDs
- Maintained backward compatibility with existing configurations

---

### Issue: Peer messages lost when target devices offline
Messages sent to offline devices were silently dropped, causing data loss and requiring manual retransmission when devices came back online.

**Solution:**
Created lightweight offline queue system:
- `backend/core/utils/offline_queue.py`: JSON-based queue (`backend/data/offline_peer_queue.json`)
- Queue limits: 100 messages per device, 3-day TTL
- Auto-enqueue on delivery failure with `enqueued` field in sender receipt
- Auto-flush and deliver queued messages when device registers (comes online)
- Added delivery statistics logging: `sent/dropped` counts

---

## Meeting System Issues

### Issue: Meeting text deduplication and throttling
Meeting snippets were accumulating duplicate text entries within short time windows, causing redundant processing and inflated meeting summaries. Batching wasn't following the 10-15 second interval requirement.

**Solution:**
In `backend/core/handle/meeting_handle.py`:
- Maintained connection-level caches: `meeting_recent_texts/meeting_pending_texts`
- Implemented 1-minute deduplication window for repeated text
- Added 12-second throttling to batch merge snippets into `meeting_segments` (satisfying 10-15s requirement)
- Made `finalize` idempotent - repeated triggers reuse last summary instead of reprocessing
- Include pending texts in final summary to avoid data loss

---

### Issue: Long meetings losing context
Extended meetings would lose early context when generating final summary, and no intermediate checkpoints were available during the meeting.

**Solution:**
Implemented checkpoint system in `backend/core/handle/meeting_handle.py`:
- Active state persistence: `backend/data/meetings/active_{device_id}.json`
- Periodic checkpoints every 10 minutes (configurable via `checkpoint_interval_min`)
- Incremental summaries marked with `checkpoint:true`
- Resume capability after disconnection
- Final summary incorporates all checkpoints

---

### Issue: Meeting summaries lacking structure
Meeting summaries were unstructured text blocks, making it difficult to extract actionable items like decisions, tasks, and risks programmatically.

**Solution:**
Structured summary format in `backend/core/handle/meeting_handle.py`:
- Enhanced LLM prompt for strict JSON output
- Added fields: `decisions/actions/risks/nextSteps`
- Implemented deduplication and length trimming per field
- Heuristic fallback when LLM fails to generate proper structure
- Extended schema in `backend/core/utils/schema.py` to validate new fields
- Include transcript with last 50 segments including timestamps

---

### Issue: Audio-to-summary pipeline disconnected
Audio inputs through ASR weren't properly integrated with the meeting snippet processing pipeline, causing audio-based meetings to miss deduplication and throttling logic.

**Solution:**
Connected audio pipeline in `backend/core/handle/receiveAudioHandle.py`:
- Route ASR text through `handle_meeting_message` in meeting mode
- Package as `meeting.snippet` to reuse existing deduplication/throttling
- Ensure consistent processing path for both text and audio inputs

---

### Issue: Speaker identification missing in transcripts
Meeting transcripts didn't identify who said what, making it difficult to attribute statements and follow conversation flow.

**Solution:**
Added speaker tracking:
- Schema extension: `meeting.items[].speakerId` field
- `backend/core/handle/receiveAudioHandle.py`: Derive `speakerId` from device-id
- Store speaker ID in segments and transcript
- Preserve speaker information through entire pipeline

---

### Issue: Meeting duration incorrectly calculated
Meeting summaries showed `00:00:00` duration when no segments present, not reflecting actual meeting time.

**Solution:**
Fixed duration calculation in `backend/core/handle/meeting_handle.py`:
- Calculate duration from `start_time → now` instead of fixed `00:00:00`
- Properly estimate duration even when no text segments captured
- Ensure duration reflects actual elapsed time

---

### Issue: No support for multilingual meetings and industry terminology
Meetings with mixed languages and industry-specific terms weren't being processed correctly.

**Solution:**
Added preprocessing and configuration support:
- `preprocess_meeting_text()`: Language detection (zh/en), normalization, term mapping
- Configurable via `conn.config.meeting`:
  - `target_lang`: Override automatic language detection
  - `industry` and `scenario`: Context for better summaries
  - `term_map`: Hierarchical term mapping by industry and language
  - Custom prompts via `prompts.system` and `prompts.userTemplate`
- Hot-reload configuration without restart via `server.update_config`

---

## Workflow System Issues

### Issue: Workflow task updates causing data overwrites
Field-level updates to workflow tasks were replacing entire task objects, causing concurrent updates from different clients to overwrite each other's changes.

**Solution:**
Enhanced workflow handling in `backend/core/handle/workflow_handle.py`:
- Implemented field-level merging for `event:"update"` - only update provided fields
- Added `upsert_fields()` in task store for partial updates
- Preserved unmodified fields during updates
- Example: Client A updates `status:'done'`, Client B updates `title:'renamed'` - both changes preserved

---

### Issue: Workflow broadcasts crossing group boundaries
All workflow updates were broadcast to all connected devices, causing unnecessary updates and potential data leakage between unrelated device groups.

**Solution:**
Implemented group-based workflow isolation:
- Calculate `groupKey=conn.device_id[:8]` for device grouping
- Store tasks with group association in `backend/core/utils/tasks_store.py`
- Broadcast only to devices in same group
- Added `list_by_group()` for filtered task retrieval
- Support group override via message `groupKey` field
- Per-group payload construction for targeted delivery

---

### Issue: Schema validation too strict for partial updates
The workflow schema required all fields for update operations, preventing field-level updates and causing validation failures for legitimate partial updates.

**Solution:**
Relaxed schema validation in `backend/core/utils/schema.py`:
- Made `title/priority/status` optional for `update` event
- Only validate fields when present (e.g., `priority` must be 0-3 only if provided)
- Added support for `delete` event with `ids` array
- Allow update with only `id` field for minimal changes

---

### Issue: Workflow group assignment too rigid
Devices could only write tasks to their own group (based on device ID prefix), preventing cross-group task assignment for legitimate use cases.

**Solution:**
Added group override support in `backend/core/handle/workflow_handle.py`:
- Priority order: `task.groupKey` > message `groupKey` > default device group
- Allow explicit group targeting while maintaining default isolation
- Example: Device `001` can write to group `94:a9:90:` by specifying `groupKey`

---

## Cross-Device Synchronization Issues

### Issue: Cross-device meeting/coding state not synchronized
Multiple devices in same session couldn't see each other's meeting snippets or coding status updates, requiring manual coordination.

**Solution:**
Implemented broadcast mechanism:
- `backend/core/handle/meeting_handle.py`: Broadcast `meeting.snippet/summary/transcript` after processing
- `backend/core/handle/coding_handle.py`: Broadcast coding events (`start/stop/clear/log/step/phase`)
- Added `from` field to identify message source
- Internal `_broadcast_to_others()` helper function
- Reused `server.get_broadcast_targets()` for efficient distribution
- Compatible with both `send_json` and string message formats

---

## LLM Integration Issues

### Issue: LLM configuration errors hard to diagnose
LLM API failures (wrong URL, invalid key, model not found) produced cryptic errors without clear indication of root cause, making troubleshooting difficult.

**Solution:**
Enhanced LLM error handling in `backend/core/providers/llm/openai/openai.py` and `backend/core/handle/meeting_handle.py`:
- Added explicit diagnostic logging: base_url, api_key, model on errors
- Print system_prompt/user_prompt before LLM calls
- Log raw LLM response and parsed JSON
- Full traceback on exceptions
- Graceful degradation: return empty summary skeleton on LLM failure

Added comprehensive LLM debugging:
```python
# Log system and user prompts before sending
print(f"[DEBUG] system_prompt: {system_prompt}")
print(f"[DEBUG] user_prompt: {user_prompt}")
# Log raw LLM response
print(f"[DEBUG] llm_raw: {llm_raw[:500]}")
# Log parsed JSON
print(f"[DEBUG] json_str: {json_str}")
```