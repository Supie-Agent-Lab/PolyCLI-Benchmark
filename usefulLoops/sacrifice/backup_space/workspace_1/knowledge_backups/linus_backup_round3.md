## Core Architectural Patterns & Refactoring History

The server's architecture has undergone several key refactorings to improve maintainability, reduce code duplication, and optimize resource usage. Understanding this evolution is critical for future development.

### 1. From Monolithic `handleTextMessage` to the Routing Table Pattern

**The Anti-Pattern:** The initial implementation funneled all incoming WebSocket messages into a single, large `handleTextMessage` function. This function contained a massive `if/elif/else` chain to determine the message type and delegate to the appropriate logic. This became unmaintainable as new features were added.

**"Before" Conceptual Example:**

```python
# ANTI-PATTERN: A single function handling all message types
async def handleTextMessage(self, message):
    """
    This monolithic handler dispatches actions based on message type.
    It quickly becomes bloated and hard to test or modify.
    """
    logger.info(f"Received message: {message}")
    data = json.loads(message)
    msg_type = data.get("type")

    if msg_type == "configure":
        # ... logic for handling configuration ...
        # ... includes sending responses, error handling, etc. ...
        logger.info("Handling 'configure' message...")
        # ... more logic ...
    elif msg_type == "text_to_text":
        # ... logic for handling text_to_text generation ...
        # ... includes creating LLM, streaming chunks, error handling ...
        logger.info("Handling 'text_to_text' message...")
        # ... more logic ...
    elif msg_type == "get_models":
         # ... logic for listing available models ...
         logger.info("Handling 'get_models' message...")
        # ... more logic ...
    else:
        # ... error handling for unknown message type ...
        error_payload = {
            "type": "error",
            "request_id": data.get("request_id"),
            "error": f"Unknown message type: {msg_type}"
        }
        await self.send_json(error_payload)
```

**The Solution: Routing Table Pattern:** We refactored this into a "Routing Table" pattern. A central dictionary, `HANDLERS`, maps message type strings directly to dedicated handler functions. The main `handleTextMessage` method now simply looks up the appropriate handler in the dictionary and calls it, passing the message data. This makes the code modular, easier to test, and trivial to extend with new message types.

**"After" Implementation:**

The core of this pattern is the `HANDLers` dictionary defined in `server/websockets.py`.

```python
# server/websockets.py

# ... imports of handler functions ...
from .handlers.configure import handle_configure
from .handlers.text_to_text import handle_text_to_text
from .handlers.text_to_speech import handle_text_to_speech
from .handlers.get_models import handle_get_models
from .handlers.interrupt import handle_interrupt

# The Routing Table
HANDLERS = {
    "configure": handle_configure,
    "text_to_text": handle_text_to_text,
    "text_to_speech": handle_text_to_speech,
    "get_models": handle_get_models,
    "interrupt": handle_interrupt,
}

# The new, simplified message dispatcher
async def handleTextMessage(self, message):
    # ... (initial message parsing)
    handler = HANDLERS.get(msg_type)
    if handler:
        await handler(self, data) # Pass self (connection handler) and data
    else:
        # ... (centralized error handling for unknown type) ...
```

### 2. Transport Layer Abstraction

**The Problem:** Many handler functions needed to send JSON data back to the client over the WebSocket. Each implementation included its own `try/except` block to handle `websockets.exceptions.ConnectionClosed` errors. This resulted in significant boilerplate code duplication.

**Example of Duplicated Error Handling:**

```python
# Inside handle_configure.py (before abstraction)
try:
    await self.connection.send(json.dumps(response_payload))
except websockets.exceptions.ConnectionClosed:
    logger.warning("Connection closed while sending config confirmation.")

# Inside handle_text_to_text.py (before abstraction)
try:
    await self.connection.send(json.dumps(chunk_payload))
except websockets.exceptions.ConnectionClosed:
    logger.warning("Connection closed during text stream.")
```

**The Solution: `ConnectionHandler` Wrapper:** We introduced a `ConnectionHandler` class to abstract away the transport layer details. This class wraps the raw WebSocket connection and provides a safe `send_json` method that centralizes the `try/except` logic. Handler functions no longer interact with the raw `connection` object directly, but with this safer wrapper.

**The `ConnectionHandler` Implementation:**

```python
# server/connection_handler.py
import json
import logging
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

class ConnectionHandler:
    """Wraps a WebSocket connection to provide safe, centralized methods."""
    def __init__(self, connection: WebSocketServerProtocol, connection_id: str):
        self.connection = connection
        self.id = connection_id
        # ... other state like config, llms, etc.

    async def send_json(self, data: dict):
        """Safely sends a JSON payload, handling connection errors."""
        try:
            await self.connection.send(json.dumps(data))
        except ConnectionClosed:
            logger.warning(
                f"Attempted to send to closed connection {self.id}. Message was not sent."
            )
        except Exception as e:
            logger.error(f"Error sending message to connection {self.id}: {e}")

    # ... other methods like send_error, etc.
```

### 3. Shared Server-Level LLM Registry

**The Problem:** The initial design created new LLM instances *per connection*. If ten clients connected and all requested the same `llama3` model, the server would load ten separate instances of `llama3` into memory. This was incredibly inefficient, leading to massive memory consumption and slow "first-time" latency for every new client as the model was reloaded.

**The Solution: Server-Level LLM Registry with Caching:** We implemented a global, server-level registry (`LLM_REGISTRY`) to cache and share LLM instances. When a connection requests a model, it calls a central function, `get_or_create_llm`. This function checks if an identical model (based on its alias and configuration overrides) already exists in the registry. If so, it returns the cached instance; otherwise, it creates a new one, adds it to the registry, and then returns it.

**The `get_or_create_llm` Method and Caching Strategy:**

The core of this solution lies in how a unique cache key is generated. The key must uniquely identify a model not just by its name (`alias`), but by its specific configuration (`overrides`). A simple concatenation is not enough, as dictionaries are unordered. The solution is to use a sorted JSON representation of the overrides.

**Exact Command/Code Snippet:**

```python
# server/llm_registry.py
import json
import logging
from typing import Dict, Any

# This is a global, server-level dictionary
LLM_REGISTRY: Dict[str, Any] = {}
logger = logging.getLogger(__name__)

def get_or_create_llm(alias: str, overrides: Dict[str, Any]) -> Any:
    """
    Gets an LLM from the registry. If it doesn't exist for the given
    alias and overrides, it creates, caches, and returns a new instance.
    """
    # The canonical cache key is "alias::{sorted_json_of_overrides}"
    # sort_keys=True is CRITICAL to ensure that {'a':1, 'b':2} and {'b':2, 'a':1}
    # produce the same key.
    cache_key = f"{alias}::{json.dumps(overrides, sort_keys=True)}"

    if cache_key in LLM_REGISTRY:
        logger.info(f"Returning cached LLM instance for key: {cache_key}")
        return LLM_REGISTRY[cache_key]

    logger.info(f"Creating new LLM instance for key: {cache_key}")
    # ... (Actual logic to instantiate the LLM model)
    # from litellm import completion
    # For demonstration, assume a factory function `create_llm_instance`
    new_llm_instance = create_llm_instance(model=alias, **overrides)

    LLM_REGISTRY[cache_key] = new_llm_instance
    return new_llm_instance

# Example Usage within a connection handler:
# self.llm = get_or_create_llm(
#     alias="ollama/llama3",
#     overrides={"temperature": 0.5, "api_base": "http://localhost:11434"}
# )
```

## System Lifecycle: Startup, Shutdown, and Restart

The server's lifecycle is managed through a sequence of well-defined startup, restart, and shutdown procedures. Understanding these processes is critical for deployment, troubleshooting, and development.

### Server Startup Sequence

When the server process is initiated, it performs a series of critical pre-flight checks before it begins accepting connections. These checks are designed to fail fast, preventing the server from starting in a misconfigured or non-functional state.

#### Pre-Flight Startup Checks

