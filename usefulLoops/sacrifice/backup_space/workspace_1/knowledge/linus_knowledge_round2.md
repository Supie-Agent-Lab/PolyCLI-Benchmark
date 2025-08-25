## Core Architectural Patterns & Refactoring

### The 'Monolithic handleTextMessage' Problem

The initial architecture for handling incoming websocket messages revolved around a single, monolithic function: `handleTextMessage`. Over time, as more message types were added, this function grew to over 500 lines of deeply nested `if/elif/else` statements.

**"Before" State:**

The structure was a procedural tangle that was difficult to navigate, debug, and extend. Adding a new message type required finding the correct place in the long `elif` chain and adding more logic, increasing the function's cyclomatic complexity and the risk of introducing regressions.

A simplified conceptual example of the old `handleTextMessage` function:

```python
# WARNING: This is an example of the old, problematic pattern. DO NOT COPY.
async def handleTextMessage(websocket, message):
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        # Handle error
        return

    msg_type = data.get("type")

    if msg_type == "INITIALIZE_SESSION":
        # ~50 lines of initialization logic
        user_id = data.get("userId")
        project_id = data.get("projectId")
        # ... more logic, database calls, file I/O
        await send_initialization_complete(websocket)

    elif msg_type == "UPDATE_FILE_CONTENT":
        # ~80 lines of file update logic
        file_path = data.get("path")
        content = data.get("content")
        if not is_path_safe(file_path):
            # error handling
            return
        # ... more logic, writing to disk, validation
        await send_update_ack(websocket)

    elif msg_type == "EXECUTE_TERMINAL_COMMAND":
        # ~100 lines of terminal execution logic...
        # ... and so on for every single message type.

    else:
        # Gneric error for unknown type
        await send_error(websocket, "Unknown message type")
```

This pattern led to frequent merge conflicts and made it impossible to isolate work. A developer working on terminal execution could easily conflict with another working on file updates.

---

### The Routing Table Pattern Solution

To solve this, we refactored the monolithic function into a **Routing Table** (also known as a Dispatch Map). This pattern decouples the message routing logic from the message handling logic.

**"After" State:**

1.  **Individual Handler Functions:** Logic for each message type was extracted into its own dedicated, single-purpose async function in a separate module (e.g., `handlers/file_handlers.py`, `handlers/session_handlers.py`).

2.  **The `HANDLERS` Dictionary:** A central dictionary, `HANDLERS`, was created to map the string message `type` to its corresponding handler function. This is the "routing table".

    The exact `HANDLERS` dictionary in `message_router.py`:
    ```python
    # In message_router.py

    from .handlers import session_handlers, file_handlers, terminal_handlers

    HANDLERS = {
        "INITIALIZE_SESSION": session_handlers.handle_initialize_session,
        "UPDATE_FILE_CONTENT": file_handlers.handle_update_file_content,
        "EXECUTE_TERMINAL_COMMAND": terminal_handlers.handle_execute_command,
        "FETCH_DIRECTORY_TREE": file_handlers.handle_fetch_directory_tree,
        "CREATE_FILE": file_handlers.handle_create_file,
        # ... all other message types are mapped here
    }
    ```

3.  **Refactored `handleTextMessage`:** The `handleTextMessage` function was reduced to a simple, clean dispatcher. Its only jobs are to parse the message, look up the appropriate handler in the `HANDLERS` dictionary, and invoke it.

    The new, lean `handleTextMessage` function:
    ```python
    # In main_server.py or websocket_server.py

    import json
    import logging
    from .message_router import HANDLERS

    async def handleTextMessage(websocket, message):
        """
        Parses incoming messages, finds the correct handler in the routing table,
        and delegates execution.
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if not msg_type:
                logging.warning("Received message without a 'type' field.")
                # Optionally send an error response
                return

            handler = HANDLERS.get(msg_type)

            if handler:
                # Pass the full message data to the handler
                await handler(websocket, data)
            else:
                logging.warning(f"No handler found for message type: {msg_type}")
                # Optionally send an error for unknown type

        except json.JSONDecodeError:
            logging.error(f"Failed to decode incoming JSON message: {message[:100]}...")
        except Exception as e:
            # Catch-all for unexpected errors within handlers
            logging.exception(f"An unhandled error occurred while processing message: {e}")

    ```
**Benefit:** To add a new message type `FOO_BAR`, a developer simply creates a `handle_foo_bar` function in the appropriate module and adds a single line to the `HANDLERS` dictionary: `"FOO_BAR": handle_foo_bar`. The core routing logic in `handleTextMessage` remains untouched.

---

### The 'send_json' Duplication Problem

The project uses the `websockets` Python library. A breaking change between versions 9.x and 10.x changed the `websocket.send()` method from a regular function to an `async` coroutine. To maintain compatibility during the transition, a defensive `try/except` block was added everywhere a message was sent.

**"Before" State:**

This compatibility check was duplicated across dozens of files and functions, leading to verbose and error-prone code.

