# Pain Points from Block 4

## Issue: WebSocket handshake device-id parsing priority incorrect
Initially, the system failed to properly parse device-id from URL query parameters during WebSocket handshake, defaulting to auto-generated IDs instead of using the provided device IDs from hardware devices.

**Solution:**
Fixed parsing priority in `backend/core/connection.py`:
- Prioritized URL Query parameters (`device-id/client-id`) over Headers
- Introduced `_normalize_id()` function to standardize IDs (remove whitespace/quotes, lowercase)
- Added source tracking in logs (query/header) for debugging
- Enhanced error handling for query parsing edge cases

---

## Issue: Case sensitivity mismatch in device ID routing
Device IDs with different cases (uppercase MAC from hardware vs lowercase in system) were not matching, causing routing failures for peer-to-peer messages.

**Solution:**
Standardized all device IDs to lowercase:
- In `backend/core/handle/peerHandle.py`: Normalized `to` list elements before ACL and distribution
- In `backend/core/connection.py`: Applied normalization during registration
- Preserved `broadcast` constant while normalizing actual device IDs

---

## Issue: Auth whitelist case sensitivity blocking valid devices
Authentication whitelist was case-sensitive, causing legitimate devices with uppercase MACs to be rejected even when listed in whitelist.

**Solution:**
Modified `backend/core/auth.py`:
- Convert `allowed_devices` to lowercase during initialization
- Lowercase device-id from headers during authentication comparison
- Maintained backward compatibility with existing configurations

---

## Issue: Meeting duplicate text accumulation
Meeting mode was accumulating duplicate text snippets within short time windows, causing redundant content in meeting summaries.

**Solution:**
Implemented deduplication and throttling in `backend/core/handle/meeting_handle.py`:
- Added `meeting_recent_texts/meeting_pending_texts` at connection level
- Deduplicated texts within 1-minute window
- Implemented 12-second throttling for merging into `meeting_segments`
- Made `finalize` idempotent - reuse previous summary on repeat calls

---

## Issue: Offline devices missing peer messages
When peer messages were sent to offline devices, messages were lost with no delivery mechanism when devices came back online.

**Solution:**
Created offline queue system:
- New `backend/core/utils/offline_queue.py` with lightweight JSON-based queue
- Maximum 100 messages per device with 3-day TTL
- Auto-enqueue on delivery failure with `enqueued` receipt field
- Auto-flush and deliver on device reconnection with statistics logging

---

## Issue: WebSocket path extraction compatibility across versions
Different websockets library versions store path in different attributes, causing handshake parsing failures.

**Solution:**
Added multi-attribute path resolution in `backend/core/websocket_server.py`:
- Try multiple path attributes: `path/request_uri/raw_request_uri/request_path/raw_path`
- Cache parsed values in `_handshake_cache[id(conn)]` during HTTP upgrade
- Fallback to cached values if direct parsing fails
- Enhanced logging with `rawPaths` snapshot for debugging

---

## Issue: Workflow updates causing dirty writes
Multiple clients updating the same workflow task simultaneously were overwriting each other's changes completely rather than merging field updates.

**Solution:**
Implemented field-level updates in `backend/core/handle/workflow_handle.py`:
- Changed from full replacement to field-level merge using `upsert_fields`
- Only update provided fields, preserve others
- Support for `update/delete/complete` events
- Added group-based isolation to prevent cross-contamination

---

## Issue: Workflow schema too restrictive for partial updates
Original schema required all fields for updates, preventing field-level modifications.

**Solution:**
Relaxed schema validation in `backend/core/utils/schema.py`:
- Made `title/priority/status` optional for update events
- Only validate fields when present
- Added support for `delete` event with `ids` array
- Maintained validation rules but applied conditionally

---

## Issue: Workflow broadcasts sent to all devices regardless of relevance
All workflow updates were broadcast to all online devices, causing unnecessary traffic and potential data leakage.

**Solution:**
Implemented group-based broadcast convergence:
- Calculate `groupKey` from device_id first 8 characters
- Only broadcast within same group or session
- Per-group payload construction for targeted delivery
- Support for explicit `groupKey` override in messages

---

## Issue: Audio-to-meeting pipeline disconnected
ASR audio transcriptions were not flowing into meeting summaries, breaking the audio→transcript→summary pipeline.

**Solution:**
Connected pipeline in `backend/core/handle/receiveAudioHandle.py`:
- Route ASR text through `handle_meeting_message` as `meeting.snippet`
- Reuse existing deduplication and throttling logic
- Maintain consistent processing regardless of input source (text/audio)

---

## Issue: Meeting summaries lacking structure
Meeting summaries were unstructured text blobs without actionable items or clear sections.

**Solution:**
Enhanced summary structure in `backend/core/handle/meeting_handle.py`:
- Enforced strict JSON output from LLM
- Added structured fields: `decisions/actions/risks/nextSteps`
- Implemented deduplication and length trimming per field
- Added heuristic fallback for empty bullets

---

## Issue: LLM configuration errors silent and hard to debug
LLM API failures (wrong URL, invalid key, model issues) were failing silently without clear error messages.

**Solution:**
Enhanced LLM error handling and logging:
- Added explicit diagnostic logs showing base_url/api_key/model on errors
- Print LLM raw response preview when not JSON
- Added full traceback for exceptions
- Include configuration check hints in error messages

---

## Issue: Meeting duration showing as 00:00:00 for empty summaries
When no snippets were recorded, meeting duration was hardcoded to zero instead of actual elapsed time.

**Solution:**
Fixed duration calculation in `backend/core/handle/meeting_handle.py`:
- Calculate duration from `start→now` for empty meetings
- Properly format duration even when no segments exist
- Maintain accurate timing regardless of content

---

## Issue: Long meetings losing context without intermediate summaries
Extended meetings accumulated too much content without intermediate checkpoints, risking data loss on disconnection.

**Solution:**
Implemented checkpoint system:
- Active state persistence in `backend/data/meetings/active_{device_id}.json`
- Periodic checkpoints every 10 minutes (configurable)
- Incremental summaries marked with `checkpoint:true`
- Auto-resume on reconnection with state restoration

---

## Issue: No speaker identification in transcripts
Meeting transcripts didn't identify who said what, losing important context about speakers.

**Solution:**
Added speaker tracking:
- Extended schema with `speakerId` field in items
- Derive speaker from device-id in audio handler
- Preserve speaker info through segments and transcripts
- Support for future speaker-based grouping in UI

---

## Issue: Debugging LLM prompts and responses difficult
No visibility into actual prompts sent to LLM or raw responses received, making troubleshooting impossible.

**Solution:**
Added comprehensive LLM debugging in `backend/core/handle/meeting_handle.py`:
```python
# Log system and user prompts before sending
print(f"[DEBUG] system_prompt: {system_prompt}")
print(f"[DEBUG] user_prompt: {user_prompt}")
# Log raw LLM response
print(f"[DEBUG] llm_raw: {llm_raw[:500]}")
# Log parsed JSON
print(f"[DEBUG] json_str: {json_str}")
```

---

## Issue: Meeting and coding events not synchronized across devices
Multiple devices in same session couldn't see each other's meeting snippets or coding status changes in real-time.

**Solution:**
Implemented broadcast mechanism:
- Added `_broadcast_to_others()` helper function
- Broadcast meeting events (snippet/summary/transcript) with `from` field
- Broadcast coding events (start/stop/clear/log/step/phase) for real-time sync
- Reuse existing broadcast infrastructure for consistency