1.  **Port Availability Check:**
    Before initializing the full web server (Uvicorn), the application performs a direct socket bind check to ensure the configured host and port are free. This prevents cryptic startup failures from the web server framework and provides a clear, immediate error message if the port is already in use.

    *   **Mechanism:** A standard `socket` object attempts to bind to the `(host, port)` tuple. If it succeeds, the socket is immediately closed, and startup proceeds. If it fails, the application exits with a non-zero status code.
    *   **Code Pattern:**
        ```python
        import socket
        import sys
        
        HOST = "0.0.0.0"
        PORT = 7860
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((HOST, PORT))
        except OSError as e:
            if e.errno == 98: # Address already in use on Linux
                print(f"FATAL: Port {PORT} is already in use. Please check for another running instance or process.", file=sys.stderr)
            else:
                print(f"FATAL: Unexpected OSError when binding to port: {e}", file=sys.stderr)
            sys.exit(1)
        
        # ... proceed with server initialization ...
        ```
    *   **Error Message & Solution:** If the port is occupied, the server will not start and will print a fatal error to `stderr`:
        ```log
        FATAL: Port 7860 is already in use. Please check for another running instance or process.
        ```
        **Solution:** Identify and terminate the process using the port (e.g., with `lsof -i :7860` and `kill <PID>`) or configure the server to use a different port.

2.  **FFmpeg Availability Check (Warning):**
    The server has features, such as processing audio from video files, that depend on the `ffmpeg` command-line tool. Previously, a missing `ffmpeg` executable would cause a hard failure at startup.

    *   **Pattern Change:** This check has been demoted from a fatal error to a warning. The server will now start successfully even if `ffmpeg` is not found in the system's `PATH`.
    *   **Rationale:** This allows the core functionality of the server to be used without requiring `ffmpeg` to be installed, improving flexibility in environments where its specific features are not needed. An attempt to use a feature requiring `ffmpeg` will fail at runtime.
    *   **Log Message:** If `ffmpeg` is not detected, the following warning is logged during startup:
        ```log
        WARN - ffmpeg not found. Features requiring audio/video processing will be disabled. To enable them, please install ffmpeg and ensure it is in your system's PATH.
        ```

### Non-Blocking Server Restart

The server supports a "hot restart" mechanism via a specific API endpoint (e.g., `POST /v1/lifecycle/restart`). This allows for configuration reloads or application updates without killing the orchestrating parent process (like a CI/CD runner or systemd service).

*   **Mechanism:** The restart is handled in a detached, non-blocking way.
    1.  The HTTP request handler for the restart endpoint immediately spawns a new `threading.Thread`.
    2.  The handler returns a `200 OK` response to the client, confirming the restart command was received.
    3.  The new thread executes the restart logic:
        *   It constructs the command to re-launch the server, typically using `sys.executable` and `sys.argv` to replicate the original command.
        *   It uses `subprocess.Popen` to launch the new server process.
        *   Crucially, `Popen` is called with `start_new_session=True` on Linux/macOS (or `creationflags=subprocess.DETACHED_PROCESS` on Windows). This detaches the new process from the current one, making it the leader of a new process group.
        *   `stdout` and `stderr` of the new process are redirected to `os.devnull` to prevent them from being tied to the parent's terminal.
    4.  After successfully launching the new process, the thread triggers the graceful shutdown of the current server process (e.g., by calling `sys.exit(0)`).

*   **Code Example:**
    ```python
    import subprocess
    import sys
    import os
    import threading
    import time
    
    def _restart_in_background():
        """
        This function runs in a separate thread to avoid blocking
        the HTTP response.
        """
        # Give the server a moment to send the HTTP 200 OK response
        time.sleep(1)
    
        # Re-launch the current script in a new, detached process
        args = [sys.executable] + sys.argv
        print(f"Restarting server with command: {' '.join(args)}")
        
        subprocess.Popen(
            args,
            start_new_session=True, # Critical for detaching
            stdout=open(os.devnull, 'w'),
            stderr=subprocess.STDOUT
        )
    
        # Terminate the current process
        sys.exit(0)
    
    def trigger_restart():
        """API endpoint handler."""
        print("Restart command received. Scheduling restart.")
        restart_thread = threading.Thread(target=_restart_in_background)
        restart_thread.daemon = True
        restart_thread.start()
        return {"status": "restarting"}
    
    # In the main app:
    # app.add_api_route("/v1/lifecycle/restart", trigger_restart, methods=["POST"])
    ```

### Resource Cleanup on Connection Close

Proper resource management is enforced when a client connection (e.g., a WebSocket) is terminated. This prevents memory leaks, orphaned tasks, and zombie processes. The following checklist is executed upon every connection closure.

*   **Cancel Asyncio Tasks:** Long-running, connection-specific background tasks are explicitly cancelled to free up the event loop.
    *   `timeout_task.cancel()`: The `asyncio.Task` responsible for monitoring connection inactivity and enforcing a timeout is cancelled.
    *   `coding_insight_task.cancel()`: Any `asyncio.Task` running a deep code analysis or other long-running operation for the specific session is cancelled. A `try...except asyncio.CancelledError` block is used to gracefully handle the cancellation.

*   **Shutdown Thread Pool Executor:** For each connection, a dedicated `ThreadPoolExecutor` is used to run blocking I/O operations without blocking the main async event loop. This executor must be shut down correctly.
    *   `self.executor.shutdown(wait=False, cancel_futures=True)`: This command is used to terminate the executor.
        *   `wait=False`: The shutdown call returns immediately without waiting for currently running futures to complete.
        *   `cancel_futures=True` (Python 3.9+): This is a critical optimization. It cancels any pending tasks in the executor's queue that have not yet started. This prevents work from a closed connection from being senselessly executed.

*   **Clear Caches and State Objects:** All in-memory objects and caches specific to the connection are cleared to release memory.
    *   `self.code_cache.clear()`: The dictionary used for caching file contents or ASTs for the session is cleared.
    *   `self.context = None`: The main context object holding session state is set to `None`.
    *   This ensures that no data from a previous session can accidentally leak into a new one and that the Python garbage collector can reclaim the associated memory.

## Critical `asyncio` & Concurrency Patterns

### 1. Unsafe Event Loop Acquisition

A critical anti-pattern observed was acquiring the asyncio event loop within a class's `__init__` method. This can lead to race conditions and `RuntimeError` exceptions, especially in multi-threaded environments or when the class is instantiated before the event loop is officially running.

**The Problem:** The `asyncio.get_event_loop()` function is context-sensitive. If called from a thread that doesn't have a current event loop set, it will fail. When a class like `ConnectionHandler` is instantiated, the thread context is not guaranteed to have an active loop.

**Incorrect Pattern & Error:**

```python
# ANTI-PATTERN: DO NOT DO THIS
import asyncio

class ConnectionHandler:
    def __init__(self, connection_id):
        self.connection_id = connection_id
        # This is UNSAFE. The loop may not exist or may be the wrong one.
        self.loop = asyncio.get_event_loop() 

    async def process_data(self, data):
        # This might fail if the class was instantiated in a different thread context
        # than the one running the coroutine.
        self.loop.create_task(self.some_background_work(data))

# This can lead to the following error if the handler is created
# in a worker thread before asyncio.run() is called on that thread.
# RuntimeError: There is no current event loop in thread 'Thread-1'.
```

**Correct Pattern & Solution:**

The event loop should be acquired *just-in-time* from within the coroutine that needs it. The `asyncio.get_running_loop()` function is the correct and safe way to do this, as it's guaranteed to be called from within a running coroutine and will always return the correct loop for that context.

```python
# CORRECT PATTERN
import asyncio

class ConnectionHandler:
    def __init__(self, connection_id):
        self.connection_id = connection_id
        # Do not acquire the loop here.

    async def handle_connection(self):
        # ... logic to read data from a stream ...
        # e.g., data = await stream.read()
        await self.process_data(data)

    async def process_data(self, data):
        # Safely get the currently running loop.
        current_loop = asyncio.get_running_loop()
        
        # Now it's safe to create tasks on this loop.
        current_loop.create_task(self.some_background_work(data))
        print(f"[{self.connection_id}] Task created for background work.")

    async def some_background_work(self, data):
        await asyncio.sleep(2) # Simulate work
        print(f"[{self.connection_id}] Background work completed for data: {data}")

```
**Rule of Thumb:** Never store the result of `asyncio.get_event_loop()` in an instance variable (`self.loop`). Always call `asyncio.get_running_loop()` inside your `async` methods when you need to interact with the loop.