An example of the duplicated logic:
```python
# WARNING: This is an example of the old, problematic pattern. DO NOT COPY.

# This block was repeated in over 30 different places in the code.
async def some_feature_handler(websocket, data):
    # ... business logic ...
    response = {"status": "success", "detail": "Feature completed"}
    json_response = json.dumps(response)

    try:
        # This works for websockets >= 10.0
        await websocket.send(json_response)
    except TypeError:
        # This is the fallback for websockets < 10.0, which raises a
        # TypeError if you await a non-coroutine function.
        # The specific error was often "TypeError: 'NoneType' object is not callable"
        # or a RuntimeWarning about a coroutine not being awaited.
        websocket.send(json_response)
```
This pattern violated the DRY (Don't Repeat Yourself) principle and made the business logic harder to read.

---

### The Transport Layer Abstraction Solution

The solution was to create a thin abstraction layer over the raw websocket connection. We introduced a `ConnectionHandler` class that wraps the websocket object and provides standardized `send_text()` and `send_json()` methods. This class contains the compatibility logic in a single, centralized location.

**"After" State:**

1.  **The `ConnectionHandler` Class:** This class is instantiated once per client connection. It determines whether `send()` is async during initialization and uses that knowledge for all subsequent sends.

    The `ConnectionHandler` class in `transport.py`:
    ```python
    import asyncio
    import json
    import logging
    from websockets.server import WebSocketServerProtocol
    from websockets.exceptions import ConnectionClosed

    class ConnectionHandler:
        """
        A wrapper around the raw websocket connection to abstract away transport-layer
        concerns, like library version differences and connection state.
        """
        def __init__(self, websocket: WebSocketServerProtocol, client_id: str):
            self.websocket = websocket
            self.id = client_id
            # Determine if websocket.send is a coroutine *once* at initialization.
            self._send_is_async = asyncio.iscoroutinefunction(self.websocket.send)

        async def send_text(self, message: str):
            """Safely sends a raw text payload, handling different library versions."""
            if self.websocket.closed:
                logging.warning(f"Attempted to send to closed websocket for client {self.id}")
                return
            try:
                if self._send_is_async:
                    await self.websocket.send(message)
                else:
                    self.websocket.send(message) # For older, non-async versions
            except ConnectionClosed:
                logging.info(f"Connection closed for client {self.id} during send.")
            except Exception as e:
                logging.exception(f"Failed to send message to client {self.id}: {e}")

        async def send_json(self, data: dict):
            """Serializes a dictionary to JSON and sends it."""
            try:
                payload = json.dumps(data)
                await self.send_text(payload)
            except TypeError as e:
                logging.error(f"Failed to serialize data to JSON: {e}. Data: {data}")
    ```

2.  **Simplified Call Sites:** All other parts of the application now interact with the `ConnectionHandler` instance instead of the raw websocket object. This makes the application logic clean and focused.

    Refactored `some_feature_handler`:
    ```python
    # The handler now receives a ConnectionHandler instance.
    async def some_feature_handler(connection: ConnectionHandler, data: dict):
        # ... business logic ...
        response = {"status": "success", "detail": "Feature completed"}

        # A single, clean, and predictable call.
        await connection.send_json(response)
    ```

**Benefit:** The websocket version-compatibility logic is now implemented and tested in exactly one place. Application code is simplified, easier to read, and completely unaware of the underlying transport implementation details. If another breaking change occurs in the `websockets` library, we only need to update the `ConnectionHandler` class.

## Critical `asyncio` and Concurrency Patterns

### 1. Unsafe Event Loop Acquisition in `__init__`

This pattern is a frequent source of hard-to-debug concurrency issues where tasks seem to disappear and never run.

**Problem:** Acquiring the event loop in a class constructor (`__init__`) using `asyncio.get_event_loop()`. The constructor is a synchronous method called during object instantiation. At this point, the main `asyncio` event loop for the application may not be running yet, or the current thread might not have a loop set. `asyncio.get_event_loop()` might create a *new, different* event loop that is never actually run by the application's top-level `asyncio.run()`.

**Symptom:** Background tasks created by the object never execute. No errors are thrown. The program seems to "swallow" the tasks.

**Anti-Pattern Example:**

```python
import asyncio
import time

class UnsafeService:
    def __init__(self):
        # ANTI-PATTERN: This may get or create a brand new loop
        # that is NOT the one asyncio.run() will use.
        print("UnsafeService.__init__: Acquiring loop...")
        self.loop = asyncio.get_event_loop() 
        print(f"  -> Loop ID in __init__: {id(self.loop)}")

    async def schedule_work(self):
        print(f"UnsafeService.schedule_work: Current running loop ID is {id(asyncio.get_running_loop())}")
        print("  -> Scheduling task on the loop captured in __init__...")
        # This task is scheduled on the wrong loop and will never run.
        self.loop.create_task(self._do_background_work())
        print("  -> Task seemingly scheduled.")

    async def _do_background_work(self):
        print("!!! This message will NEVER appear !!!")
        await asyncio.sleep(1)

async def main():
    print("Instantiating UnsafeService before the main loop is fully established by run()...")
    service = UnsafeService()
    await asyncio.sleep(0.1) # Give a moment to see the printouts
    await service.schedule_work()
    print("Main function waiting for background task to complete (it won't)...")
    await asyncio.sleep(2)
    print("Main function finished.")

# On many systems, this will show two different loop IDs, and the background task will be lost.
asyncio.run(main())
```

**Solution: Acquire the loop within the coroutine context.**

Always use `asyncio.get_running_loop()` from *inside* an `async def` function. This function correctly returns the currently executing event loop. If called outside of a running loop, it raises a `RuntimeError`, which is desirable behavior as it makes the error explicit and immediate.

**Correct Pattern Example:**

```python
import asyncio
import time

class SafeService:
    def __init__(self):
        # CORRECT: The constructor is clean and does not deal with the loop.
        print("SafeService.__init__: No loop operations.")
        self.background_task = None

    async def schedule_work(self):
        # CORRECT: Get the loop that is guaranteed to be running right now.
        loop = asyncio.get_running_loop()
        print(f"SafeService.schedule_work: Got running loop with ID {id(loop)}")
        print("  -> Scheduling task on the correct, running loop...")
        self.background_task = loop.create_task(self._do_background_work())
        print("  -> Task correctly scheduled.")

    async def _do_background_work(self):
        print(">>> Background task started successfully!")
        await asyncio.sleep(1)
        print(">>> Background task finished.")

async def main():
    print("Instantiating SafeService...")
    service = SafeService()
    await service.schedule_work()
    print("Main function waiting for background task to complete...")
    if service.background_task:
        await service.background_task # Wait for it to finish
    print("Main function finished.")

asyncio.run(main())
```

***

### 2. Silent Task Creation Failure due to Tuple Typo

This is a subtle syntax bug that leads to silent failures, where critical background work is never initiated.

**Problem:** A common typo when creating a task is to add a trailing comma, which accidentally creates a single-element tuple containing the coroutine object instead of passing the coroutine itself.
```python
# The Bug
asyncio.create_task((my_coroutine(),))
```
`asyncio.create_task()` expects a coroutine as its first argument. When it receives a tuple, it raises a `TypeError`. However, because `create_task` is often called in a "fire-and-forget" manner (without being `await`ed or its result being checked), this `TypeError` exception is raised, immediately garbage-collected, and never surfaces in the application logs.

**Symptom:** The coroutine you intended to run as a background task never starts. The application continues to run without any error messages, making it seem like the task was successfully created.

**Buggy Code Example:**

```python
import asyncio

async def critical_update():
    print("!!! CRITICAL UPDATE - This message will NOT appear !!!")

async def main():
    print("Main: Scheduling critical update...")
    
    # BUG: The trailing comma creates a tuple `(coroutine,)`
    # This raises a TypeError that is immediately swallowed.
    asyncio.create_task((critical_update(),))
    
    print("Main: 'Update' scheduled. Program will continue.")
    await asyncio.sleep(1)
    print("Main: Exiting. The critical update never ran.")

asyncio.run(main())
```

**Solution: Use a robust wrapper for creating tasks.**

While being careful to avoid the typo is the immediate fix, a more robust and maintainable pattern is to use a dedicated wrapper function for creating tasks. This provides a single point to add validation, logging, and error handling.

**Recommended Wrapper Pattern:**

```python
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

def safe_create_task(coro, *, name=None) -> asyncio.Task:
    """
    Safely creates a task, adding validation and logging.
    This prevents the silent-failure-on-tuple bug.
    """
    if not asyncio.iscoroutine(coro):
        # This makes the error explicit and debuggable.
        logging.error(f"FATAL: Attempted to schedule a non-coroutine: {coro!r}. Type: {type(coro)}")
        # In a real app, you might want to raise TypeError here
        # to halt on such a critical programming error.
        return None

    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coro, name=name)
    except RuntimeError as e:
        logging.error(f"Failed to create task; no running event loop. Error: {e}")
        return None

# --- Usage Example ---
async def critical_update():
    print(">>> Critical update is running successfully!")

async def main():
    print("Main: Scheduling critical update with the safe wrapper...")
    
    # Correct usage:
    task = safe_create_task(critical_update(), name="updater")
    
    # Example of catching the bug:
    print("\nMain: Attempting to schedule a buggy task...")
    safe_create_task((critical_update(),)) # This will now log a fatal error!
    
    await asyncio.sleep(1)
    if task:
        await task
    print("\nMain: Exiting.")

asyncio.run(main())
```

***

### 3. Asynchronous Logging for Performance and Stability

Blocking I/O operations from standard logging calls can starve the `asyncio` event loop, leading to poor performance and critical failures under load.

**Problem:** Standard logging libraries write to files or `stderr` using blocking I/O calls. In a high-throughput `asyncio` application, if many coroutines attempt to log simultaneously, these blocking calls can stall the entire event loop. When the system is under heavy I/O load, the OS buffer for `stderr`/`stdout` can fill up. A subsequent write would need to block, but since it's called from an `asyncio` context, it instead fails immediately.

**Error Message:** This often manifests as a `BlockingIOError`, which crashes the service.

> `BlockingIOError: [Errno 11] Resource temporarily unavailable`

**Solution: Use a logging library that can offload I/O to a separate thread.**

The `loguru` library provides a simple and effective solution. By setting `enqueue=True` in its configuration, `loguru` will place all log messages into a thread-safe queue. A dedicated background thread, managed by `loguru`, consumes from this queue and performs the actual (blocking) write to the destination (the "sink"). This completely decouples the `asyncio` event loop from the slow I/O, ensuring that logging calls are non-blocking and return instantly.

**Fix/Configuration Example:**

```python
import asyncio
from loguru import logger
import sys

# --- Recommended Loguru Configuration for Asyncio Services ---

# 1. Remove the default, synchronous logger.
logger.remove()

# 2. Add a new sink with enqueue=True to make it async-safe.
# This moves all logging I/O to a separate, background thread.
logger.add(
    sys.stderr,           # The destination for logs (e.g., console, file)
    enqueue=True,         # CRITICAL: This is the magic parameter.
    backtrace=True,       # Best practice: show full stack traces on exceptions
    diagnose=True,        # Best practice: add detailed exception variable info
    level="INFO"
)

logger.info("This is the recommended configuration for production asyncio services.")

# --- Demonstration ---

async def worker(id):
    """A worker that logs frequently."""
    for i in range(5):
        logger.info(f"Worker {id} reporting progress: item {i}")
        await asyncio.sleep(0.01)

async def main():
    logger.info("Starting a high-concurrency simulation.")
    
    # Launching many workers that log in parallel.
    # Without `enqueue=True`, this could cause a BlockingIOError under real load.
    tasks = [worker(i) for i in range(50)]
    await asyncio.gather(*tasks)
    
    logger.success("All workers completed without blocking the event loop.")

# To see the effect, you must run this. The key is that the event loop
# remains responsive even with a flood of log messages.
if __name__ == "__main__":
    # In a real service, you'd run your main async function.
    # We call a dummy main here to showcase the logger's behavior.
    asyncio.run(main())

```

**Rule of Thumb:** For any production `asyncio` service, logging MUST be asynchronous (queue-based). The `loguru` library with `enqueue=True` is the recommended pattern to prevent performance degradation and `BlockingIOError` crashes.

## Feature Deep Dive: Meeting System Lifecycle and Data Persistence

### Long Meeting Persistence Strategy

This strategy is designed to handle long-running meetings (e.g., hours-long sessions generating thousands of transcript snippets) without consuming excessive memory or hitting single-file I/O limits. It relies on a sharding system where meeting transcripts are split into smaller, manageable file segments, with a central index file tracking the overall structure.

#### The `index.json` File

For every meeting session, a corresponding `index.json` file is created. This file is the single source of truth for the meeting's metadata and the location of its data shards. It is updated throughout the meeting's lifecycle.

**Location:** `meetings/{sessionId}/index.json`

**Key Attributes:**

*   `sessionId`: The unique identifier for the meeting.
*   `createdAt`: ISO 8601 timestamp of meeting creation.
*   `status`: The current state of the meeting (`active`, `finalizing`, `finalized`).
*   `totalEntries`: The total count of transcript snippets across all shards and the active buffer. This is critical for pagination calculations.
*   `shards`: An array of objects, where each object points to a data shard file and contains its metadata.

**Example: `meetings/session-af33b1/index.json`**
```json
{
  "sessionId": "session-af33b1",
  "createdAt": "2023-10-27T10:00:00Z",
  "status": "active",
  "totalEntries": 234,
  "shards": [
    {
      "path": "meetings/segments/session-af33b1_shard_0.json",
      "entries": 100,
      "finalizedAt": "2023-10-27T10:15:22Z"
    },
    {
      "path": "meetings/segments/session-af33b1_shard_1.json",
      "entries": 100,
      "finalizedAt": "2023-10-27T10:31:04Z"
    }
  ]
}
```

#### The Sharding and Indexing Mechanism

The core of the persistence strategy is a periodic flush-to-disk mechanism. An in-memory buffer holds incoming transcript snippets for each active meeting.

1.  **Buffering:** New snippets are appended to an in-memory array (the "active segment").
2.  **Trigger:** A background timer or an event count checks the size of this active segment. When the number of entries in the active segment exceeds the shard size threshold of **100 entries**, a sharding operation is triggered.
3.  **Sharding Process:**
    *   A new shard filename is generated: `meetings/segments/{sessionId}_shard_N.json`, where `N` is the next sequential integer (0-indexed).
    *   The 100 snippets from the in-memory active segment are serialized into a JSON array and written to this new file.
    *   **Crucially, the `index.json` file is updated** to add a new object to its `shards` array, pointing to the newly created file.
    *   The in-memory active segment is cleared to begin collecting the next 100 snippets.

**File Structure Example:**
```
meetings/
├── session-af33b1/
│   └── index.json
└── segments/
    ├── session-af33b1_shard_0.json
    └── session-af33b1_shard_1.json
```

**Example Shard File: `session-af33b1_shard_0.json`**
This file is a simple JSON array of transcript objects.
```json
[
  { "speaker": "user1", "timestamp": "10:00:05", "text": "Hello everyone, let's get started." },
  { "speaker": "user2", "timestamp": "10:00:08", "text": "Good morning." },
  // ... 98 more entries
]
```

**Fix / Workaround (Atomic Writes):** To prevent corruption if the server crashes mid-operation, the system follows a "write-then-update" pattern. The shard file (`_shard_N.json`) is fully written and closed *before* the `index.json` file is modified to reference it. This ensures the index never points to a partially written or corrupt shard file.

---

### Meeting Finalization Lifecycle

Properly finalizing a meeting is critical to ensure data integrity and release system resources. This is managed by a state machine and a "triple-protection" mechanism to handle race conditions.

#### State Machine

A meeting progresses through a simple, one-way state machine: `active` -> `finalizing` -> `finalized`. These states are tracked by the `status` flag in the `index.json` file and in the in-memory meeting object.

*   `active`: The meeting is ongoing and accepting new transcript snippets.
*   `finalizing`: The "end meeting" signal has been received. The system is performing its final shutdown tasks. No new data is accepted.
*   `finalized`: All data has been persisted to disk, and all in-memory resources for the session have been cleaned up.

#### The Triple-Protection Mechanism

When a client signals the end of a meeting, the following sequence provides a robust and responsive shutdown process:

1.  **Instant Acknowledgement (ACK):** The API endpoint that receives the "end meeting" request immediately responds with an `HTTP 202 Accepted`. This provides a fast response to the client, which can then update its UI accordingly. The actual finalization work is performed asynchronously in the background.

2.  **Set "Finalizing" Flag to Block New Snippets:** The very first synchronous action the server takes is to set the in-memory state of the meeting to `finalizing`. Any subsequent requests attempting to post new snippets to this `sessionId` will be rejected immediately with an error. This prevents a race condition where a late-arriving snippet could be processed after the finalization has begun.

    **Code Pattern (Snippet Ingestion Endpoint):**
    ```javascript
    function handleNewSnippet(sessionId, snippet) {
      const meeting = getMeetingFromMemory(sessionId);
      if (meeting.status === 'finalizing' || meeting.status === 'finalized') {
        // Reject the request
        throw new MeetingFinalizingError('Meeting is closing and cannot accept new data.');
      }
      //... proceed with processing the snippet
    }
    ```

    **Resulting Error Message:**
    *   **Status Code:** `HTTP 409 Conflict`
    *   **Body:** `{"error": "Meeting is finalizing and cannot accept new data."}`

3.  **Stop Background Timers and Perform Final Flush:**
    *   The background timer responsible for periodic sharding is stopped for this `sessionId`.
    *   A final, one-time flush operation is performed. Any remaining snippets in the "active segment" (even if fewer than 100) are written to a final shard file (e.g., `_shard_2.json`).
    *   The `index.json` is updated a final time:
        *   The last shard is added to the `shards` array.
        *   The `totalEntries` count is finalized.
        *   The `status` is set to `finalized`.
    *   Finally, the in-memory representation of the meeting is destroyed to free up memory.

---

### Paginated Transcript API

This API endpoint allows clients to efficiently retrieve the full meeting transcript in manageable chunks, intelligently reading from the persisted shard files and any in-memory data.

**Endpoint:** `GET /supie/meetings/{sessionId}/transcript`

**Query Parameters:**

*   `offset` (integer, optional, default: `0`): The starting index of the transcript entries to retrieve.
*   `limit` (integer, optional, default: `50`, max: `200`): The maximum number of transcript entries to return.

#### Intelligent Read Logic

The server-side logic is designed to minimize disk I/O and handle requests for data that may span multiple shards or include the most recent, not-yet-persisted snippets.

1.  **Load Index:** The request handler first reads the `meetings/{sessionId}/index.json` file to get the list of shards and the `totalEntries`.
2.  **Calculate Target Shards:** Based on the `offset` and `limit`, the logic calculates which shards need to be read. Since each shard (except the last) contains exactly 100 entries, the calculation is straightforward:
    *   `start_shard_index = floor(offset / 100)`
    *   `end_shard_index = floor((offset + limit - 1) / 100)`
3.  **Read from Shard Files:** The server reads the JSON content from the required shard files (from `start_shard_index` to `end_shard_index`).
4.  **Check In-Memory "Preview" Data:** If the meeting is still `active`, the requested range might include snippets that are still in the in-memory "active segment." The logic checks if `offset + limit` is greater than the total entries stored on disk (`shards.length * 100`). If so, it appends the relevant in-memory snippets to the data retrieved from the disk. This ensures the client gets the absolute latest data.
5.  **Slice and Return:** The combined data from all sources is assembled into a single array. The final slice is taken using the original `offset` and `limit` to create the precise response payload. The local offset within a shard is `offset % 100`.

**Example Request:**

Let's assume the `index.json` from the first section, where 200 entries are on disk and 34 are in memory (`totalEntries: 234`). A client wants the 10 most recent snippets.

**Command:**
```bash
curl -X GET "https://api.example.com/supie/meetings/session-af33b1/transcript?offset=225&limit=10"
```

**Server-Side Logic for this Request:**
1.  Read `index.json`. Total entries = 234. Entries on disk = 200.
2.  Requested range is 225-234. This is entirely contained within the 34 snippets in the in-memory active segment.
3.  No disk I/O is needed. The server accesses the in-memory segment for `session-af33b1`.
4.  It slices the in-memory array from its local index 25 (`225 - 200`) to the end.
5.  It constructs the final JSON response.

**Example Response:**

The response includes the requested data along with pagination metadata for the client.

```json
{
  "metadata": {
    "sessionId": "session-af33b1",
    "total": 234,
    "offset": 225,
    "limit": 10
  },
  "transcript": [
    { "speaker": "user1", "timestamp": "10:41:15", "text": "This is the 226th entry." },
    // ... 8 more entries
    { "speaker": "user2", "timestamp": "10:41:58", "text": "And this is the final thought." }
  ]
}
```

## Feature Deep Dive: Workflow and Peer Messaging Systems

### Workflow Group-Based Isolation

This pattern implements a form of soft multi-tenancy to ensure that devices can only interact with workflows belonging to their designated "group." This prevents data leakage or cross-tampering between different customer deployments or logical device groupings that share the same backend infrastructure.

#### Pattern Description and `groupKey` Derivation

The isolation is achieved by deriving a `groupKey` from the unique `device_id` of each device. All API operations that create, read, update, or broadcast workflows are strictly partitioned by this `groupKey`.

*   **Key Derivation Rule:** The `groupKey` is the first 8 characters of the `device_id`.

*   **Rationale:** This approach is deterministic and stateless. No central lookup table is required to map a device to its group, simplifying the architecture. Any device with a `device_id` sharing the same 8-character prefix is automatically part of the same group.

**Example Code for `groupKey` Generation (Python):**

```python
def get_group_key(device_id: str) -> str:
    """
    Derives the group key from the device ID.
    The group key is the first 8 characters of the device ID.
    """
    if not device_id or len(device_id) < 8:
        raise ValueError("device_id must be at least 8 characters long")
    return device_id[:8]

# --- Example Usage ---
device_id_a = "c0a80101-abcd-1234-efgh-567890ijklmn"
device_id_b = "c0a80101-wxyz-5678-qrst-901234uvwxyz"
device_id_c = "b1b2b3b4-1111-2222-3333-444444444444"

group_key_a = get_group_key(device_id_a)  # "c0a80101"
group_key_b = get_group_key(device_id_b)  # "c0a80101"
group_key_c = get_group_key(device_id_c)  # "b1b2b3b4"

# Devices A and B are in the same group. Device C is in a different group.
print(f"Device A Group: {group_key_a}")
print(f"Device B Group: {group_key_b}")
print(f"Device C Group: {group_key_c}")
```

#### API Endpoint Behavior and Filtering

The derived `groupKey` is implicitly added as a mandatory filter to the data access layer for all workflow operations. A device never provides its `groupKey`; the server derives it from the authenticated device's `device_id`.

*   **List Workflows (`GET /api/workflows`):**
    The query to fetch workflows will always include a `WHERE` clause for the `groupKey`.

    **Pseudo-SQL:**
    ```sql
    -- device_id = "c0a80101-abcd-1234-efgh-567890ijklmn"
    -- derived groupKey = "c0a80101"
    SELECT * FROM workflows WHERE group_key = 'c0a80101';
    ```

*   **Update Workflow (`PUT /api/workflows/{workflow_id}`):**
    To prevent a device from one group from modifying a workflow in another (even if it guesses a valid `workflow_id`), the update operation also includes the `groupKey` check.

    **Pseudo-SQL:**
    ```sql
    -- device_id = "c0a80101-abcd-1234-efgh-567890ijklmn"
    -- derived groupKey = "c0a80101"
    UPDATE workflows
    SET status = 'COMPLETED'
    WHERE id = 'wf-xyz-789' AND group_key = 'c0a80101';
    ```
    If the `group_key` does not match, the update affects 0 rows, and the API returns a `404 Not Found` or `403 Forbidden` error.

*   **Broadcast Workflow Command (`POST /api/workflows/broadcast`):**
    Broadcasts are contained within the group. The command is sent to all devices that share the same `groupKey`.

    **Broadcast Logic:**
    1.  Request is received from a device.
    2.  Server derives the `groupKey` from the source `device_id`.
    3.  Server identifies all active connections (e.g., WebSockets) for devices whose `device_id` starts with the derived `groupKey`.
    4.  The message is sent only to those connections.

#### Troubleshooting and Common Issues

*   **Issue:** A newly provisioned device cannot see workflows that are visible to other devices at the same physical site.
*   **Root Cause:** The `device_id` of the new device likely has a different 8-character prefix than the other devices. This can happen due to a typo during provisioning, a different generation scheme, or manual error.
*   **Solution:**
    1.  **Retrieve** the full `device_id` from the problematic device and a working device from the same group.
        *   Command (example): `cat /etc/machine-id` or check application logs.
    2.  **Verify** the `groupKey` for both.
        *   Problematic Device ID: `c0a80102-abcd-....` -> `groupKey`: `c0a80102`
        *   Working Device ID: `c0a80101-wxyz-....` -> `groupKey`: `c0a80101`
    3.  **Confirm** they are different. The problematic device is in the wrong group.
    4.  **Fix:** The `device_id` of the problematic device must be corrected to match the correct prefix for its intended group. This usually requires re-provisioning or manual adjustment of the ID file.

---

### Peer Messaging Offline Queue

The peer messaging system requires high reliability. If a target device is offline when a message is sent, the message must be queued and delivered upon reconnection. This system evolved from a simple but fragile JSON file implementation to a robust SQLite database.

#### System Evolution: from JSON to SQLite

*   **Initial Implementation (Deprecated):** A single JSON file (`offline_queue.json`) was used to store pending messages.
    *   **Problems Encountered:**
        *   **Race Conditions:** Concurrent message sends from different threads/processes would lead to file corruption, as one process would overwrite changes made by another.
        *   **No Transactional Integrity:** If the server crashed during a write, the file could be left in a malformed state, causing the entire queue to be lost on restart.
        *   **Inefficient Operations:** Deleting a single message or purging expired messages required reading the entire file, modifying it in memory, and writing it back to disk, which was slow and resource-intensive.

*   **Current Implementation (Robust):** A dedicated SQLite database (`offline_queue.db`).
    *   **Advantages:**
        *   **ACID Compliance:** Guarantees atomicity, consistency, isolation, and durability. Operations are transactional, preventing data corruption.
        *   **Concurrency Handling:** SQLite handles file-level locking, preventing concurrent writes from clobbering each other.
        *   **Efficient Queries:** Indexing allows for fast lookups, deletions, and TTL-based purging without scanning the entire dataset.

#### Core Business Rules

The offline queue is governed by two critical business rules to prevent resource exhaustion and stale data.

1.  **Per-Device Queue Limit:** A maximum of **100 messages** can be queued for any single target device.
    *   **Behavior:** If a message is sent to an offline device whose queue is already full, the new message is dropped. An error is logged on the server, but no error is returned to the sender to keep the sending process non-blocking.
2.  **Message Time-To-Live (TTL):** Messages are stored for a maximum of **3 days (72 hours)**.
    *   **Behavior:** A background task runs periodically (e.g., every hour) to purge messages older than the TTL. This prevents the database from growing indefinitely with undeliverable messages for devices that are permanently offline.

#### Database Schema

The SQLite database consists of a single table designed for efficient queuing logic.

**`offline_messages` Table Definition:**
```sql
CREATE TABLE IF NOT EXISTS offline_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_device_id TEXT NOT NULL,
    payload BLOB NOT NULL,
    created_at INTEGER NOT NULL -- Stored as Unix timestamp
);

-- Indexes for efficient lookups and cleanup
CREATE INDEX IF NOT EXISTS idx_target_device_id ON offline_messages (target_device_id);
CREATE INDEX IF NOT EXISTS idx_created_at ON offline_messages (created_at);
```

#### Detailed Message Flow

**1. Enqueue on Send Failure:**
This flow is triggered when a direct peer-to-peer message send fails because the target is not connected.

```plantuml
@startuml
participant Sender
participant Server
participant "SQLite Queue"

Sender -> Server: Send message M to Device B
Server ->> Server: Attempt to find active connection for B
alt Device B is Offline
    Server -> "SQLite Queue": SELECT COUNT(*) WHERE target_device_id = 'B'
    "SQLite Queue" -->> Server: count = N

    alt N < 100
        Server -> "SQLite Queue": INSERT (target_device_id='B', payload=M, ...)
        "SQLite Queue" -->> Server: OK
    else N >= 100
        Server -> Server: Log "Queue full for device B. Message dropped."
    end
else Device B is Online
    Server ->> Sender: (Message sent directly)
end
@enduml
```

**2. Auto-Flush on Device Reconnection:**
This flow is triggered when a device establishes a new connection to the server.

```plantuml
@startuml
participant Device
participant Server
participant "SQLite Queue"

Device ->> Server: Connected (device_id: 'B')
Server -> "SQLite Queue": SELECT id, payload FROM offline_messages \n WHERE target_device_id = 'B' ORDER BY created_at
"SQLite Queue" -->> Server: [msg1, msg2, ...]

loop for each message in list
    Server ->> Device: Send(message.payload)

    alt Send Successful
        Server -> "SQLite Queue": DELETE FROM offline_messages \n WHERE id = message.id
        "SQLite Queue" -->> Server: OK
    else Send Fails
        Server -> Server: Log "Flush failed for msg_id on disconnect. Aborting."
        break Loop
    end
end
@enduml
```

**Key Implementation Fix:** The flush logic is critical. A message must only be deleted from the database *after* it has been successfully delivered to the device. Early implementations that deleted the message before sending risked message loss if the device disconnected during the flush operation. The current "send-then-delete" pattern for each message ensures at-least-once delivery.

## Configuration, Hot-Reloading, and LLM Management

The system's configuration is managed through a central YAML file (`config.yml`) and can be updated at runtime via a specific API endpoint. This design allows for dynamic adjustments to LLM models, behavior, and performance parameters without requiring a server restart.

### 1. LLM Instance Management

To optimize resource usage and prevent memory exhaustion, the system has moved from creating per-connection LLM instances to a shared, server-level registry. This ensures that identical LLM configurations are instantiated only once and shared across all connections that require them.

#### The `WebSocketServer.get_or_create_llm()` Method

The core of this pattern is the `get_or_create_llm()` method on the main server instance. WebSocket connection handlers do not create LLMs directly; they request them from this central factory method.

**Function:** This method is responsible for lazily instantiating and caching `LiteLLM` proxy objects. It uses a sophisticated caching key to ensure that only truly identical configurations are shared.

**Code Snippet (Conceptual):**

```python
# In WebSocketServer class
async def get_or_create_llm(self, alias: str, overrides: dict = None) -> 'LiteLLM':
    """
    Retrieves a cached LiteLLM instance or creates a new one.
    The cache is shared across the entire server.
    """
    overrides = overrides or {}
    # Sort keys to ensure consistent JSON string for the same overrides
    sorted_overrides_str = json.dumps(overrides, sort_keys=True)
    
    # The caching key combines the model alias and its specific configuration
    cache_key = f'{alias}::{sorted_overrides_str}'

    if cache_key not in self._server_llm_cache:
        print(f"Cache miss for key: {cache_key}. Creating new LLM instance.")
        
        # Base model configuration is fetched from the main server config
        model_config = self.config.get('llms', {}).get(alias, {})
        
        # Apply runtime overrides
        final_config = {**model_config, **overrides}
        
        # LiteLLM requires 'model' to be set
        if 'model' not in final_config:
            # Handle error: alias not found in config.yml
            raise ValueError(f"LLM alias '{alias}' not found in server configuration.")
        
        # LiteLLM uses aiohttp.ClientSession for async calls
        # We can reuse a single session for performance
        if not self.http_session:
            self.http_session = aiohttp.ClientSession()

        # Instantiate the LiteLLM proxy object
        self._server_llm_cache[cache_key] = LiteLLM(
            **final_config,
            # Pass the shared session to LiteLLM
            acompletion_kwargs={'session': self.http_session}
        )
        
    return self._server_llm_cache[cache_key]

```

#### The Caching Key Strategy: `f'{alias}::{json.dumps(overrides)}'`

This key is essential for the system's flexibility and efficiency.

*   **`alias`**: This is the friendly name defined in `config.yml` (e.g., `fast_model`, `quality_model`). It points to a base configuration.
*   **`json.dumps(overrides)`**: This part makes the cache dynamic. If a specific connection needs to use the `quality_model` but with a different temperature (e.g., `{"temperature": 0.9}`), this override is converted to a JSON string and appended to the key.

**Example Scenario:**

1.  **Connection A** needs the default analysis model: `get_or_create_llm(alias='analysis_model')`
    *   `overrides` is empty, `json.dumps({})` is `'{}'`.
    *   **Cache Key:** `'analysis_model::{}'`
    *   A new LLM instance is created and stored under this key.

2.  **Connection B** also needs the default analysis model: `get_or_create_llm(alias='analysis_model')`
    *   **Cache Key:** `'analysis_model::{}'`
    *   Cache hit. The existing instance is returned immediately. No new resources are consumed.

3.  **Connection C** needs the analysis model but with higher creativity: `get_or_create_llm(alias='analysis_model', overrides={'temperature': 0.8})`
    *   `overrides` is `{'temperature': 0.8}`.
    *   **Cache Key:** `'analysis_model::{"temperature": 0.8}'`
    *   Cache miss. A new LLM instance is created with `temperature=0.8` and stored under this new key. This instance is distinct from the default one.

This strategy correctly balances resource sharing with the need for runtime configuration flexibility.

### 2. Key Configuration Parameters

Configuration is managed in `config.yml`. Below is a reference for critical parameters.

| Parameter | Type | Default | Description | Example (in `config.yml`) |
| :--- | :--- | :--- | :--- | :--- |
| `server.meeting_api_token` | string | `None` | A **secret bearer token** required for authenticating administrative API calls, such as starting/stopping meetings or hot-reloading the configuration. **CRITICAL for production security.** | `server: { meeting_api_token: 'your-very-secret-token' }` |
| `llm_by_mode` | object | `{}` | Maps a functional "mode" (e.g., `summarization`, `transcription_correction`) to a specific LLM `alias` defined under the `llms` section. This decouples application logic from specific model implementations. | `llm_by_mode: { summarization: 'gpt4_turbo', question_answering: 'haiku' }` |
| `llms.<alias>.model` | string | `None` | The `LiteLLM` model string (e.g., `openai/gpt-4-turbo`, `anthropic/claude-3-haiku-20240307`). This is the primary identifier for the model provider. | `llms: { gpt4_turbo: { model: 'openai/gpt-4-turbo' } }` |
| `llms.<alias>.api_key` | string | `None` | The API key for the specified model. Can also be set via environment variables (e.g., `OPENAI_API_KEY`), which is the recommended practice. | `llms: { gpt4_turbo: { api_key: 'sk-...' } }` |
| `meeting.transcript_push_interval_ms` | integer | `3000` | The interval, in milliseconds, at which the server pushes accumulated transcript chunks to connected clients. Lower values increase real-time feel but also network traffic. | `meeting: { transcript_push_interval_ms: 2500 }` |

### 3. Hot-Reloading Mechanism

The system supports runtime configuration updates without service interruption via an authenticated API endpoint. This is crucial for changing LLM models, adjusting prompts, or tuning performance parameters on a live server.

**Flow:**

1.  An administrator sends a `POST` request to the `/v1/server/config/update` endpoint with the new configuration content in the request body. The request must be authenticated using the `server.meeting_api_token`.

    **Example Command:**
    ```bash
    curl -X POST "http://localhost:8000/v1/server/config/update" \
         -H "Authorization: Bearer your-very-secret-token" \
         -H "Content-Type: application/json" \
         --data-binary "@/path/to/new_config.json"
    ```

2.  The `server.update_config()` method is invoked. It parses the new configuration and updates the server's central `self.config` object in memory.

3.  **Critical Side Effects** are triggered to ensure the new configuration is applied gracefully:

    *   **Side Effect 1: Invalidation of LLM Caches**
        *   **Problem:** The existing, shared LLM instances in `self._server_llm_cache` are now potentially stale. For example, if `llm_by_mode.summarization` was changed from `gpt4_turbo` to `haiku`, any connection using the old instance must be forced to re-request it.
        *   **Solution:** The `update_config` method explicitly clears the server-wide LLM cache.
        ```python
        # In server.update_config() after loading the new config
        print("Configuration updated. Clearing all cached LLM instances.")
        self._server_llm_cache.clear()
        ```
        *   **Result:** The next time *any* part of the code calls `get_or_create_llm()`, it will result in a cache miss. A new LLM instance will be created using the *newly loaded configuration*, effectively applying the change.

    *   **Side Effect 2: "Next Cycle" Update for Timers**
        *   **Problem:** Asynchronous tasks running on a timer (like the transcript pusher controlled by `meeting.transcript_push_interval_ms`) are often in the middle of a `asyncio.sleep()` call. You cannot dynamically change the duration of an in-progress sleep.
        *   **Pattern:** The timer loops are designed to read the configuration value at the *beginning* of each cycle, just before the `sleep`.
        ```python
        # Conceptual code for the transcript pusher task
        async def push_transcripts_loop(self):
            while not self._shutdown_event.is_set():
                # Read the config value AT THE START of the loop
                interval_seconds = self.config.get('meeting.transcript_push_interval_ms', 3000) / 1000.0
                
                # ... perform transcript push logic ...
                
                # Sleep for the duration read in this cycle
                await asyncio.sleep(interval_seconds)
        ```
        *   **Result:** The configuration change is not immediate for these tasks. The current sleep cycle completes using the *old* interval. Once it wakes up, the next loop iteration begins, reads the *new* value from the updated `self.config`, and then uses that new interval for its next sleep. This provides a safe and predictable (though not instantaneous) update pattern.

## Connection Management and Race Condition Mitigation

The reliability of a WebSocket connection is paramount for real-time audio processing. Instability can lead to lost audio, corrupted state, and a poor user experience. This section details the patterns and mechanisms implemented to manage the connection lifecycle, mitigate race conditions, and prevent system hangs.

### 1. Duplicate Connection Handling Evolution

When a client experiences a network disruption, it will attempt to reconnect. How the server handles this new connection attempt for an already-active session (`meeting_id`) is critical. Our approach has evolved through three distinct stages to maximize reliability and prevent data loss.

#### Stage 1: Reject New Connection (Initial Approach)

In this naive implementation, the server maintains a simple map of active `meeting_id`s to their corresponding WebSocket connections.

*   **Logic:** If a new connection request arrives for a `meeting_id` that is already in the active map, the server rejects the new connection outright.
*   **Error Sent to New Client:**
    ```json
    {
      "event": "error",
      "code": 4009,
      "message": "Connection Refused: An active session for this meeting_id already exists."
    }
    ```
*   **Problem:** This approach is brittle. During a typical network blip, the server's TCP keepalive has not yet detected that the old connection is dead. The client, knowing it has disconnected, attempts to reconnect but is rejected. The user is forced to wait until the server-side timeout (which can be 30-60 seconds) cleans up the old connection before they can successfully reconnect. This results in significant perceived downtime and lost audio.

#### Stage 2: Kick Old Connection (Improved Approach)

This stage improves upon the reconnect experience by prioritizing the new connection attempt.

*   **Logic:** When a new connection request arrives for an existing `meeting_id`, the server finds the *old* connection associated with that ID, forcibly closes it, and then accepts the new connection.
*   **Close Code Sent to Old Client:** The server sends a WebSocket close frame with a custom code to inform the old client instance why it was disconnected.
    *   **Close Code:** `4010`
    *   **Reason:** `Session Replaced`
*   **Problem:** While this allows the client to reconnect immediately, it introduces a critical data loss window. There is a small but non-zero gap between the old connection being terminated and the new connection being fully established and ready to stream audio. Any audio spoken by the user during this transition is lost. For many use cases, this loss of the initial part of an utterance is unacceptable.

#### Stage 3: Dual-Channel Transition (Current and Recommended Approach)

This is the most robust solution, designed specifically to prevent audio data loss during a reconnect. It creates a brief, seamless handover period where both the old and new connections are temporarily active.

*   **Logic:**
    1.  A new connection for an existing `meeting_id` arrives.
    2.  The server accepts the new connection immediately, placing it into a "pending promotion" state. Now, two WebSocket connections exist for the same `meeting_id`.
    3.  The server continues to **receive** and process audio from the **old connection**, ensuring no incoming data is lost.
    4.  All outgoing messages from the server (e.g., transcripts, system events) are now routed to the **new connection**.
    5.  A grace period timer is started, configured via `connection.graceful_transition_ms` (e.g., `2000` ms).
    6.  Once the new client has stabilized and sent its first audio packet, or when the grace period timer expires, the server promotes the new connection to "primary" and sends a `4010 - Session Replaced` close frame to the old connection.

*   **Key Benefit:** This approach creates an **atomic handover**. The client can continue streaming audio uninterrupted through the old connection while the new connection is established in the background. By the time the old connection is severed, the new one is already receiving and processing audio, resulting in **zero audio loss** during the reconnect event.

*   **Configuration Example (`config.yaml`):**
    ```yaml
    connection:
      # Time in milliseconds to wait for a new connection to stabilize
      # before closing the old one. During this period, audio is still
      # accepted from the old connection.
      graceful_transition_ms: 2000
    ```

### 2. Race Condition in Meeting Finalization

Finalizing a meeting involves complex operations like generating summaries, calculating analytics, and writing results to a database. If multiple `meeting:finalize` events for the same meeting are processed concurrently, it can lead to data corruption, duplicate entries, or inconsistent state. This is mitigated through a two-pronged approach: a connection-level mutex and application-level idempotency.

#### The Problem: Concurrent Finalization

A client-side bug or a network retry mechanism could cause two `meeting:finalize` requests to be sent and arrive at the server at nearly the same time.

*   **Example Erroneous Client Logic:**
    ```javascript
    // BAD PATTERN: No request tracking
    socket.send(JSON.stringify({ event: 'meeting:finalize' }));
    // ... some time later, on a dubious error condition ...
    socket.send(JSON.stringify({ event: 'meeting:finalize' })); // Second request is sent
    ```
*   **Potential Outcome:** Two server threads could both read the meeting's transcript data, both generate a summary, and both attempt to write to the database, resulting in a classic race condition.

#### Solution Part 1: Connection-Level Mutex

To prevent a single, misbehaving client connection from causing a race condition with itself, we employ an `asyncio.Lock` that is scoped to the connection object.

*   **Pattern:** All critical, state-changing operations are wrapped in an `async with` block that acquires the lock.
*   **Code Snippet (Server-side Python):**
    ```python
    # self.conn represents the connection-specific object
    # self.conn.meeting_finalize_lock is an instance of asyncio.Lock

    async def handle_meeting_finalize(self, msg: dict):
        log.info("Attempting to acquire finalize lock for meeting %s", self.conn.meeting_id)
        async with self.conn.meeting_finalize_lock:
            # --- CRITICAL SECTION ---
            # Only one coroutine per connection can execute this code at a time.
            # If a second 'meeting:finalize' arrives, it will wait here
            # until the first one is complete.
            log.info("Finalize lock acquired for meeting %s", self.conn.meeting_id)

            if await self.is_already_finalized(self.conn.meeting_id):
                log.warning("Meeting %s already finalized. Ignoring request.", self.conn.meeting_id)
                return

            # ... perform expensive and stateful finalization logic here ...
            await self.datastore.write_summary(...)
            await self.set_finalized_flag(self.conn.meeting_id)
            # --- END CRITICAL SECTION ---
        log.info("Finalize lock released for meeting %s", self.conn.meeting_id)
    ```
This lock effectively serializes finalization requests *from the same connection*.

#### Solution Part 2: Idempotency Flags

The mutex solves the problem for a single connection, but not for multiple connections trying to finalize the same meeting (e.g., during a faulty dual-channel transition). For this, we use an idempotency flag in the event payload.

*   **Logic:** The client generates a unique ID for each finalization attempt. The server checks if it has processed this ID before executing the logic.
*   **Client-side Event Payload:**
    ```json
    {
      "event": "meeting:finalize",
      "idempotency_key": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"
    }
    ```
*   **Server-side Check (inside the mutex lock):**
    ```python
    # This logic is inside the 'async with conn.meeting_finalize_lock:' block
    idempotency_key = msg.get("idempotency_key")
    if idempotency_key:
        if await self.redis_cache.exists(f"finalize_key:{idempotency_key}"):
            log.warning("Idempotency key %s already processed. Skipping.", idempotency_key)
            # Optionally, return the cached result of the previous request
            return

    # ... proceed with finalization logic ...

    if idempotency_key:
        # Mark this key as processed with a TTL
        await self.redis_cache.set(f"finalize_key:{idempotency_key}", "processed", ex=3600)
    ```
This defense-in-depth strategy ensures that even if multiple requests get through, the meeting is only finalized once.

### 3. VAD Fallback Logic for Manual Listen Mode

To give clients maximum control, the system supports a "manual listen mode." However, this introduces the risk of a client disconnecting or crashing while the server is in a listening state, leading to a hung process. A fallback mechanism prevents this.

#### The Scenario: Manual Listen Mode

A client can request to manage the listening state manually, bypassing server-side Voice Activity Detection (VAD) for starting and stopping a turn.

1.  Client sends `listen.start` with a `manual` flag.
2.  Server starts ingesting audio, but does **not** run its own VAD to detect the end of speech.
3.  Server waits indefinitely for the client to send a `listen.stop` event.

*   **Client Event to Start Manual Listening:**
    ```json
    {
      "event": "listen.start",
      "manual": true
    }
    ```

#### The Risk: Indefinite Hangs

If the client crashes, loses its connection permanently (and reconnect logic fails), or has a bug that prevents it from sending `listen.stop`, the server-side meeting process will remain in the listening state forever. It will never finalize the turn, never process the transcript, and its resources will never be released, causing a resource leak.

#### The Solution: Configurable Fallback Timeout

A server-side safety net timer is triggered whenever a manual listening session starts.

*   **Configuration:** A timeout is defined in the system configuration.
    ```yaml
    meeting:
      # If a client starts manual listening and does not send 'listen.stop'
      # within this many milliseconds, the server will force-fallback to
      # its own VAD to prevent the meeting from hanging indefinitely.
      manual_listen_fallback_ms: 15000
    ```
*   **Logic:**
    1.  Upon receiving `{"event": "listen.start", "manual": true}`, the server starts a 15-second (based on config) timer.
    2.  If a `listen.stop` event is received from the client before the timer fires, the timer is cancelled, and normal processing continues.
    3.  If the timer fires, the server takes over automatically:
        *   It logs a warning: `WARN: Manual listen fallback triggered for meeting_id [xyz]. Client failed to send listen.stop within 15000ms.`
        *   It stops ingesting new audio for the current turn.
        *   It runs its internal server-side VAD on the audio buffer it has collected to cleanly determine the end-of-speech and finalize the turn.

This pattern ensures that client-side failures do not lead to server-side instability or resource exhaustion, making the system more robust against unpredictable client behavior.

## Error Handling, Data Integrity, and System Robustness

To ensure the system is production-ready, we employ several patterns to guarantee data integrity, handle unexpected outputs, and fail gracefully without crashing or corrupting data.

### 1. Atomic File Writes for Data Integrity

**Problem:** A standard `file.write()` operation is not atomic. If the server crashes, is powered off, or the process is killed midway through writing a large JSON file (e.g., a meeting summary), the file can be left in a corrupted state—either empty or partially written. Subsequent processes attempting to read this file will fail, leading to data loss.

**Solution: The "Temporary File + Atomic Replace" Pattern**

We exclusively use this pattern for writing all critical data files, including meeting summaries, `index.json`, and `tasks.json`. The principle is to never modify a known-good file directly. Instead, all write operations are performed on a new, temporary file. Only after the write operation completes successfully is the original file replaced with the new one in a single, atomic step.

**How It Works:**

1.  A temporary filename is generated in the same directory as the target destination file (e.g., `summary.json.tmp_a8b3e1`).
2.  The full JSON content is written and saved to this temporary file.
3.  If the write succeeds without errors, we use `os.replace(tmp_path, final_path)`. This function is an atomic operation at the filesystem level. It instantly renames/moves the temporary file to the final destination path, overwriting the old file if it exists.

**Why This is Robust:**

*   **Crash During Write:** If the system crashes while writing to `summary.json.tmp_a8b3e1`, the original `summary.json` remains untouched and valid. On restart, the incomplete `.tmp` file can be ignored or cleaned up.
*   **Crash During Replace:** The `os.replace()` operation is guaranteed by the operating system to either complete fully or not at all. There is no intermediate state where the destination file is corrupted.

**Implementation Example:**

Here is the utility function used across the application to save JSON data safely.

```python
import os
import json
import uuid

def save_json_atomically(data: dict, filepath: str):
    """
    Saves a dictionary to a JSON file using an atomic write pattern.

    Args:
        data: The Python dictionary to save.
        filepath: The final destination path for the JSON file.
    """
    # Get the directory and create a unique temporary filename
    temp_filepath = f"{filepath}.tmp_{uuid.uuid4().hex}"

    try:
        # 1. Write to the temporary file first
        with open(temp_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        # 2. If write is successful, perform the atomic replace
        os.replace(temp_filepath, filepath)
        print(f"Successfully saved data to {filepath}")

    except Exception as e:
        print(f"Error saving file atomically: {e}")
        # 3. Clean up the temporary file on failure
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        raise
```

---

### 2. LLM Reliability Patterns

**Problem:** LLMs are non-deterministic and can return responses that are not perfectly formatted JSON. Common issues include:
*   Wrapping the JSON object in conversational text (e.g., "Here is the JSON you requested: {...}").
*   Adding trailing commas, which are invalid in the JSON standard.
*   Omitting a starting or closing curly bracket.

A naive call to `json.loads()` on such a response would raise a `json.JSONDecodeError` and crash the processing pipeline.

**Solution: Two-Layer Defense Strategy**

We use a combination of proactive prompt engineering and reactive parsing fallbacks to handle these cases.

**Layer 1: Proactive Prompt Engineering**

The first line of defense is to design prompts that explicitly instruct the LLM to produce clean, valid JSON. We provide a clear structure, describe each field, and demand JSON-only output.

*   **Prompt Snippet Example:**

    ```
    Your task is to act as a meeting summarizer. Analyze the provided transcript and generate a JSON object containing the summary, decisions, and action items.

    Do NOT include any explanatory text before or after the JSON object.
    Your output MUST start with `{` and end with `}`.

    The JSON object must have the following structure:
    {
      "title": "会议标题",
      "summary": "一段式会议摘要，总结会议的核心内容和目标。",
      "decisions": [
        "识别已达成的决定。这是一个字符串数组。"
      ],
      "action_items": [
        {
          "task": "具体的任务描述。",
          "assignee": "负责人姓名，如果未指定则为 '未分配'。",
          "due_date": "截止日期，格式为 YYYY-MM-DD，如果未提及则为 '未指定'。"
        }
      ]
    }
    ```

**Layer 2: Robust Parsing with a "Bracket Extraction" Fallback**

Even with careful prompting, malformed outputs can occur. Our parsing logic is designed to handle this.

1.  **Attempt `json.loads()`:** The primary method is to try parsing the entire LLM response text directly.
2.  **Fallback on Failure:** If a `json.JSONDecodeError` is caught, we assume the valid JSON is wrapped in extraneous text. Our fallback logic finds the first opening curly bracket `{` and the last closing curly bracket `}` and attempts to parse the substring between them.

*   **Example Malformed LLM Output:**

    ```text
    Of course! Here is the summary of your meeting in the requested JSON format:
    {
        "title": "Q3 Project Phoenix Planning",
        "summary": "The team aligned on the main objectives for the Q3 launch of Project Phoenix...",
        "decisions": ["We will proceed with the blue-themed UI mockups."],
        "action_items": [
            { "task": "Finalize UI mockups", "assignee": "Alice", "due_date": "2023-09-15" }
        ]
    }
    I hope this helps!
    ```

*   **Parsing Logic Implementation:**

    ```python
    import json

    def parse_llm_json_robustly(response_text: str) -> dict:
        """
        Parses a JSON string from an LLM response, with a fallback
        for extraneous text around the JSON object.
        """
        try:
            # 1. First attempt: parse the whole string
            return json.loads(response_text)
        except json.JSONDecodeError:
            print("Initial JSON parsing failed. Attempting bracket extraction fallback.")
            try:
                # 2. Fallback: find the first '{' and last '}'
                start_index = response_text.find('{')
                end_index = response_text.rfind('}')
                if start_index != -1 and end_index != -1 and start_index < end_index:
                    json_substring = response_text[start_index:end_index + 1]
                    return json.loads(json_substring)
                else:
                    raise ValueError("Could not find a valid JSON object within the response.")
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Robust parsing failed: {e}")
                # In a real scenario, this would either raise the error
                # or return a default object (see Graceful Degradation)
                raise
    ```

---

### 3. Graceful Degradation for LLM Service Unavailability

**Problem:** The external LLM service (e.g., OpenAI API) can be unavailable due to network issues, rate limiting, API key errors, or service outages. An unhandled exception from the API call would crash the entire process, preventing any output from being generated.

**Solution: Hardcoded Default Summary**

If the LLM API call fails and cannot be retried, we do not crash. Instead, we log the error and generate a hardcoded, default summary object. This ensures that:
*   The program completes its execution.
*   A placeholder file is created, preventing downstream processes that expect a file from failing.
*   The user or system administrator is clearly notified of the failure via the file's content and server logs.

**Implementation:**

The API call is wrapped in a `try...except` block. If an exception like `openai.APIError`, `requests.exceptions.ConnectionError`, or a timeout occurs, the `except` block returns a predefined default dictionary.

*   **Default Summary Object:**

    ```json
    {
      "title": "处理失败：无法生成会议摘要",
      "summary": "由于系统无法连接到AI服务或处理时发生内部错误，本次会议的摘要未能生成。请检查服务状态或输入文件，然后重试。",
      "decisions": [],
      "action_items": [],
      "error_state": true
    }
    ```

*   **Code Logic Snippet:**

    ```python
    # A simplified example of the function that calls the LLM
    def get_summary_from_llm(transcript: str) -> dict:
        # The default object to return on failure
        DEFAULT_FAILURE_SUMMARY = {
            "title": "处理失败：无法生成会议摘要",
            "summary": "由于系统无法连接到AI服务或处理时发生内部错误，本次会议的摘要未能生成。请检查服务状态或输入文件，然后重试。",
            "decisions": [],
            "action_items": [],
            "error_state": True
        }

        try:
            # Fictional function to call the LLM API
            response = call_llm_api_with_transcript(transcript)
            
            # Robust parsing is used here
            return parse_llm_json_robustly(response.text)

        except Exception as e:
            # Catch any exception during the API call or parsing
            print(f"FATAL: Could not generate summary. Reason: {e}. Falling back to default object.")
            return DEFAULT_FAILURE_SUMMARY
    ```