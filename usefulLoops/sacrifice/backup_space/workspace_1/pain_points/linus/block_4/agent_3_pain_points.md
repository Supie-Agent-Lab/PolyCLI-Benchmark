# Pain Points from Block 4 - WebSocket/Meeting System Development

## Issue: Device ID parsing priority and consistency problems
During WebSocket handshake, device IDs were not being parsed consistently from different sources (URL query parameters vs headers), causing device registration mismatches.

**Solution:**
Implemented explicit parsing priority in `backend/core/connection.py`:
- Priority 1: URL Query parameters (`device-id/client-id` from `path`)
- Priority 2: Headers (supporting variants like `device-id`, `device_id`, `x-device-id`)
- Priority 3: Auto-generated fallback (`auto-xxxx`)
- Added `_normalize_id()` function to standardize IDs (remove whitespace/quotes, convert to lowercase)
- Enhanced logging to show source of ID (`source=query` or `source=header`)

---

## Issue: Case sensitivity causing device matching failures
Device IDs with different casing (uppercase MAC vs lowercase MAC) were treated as different devices, causing routing and broadcast failures.

**Solution:**
Standardized all device IDs to lowercase throughout the system:
- `backend/core/connection.py`: Normalize IDs during handshake parsing
- `backend/core/handle/peerHandle.py`: Standardize target IDs in ACL and distribution
- `backend/core/auth.py`: Convert `allowed_devices` whitelist to lowercase during initialization
- Preserved `broadcast` constant while normalizing all device-specific IDs

---

## Issue: Meeting snippet duplication and inefficient batching
Consecutive meeting snippets with identical text were being accumulated multiple times, and batching wasn't following the 10-15 second interval requirement.

**Solution:**
Implemented deduplication and throttling in `backend/core/handle/meeting_handle.py`:
- Maintain connection-level caches: `meeting_recent_texts` (1-minute dedup window) and `meeting_pending_texts`
- Default 12-second throttling to batch snippets into `meeting_segments`
- Idempotent `finalize`: Re-send previous summary on duplicate triggers
- Graceful degradation: Return empty bullets array on exceptions
- Include pending texts in final summary to avoid data loss

---

## Issue: Messages lost when devices were offline
Peer-to-peer messages were being dropped when target devices were offline, with no retry mechanism.

**Solution:**
Implemented lightweight offline queue system:
- `backend/core/utils/offline_queue.py`: JSON-based queue (`backend/data/offline_peer_queue.json`)
- Maximum 100 messages per device, 3-day TTL
- Auto-enqueue on delivery failure
- Auto-flush and deliver when device comes online
- Enhanced receipts with `enqueued` field listing successfully queued targets
- Delivery statistics in logs showing `sent/dropped` counts

---

## Issue: WebSocket handshake path extraction failing across different library versions
Different versions of the websockets library exposed the request path through different attributes, causing handshake failures.

**Solution:**
Multi-attribute fallback approach in `backend/core/websocket_server.py` and `backend/core/connection.py`:
- Try multiple path attributes: `path`, `request_uri`, `raw_request_uri`, `request_path`, `raw_path`
- Implement handshake cache: Store parsed IDs in `_handshake_cache[id(conn)]` during HTTP upgrade
- Enhanced diagnostics: Log `rawPaths` snapshot (first 256 chars) for debugging
- Fallback to cached values if direct extraction fails

---

## Issue: Workflow tasks showing across all devices instead of group isolation
All connected devices were receiving all workflow updates, causing data leakage and unnecessary updates.

**Solution:**
Implemented group-based task isolation:
- Calculate `groupKey` from device ID (first 8 characters)
- `backend/core/utils/tasks_store.py`: Add group-aware methods (`list_by_group`, `upsert_fields`, `delete_by_ids_and_group`)
- `backend/core/handle/workflow_handle.py`: Construct and broadcast group-specific payloads
- Support group override: Allow explicit `groupKey` in message to target specific groups

---

## Issue: Workflow schema too strict for field-level updates
The schema required all fields for updates, preventing partial field updates and causing validation failures.

**Solution:**
Relaxed schema validation in `backend/core/utils/schema.py`:
- Made `title`, `priority`, `status` optional for `update` events
- Only validate fields when present (priority: 0-3, status: open|done)
- Added support for `delete` event with `ids` array
- Enable field-level updates without overwriting entire task

---

## Issue: LLM integration failures not observable
When LLM calls failed (wrong API key, endpoint, or model), errors were silent or unclear.

**Solution:**
Enhanced LLM error handling and debugging:
- `backend/core/providers/llm/openai/openai.py`: Add explicit diagnostic logs for base_url, api_key, and model
- `backend/core/handle/meeting_handle.py`: 
  - Log system_prompt and user_prompt before LLM call
  - Log raw LLM response and parsed JSON
  - Print truncated preview when response is non-JSON
  - Show configuration check hints when bullets remain empty
  - Full traceback on exceptions

---

## Issue: Meeting duration showing as "00:00:00" for empty meetings
When meetings had no segments, the duration was hardcoded to zero instead of actual elapsed time.

**Solution:**
Fixed duration calculation in `backend/core/handle/meeting_handle.py`:
- Calculate duration from `start_time` to `now` when no segments exist
- Maintain accurate timing even for meetings without content
- Ensure duration reflects actual meeting length in all cases

---

## Issue: Audio-to-meeting pipeline disconnected
ASR transcriptions from audio weren't being integrated into the meeting summary system.

**Solution:**
Connected audio pipeline in `backend/core/handle/receiveAudioHandle.py`:
- In meeting mode, wrap ASR text as `meeting.snippet` 
- Inject through `handle_meeting_message` to reuse deduplication and throttling
- Maintain consistent processing path for both text and audio inputs

---

## Issue: Meeting summaries lacking structure
Meeting summaries were unstructured text, making it difficult to extract actionable items.

**Solution:**
Implemented structured summary format:
- Extended schema with `decisions`, `actions`, `risks`, `nextSteps` fields
- Enforce strict JSON output from LLM with structured prompts
- Add deduplication and length truncation for each field
- Heuristic fallback when bullets are empty
- Include transcript with last 50 segments including timestamps

---

## Issue: No support for multilingual meetings and industry terminology
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

## Issue: No speaker identification in meeting transcripts
Meeting transcripts didn't indicate who said what, making it difficult to follow conversations.

**Solution:**
Added speaker tracking:
- Extended schema with `speakerId` field in meeting items
- Derive speaker ID from device ID in audio handler
- Persist speaker information in segments and transcripts
- Enable frontend to group or filter by speaker

---

## Issue: Long meetings losing context without intermediate summaries
Extended meetings would accumulate too much content without intermediate checkpoints.

**Solution:**
Implemented checkpoint system:
- Active state persistence in `backend/data/meetings/active_{device_id}.json`
- Automatic state recovery on reconnection
- Periodic summaries every `checkpoint_interval_min` (default 10 minutes)
- Incremental summaries marked with `checkpoint: true`
- Final summary includes complete transcript and all checkpoints

---

## Issue: Broadcast messages not reaching other connected devices
Meeting and coding events were only visible to the originating device, not other connected clients.

**Solution:**
Implemented broadcast system:
- `backend/core/handle/meeting_handle.py`: Broadcast snippet, summary, and transcript events
- `backend/core/handle/coding_handle.py`: Broadcast start/stop/clear/log/step/phase events
- Internal `_broadcast_to_others()` function using existing broadcast infrastructure
- Include `from` field to identify message source
- Compatible with both `send_json` and string message formats