---

### 2. Silent Task Creation Failure: The Tuple Typo

A subtle but catastrophic bug was discovered where background tasks were not running, but no exceptions were being thrown. The application appeared to be dropping work silently.

**The Problem:** A typo was introduced when creating a task, wrapping the coroutine in a single-element tuple. `asyncio.create_task()` will happily accept this tuple, create a task for it, and consider the task "done" immediately because evaluating a tuple is not an awaitable operation. The actual coroutine is never scheduled or executed.

**Incorrect Code (Before):**

```python
# BUG: Note the trailing comma, creating a tuple
# This task does nothing and completes instantly and silently.
task = asyncio.create_task((self.process_message(msg),)) 
```

When you inspect this `task` object, its `get_coro()` method would return a tuple `(<coroutine object process_message at ...>,)`, not the coroutine itself. The task is "done" as soon as it's created.

**Correct Code (After):**

The fix is simply to remove the extraneous parenthesis and comma, passing the coroutine object directly to `create_task`.

```python
# CORRECT: The coroutine object is passed directly
task = asyncio.create_task(self.process_message(msg))
```

**Diagnostic Tip:** If you suspect tasks are being dropped, you can use `asyncio.all_tasks()` to get a set of all active tasks and print their contents for inspection. You would have quickly seen tasks whose coroutine was a tuple instead of a coroutine object.

---

### 3. Race Condition Mitigation in `finalize_meeting`

The `finalize_meeting` coroutine, responsible for tearing down a meeting's resources, was susceptible to a classic race condition. It could be called nearly simultaneously for the same meeting ID by different events (e.g., last participant leaves, moderator explicitly ends it), leading to duplicate teardown operations and potential errors.

A two-layer defense strategy was implemented to ensure idempotency.

**Layer 1: Connection-Level `asyncio.Lock`**

A lock is used to prevent the `finalize_meeting` logic from running concurrently *within the same `ConnectionHandler` instance*. This handles the case where a single client connection might send rapid, duplicate requests.

**Code Implementation:**

```python
import asyncio

class ConnectionHandler:
    def __init__(self, connection_id):
        self.connection_id = connection_id
        # A lock specific to this connection handler instance
        self.finalize_lock = asyncio.Lock()
        self.is_finalized = False

    async def finalize_meeting(self, meeting_id):
        # Acquire the lock. If another coroutine in this instance has the lock,
        # it will wait here.
        async with self.finalize_lock:
            # Check a flag to avoid re-entering logic even after the lock is acquired.
            if self.is_finalized:
                print(f"Meeting {meeting_id} already finalized by this handler. Skipping.")
                return

            print(f"Finalizing meeting {meeting_id}...")
            # ... Perform actual resource cleanup (API calls, DB updates) ...
            await asyncio.sleep(1) # Simulate I/O work for cleanup

            self.is_finalized = True
            print(f"Meeting {meeting_id} cleanup complete.")

```

**Layer 2: Server-Side Idempotency Flag in Response**

The `asyncio.Lock` only protects a single instance. If two different server processes or pods receive a request to finalize the same meeting, they would both execute. The ultimate solution is to have the backend service that manages meetings (e.g., a central database or Redis) perform its own check.

The first `finalize` call that reaches the backend succeeds. The backend marks the meeting as "finalized". Subsequent calls for the same meeting ID will be detected by the backend as duplicates. The backend performs no action but returns a specific success response indicating the work was already done.

**Example Client-Server Interaction:**

1.  **Client A** calls `finalize_meeting('meeting-123')`.
2.  Backend receives the request, sees `meeting-123` is active, finalizes it, and marks it as `state: 'terminated'` in the database.
3.  **Client B** calls `finalize_meeting('meeting-123')` 50ms later.
4.  Backend receives the request, looks up `meeting-123`, sees its state is already `'terminated'`.
5.  Backend does nothing but returns a success message to Client B with an extra flag.

**Example Response Payload (JSON):**

This allows the client to know that its command was effectively a NO-OP, but the desired state was achieved.

```json
{
  "status": "success",
  "meeting_id": "meeting-123",
  "message": "Meeting is already finalized.",
  "idempotent": true 
}
```

---

### 4. Avoiding `BlockingIOError` with Asynchronous Logging

Under heavy load, the application was crashing with a `BlockingIOError`. This was traced back to standard synchronous logging calls (`print`, `logging.info`) to stdout.

**The Problem:** In an `asyncio` application, any I/O that blocks the event loop is dangerous. When logging many messages very quickly, the OS buffer for `stdout` can fill up. When this happens, a `print()` or `logging.info()` call will block the entire thread, and therefore the event loop, until the buffer has space. If the event loop is blocked, it can't process other I/O, and `asyncio` detects this, raising an error.

**Error Message:**

```
BlockingIOError: [Errno 11] write could not complete without blocking
```

**Solution: Queue-Based, Asynchronous Logging with `loguru`**

The standard library's `logging` module can be configured for this, but it's complex. The `loguru` library provides a simple, built-in solution using its `enqueue=True` parameter.

When `enqueue=True`, calls to `logger.info()` (or other levels) do not write directly to the destination (the "sink"). Instead, they place the log message into a thread-safe `multiprocessing.Queue`. A separate, internal background thread managed by `loguru` reads from this queue and performs the slow, potentially blocking write operation, leaving the main application's event loop completely unblocked.

**Implementation Example:**

This configuration should be run once at application startup.

```python
import sys
from loguru import logger

# At the start of your application, before starting the event loop
def setup_logging():
    """
    Configures loguru to use a queue, preventing logging calls from
    blocking the asyncio event loop.
    """
    # Remove the default, synchronous logger
    logger.remove() 
    
    # Add a new sink with enqueue=True
    # This automatically creates a background thread to handle writing.
    logger.add(
        sys.stderr,          # The destination for logs
        enqueue=True,        # CRITICAL: This makes the logger async-safe
        level="INFO",        # Set your desired log level
        format="{time} {level} {message}" # Optional: customize format
    )
    
    logger.info("Asynchronous logging configured successfully.")

# --- In your async code, use the logger as normal ---
# This call is now non-blocking. It just puts a message in a queue and returns.
async def some_async_function():
    logger.info("This is an async-safe log message.")
    await asyncio.sleep(1)

```
This pattern completely resolves the `BlockingIOError` and is a mandatory practice for any high-throughput `asyncio` application that performs significant logging.

## Error Handling, Recovery, and Graceful Degradation

### `AttributeError` on `_vad_detection_count` in Voicemail Detection

*   **Symptom:** The application crashes during voicemail processing with the following traceback:
    ```
    Traceback (most recent call last):
      File "/app/voicemail.py", line 123, in process_final_chunk
        if self._vad_detection_count == 0:
    AttributeError: 'Voicemail' object has no attribute '_vad_detection_count'
    ```

*   **Root Cause:** The `self._vad_detection_count` attribute was only initialized within a conditional block in the audio processing loop. In scenarios where this block was never entered (e.g., very short audio clips, or clips that started with silence), the attribute was never created. Later code, assuming the attribute's existence for final logic checks, would then fail.

*   **Solution:** The fix is to ensure the attribute is unconditionally initialized in the object's constructor (`__init__`). This guarantees the attribute always exists, even if its value remains at its initial state.

*   **Code Fix:**
    ```python
    # in voicemail.py

    class Voicemail:
        def __init__(self, *args, **kwargs):
            # ... other initializations ...
            
            # FIX: Unconditionally initialize the counter to ensure it always exists.
            self._vad_detection_count = 0

        def process_audio_chunk(self, chunk):
            is_speech = self.vad.is_speech(chunk)
            if is_speech:
                # This is the block that previously held the only initialization
                self._vad_detection_count += 1
                # ...
    ```

---

### Opus Decoder Stream Corruption and Automatic Reset

*   **Symptom:** After a period of network instability (packet loss, jitter), a user's audio becomes garbled, robotic, or turns to static for all other participants. The stream does not self-correct, even after the network connection stabilizes. There are no application crashes or error logs.

*   **Root Cause:** The Opus decoder is stateful. It relies on a continuous, ordered stream of packets to maintain its internal state. When packets are lost or arrive severely out of order, the decoder's state becomes desynchronized from the audio stream. Any subsequent, perfectly valid packets are then misinterpreted, resulting in corrupted audio output.

*   **Recovery Mechanism:** An automatic decoder reset mechanism was implemented. The server monitors characteristics of the decoded audio stream. If it detects a sustained period of audio that is classified as non-speech/silence *while still receiving RTP packets* from the client, it flags a potential decoder corruption.

*   **Solution Logic:**
    1.  The server's audio processor tracks the number of consecutive audio chunks received from a client that contain no speech.
    2.  If this count exceeds a predefined threshold (e.g., 50 consecutive non-speech chunks, equivalent to ~1 second of audio), it's a strong indicator of a corrupt decoder state.
    3.  The system logs a warning and triggers a decoder reset.
    4.  The reset involves destroying the current Opus decoder instance for that user's stream and creating a fresh one.
    5.  The very next audio packet received from the client will initialize the new decoder, immediately re-synchronizing the stream and restoring correct audio.

*   **Example Code Snippet (Conceptual):**
    ```python
    # In the server-side audio processing loop for a user's stream
    
    if not is_speech(decoded_audio):
        self.consecutive_silence_chunks += 1
    else:
        self.consecutive_silence_chunks = 0

    # THRESHOLD_FOR_RESET is a configurable value, e.g., 50
    if self.consecutive_silence_chunks > THRESHOLD_FOR_RESET:
        log.warning(f"Potential Opus stream corruption for user {self.user_id}. Resetting decoder.")
        # This function destroys the old decoder and creates a new one
        self._reset_decoder()
        self.consecutive_silence_chunks = 0
    ```

---

### ASR Service Initialization Failure on Second Meeting

*   **Symptom:** A user successfully completes a meeting with real-time transcription (ASR). They leave that meeting and immediately join a second meeting. The second meeting fails to start transcription. Logs show errors like "ASR WebSocket connection failed" or a timeout attempting to connect to the ASR service. Restarting the client application resolves the issue.

*   **Root Cause:** The WebSocket connection to the ASR service, established during the first meeting, was not being explicitly closed during the meeting teardown sequence. The underlying connection object (`conn.asr`) was being destroyed, but the socket itself was left in a `CLOSE_WAIT` or similar state by the OS. When the next meeting tried to establish a new WebSocket connection to the same ASR endpoint, the lingering old socket prevented the new connection from being established.

*   **Solution:** Implement an explicit teardown call to the ASR connection object within the meeting cleanup logic. This ensures the WebSocket is properly closed and the underlying socket is released.

*   **Code Fix:** The `conn.asr.stop_ws_connection()` method was added and must be called when a meeting ends.
    ```python
    # in meeting_manager.py

    def end_current_meeting(self):
        """
        Handles all cleanup when a user leaves a meeting.
        """
        if not self.current_meeting:
            return

        # ... other cleanup logic for media, state, etc. ...

        # FIX: Explicitly close the ASR WebSocket connection.
        # This prevents connection issues when joining a subsequent meeting.
        if self.current_meeting.conn and self.current_meeting.conn.asr:
            log.info("Closing ASR WebSocket connection explicitly.")
            self.current_meeting.conn.asr.stop_ws_connection()

        self.current_meeting = None
    ```

---

### Pattern: Atomic File Writes for Critical Data

*   **Problem:** If the application terminates unexpectedly (crash, power loss) while writing to a critical file (e.g., `config.json`, `user_state.dat`), the file can be left partially written and corrupted, potentially preventing the application from starting again.

*   **Pattern:** To prevent corruption, all critical file writes must be atomic. This is achieved by writing the new content to a temporary file first, and only upon successful completion, replacing the original file with the temporary one using an atomic `rename` operation.

*   **Mechanism:**
    1.  Determine the final destination path (e.g., `/data/config.json`).
    2.  Create a unique temporary file path in the *same filesystem* as the destination (e.g., `/data/config.json.tmp.a3b8d9c1`). Writing to the same filesystem is critical for ensuring the final `rename` is an atomic metadata operation.
    3.  Write all new data to the temporary file.
    4.  Force the OS to flush all buffers to disk for the temporary file (`os.fsync()`).
    5.  Use `os.replace(tmp_path, final_path)` to atomically substitute the original file with the new one. `os.replace()` is a cross-platform wrapper for `os.rename()` that will overwrite the destination if it exists.

*   **Example Implementation:**
    ```python
    import os
    import uuid
    import json

    def atomic_write_json(data: dict, path: str):
        """
        Writes JSON data to a file atomically to prevent corruption.
        """
        # A temporary path on the same filesystem is required for atomic os.replace()
        temp_path = f"{path}.tmp.{uuid.uuid4()}"
        
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                # Ensure data is written to the file on disk, not just in a buffer
                f.flush()
                os.fsync(f.fileno())

            # The atomic operation: replaces the original file with the temp file.
            # This is a metadata-only change on most filesystems and is instantaneous.
            os.replace(temp_path, path)
            log.info(f"Atomically wrote to {path}")

        except Exception as e:
            log.error(f"Failed to atomically write to {path}: {e}")
            # Clean up the temporary file if it exists
            if os.path.exists(temp_path):
                os.remove(temp_path)
    ```

---

### Duplicate Connection Handling and Dual-Channel Transition

*   **Problem:** Due to client-side bugs or rapid reconnects after network loss, a single client instance could attempt to establish a second, concurrent connection to the same meeting. This leads to duplicate media streams and inconsistent state on both client and server.

*   **Solution:** A three-stage handling process was implemented to manage these scenarios gracefully.

    *   **Stage 1: Server-Side Rejection:** The server now maintains a set of active connections identified by a `(user_id, device_id)` tuple. If an incoming connection request presents a tuple that is already active, the server immediately rejects the new connection with a specific error code and reason.
        *   **Command:** `HTTP/1.1 409 Conflict`
        *   **Response Body:** `{"error": "DUPLICATE_CONNECTION", "message": "This user/device is already connected to the meeting."}`

    *   **Stage 2: Client-Side Graceful Handling:** The client is programmed to recognize the `DUPLICATE_CONNECTION` error. Instead of showing a generic "Failed to connect" error, it interprets this as a confirmation that its existing connection is still valid. The client silently discards the failed connection attempt and continues with its active session, providing a seamless user experience.

    *   **Stage 3: Dual-Channel Transition (Planned Handover):** In a specific scenario where a client needs to perform a "hot swap" of its connection (e.g., for a seamless client update or recovery), it can initiate a new connection with a special parameter indicating a planned transition.
        *   **Connection Request Payload:** `{..., "transition_from_connection_id": "old_conn_abc123"}`
        *   **Server Logic:** When the server receives a connection request with this key:
            1.  It validates that `old_conn_abc123` is an active connection for the same user.
            2.  It fully establishes the new connection and prepares it to receive media.
            3.  Once the new channel is ready, it sends a `disconnect` message to the `old_conn_abc123`.
            4.  Finally, it promotes the new connection to be the primary one.
        *   This mechanism allows for a zero-downtime connection handover, which is crucial for complex recovery scenarios.

---

### VAD Fallback for Lost `listen.stop` Events

*   **Problem:** The client is responsible for sending `listen.start` and `listen.stop` events based on its local Voice Activity Detection (VAD) to control when the server's ASR is active. If a client hangs or a `listen.stop` message is lost due to network failure, the server might believe a user is speaking indefinitely. This wastes significant ASR processing resources and can lead to erroneous, long transcriptions.

*   **Recovery Mechanism:** A server-side safety net, or "VAD Fallback," was implemented using a timeout. This provides graceful degradation when client-side signals fail.

*   **Mechanism:**
    1.  When the server receives a `listen.start` message from a client, it starts a timer for that user's speech turn.
    2.  The duration of this timer is set by the server configuration value `meeting.manual_listen_fallback_ms` (e.g., `15000` for 15 seconds).
    3.  If the server does not receive a `listen.stop` message before the timer expires, it triggers the fallback logic.
    4.  The fallback logic engages a *server-side* VAD on the user's audio stream. The server will continue to process the audio through its own VAD.
    5.  As soon as the server-side VAD detects a sufficient period of silence, it behaves as if it received a `listen.stop` message, terminating the ASR for that turn and saving resources.

*   **Configuration and Logging:**
    *   **Configuration Key:** `meeting.manual_listen_fallback_ms`
    *   **Example Value:** `15000` (15 seconds). This value is a trade-off: too short, and it may prematurely cut off long-winded speakers; too long, and it wastes more resources in a failure case.
    *   **Server Log Message:** When this mechanism is triggered, a clear warning is logged for debugging purposes.
        ```
        WARN  [Meeting-123] [User-456] VAD Fallback Triggered: No 'listen.stop' received within 15000ms. Engaging server-side VAD to manage turn.
        ```

## Feature Deep Dive: The Meeting System

### Data Persistence for Long Meetings

To handle meetings of arbitrary length without consuming excessive memory, the system employs a sharding and indexing strategy. As a meeting progresses, the live transcript is not held entirely in RAM. Instead, it is periodically flushed to disk in numbered, sequential files called "shards."

#### Sharding and Indexing Strategy

A central `index.json` file within each meeting's data directory acts as the manifest, tracking all metadata and the location of data shards.

1.  **In-Memory Buffer**: A small buffer holds the most recent transcript utterances.
2.  **Flushing Trigger**: Once the buffer reaches a predefined size (e.g., 100 utterances) or a time threshold is met, its contents are written to a new shard file (e.g., `shard_N.json`).
3.  **Index Update**: After successfully writing the shard, the `index.json` file is updated atomically to include a reference to the new shard. This ensures that even if the service restarts, it can reconstruct the entire meeting transcript by reading the index and its referenced shards.

#### `index.json` Structure

This file is the single source of truth for a persisted meeting's structure and status.

```json
{
  "sessionId": "a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890",
  "startTime": "2023-10-27T10:00:00Z",
  "endTime": "2023-10-27T11:30:00Z",
  "status": "finalized",
  "summary": {
    "title": "Q4 Project Sync",
    "key_points": [
      "Finalize budget by EOD.",
      "Alice to send updated design mockups.",
      "Tech debt discussion postponed to next week."
    ],
    "action_items": [
      { "owner": "Bob", "task": "Review and approve the final budget." },
      { "owner": "Alice", "task": "Send updated design mockups to the team." }
    ]
  },
  "shards": [
    {
      "shardId": 0,
      "startTime": "2023-10-27T10:00:00Z",
      "endTime": "2023-10-27T10:15:23Z",
      "utteranceCount": 100,
      "filePath": "shards/shard_0.json"
    },
    {
      "shardId": 1,
      "startTime": "2023-10-27T10:15:24Z",
      "endTime": "2023-10-27T10:30:45Z",
      "utteranceCount": 100,
      "filePath": "shards/shard_1.json"
    }
  ]
}
```

*   `status`: One of `active`, `finalizing`, `finalized`.
*   `summary`: Populated only after successful finalization.
*   `shards`: An array of objects, where each object is a pointer to a shard file containing a chunk of the transcript. `utteranceCount` is critical for calculating offsets for pagination.

#### Shard File System Layout

Each meeting is stored in a dedicated directory named after its `sessionId`.

```
/data/meetings/
└── a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890/
    ├── index.json
    └── shards/
        ├── shard_0.json
        ├── shard_1.json
        └── ...
```

A typical shard file (`shard_N.json`) contains a simple JSON array of utterance objects:

```json
[
  {
    "speaker": "Alice",
    "timestamp": "2023-10-27T10:00:05Z",
    "text": "Okay, let's get started. First on the agenda is the Q4 budget."
  },
  {
    "speaker": "Bob",
    "timestamp": "2023-10-27T10:00:08Z",
    "text": "Right. I've sent the draft a couple of hours ago."
  }
]
```

### State Management & Lifecycle

A meeting progresses through three distinct states, managed by a `status` flag in its `index.json`.

*   **`active`**: The meeting is in progress. The application can append new utterances, which are periodically flushed to new shards. The system primarily interacts with the in-memory buffer and the latest shard file.
*   **`finalizing`**: The meeting has ended, but post-processing (LLM summarization) is not yet complete. In this state, the meeting transcript is **read-only**. No new utterances can be added. This is a critical guardrail to prevent data corruption while the full transcript is being read for summarization. If a request to add an utterance arrives for a `finalizing` meeting, it should be rejected with an error.
    *   **Error Example**: `HTTP 409 Conflict: {"error": "Meeting is currently being finalized and cannot be modified."}`
*   **`finalized`**: Post-processing is complete. The summary has been generated and saved to `index.json`. The entire meeting record, including all shards, is now immutable.

#### Triple-Layer Protection for Finalization

To prevent race conditions where a meeting might be finalized multiple times (e.g., due to duplicate webhook events or API calls), we employ a three-layer defense mechanism.

1.  **Application Logic State Check**: The simplest check. Before initiating the finalization process, the application logic must check the meeting's current status.
    ```python
    # Pseudo-code
    meeting = get_meeting_by_id(session_id)
    if meeting.status != 'active':
        log.warn(f"Finalization for session {session_id} skipped. Status is already '{meeting.status}'.")
        return # Abort
    
    # Proceed with finalization
    meeting.set_status('finalizing') 
    ```

2.  **Idempotent API Endpoint**: The `POST /supie/meetings/{sessionId}/finalize` endpoint is designed to be idempotent. The first successful call will trigger the process, but subsequent calls will see that the state is no longer `active` and will return a success or neutral response without re-triggering the logic.

3.  **Distributed Lock (Redis)**: This is the strongest guarantee, preventing race conditions across multiple server instances or processes. Before beginning finalization, the system acquires a distributed lock.

    *   **Command**: `SET finalization_lock:{sessionId} "in_progress" NX PX 300000`
        *   `finalization_lock:{sessionId}`: The unique key for the lock.
        *   `NX`: "Not Exists". The command will only succeed if the key does not already exist. This is the core of the atomic locking mechanism.
        *   `PX 300000`: "Set expiry in milliseconds". Sets a 5-minute timeout on the lock to prevent it from being held indefinitely if a process crashes.
    *   **Implementation Pattern**:
    ```python
    # Pseudo-code using a redis client
    lock_key = f"finalization_lock:{session_id}"
    if redis_client.set(lock_key, "in_progress", nx=True, px=300000):
        try:
            # Acquired the lock, proceed with safe finalization logic
            # (which includes the application logic state check as well)
            finalize_meeting(session_id)
        finally:
            # Always release the lock
            redis_client.delete(lock_key)
    else:
        log.info(f"Finalization for {session_id} is already in progress by another process.")
        # Another process holds the lock, so this call can safely exit.
    ```

### Paginated Transcript API

The API provides access to the full meeting transcript without loading the entire file into memory, which is crucial for very long meetings.

**Endpoint**: `GET /supie/meetings/{sessionId}/transcript`

**Query Parameters**:
*   `offset` (integer, optional, default: 0): The number of utterances to skip from the beginning.
*   `limit` (integer, optional, default: 100): The maximum number of utterances to return.

**How it Works**:
1.  The API handler reads the `index.json` for the given `sessionId`.
2.  It iterates through the `shards` array in the index, accumulating the `utteranceCount` of each shard to find where the requested `offset` begins.
3.  It identifies the starting shard and the starting index within that shard.
4.  It then reads only the necessary shard files from disk (it might need to read from more than one shard if the requested `limit` spans a shard boundary).
5.  It collects the utterances until the `limit` is reached and returns them as a JSON array.

**Example Request**:
To get the third page of a transcript, with 50 utterances per page (utterances 100-149):
```bash
curl "http://localhost:8080/supie/meetings/a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890/transcript?offset=100&limit=50"
```

### LLM Reliability Patterns

Interacting with LLMs can be unreliable. They can be slow, return malformed data, or fail entirely. The system employs several patterns to mitigate these issues.

#### Bracket-Extraction Parsing Fallback

**Problem**: LLMs sometimes wrap valid JSON in conversational text or markdown code fences. For example: `Here is the JSON you requested: \n\`\`\`json\n{"title": "..."}\n\`\`\``

**Solution**: Instead of relying on `JSON.parse()` to succeed on the raw LLM output, we first attempt to extract a JSON object from the text.

1.  **Primary Strategy**: Attempt to parse the entire response string as JSON.
2.  **Fallback Strategy**: If parsing fails, use a robust method to find the first opening curly brace `{` and the last closing curly brace `}`. Extract the substring between them.
3.  Attempt to parse this extracted substring as JSON. If this also fails, the parsing has failed.

**Pseudo-code Example**:
```python
def parse_llm_json_robustly(response_text: str):
    try:
        # 1. Try direct parsing
        return json.loads(response_text)
    except json.JSONDecodeError:
        log.warn("Direct JSON parsing failed. Attempting bracket extraction fallback.")
        try:
            # 2. Find first '{' and last '}'
            start_index = response_text.find('{')
            end_index = response_text.rfind('}')
            if start_index != -1 and end_index != -1 and end_index > start_index:
                potential_json = response_text[start_index:end_index+1]
                # 3. Try parsing the extracted substring
                return json.loads(potential_json)
            else:
                raise ValueError("Could not find valid JSON brackets in response.")
        except (json.JSONDecodeError, ValueError) as e:
            log.error(f"Fallback JSON parsing failed: {e}")
            return None # Or raise a specific exception
```

#### Detailed Prompt Engineering

To maximize the chance of getting a corrrect, structured response, prompts are highly specific and include examples.

**Good Prompt Example**:
```
SYSTEM: You are a helpful assistant that summarizes meeting transcripts. Your task is to analyze the provided transcript and generate a JSON object containing a concise title, a list of key discussion points, and a list of specific action items.

You MUST follow these rules:
1. Your entire response MUST be a single, valid JSON object.
2. Do NOT include any preamble, explanation, or markdown formatting like ```json.
3. The JSON object must conform to this exact structure: {"title": "string", "key_points": ["string"], "action_items": [{"owner": "string", "task": "string"}]}
4. For action items, the 'owner' must be the name of a person. If no owner is mentioned, use "Unassigned".
5. The title should be no more than 10 words.

USER:
Here is the meeting transcript:
[10:00:05] Alice: Okay, let's get started. First on the agenda is the Q4 budget.
[10:00:08] Bob: Right. I've sent the draft a couple of hours ago. Everyone needs to review and approve the final budget. I need that by end of day.
[10:01:15] Alice: Got it. I'll also send the updated design mockups to the team.
...
```

This prompt is effective because it defines the role, provides an explicit JSON structure, sets constraints, and gives clear instructions on how to handle edge cases ("Unassigned" owner).

#### Hardcoded Default Summary

**Problem**: The external LLM service might be completely unavailable (e.g., returning HTTP 503 Service Unavailable) or time out. This would normally cause the entire finalization process to fail, leaving the meeting stuck in the `finalizing` state.

**Solution**: A `try...except` block wraps the LLM API call. If a critical network error or timeout occurs, instead of failing, the system logs the error and writes a hardcoded, default summary to the `index.json`.

**Logged Error Example**:
`ERROR: LLM service request failed for session a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890. Reason: ConnectionTimeout. Applying default summary.`

**Default Summary Object**:
This allows the meeting to be moved to the `finalized` state, ensuring system stability.
```json
{
  "title": "Meeting Summary Unavailable",
  "key_points": [
    "The automatic summary for this meeting could not be generated due to a temporary service issue."
  ],
  "action_items": []
}
```
This workaround ensures the meeting lifecycle completes. A separate background job or manual process can later identify meetings with this default summary and re-queue them for summarization once the LLM service is restored.

## Feature Deep Dive: Workflow & Peer Messaging

### Group-Based Isolation & the `groupKey`

To ensure data privacy and prevent crosstalk between different sets of devices owned by the same user, all workflow and messaging data is strictly partitioned using a `groupKey`. This key acts as a namespace for all real-time and stored data.

**Derivation:**

The `groupKey` is automatically and deterministically derived from the `device_id` of the first device that establishes a session for a new group. Specifically, it is the **first 8 characters of the `device_id`**.

*   **Example `device_id`:** `a1b2c3d4-e5f6-4a9b-8c7d-0e1f2a3b4c5d`
*   **Resulting `groupKey`:** `a1b2c3d4`

**Implementation:**

Once a client connects and authenticates, its `groupKey` is established. Every subsequent data operation—including reads, writes, and real-time subscriptions—is filtered by this key. This is enforced at the database and pub/sub topic level.

*   **Database Query Example (SQL):** A request to fetch tasks will always include a `WHERE` clause for the current session's `groupKey`.
    ```sql
    -- Fetch tasks ONLY for the active group
    SELECT * FROM tasks WHERE groupKey = 'a1b2c3d4' AND user_id = 'user-123';
    ```

*   **Pub/Sub Topic Example (MQTT/WebSocket):** Clients subscribe to topics that are namespaced with their `groupKey`.
    *   `Command to Subscribe:` `SUBSCRIBE /workflows/a1b2c3d4/updates`
    *   `Command to Publish:` `PUBLISH /workflows/a1b2c3d4/updates '{"taskId": "t-456", "status": "completed"}'`

A device with a `groupKey` of `b2c3d4e5` will be completely unable to see or interact with data from the `a1b2c3d4` group, even if both groups are associated with the same `user_id`.

---

### Offline Message Queueing

When a peer device is offline, messages intended for it are not dropped. Instead, they are persisted in a local offline queue on the sending device. This system has evolved to improve reliability.

**Evolution:**

1.  **Legacy (deprecated):** A simple `queue.json` file was used. This approach suffered from file-locking issues during rapid read/write cycles and was prone to corruption on unclean shutdowns.
2.  **Current:** A lightweight **SQLite** database (`message_queue.db`). This provides transactional integrity, better performance, and resilience against corruption.

**Queue Rules and Limits:**

*   **Storage:** `message_queue.db` file in the application's private data directory.
*   **Queue Capacity:** A hard limit of **100 pending messages** per destination peer device. If the queue is full, new messages intended for that peer are dropped. A warning is logged to the console.
    *   **Example Warning Log:**
        ```
        WARN: Message queue for peer [device-id-of-offline-peer] is full (100 messages). Dropping new message. Payload: {"action":"UPDATE_TASK",...}
        ```
*   **Time-to-Live (TTL):** Messages are automatically purged from the queue after **3 days (72 hours)** if they still cannot be delivered. This is handled by a background job that runs every hour.

**Process Flow:**

1.  Device A attempts to send a message to Device B.
2.  The connection to Device B fails (timeout, network error).
3.  The message is written as a new row into the `message_queue.db` on Device A. The schema includes `target_device_id`, `payload`, `created_at`, and `retry_count`.
4.  The queuing service on Device A retries sending messages from the queue whenever Device B's presence status changes to `online`.
5.  Upon receiving a successful delivery acknowledgement from Device B, the message is permanently deleted from the SQLite queue on Device A.

---

### Workflow Update Mechanism: Field-Level Merging

To prevent race conditions and data loss in multi-device scenarios, the mechanism for updating workflow objects was changed from a full object replacement to a more granular, field-level merge.

**The Problem with Full Object Replacement (Legacy PUT):**

Consider two devices managing the same task list.
1.  Device A updates a task's `status` to `in_progress`.
2.  Simultaneously, Device B updates the same task's `title` to "Revised Task Title".
3.  Device A sends its full task object: `{"id": "t-1", "title": "Original Title", "status": "in_progress"}`.
4.  Device B sends its full task object: `{"id": "t-1", "title": "Revised Task Title", "status": "pending"}`.

The last write wins. If Device B's update arrives last, Device A's status change is lost.

**The Solution: Field-Level Merging (Current PATCH):**

The system now uses a `PATCH`-like methodology where clients send *only the fields that have changed*. The backend intelligently merges these deltas into the existing object.

*   **Example of a PATCH-based update:**
    *   Device A sends only its specific change:
        ```http
        PATCH /api/tasks/t-1
        Content-Type: application/json

        {
          "status": "in_progress"
        }
        ```
    *   Device B sends only its specific change:
        ```http
        PATCH /api/tasks/t-1
        Content-Type: application/json

        {
          "title": "Revised Task Title"
        }
        ```
*   **Result:** The final object on the server is correctly updated with both changes, preserving data integrity:
    ```json
    {
      "id": "t-1",
      "title": "Revised Task Title",
      "status": "in_progress"
    }
    ```

---

### Direct Command Parsing for 'Working Mode'

For common and unambiguous commands within 'working mode,' the system uses direct keyword parsing to bypass the slower, cloud-based NLU (Natural Language Understanding) service. This results in near-instantaneous command execution.

This is a client-side optimization that scans the raw voice transcription for specific keywords.

**Action: Complete Task**
The system listens for phrases indicating a task should be marked as done.

*   **Recognized Keywords/Phrases:**
    *   **English:** `mark done`, `complete task`, `task complete`, `task finished`, `finish this`, `it is done`
    *   **Chinese (Mandarin):** `完成任务` (wánchéng rènwù), `标记为完成` (biāojì wèi wánchéng), `搞定了` (gǎo dìng le), `完成了` (wánchéng le)

*   **Implementation (Conceptual):** The logic involves checking if the transcribed string contains any of the keywords from a predefined list.
    ```javascript
    // Pseudocode for the parsing logic
    function parseDirectCommand(transcript) {
        const lowerTranscript = transcript.toLowerCase();
        const completionKeywords = ['mark done', 'complete task', '完成任务', '搞定了'];

        for (const keyword of completionKeywords) {
            if (lowerTranscript.includes(keyword)) {
                return { action: 'COMPLETE_CURRENT_TASK' };
            }
        }
        // If no keyword is found, return null to proceed to full NLU
        return null;
    }
    ```
If a match is found, the client executes the `COMPLETE_CURRENT_TASK` action locally and syncs the state change. If not, the full transcript is sent to the NLU service for deeper analysis.

---

### Populating `speakerId` from Audio Source

In a multi-device environment, it's critical to know which device originated a command or message. The `speakerId` field serves this purpose by identifying the source of the audio input.

**Mechanism:**

When a user issues a voice command, the device whose microphone captures the audio injects its own **full `device_id`** into the `speakerId` field of any resulting event or message payload. This happens before the message is broadcast to other peers or sent to the backend.

This allows all other system components (other devices, backend logic, analytics) to correctly attribute the action to a specific physical device within the group.

*   **Example Message Payload:**
    A user speaks "Mark this task done" into their headset (Device B), which is part of a group with a smart display (Device A). The headset generates the following message and broadcasts it.

    ```json
    {
      "type": "WORKFLOW_EVENT",
      "groupKey": "a1b2c3d4",
      "speakerId": "headset-device-id-b-789", // The ID of the device that heard the voice
      "target": "all",
      "payload": {
        "action": "UPDATE_TASK",
        "taskId": "task-xyz-123",
        "update_data": {
          "status": "completed"
        }
      }
    }
    ```
The smart display (`device-id-a-456`) receives this message and knows that the action was initiated by the headset, not by a local user interaction.

## Configuration & Hot-Reloading

This section details the key configuration parameters and the mechanism for applying configuration changes to a running server without requiring a restart.

### Key Configuration Parameters

The following table provides a reference for critical configuration parameters, their purpose, and examples. Configuration is typically managed in a `config.yaml` file.

| Parameter | Description | Example Value | Notes & Technical Details |
| --- | --- | --- | --- |
| `llm_by_mode` | A mapping that specifies which Large Language Model (LLM) to use for different operational modes. This is a primary lever for balancing performance and cost. | `yaml llm_by_mode: meeting: "claude-3-opus" idle: "claude-3-haiku"` | **Cost/Performance Benefit:** Use a powerful but expensive model like Opus for core, high-value tasks (e.g., meeting summarization). Use a faster, cheaper model like Haiku for low-stakes, high-frequency tasks (e.g., detecting idle conversation or simple commands), significantly reducing operational costs. The system dynamically selects the LLM based on its current `mode`. |
| `meeting.transcript_push_interval_ms` | The frequency in milliseconds at which the server pushes real-time transcript updates to connected clients. | `500` | A lower value (~250-500ms) provides a more "live" feel but increases network traffic and server load. A higher value (~1000-2000ms) is more efficient but results in noticeable latency for the user. This value can be hot-reloaded. |
| `meeting.manual_listen_fallback_ms` | A failsafe timeout in milliseconds. If a user manually triggers "listen" mode but no speech is detected, the system reverts to its previous state after this duration. | `15000` | This prevents the device from getting "stuck" in a listening state after an accidental trigger. If the `VAD` (Voice Activity Detection) is silent for this entire duration, the listen mode is cancelled. |
| `server.meeting_api_token` | A static bearer token used to authenticate requests to the meeting management API endpoints (e.g., `POST /meeting/start`). | `"sec_a1b2c3d4-e5f6-7890-ghij-klmnopqrstuv"` | **Security Critical:** This token must be present in the `Authorization: Bearer <token>` header for all protected API calls. The server will respond with `401 Unauthorized` if the token is missing or invalid. **Error Example:** `{"error": "Invalid or missing API token"}` |
| `meeting.checkpoint_interval_min` | The interval in minutes for saving a full checkpoint of the meeting state (transcript, summary, participants) to persistent storage. | `10` | This mechanism ensures state can be recovered in case of a server crash or restart. On startup, the system will look for a recent checkpoint file to resume the meeting. The default is 10 minutes. A lower value provides better data safety but increases disk I/O. |
| `meeting_idle_timeout_multiplier` | A multiplier applied to the base system idle timeout when the device is in the `meeting` mode. | `3` | The system may have a global idle timeout of 2 minutes. During meetings, long pauses are common. This multiplier extends the timeout (e.g., 2 mins * 3 = 6 mins) specifically for the `meeting` mode, preventing the system from incorrectly assuming the meeting has ended during a period of silence. |

### Hot-Reloading Mechanism

The server supports updating its configuration on-the-fly without a restart. This is essential for tuning performance, changing models, or updating credentials in a live environment. The process is triggered by an administrative action, such as sending a `SIGHUP` signal to the server process or calling a specific API endpoint.

The core of this mechanism is the `server.update_config()` function. When invoked, it performs the following critical actions:

**1. LLM Cache Invalidation**

The most immediate effect of a configuration update is the invalidation of the LLM client cache.

*   **Trigger:** The `server.update_config()` function is called.
*   **Action:** The function directly executes `conn._llm_cache.clear()`.
*   **Reasoning:** The configuration may have changed `llm_by_mode`, specifying a different model (e.g., switching from "Haiku" to "Sonnet"). The `_llm_cache` stores instantiated LLM clients to avoid the overhead of re-creating them on every request. Clearing the cache forces the application to create a new LLM client using the updated configuration on its very next request. Without this step, the system would continue to use the old, cached client, ignoring the configuration change.

**Code Snippet Context:**

```python
# In the Server class
class Server:
    # ...
    def update_config(self, new_config_data):
        # Step 1: Validate the new configuration
        if not self.validator.validate(new_config_data):
            log.error("Config update failed validation.")
            return False

        # Step 2: Invalidate the LLM client cache
        # This ensures the next LLM call uses the new model config
        log.info("Configuration updated. Invalidating LLM cache.")
        self.conn._llm_cache.clear()

        # Step 3: Atomically swap the configuration object
        self.config = new_config_data
        return True
```

**2. "Next Cycle" Update Pattern for Timers**

Configuration parameters that control the intervals of recurring background tasks (like timers and polling loops) are updated on the "next cycle." They are not applied instantaneously to an in-progress `sleep` or wait period.

*   **Pattern:** A background task's loop is typically structured as `[DO WORK] -> [READ CONFIG] -> [SLEEP]`.
*   **Behavior:** When a configuration is updated, any task currently in its `[SLEEP]` phase will complete its sleep using the **old** interval value. Once it wakes up and re-enters the loop, it will read the **new** configuration value before starting its next sleep period.

**Pseudo-code Example (`transcript_push_interval_ms`):**

This demonstrates how a background thread for pushing transcripts handles a config change.

```python
# Simplified worker thread loop
def transcript_pusher_thread(server_instance):
    while True:
        # 1. DO WORK: Gather and push transcript chunks
        push_latest_transcript_chunks()
        
        # 2. READ CONFIG: Get the latest sleep interval from the live config object
        # The server_instance.config object has been updated by the hot-reload mechanism.
        current_interval_ms = server_instance.config.get(
            'meeting.transcript_push_interval_ms', 1000  # Default value
        )
        
        # 3. SLEEP: The new interval is used for this sleep cycle.
        # If the config was just updated from 1000 to 500, this sleep will be 0.5s.
        time.sleep(current_interval_ms / 1000.0)

```

This pattern ensures stability by preventing running timers from being abruptly terminated or modified mid-cycle.

## Security & API Contracts

### Webhook Signature Verification

To ensure that incoming webhook notifications are genuinely from our system and have not been tampered with, we employ a signature verification mechanism using a shared secret. All outgoing webhooks include a special header, `X-Meeting-Signature`.

Your webhook endpoint must verify this signature before processing the payload.

**Verification Process:**

1.  **Retrieve the Shared Secret:** This secret is provided to you during the webhook configuration process in your developer portal. Treat this secret as a password; it should be stored securely and never exposed on the client-side.
2.  **Extract the Signature:** Get the value of the `X-Meeting-Signature` header from the incoming HTTP request.
3.  **Prepare the Payload:** Use the raw, unmodified request body as the payload for the HMAC calculation. It is critical that the body is not parsed or altered in any way before this step, as even a whitespace change will result in a signature mismatch.
4.  **Calculate the Expected Signature:** Compute an HMAC with the `SHA256` hash function. The key for the HMAC is your shared secret, and the message is the raw request body. The result should be represented as a hexadecimal string.
5.  **Compare Signatures:** Compare the signature extracted from the `X-Meeting-Signature` header with your calculated signature. They must be an exact match. Using a constant-time comparison function is highly recommended to mitigate timing attacks.

**Example Verification in Python:**

```python
import hashlib
import hmac

# Your shared secret key obtained from the developer portal
SHARED_SECRET = b'your_very_secret_key_here'

def verify_webhook_signature(request_body: bytes, received_signature: str) -> bool:
    """
    Verifies the HMAC-SHA256 signature of an incoming webhook.

    :param request_body: The raw body of the HTTP request.
    :param received_signature: The value from the 'X-Meeting-Signature' header.
    :return: True if the signature is valid, False otherwise.
    """
    if not received_signature:
        return False

    # Calculate the expected signature
    hashed = hmac.new(SHARED_SECRET, request_body, hashlib.sha256)
    expected_signature = hashed.hexdigest()

    # Use hmac.compare_digest for secure, constant-time comparison
    return hmac.compare_digest(expected_signature, received_signature)

# --- In your web framework (e.g., Flask) ---
# from flask import request, abort
#
# @app.route('/webhook-receiver', methods=['POST'])
# def handle_webhook():
#     signature = request.headers.get('X-Meeting-Signature')
#     raw_body = request.get_data() # get the raw body
#
#     if not verify_webhook_signature(raw_body, signature):
#         print("ERROR: Invalid signature received!")
#         abort(403) # Forbidden
#
#     # Signature is valid, process the payload
#     payload = request.get_json()
#     # ... do work with payload ...
#     return 'OK', 200

```

**Error Handling:** If signature verification fails, your endpoint should respond with an HTTP `403 Forbidden` status code and discard the request body. Do not process unverified payloads.

***

### API Endpoint Contracts

#### `GET /supie/meetings/{sessionId}/transcript`

This endpoint retrieves the full or partial transcript for a specific meeting session. It supports pagination via query parameters.

**URL Parameters:**
*   `{sessionId}` (string, required): The unique identifier for the meeting session.

**Query Parameters:**
*   `offset` (integer, optional, default: `0`): The number of transcript segments to skip from the beginning. Used for pagination.
*   `limit` (integer, optional, default: `100`, max: `500`): The maximum number of transcript segments to return in a single request.

**Example Request:**

```bash
curl -X GET \
  'https://api.example.com/supie/meetings/a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890/transcript?offset=100&limit=50' \
  -H 'Authorization: Bearer your_api_token'
```

**Example Successful Response (`200 OK`):**

The response is a JSON object containing a list of transcript segments.

```json
{
  "transcript": [
    {
      "segment_id": "seg_101",
      "start_time_ms": 125400,
      "end_time_ms": 128900,
      "text": "Okay, so the next item on the agenda is the Q3 roadmap.",
      "speaker_id": "user_jane_doe",
      "speaker_label": "Jane Doe"
    },
    {
      "segment_id": "seg_102",
      "start_time_ms": 129500,
      "end_time_ms": 131100,
      "text": "Right, let's dive into that.",
      "speaker_id": "user_john_smith",
      "speaker_label": "John Smith"
    }
    // ... up to 50 segments
  ],
  "total_segments": 352,
  "offset": 100,
  "limit": 50
}
```

***

### Peer-to-Peer Messaging System

#### Broadcast Rate Limiting

To prevent system abuse and ensure fair resource allocation, the peer-to-peer messaging system imposes rate limits on messages sent to multiple recipients (broadcasts).

*   **Rule:** A single client may only send one broadcast message (a message with more than one target peer) every **10 seconds**. This was relaxed from a stricter, per-message limit to better accommodate collaborative use cases.
*   **Target Limit:** The maximum number of recipients for a single peer message is controlled by the `max_targets` configuration parameter. This acts as a hard ceiling on the scope of any single broadcast.

**Configuration Example (`config/messaging.yaml`):**

```yaml
# Maximum number of peer_ids that can be specified in the 'targets'
# array of a single peer message.
#
# Default is 25.
max_targets: 25
```

**Error Behavior:** If a client attempts to send a broadcast message before the 10-second cool-down period has elapsed, the message will be dropped, and an error message will be sent back to the originating client's WebSocket connection.

**Example Error Message:**

```json
{
  "type": "system",
  "event": "error",
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "Broadcast rate limit exceeded. Please wait before sending another message to multiple targets.",
  "retry_after_ms": 7500
}
```

#### Offline Message Redelivery Notification

The system supports offline messaging. If a message is sent to a peer who is not currently connected, the system stores the message and attempts to deliver it once the peer reconnects.

To provide a delivery guarantee to the sender, the system sends a notification back to the **original sender** upon successful delivery of a queued message. This confirms that the offline message has reached its target.

**Redelivery Notification Payload:**

This message is sent over the sender's WebSocket connection.

```json
{
  "type": "peer",
  "event": "redelivered",
  "message_id": "msg_xyz789",
  "target_peer_id": "peer_user_bob_456"
}
```

**Payload Fields:**
*   `type`: Always `peer` for peer-messaging related events.
*   `event`: Always `redelivered` to signify this specific notification type.
*   `message_id`: The unique ID of the original message that was successfully delivered. This allows the sender's application to correlate the delivery confirmation with the sent message.
*   `target_peer_id`: The `peer_id` of the recipient who just received the offline message.