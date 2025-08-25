## The Backend-Driven Architecture: A 'Brain' and its 'Limbs'

Our system's core philosophy is built upon a central, backend-driven architecture. This design was not an arbitrary choice but a direct solution to a critical problem discovered early in development: **state drift**.

### The Problem: State Drift and the 'Schizophrenic' Device

The initial prototype allowed the e-ink hardware to manage its own state. For example, a button press on the device itself would cycle it through different display modes (e.g., `weather` -> `calendar` -> `system_stats`). The backend was only aware of these changes if the device explicitly sent an update.

This led to a fundamental inconsistency, or 'state drift', where the backend's understanding of the device's state could diverge from the device's actual state.

**Concrete Example of Failure:**

1.  The device is in `weather` mode.
2.  A user presses a physical button on the device, changing its internal mode to `calendar`. Due to a transient network issue, the status update to the backend fails silently.
3.  **State Drift:** The device is now in `calendar` mode, but the backend's database still records its state as `weather`.
4.  Later, a scheduled background job on the backend runs to refresh the weather data. It queries its state, sees `weather`, generates a new weather image, and pushes it to the device.
5.  The device, expecting calendar data, suddenly has its display overwritten with a weather forecast. To the user, it appears the device has "forgotten" its mode or is behaving erratically.

Debugging this was a nightmare. Backend logs would show a perfectly logical sequence: "Device is in weather mode, I will send updated weather data." There was no record of the user's intent to switch to the calendar. The system became unreliable and unpredictable.

### The Solution: The Backend as the 'Brain'

The 'Backend-Driven Architecture' was established to eliminate state drift entirely. The principle is simple:

*   **The Backend is the 'Brain':** It is the single, undisputed source of truth for all device state, configuration, and display content. It makes all decisions.
*   **The Hardware is a 'Limb':** The e-ink device is a "thin" or "dumb" rendering client. It holds no persistent state of its own between refreshes. Its only job is to ask the brain, "What should I display now?" and render the response.

Under this model, the hardware has one primary loop:

1.  Wake from sleep.
2.  Make an API call to a backend endpoint like `GET /api/v1/device/render_instructions`.
3.  Receive a complete payload from the backend (e.g., a pre-rendered bitmap image).
4.  Display the image on the screen.
5.  Go back to sleep.

Physical button presses on the device do not change the local state. Instead, they simply send an event to the backend, for example: `POST /api/v1/device/events` with a payload of `{"event": "button_1_press"}`. The backend, as the brain, then decides what this event means. It might change the device's mode in its database, and on the *next* poll from the device, it will serve the content for the new mode.

This ensures the system is always in a consistent state. The device display is a direct reflection of the state held in the backend's database.

### Formalizing the Logic: The `EinkRenderEngine` Debate

While the "brain and limbs" model solved the state problem, it created a new architectural question: where should the rendering logic live within the backend?

Initially, the logic was scattered. The `/api/v1/device/render_instructions` endpoint contained a large `if/elif/else` block:

```python
# WARNING: This is an example of the old, "bad" pattern
@app.route('/api/v1/device/render_instructions')
def get_render_instructions():
    device_mode = db.get_device_mode(DEVICE_ID)

    if device_mode == 'weather':
        # ... logic to fetch weather data, create an image, draw text ...
        image = generate_weather_image()
        return send_file(image, mimetype='image/png')
    elif device_mode == 'calendar':
        # ... logic to fetch calendar events, create an image, draw them ...
        image = generate_calendar_image()
        return send_file(image, mimetype='image/png')
    # ... etc ...
```

This approach quickly became unmanageable. Common elements like headers, footers, or font styles had to be duplicated or awkwardly abstracted. Testing a single view in isolation was difficult.

A debate ensued: should we continue with this "fast" but messy approach, or invest time in building a formal rendering system? The decision was to create a dedicated, centralized `EinkRenderEngine`. This decision was a defining moment for the project's engineering values, capturing the sentiment that **"long-term maintainability outweighs initial complexity."**

The `EinkRenderEngine` is a class that decouples the API endpoint from the rendering logic itself.

**A Simplified Representation of the Final Pattern:**

```python
# /render_engine/engine.py

class EinkRenderEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # ... other configurations like fonts, etc.

    def _draw_header(self, image, device_state):
        # ... standardized header drawing logic ...
        pass

    def _render_weather_view(self, data):
        # ... logic specific to rendering weather ...
        pass

    def _render_calendar_view(self, data):
        # ... logic specific to rendering the calendar ...
        pass

    def render(self, mode, data, device_state):
        """
        The main public method. Takes a mode and data, returns an image buffer.
        """
        image = Image.new('1', (self.width, self.height), 255) # 1-bit monochrome

        if mode == 'weather':
            self._render_weather_view(image, data)
        elif mode == 'calendar':
            self._render_calendar_view(image, data)
        else:
            # Render a default error or unknown state view
            pass

        # Always draw common elements
        self._draw_header(image, device_state)

        # ... convert image to buffer and return ...
        return image_buffer
```

The API endpoint becomes clean, simple, and only responsible for orchestration:

```python
# /api/routes.py

render_engine = EinkRenderEngine(width=800, height=600)

@app.route('/api/v1/device/render_instructions')
def get_render_instructions():
    # 1. Get current state from the DB (the source of truth)
    device = db.get_device(DEVICE_ID)

    # 2. Fetch the necessary data for the current mode
    data = data_provider.fetch_data_for_mode(device.mode)

    # 3. Ask the engine to render the image
    image_buffer = render_engine.render(
        mode=device.mode,
        data=data,
        device_state=device.get_state_summary()
    )

    # 4. Send the result to the "limb"
    return send_file(image_buffer, mimetype='image/bmp')
```

This architecture makes the system robust, testable, and easier to extend. To add a new display mode, a developer only needs to add a new `_render_..._view` method to the `EinkRenderEngine` and a new mode option in the backend, without touching the API routing or core state management logic.

## The Rendering & Control Protocol: A Universal Language

All communication between services and devices is managed through a single, unified protocol. This protocol uses a simple, message-based contract built on JSON payloads. It governs both rendering user interfaces on a device's screen and executing device-level control commands. Understanding this contract is fundamental to interacting with any device on the network.

The core of the protocol is a standard message envelope that contains the message `type` and a `body` with the specific payload. Critically, it also includes a `to` field for routing.

### The `to` Field: Targeting Specific Devices

All messages sent from a service to a device *must* include the `to` field to specify one or more recipients.

-   **Structure**: `to: ["device-id-1", "device-id-2", ...]`
-   **Type**: An array of strings.
-   **`device-id` Definition**: The device identifier is **always** the lowercase, colon-separated MAC address of the device's primary network interface. This is a non-configurable, permanent identifier.

**Example: Targeting a single device**
```json
{
  "to": ["0a:1b:2c:3d:4e:5f"]
}
```

**Example: Targeting multiple devices (multicast)**
```json
{
  "to": ["0a:1b:2c:3d:4e:5f", "11:22:33:aa:bb:cc"]
}
```

---

### Primary Message Types

There are four primary message types that form the complete communication loop. Two are initiated by the server/UI (`ui.render`, `device.control`), and two are sent by the device in response (`ui.ack`, `ui.error`).

#### 1. `ui.render`

This is the most common message. It instructs a device to render a specific user interface screen. The content and layout are defined by the "page type + slot content" Rendering DSL within the message `body`.

**Purpose**: To display a user interface on the device's screen.

**Canonical Example**:
```json
{
  "type": "ui.render",
  "to": ["b4:8a:0c:12:ef:99"],
  "correlation_id": "req-12345-abcde",
  "body": {
    "kind": "info_screen",
    "slots": {
      "title": "Welcome, User!",
      "message": "Please tap the screen to begin setup.",
      "icon_url": "https://example.com/icons/welcome.png"
    }
  }
}
```

#### 2. `device.control`

This message sends a non-rendering command to a device. This is used for administrative or hardware-level actions that don't directly involve displaying a UI.

**Purpose**: To execute a system-level command on the device.

**Canonical Example (Reboot)**:
```json
{
  "type": "device.control",
  "to": ["b4:8a:0c:12:ef:99"],
  "correlation_id": "req-67890-fghij",
  "body": {
    "command": "reboot",
    "params": {
      "delay_seconds": 5
    }
  }
}
```

#### 3. `ui.ack`

This message is a positive acknowledgement sent from the device back to the originating service. It confirms that a `ui.render` or `device.control` message was received, parsed, and successfully executed.

**Purpose**: To confirm successful receipt and execution of a command.

**Canonical Example**:
```json
{
  "type": "ui.ack",
  "from": "b4:8a:0c:12:ef:99",
  "correlation_id": "req-12345-abcde",
  "body": {
    "message": "Render 'info_screen' successful."
  }
}
```
*Note: The `correlation_id` is critical. It must match the `correlation_id` of the original request (`ui.render` or `device.control`) so the service can correlate the response to the request.*

#### 4. `ui.error`

This message is a negative acknowledgement sent from the device back to the originating service. It indicates that a command could not be executed and provides a structured error code and details.

**Purpose**: To report a failure in processing a command.

**Canonical Example (Invalid Payload)**:
```json
{
  "type": "ui.error",
  "from": "b4:8a:0c:12:ef:99",
  "correlation_id": "req-11223-xyz",
  "body": {
    "code": "INVALID_PAYLOAD",
    "details": "Field 'body.slots.title' is required for kind 'info_screen' but was not provided."
  }
}
```

---

### The Rendering DSL (`ui.render`)

The power of the `ui.render` message lies in its `body`. The device firmware contains a set of pre-defined UI templates, or "page types". The `body.kind` field selects which template to use, and the `body.slots` object provides the data to populate it.

#### Known `body.kind` Page Types

| `kind` | Description | Expected `slots` |
| :--- | :--- | :--- |
| `info_screen` | A simple, read-only informational screen. | `title` (string), `message` (string), `icon_url` (optional string) |
| `confirmation_dialog` | Presents a message and action buttons (e.g., OK/Cancel). Tapping a button sends an event back to the server. | `title` (string), `message` (string), `actions` (array of objects with `label` and `event_name`) |
| `loading_spinner` | Displays a simple loading animation with an optional message. | `message` (optional string) |
| `numeric_input` | A screen for the user to input a number, typically with a numeric keypad. | `title` (string), `label` (string), `max_length` (integer), `submit_event` (string) |
| `device_status` | Renders a list of key-value pairs, ideal for showing technical status. | `title` (string), `items` (array of objects with `label` and `value`) |
| `error_display` | A standardized screen for showing a fatal error that occurred on the device itself. | `error_code` (string), `error_message` (string) |


**Example of a `confirmation_dialog`:**

```json
{
  "type": "ui.render",
  "to": ["c3:d4:e5:f6:ab:cd"],
  "correlation_id": "req-confirm-del",
  "body": {
    "kind": "confirmation_dialog",
    "slots": {
      "title": "Confirm Deletion",
      "message": "Are you sure you want to permanently delete this item?",
      "actions": [
        { "label": "Cancel", "event_name": "delete_cancelled" },
        { "label": "Delete", "event_name": "delete_confirmed" }
      ]
    }
  }
}
```

---

### Structured Error Handling (`ui.error`)

To enable robust, automated error handling, the `ui.error` message uses a set of standardized codes in the `body.code` field.

| Error Code | Description | Example `details` | Solution / Action |
| :--- | :--- | :--- | :--- |
| `INVALID_PAYLOAD` | The received JSON message was malformed, or required fields were missing. | "Field 'body.kind' is missing." | The client-side service should fix its message generation logic. This is a non-recoverable client error. |
| `RATE_LIMITED` | The device received too many commands in a short period and is throttling requests. | "Rate limit exceeded. Max 10 requests per minute." | The client service must implement an exponential backoff strategy and retry the request later. |
| `UNKNOWN_COMMAND` | The command in a `device.control` message is not supported by the device's firmware. | "Command 'format_disk' is not recognized." | Check device documentation or firmware version for supported commands. Do not retry. |
| `UNKNOWN_KIND` | The `kind` in a `ui.render` message is not a known page type for this device. | "Rendering kind 'fancy_chart' is not supported." | Update device firmware or use a supported `kind`. Do not retry. |
| `RENDERING_FAILED` | The device failed to render the UI for an internal reason (e.g., out of memory, failed to fetch an image). | "Failed to download image from 'icon_url'." | Check the device's local logs for more detail. May be a transient network issue; a retry might succeed. |
| `DEVICE_OFFLINE`| Generated by an intermediary service, not the device itself. Indicates the target device is not connected. | "Device 0a:1b:2c:3d:4e:5f is not connected to the message broker." | Check device power and network connectivity. The service should queue the message or retry after a delay. |

## Fail-Closed Reliability: The ACK-Driven Safety Valve

To prevent system instability caused by unresponsive or overloaded devices, we employ a fail-closed reliability pattern we call the "ACK-Driven Safety Valve." This automated mechanism detects when a device is struggling and temporarily isolates it, preventing a single failing device from creating a cascading failure across the command bus.

The entire process is triggered by a failure to receive an acknowledgment (ACK) for a sent command. It's a critical health monitoring and flow control system that operates in a deterministic three-step sequence.

### The Three-Step ACK Timeout Flow

#### Step 1: Initial Timeout and Single Retry (3-Second Window)

When the command dispatcher sends a command to a device, it starts a 3-second timer.

*   **Trigger**: The system does not receive an ACK for the command's `command_id` within 3 seconds.
*   **Action**:
    1.  A `WARN`-level event is logged, indicating a potential transient issue.
    2.  The system immediately attempts a **single retry** of the exact same command.
*   **Rationale**: Network latency, temporary packet loss, or a momentary heavy load on the device are common. A single, immediate retry is a low-cost way to overcome these transient issues without escalating to a full failure state.

**Example Log Message for a Retry:**
```log
[WARN] ack-timeout, retrying. device=edge-router-01a command_id=c7b1a0f9-e3d2-48a5-92c2-7ab9876ef4de elapsed_ms=3012
```

#### Step 2: Device Freeze on Repeated Failure (30-Second Cooldown)

If the retry also fails to receive an ACK within its own 3-second window, the system concludes that the device is in a non-transient failure state.

*   **Trigger**: The retried command fails to receive an ACK within 3 seconds.
*   **Action**:
    1.  The device is immediately moved into a `FROZEN` state for a fixed duration of **30 seconds**.
    2.  All pending and future commands in the queue for this device are dropped with a `device-frozen` error.
    3.  A critical `ERROR`-level log is generated, clearly marking the event for monitoring and alerting.

**Canonical Log Message for a Device Freeze:**
This is the key indicator of a serious device communication problem.
```log
[ERROR] [FREEZE] device=edge-router-01a seconds=30 reason=ack-timeout
```

#### Step 3: The "Punishment" Phase & Health Probing

During the 30-second freeze, the device is not completely ignored. It enters a "punishment" or "rehabilitation" phase where its operational capacity is severely restricted.

*   **Behavior during Freeze**:
    *   The primary command queue for the device remains halted. No business-logic or high-level configuration commands will be sent.
    *   A separate, low-priority health-check loop is the **only** process allowed to communicate with the frozen device.
*   **Health-Check Command**:
    *   This loop periodically sends a minimal, low-impact command to probe for signs of life. The standard command for this is `net.banner`.
    *   `net.banner` is ideal because it only requires a basic TCP connection and elicits a simple response, testing Layer 4 connectivity and basic application responsiveness without stressing the device's CPU or memory.

**Example Command Sent During Freeze:**
```bash
# This is the type of command sent by the health-checker to the frozen device
# It will NOT be sent from the main command queue.
device-cli --device edge-router-01a --command 'net.banner'
```

### Recovery from a Frozen State

A device can exit the `FROZEN` state in one of two ways:

1.  **Successful Health Probe**: If a `net.banner` command (or another designated health-check command) receives a successful ACK during the 30-second window, the freeze is lifted immediately. The device is moved back to an `ACTIVE` state, and the command queue is cautiously re-enabled.
2.  **Timer Expiration**: If all health probes fail, the device is automatically transitioned back to an `ACTIVE` state after the 30-second timer expires. The system will then attempt to send the next scheduled command. If it fails again, the entire 3-step freeze cycle will restart.

### Troubleshooting Guide for `[FREEZE]` Events

When you see a `[FREEZE] device=... reason=ack-timeout` log message, it is an actionable alert.

1.  **Check Device-Side Logs**: Immediately SSH to the device (if possible) and inspect its system logs (`/var/log/messages`, `dmesg`, or application-specific logs). Look for:
    *   Kernel panics or crashes.
    *   Application process restarts or segfaults.
    *   High CPU or memory utilization warnings (e.g., from `top` or `htop` logs).
    *   Firewall rules that may have been updated incorrectly, dropping packets.

2.  **Verify Network Path**:
    *   From the control server, can you `ping` the device's IP address?
    *   Can you `traceroute` to the device to check for network hops that are timing out?
    *   Manually execute the health-check command to replicate the system's probe: `device-cli --device <frozen-device-name> --command 'net.banner'`. If this fails, the issue is persistent. If it succeeds, the issue may have been transient.

3.  **Known Issue Workaround**: If a device repeatedly enters a freeze-thaw cycle, it may be stuck in a bad state.
    *   **Fix**: Manually reboot the device. For many embedded devices, this is the most effective way to clear a corrupted memory state or a hung process.
    *   **Post-Fix**: After rebooting, monitor the logs closely to ensure the `[FREEZE]` messages for that device do not reappear. If they do, it may indicate a hardware or persistent software flaw requiring replacement or re-imaging.

## The Validation Pipeline: Guarding the Gates

The validation pipeline is a non-negotiable, sequential, three-stage process that every inbound message must pass through before it can be considered for transmission to a target device. Its primary function is to act as a robust gatekeeper, ensuring that only structurally sound, contextually appropriate, and safe messages are ever sent. This prevents malformed data from causing device errors, protects devices from receiving commands they cannot handle in their current state, and mitigates security risks from unsanitized content.

The pipeline's stages are executed in a precise, unchangeable order. A message's failure at any stage results in its immediate rejection and prevents it from being evaluated by subsequent stages.

### The 3 Stages of Validation

1.  **Structural Schema Validation:** Is the message shaped correctly?
2.  **Mode-Based Whitelist Filtering:** Is this message *allowed* right now?
3.  **Content Sanitization & Limiting:** Is the data within the message safe and within bounds?

---

### Stage 1: Structural Schema Validation

This is the first and most fundamental check. It validates the message's structure against a predefined JSON Schema. It is concerned only with the message's anatomy, not its content or the target device's state.

**Checks Performed:**
*   Presence of all required fields.
*   Correct data types for all fields (e.g., `power_level` must be an integer, not a string).
*   Adherence to enumerations (e.g., `priority` must be one of `"LOW"`, `"NORMAL"`, or `"HIGH"`).
*   Format constraints (e.g., `timestamp` must be in ISO 8601 format).

**Mechanism:** Each message `type` is associated with a specific JSON Schema file.

**Example Schema (`set_device_label.json`):**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SetDeviceLabel",
  "type": "object",
  "properties": {
    "type": {
      "type": "string",
      "const": "set_device_label"
    },
    "label": {
      "type": "string",
      "description": "The new user-defined label for the device. Max 50 chars.",
      "minLength": 1,
      "maxLength": 50
    },
    "request_id": {
      "type": "string",
      "format": "uuid"
    }
  },
  "required": ["type", "label", "request_id"]
}
```

**Failure Scenario:** A client sends a message with a missing required field.

**Invalid Message Sent:**
```json
{
  "type": "set_device_label",
  "label": "Primary Sensor"
}
```

**Result:** The message is immediately dropped by the pipeline.

**Exact Log Output:**
```
2023-10-27T10:30:05Z ERROR [validation-pipeline] Message dropped. reason_code=[DROP_INVALID] details="Schema validation failed: data must have required property 'request_id'." message_id=... source_ip=...
```
This error is unambiguous: the client-side code that constructed the message is buggy. It is a structural problem, not a state or timing issue.

---

### Stage 2: Mode-Based Whitelist Filtering

A message that is structurally perfect may still be inappropriate given the device's current operational mode. This stage checks the message `type` against a whitelist of commands permitted for the target device's reported mode.

**Checks Performed:**
*   Is the message `type` included in the list of allowed types for the device's current `mode`?

**Mechanism:** The system maintains a configuration map that links device modes to allowed message types. The device's current mode is retrieved from a state cache (e.g., Redis) before validation.

**Example Configuration (`mode_permissions.yaml`):**
```yaml
device_modes:
  STANDBY:
    - "get_status"
    - "set_device_label"
    - "enter_maintenance"
  ACTIVE:
    - "get_status"
    - "set_power_level"
    - "stream_data"
  MAINTENANCE:
    - "get_status"
    - "reboot_device"
    - "run_diagnostics"
    - "exit_maintenance"
```

**Failure Scenario:** A client attempts to reboot a device that is currently in `ACTIVE` mode.

**Valid Message Sent (Structurally):**
```json
{
  "type": "reboot_device",
  "delay_sec": 5,
  "request_id": "c4bb1cdd-5b87-4148-8f5b-1e3d08c42c9e"
}
```
**Device State:** The target device is currently in `mode: ACTIVE`.

**Result:** The message passes Stage 1 (it's well-formed) but is dropped by Stage 2. The `reboot_device` command is not on the whitelist for the `ACTIVE` mode.

**Exact Log Output:**
```
2023-10-27T10:35:12Z WARN [validation-pipeline] Message dropped. reason_code=[DROP_BY_MODE] details="Message type 'reboot_device' is not permitted for device_id='DEV123' in current mode 'ACTIVE'." message_id=... source_ip=...
```
This error indicates a logic or timing issue. The sender is either unaware of the device's state or sent the command at the wrong time.

---

### Stage 3: Content Sanitization & Limiting

Only messages that are both structurally valid and contextually appropriate reach this final stage. Here, the *values* within the message fields are cleaned and constrained to prevent security vulnerabilities (like XSS in a web UI that displays the data) and to enforce practical limits. The message is typically modified in-place, not dropped.

**Actions Performed:**
*   **Trimming:** Whitespace is removed from the beginning and end of strings.
*   **Truncating:** Strings that are technically valid per the schema's `maxLength` but should be defensively shortened are truncated (e.g., a `log_message` field).
*   **Character Stripping:** Potentially dangerous characters (e.g., `<` `>` `&` `'` `"`) are removed or encoded from user- E.g., `>` becomes `&gt;`.
*   **Range Clamping:** Numerical values are clamped to a safe, practical range. For example, a `set_power_level` schema might allow an integer from 0-100, but sanitization might clamp any value over 90 to 90 to prevent device overuse.

**Example Scenario:** A user sets a device label with extra whitespace and potentially malicious script tags.

**Message Entering Stage 3:**
```json
{
  "type": "set_device_label",
  "label": "  <script>alert('XSS')</script> Main Hub  ",
  "request_id": "f8a966a3-2c1b-4b8e-9d0a-e5f639a0bce1"
}
```

**Result:** The `label` field is modified. The message is not dropped but proceeds to the sending queue in its sanitized form.

**Message After Sanitization:**
```json
{
  "type": "set_device_label",
  "label": "&lt;script&gt;alert('XSS')&lt;/script&gt; Main Hub",
  "request_id": "f8a966a3-2c1b-4b8e-9d0a-e5f639a0bce1"
}
```

**Exact Log Output:**
```
2023-10-27T10:40:01Z INFO [validation-pipeline] Message content sanitized. field='label' actions=['trim_whitespace', 'html_encode'] message_id=...
```

---

### Case Study: Why This Order Is Critical for Debugging

The strict `Schema -> Mode -> Sanitize` order is essential for accurate and efficient troubleshooting. An incorrect order can send developers on a "wild goose chase," debugging the wrong problem.

**Scenario:** A malformed `reboot_device` message (missing the `request_id`) is sent to a device in `MAINTENANCE` mode.

#### **Correct Pipeline Order (Schema First)**

1.  **Stage 1 (Schema):** The message `{ "type": "reboot_device", "delay_sec": 5 }` arrives. It immediately **FAILS** schema validation because `request_id` is a required field.
2.  **Action:** The message is dropped.
3.  **Log:** `ERROR ... reason_code=[DROP_INVALID] details="...must have required property 'request_id'"`
4.  **Debugging Result:** The developer sees `[DROP_INVALID]` and instantly knows the error is in their client-side code. The fix is to add the `request_id` field to the message payload. The root cause is identified in seconds.

#### **Incorrect Pipeline Order (Mode First)**

1.  **Stage 1 (Mode - Incorrect):** The message `{ "type": "reboot_device", "delay_sec": 5 }` arrives. The system checks the device mode, which is `MAINTENANCE`. According to `mode_permissions.yaml`, `reboot_device` **IS** allowed in this mode. The message **PASSES** this stage.
2.  **Stage 2 (Schema - Incorrect):** The message now hits the schema validator. It **FAILS** because `request_id` is missing.
3.  **Action:** The message is dropped.
4.  **Log:** `ERROR ... reason_code=[DROP_INVALID] details="...must have required property 'request_id'"`

Wait, this seems to work too. Let's flip the scenario.

**Scenario 2:** A malformed `set_power_level` (missing `request_id`) is sent to a device in `MAINTENANCE` mode.

#### **Incorrect Pipeline Order (Mode First)**

1.  **Stage 1 (Mode - Incorrect):** The message arrives. The system checks device mode (`MAINTENANCE`). The `set_power_level` type is **NOT** on the whitelist for this mode.
2.  **Action:** The message is immediately dropped.
3.  **Log:** `WARN ... reason_code=[DROP_BY_MODE] details="...Message type 'set_power_level' is not permitted for device ... in current mode 'MAINTENANCE'"`
4.  **Debugging Result (MISLEADING):** The developer sees `[DROP_BY_MODE]`. Their conclusion is that they have a race condition or a state-synchronization problem. They will spend hours, or even days, trying to figure out why their application is sending the command when the device is in the wrong mode. **They are completely unaware that the message they sent was fundamentally broken and would have been rejected anyway.** They are debugging a phantom timing issue instead of a simple, local bug in their code.

By enforcing the **`Schema -> Mode`** order, we guarantee that the first reason a message is rejected is the most fundamental one. `[DROP_INVALID]` always points to a malformed message, while `[DROP_BY_MODE]` always points to a correctly formed message that was sent at the wrong time. This distinction is the key to rapid, accurate debugging.

## The Full Device State Machine: From Boot to Task

### The Boot Sequence and Backend Handover

The device's boot process is a two-stage sequence with a clear division of responsibility between the onboard hardware/firmware and the backend `Orchestrator` service. Understanding this division is critical for troubleshooting connectivity and initial state issues.

1.  **Hardware-Managed Boot**: Upon power-on, the device's firmware is solely responsible for its initial state. This includes:
    *   Power-On Self-Test (POST).
    *   Displaying the manufacturer's boot logo/animation.
    *   Initializing the base operating system and network stack.
    *   Attempting to connect to the configured network (Wi-Fi/Ethernet).
    *   Once network connectivity is established, it displays a static, locally-stored "Welcome" or "Connecting..." page. **The backend has no control or rendering capabilities at this stage.**

2.  **Backend Handover**: The handover process is initiated by the device and begins only after it has successfully connected to the network.
    *   The device establishes a secure WebSocket connection to the backend.
    *   It sends an initial `device.hello` message, containing its unique ID, firmware version, and capabilities.
    *   The backend validates the device and responds with a handshake confirmation.
    *   This successful handshake constitutes the **'wake' event**.
    *   The backend's first command is typically `render.ui`, which replaces the static welcome page with the dynamic UI for the `connected(idle)` state. The device is now fully managed by the backend.

If a device is stuck on the welcome screen, the issue lies in the network connection, DNS resolution, or WebSocket handshake phase, not in the backend's state logic.

### Device State Machine

The device operates as a strict finite state machine (FSM). The current state dictates which commands are permissible (the "whitelist"). Sending a command not allowed in the current state will cause the device to respond with a `command.error` event, preserving its current state. The `correlationId` of the original command is echoed in the error message for debugging.

**Example `command.error` response:**
A `dialog.show` command sent while the device is in a `meeting.active` state will be rejected.

```json
{
  "event": "command.error",
  "payload": {
    "correlationId": "cmd_a4b2-9z7k",
    "reason": "Command 'dialog.show' not allowed in state 'meeting.active'."
  }
}
```

The state machine is detailed in the table below. The `*` in state names like `dialog.*` or `meeting.*` indicates a group of related states that share a common context and often, a subset of commands.

| State | Entry Trigger Events | Allowed Commands (Whitelist) | Exit / Transition Conditions |
| :--- | :--- | :--- | :--- |
| **`connected(idle)`** | - Initial 'wake' event after boot. <br/> - `meeting.left`, `meeting.rejected` events. <br/>- `dialog.response`, `dialog.dismiss` events. <br/>- `task.complete`, `task.cancelled`, `task.error` events. | - `render.ui` <br/>- `device.ping` <br/>- `device.reboot` <br/>- `device.config.update` <br/>- `dialog.show` <br/>- `meeting.invite` <br/>- `task.assign` | - On `dialog.show` command -> `dialog.prompt` <br/>- On `meeting.invite` command -> `meeting.incoming` <br/>- On `task.assign(type: 'coding')` command -> `coding.setup` <br/> - On `task.assign(type: 'data_entry')` command -> `working.form` |
| **`dialog.prompt`** | Backend sends `dialog.show` command. | - `dialog.update` <br/>- `dialog.dismiss` | - User selects an option -> device sends `dialog.response` event -> `connected(idle)` <br/>- Backend sends `dialog.dismiss` command -> `connected(idle)` <br/>- Timeout (120s) -> device sends `dialog.error(reason: 'timeout')` -> `connected(idle)` |
| **`meeting.incoming`** | Backend sends `meeting.invite` command. | - `meeting.cancel_invite` | - User accepts -> device sends `meeting.accepted` event -> `meeting.active` <br/>- User rejects -> device sends `meeting.rejected` event -> `connected(idle)` <br/>- Backend sends `meeting.cancel_invite` -> `connected(idle)` <br/>- Timeout (30s) -> device sends `meeting.error(reason: 'invite_timeout')` -> `connected(idle)` |
| **`meeting.active`** | Device sends `meeting.accepted` event. | - `meeting.mute_toggle` <br/>- `meeting.video_toggle` <br/>- `meeting.participant_update` <br/>- `meeting.end` | - User hangs up -> device sends `meeting.left` event -> `connected(idle)` <br/>- Backend sends `meeting.end` command -> `connected(idle)` <br/>- Network transport layer fails for > 60s -> device sends `meeting.error(reason: 'connection_lost')` -> `connected(idle)` |
| **`working.form`** | Backend sends `task.assign(type: 'data_entry', ...)` followed by `render.ui` for the form. | - `form.field.update` <br/>- `task.cancel` | - User submits form -> device sends `task.complete(payload: {...})` -> `connected(idle)` <br/>- User hits cancel button -> device sends `task.cancelled` -> `connected(idle)` <br/>- Backend sends `task.cancel` command -> `connected(idle)` |
| **`coding.setup`** | Backend sends `task.assign(type: 'coding', repo: '...')` | - `device.status.update` <br/>- `task.cancel` | - Environment setup succeeds -> device sends `coding.ready` event -> `coding.active` <br/>- Setup fails (e.g., git clone fails, dependency error) -> device sends `task.error(reason: 'setup_failed', details: '...')` -> `connected(idle)` <br/>- Backend sends `task.cancel` -> `connected(idle)` |
| **`coding.active`** | Device sends `coding.ready` event. | - `coding.file.sync` <br/>- `coding.exec` <br/>- `coding.debug.start` / `.stop` <br/>- `task.end_session` <br/>- `task.cancel` <br/>- `device.reboot_service(service: 'coding_env')` (*Fix/Workaround*) | - Backend sends `task.end_session` -> device cleans up -> device sends `task.complete` event -> `connected(idle)` <br/>- Fatal runtime error (e.g., OOM) -> device sends `task.error(reason: 'env_crash')` -> `connected(idle)` |

---
**Patterns and Workarounds:**

*   **State-Specific Reboots**: The `coding.active` state includes a special command: `device.reboot_service(service: 'coding_env')`. This is a documented workaround for when a sub-process (like the interactive terminal shell) becomes unresponsive without crashing the entire task environment. Issuing this command allows the backend to perform a "soft reset" of that component *without* exiting the `coding.active` state, which is far less disruptive to the user than ending the entire session. This pattern highlights the need for granular device control commands within complex states.
*   **Optimistic UI Rendering**: For state transitions that require device-side processing (like `coding.setup`), the backend should first send a `render.ui` command with a "Setting up..." screen, and *then* send the `task.assign` command that triggers the long-running process. This prevents the UI from appearing frozen during setup.

## Performance Constraints: E-Ink, Throttling, and Rate Limiting

The performance of the device is governed by three primary factors: the physical limitations of its E-Ink display, a mandatory hardware-level refresh throttle, and backend API rate limits. Understanding these constraints is critical for building responsive and reliable applications.

### E-Ink Display Characteristics and Refresh Cycle

The device uses an E-Ink (Electrophoretic Ink) display, which has unique properties compared to traditional LCD or OLED screens. It is not backlit and has a very slow refresh rate. To prevent screen artifacts, ghosting, and damage to the panel, updates are carefully managed.

#### Hardware Refresh Throttle: 500ms Minimum Interval

There is a **mandatory, non-configurable hardware throttle** that prevents the screen from being refreshed more than once every **500ms**. Any attempt to refresh the screen faster than this will be ignored by the device's firmware.

This means the maximum possible frame rate for a full-screen update is **2 FPS**. This is a physical limitation of the display panel itself.

*   **Command:** Any command that triggers a full screen refresh (e.g., `ui.render`).
*   **Behavior:** The device firmware will only accept one screen refresh command every 500ms. Subsequent commands received within this window are discarded.
*   **Example:** If you send two `ui.render` calls 100ms apart, the first will be processed, and the second will be dropped by the device firmware. The screen will only refresh once.

#### Three-Region Screen Layout

The display is conceptually divided into three regions: a `header`, a `body`, and a `footer`. This layout is designed to support **future partial refresh capabilities**. Partial refresh would allow for updating only a specific region of the screen, resulting in a much faster update cycle (sub-100ms) and reduced screen flicker.

However, the current firmware version **does not support partial refresh**. All calls to `ui.render` trigger a full-screen refresh and are therefore subject to the 500ms hardware throttle. The regional layout should be considered a forward-looking design pattern for now.

### Backend API Rate Limiting

To ensure service stability and fair use, the backend enforces strict, per-device rate limits on API endpoints. Exceeding these limits will result in an `HTTP 429 Too Many Requests` error response.

| Endpoint | Method | Per-Device Limit | Description |
| :--- | :--- | :--- | :--- |
| `/v1/ui.render` | `POST` | **≤ 2 Queries Per Second (QPS)** | Submits a new frame to be rendered on the device's screen. This limit aligns with the hardware's 500ms refresh throttle. |
| `/v1/device.control` | `POST` | **≤ 5 Queries Per Second (QPS)** | Used for state-change commands that do not involve screen refreshes, such as controlling the device's LED or playing an audio tone. |

It is crucial that client-side applications respect these limits. A properly implemented client should include logic for backoff and retry mechanisms when a `429` response is received.

### Client-Side Backpressure and Frame Dropping

To manage the discrepancy between a fast-updating application and the slow device refresh rate, the recommended client-side strategy is to use a bounded queue for rendering frames. This creates backpressure and gracefully handles situations where an application generates frames faster than 2 FPS.

The strategy involves:
1.  **Bounded Queue:** A fixed-size queue (e.g., size of 2 or 3) holds pending frames.
2.  **Dropping the Oldest Frame:** When the application generates a new frame and the queue is already full, the **oldest frame in the queue is discarded**. The new frame is then added.

This ensures that the device always renders the most recent state available, preventing a long lag of outdated frames from building up.

#### Conceptual Implementation

Here is a conceptual Python snippet demonstrating this logic using `collections.deque`.

```python
from collections import deque
import time

# A bounded queue that holds a maximum of 2 frames.
# When a 3rd item is added, the oldest (leftmost) item is automatically discarded.
frame_queue = deque(maxlen=2)

def schedule_render(new_frame_data):
    """Adds a frame to the queue. If the queue is full, the oldest is dropped."""
    if len(frame_queue) == frame_queue.maxlen:
        print("WARN: Bounded queue is full. Dropping the oldest frame.")
    frame_queue.append(new_frame_data)
    print(f"Queue now contains {len(frame_queue)} frame(s).")

# --- Worker thread that consumes frames and sends to device ---
def render_worker():
    while True:
        if frame_queue:
            frame = frame_queue.popleft() # Get the oldest frame
            print(f"INFO: Sending frame to device...")
            # api.send_render_request(frame) # Actual API call
            time.sleep(0.5) # Simulate the 500ms device throttle
        else:
            time.sleep(0.1) # Wait for new frames

# Example Usage: Simulating an app generating frames at 10 FPS
# for i in range(10):
#     schedule_render({"frame_id": i, "content": f"Update #{i}"})
#     time.sleep(0.1) # 100ms interval
```
This strategy prevents the application from hitting the `ui.render` rate limit, as the `render_worker` naturally spaces out requests by at least 500ms.

### Troubleshooting: Rate Limiting vs. Device Offline Bug

A critical bug in older SDK versions caused misleading error logs when rate limits were exceeded. Understanding this behavior is essential for diagnosing issues with older systems.

*   **Symptom:** The application log is flooded with `'device offline'` or `'connection failed'` error messages, yet the device appears healthy and online in the administration dashboard. API calls for `device.control` might still succeed.
*   **Root Cause:** The SDK's HTTP client did not properly handle the `HTTP 429 Too Many Requests` status code returned by the backend. Instead of interpreting it as a rate-limiting signal, it fell through to a generic network error handler, which incorrectly reported the device as being offline.

#### Example Error Logs

**Incorrect log message (pre-fix):**
```log
2023-01-15 10:30:05 ERROR [api_client] Failed to send update to device 'dev_abc123'. Reason: Device offline. Retrying in 10s.
```

**Correct log message (post-fix):**
```log
2023-05-20 11:00:15 WARN [api_client] Rate limit exceeded for device 'dev_abc123' on endpoint '/v1/ui.render'. Throttling requests. Check application render frequency.
```

*   **Solution & Fix:** The SDK was patched to specifically check for the `429` status code. Upon receiving it, the SDK now logs the correct warning message and implements an exponential backoff strategy, allowing the client-side frame-dropping mechanism to take over.

**Actionable Advice:** If you see "device offline" errors but can confirm the device is online, immediately suspect a rate-limiting issue. Your first step should be to check the frequency of `ui.render` or `device.control` calls and update the client SDK to the latest version.

## Configuration, Data, and Migration Strategy

### Device Registry: The Source of Truth for Identity

The primary mechanism for associating anonymous device identifiers (MAC addresses) with real-world entities (people, equipment) is a manually-curated YAML file. This file acts as a central, human-readable registry.

*   **Location:** `backend/data/devices.yaml`
*   **Schema:** The file uses the device's MAC address as the primary key. Each key maps to an object containing metadata.
    *   `mac`: The unique MAC address of the device (key).
    *   `badge`: A human-friendly identifier for the device (e.g., a badge number, asset tag).
    *   `owner`: The name of the person or department responsible for the device.
    *   `group`: A logical grouping for categorization and access control (e.g., "Engineering", "Facilities", "Sensors").

**Dual Purpose: Mapping and Privacy by Design**

This file serves two critical functions:
1.  **Enrichment and Mapping:** It allows the application to display human-readable names and groupings instead of raw MAC addresses in user interfaces and reports.
2.  **Privacy and Security:** The main event database (see migration plan below) **only stores the MAC address**. It contains no Personally Identifiable Information (PII). By keeping the mapping of `MAC -> Owner` in this separate, more tightly controlled file, we limit the exposure of sensitive information. If the main event log were ever compromised, it could not be immediately tied back to individuals without also compromising this file.

**Configuration Example (`backend/data/devices.yaml`)**

```yaml
# backend/data/devices.yaml
#
# Maps device MAC addresses to metadata. This is the single source of truth
# for device identity. It is manually maintained. All MAC addresses should be
# lowercase.

# --- Engineering Team ---
aa:bb:cc:11:22:33:
  badge: "NFC_Badge_001"
  owner: "Alice"
  group: "Engineering"
dd:ee:ff:44:55:66:
  badge: "BT_Beacon_005"
  owner: "Bob"
  group: "Engineering"

# --- Facilities and Sensors ---
gg:hh:ii:77:88:99:
  badge: "Lobby_Temp_Sensor"
  owner: # Can be left blank for non-personal devices
  group: "Sensors"
ab:cd:ef:12:34:56:
  badge: "Door_Contact_Main"
  owner: "Facilities Team"
  group: "Facilities"

# --- Error Case: Unregistered Device ---
# Any MAC address seen by the system but not listed in this file will
# be treated as "unknown" and cannot be used for privileged actions.
```

---

### Storage System and Migration Strategy

The current system stores event data in a large number of individual, date-stamped JSON files. This architecture has led to significant performance degradation on read operations and lacks transactional integrity.

**Proposed Solution: Unified SQLite + WAL Database**

We are migrating the event data storage from scattered JSON files to a single, unified SQLite database file.

*   **Technology:** SQLite
*   **Mode:** **Write-Ahead Logging (WAL)**. This is a non-negotiable requirement. WAL mode allows for significantly higher concurrency by permitting read operations to occur simultaneously with write operations, which is essential for a responsive live system. It also provides better data integrity against application or system crashes.
*   **Database File:** `backend/data/events.db`

**Proposed Database Schema**

```sql
-- Schema for the central events table in events.db
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,         -- ISO 8601 format (e.g., '2023-10-27T10:00:00Z')
    mac_address TEXT NOT NULL,
    event_type TEXT NOT NULL,      -- e.g., 'entry', 'exit', 'heartbeat'
    signal_strength INTEGER,
    source_node TEXT NOT NULL,       -- ID of the collector/node that saw the event
    raw_data TEXT                  -- The original raw JSON payload for auditing and recovery
);

-- Indexes for performance-critical lookup operations
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp);
CREATE INDEX IF NOT EXISTS idx_events_mac_address ON events (mac_address);
```

### Rollback-Safe Migration Plan

To migrate from the legacy JSON files to the new SQLite database without downtime or data loss, we will employ a **dual-write/shadow-read** strategy. This ensures the old system remains the definitive source of truth until we are 100% confident in the new system.

**Phase 1: Dual-Write**

All new events received by the backend will be written to **both** the legacy JSON file system and the new SQLite database.

*   **Logic:** The write to the legacy JSON system is considered the primary operation. If it fails, the event is rejected or queued for retry. A failure to write to the new SQLite database will only generate a warning log and will **not** block the event, as the legacy system is still the source of truth.

*   **Error Message Example (SQLite write failure):**
    ```
    WARNING: DUAL_WRITE_FAILURE: Event for MAC [aa:bb:cc:11:22:33] saved to JSON successfully but failed to write to SQLite. Error: database is locked.
    ```

**Phase 2: Shadow-Read and Verification**

All application read operations (e.g., fetching a device's history) will continue to read from the legacy JSON files. However, in the background, a "shadow read" will be performed against the SQLite database for the same query.

*   **Logic:** The results from both data sources are compared in memory. Any discrepancy is logged in detail for immediate investigation. This allows us to verify the integrity and performance of the new database under a real-world load without affecting users.
*   **Discrepancy Log Example:**
    ```
    ERROR: MIGRATION_VERIFICATION_FAILURE: Discrepancy found for query [mac=dd:ee:ff:44:55:66, since=2023-10-26]. JSON record count: 15, SQLite record count: 14.
    ```

**Phase 3: Daily Bulk Verification**

To guard against silent data drift, a daily automated job will perform a full comparison of the two data stores.

*   **Process:**
    1.  A script exports the entire SQLite `events` table into a set of JSON files, structured identically to the legacy system. This export is written to a temporary directory (e.g., `/tmp/sqlite_export/`).
    2.  A `diff` command is run to compare the directory of active JSON files with the new export.
*   **Exact Commands:**
    ```bash
    # This process will be managed by a cron job, running daily at 3:00 AM.
    # 0 3 * * * /bin/bash /opt/app/scripts/run_migration_verify.sh

    # Contents of run_migration_verify.sh
    #!/bin/bash
    EXPORT_DIR="/tmp/sqlite_export"
    LEGACY_DIR="/opt/app/backend/data/events"
    LOG_FILE="/var/log/migration_diff.log"

    echo "Starting daily migration verification on $(date)" > $LOG_FILE

    # 1. Export SQLite to JSON format
    /usr/bin/python3 /opt/app/scripts/export_sqlite_to_json.py --output $EXPORT_DIR

    # 2. Compare directories and log differences
    diff -qr $LEGACY_DIR $EXPORT_DIR >> $LOG_FILE

    # 3. Check if the log file contains differences and alert if it does
    if [ $(grep -c "differ" $LOG_FILE) -gt 0 ]; then
        # Send alert to monitoring system (e.g., Slack webhook, PagerDuty)
        echo "CRITICAL: Data drift detected between JSON and SQLite stores." | send_alert.sh
    fi
    ```

**Cutover and Rollback**

*   **Cutover:** Once the system has run for a sustained period (e.g., 1-2 weeks) with zero discrepancies from shadow reads and daily diffs, we can schedule the final cutover. This involves a configuration change to make SQLite the primary source for both reads and writes, and subsequently disabling the legacy JSON path.
*   **Rollback Plan:** At any point before the final cutover, we can instantly and safely revert to the old system. The migration logic is controlled by feature flags. To roll back, we simply set `ENABLE_SQLITE_WRITE=false` and `ENABLE_SQLITE_SHADOW_READ=false` in the environment configuration and restart the application. Since the legacy JSON files have been continuously maintained, there will be **no data loss**.

## Observability & Developer Guide: Logs, Lessons, and Principles

This document provides essential knowledge for developers working on this system, covering our logging philosophy for observability and the core principles that guide our development process.

### A Guide to Understanding Our Directional Logs

To achieve clear, instantaneous observability into our asynchronous message-driven architecture, we have standardized a set of log prefixes. These prefixes indicate the disposition of a message at a critical point in its lifecycle. Understanding them is the first step to debugging any issue.

#### Glossary of Log Prefixes

A message journey is typically `[SEND]` -> `[REDELIVER]`* (optional, repeated) -> `[ACK]` (success) or `[FREEZE]` (failure). Drops can happen at the start.

---

**`[SEND]`**

*   **Meaning:** A message is being published to a message queue or topic for the *first time* or is being sent from one internal component to another. This log entry signifies the *intent* to process.
*   **When to Look for It:** This is the starting point for tracing any new piece of work entering the system. If you expect a process to have started, you must find the corresponding `[SEND]` log.
*   **Log Example:**
    ```log
    INFO: [SEND] msg_id: msg-7a8f8b8c-8e8e-4f4f-b8b8-c8c8d8e8f8f8 | payload_size: 1452 bytes | target_queue: user-creation-queue | attempt: 1
    ```
*   **Debugging Tip:** If you see a `[SEND]` but never see a corresponding `[ACK]`, `[FREEZE]`, or `[DROP_*]` for the same `msg_id`, it might indicate the message was lost in transit or the consuming service is completely down and not even pulling messages.

---

**`[ACK]`**

*   **Meaning:** Acknowledgment of success. The consuming service has successfully processed the message and is signaling to the message broker that it can be safely and permanently deleted. This is the terminal state for a successful workflow.
*   **When to Look for It:** When you need to confirm that a business process was completed successfully.
*   **Log Example:**
    ```log
    INFO: [ACK] msg_id: msg-7a8f8b8c-8e8e-4f4f-b8b8-c8c8d8e8f8f8 | processing_time: 215ms | consumer: user-service-pod-a4b3c2
    ```
*   **Debugging Tip:** If a user reports that an action didn't complete, but you find the `[ACK]` log, the problem lies elsewhere. Either the logic within the consumer was flawed (e.g., it "succeeded" but did the wrong thing), or a subsequent, independent process failed. The message itself was processed correctly from the broker's perspective.

---

**`[DROP_INVALID]`**

*   **Meaning:** The message is being permanently discarded because it is structurally invalid. This is for "poison pills" that can *never* be processed, such as messages that fail schema validation, are malformed, or are missing fundamental fields.
*   **When to Look for It:** When data from a producing service seems to be disappearing. This is a critical error that should be alerted on.
*   **Log Example:**
    ```log
    ERROR: [DROP_INVALID] msg_id: msg-b3a9c1d2-e3f4-5678-90ab-cdef12345678 | reason: "Schema validation failed: missing required field 'email_address'" | source_queue: user-creation-queue
    ```
*   **Solution:** This is almost always a bug in the **producing service**. The fix is to correct the code that generates the message to conform to the agreed-upon data contract. Do not attempt to make consumers more "lenient"; this leads to technical debt and data corruption.

---

**`[DROP_BY_MODE]`**

*   **Meaning:** The message is structurally valid but is being intentionally and permanently discarded due to the system's current operating mode. This is a deliberate, configuration-driven action, not an error.
*   **When to Look for It:** During planned maintenance, incident response ("safe mode"), or for specific feature flags that disable a processing path.
*   **Configuration Example (`config.yaml`):**
    ```yaml
    system:
      operating_mode: "MAINTENANCE_MODE" # Other modes: "FULL_OPERATION", "READ_ONLY"
    ```
*   **Log Example:**
    ```log
    WARN: [DROP_BY_MODE] msg_id: msg-f1e2d3c4-b5a6-7890-1234-567890abcdef | reason: "System in MAINTENANCE_MODE" | current_mode: MAINTENANCE_MODE
    ```
*   **Solution:** This is not a code bug. The system is behaving as configured. To resume processing, an operator must change the system's operating mode.

---

**`[FREEZE]`**

*   **Meaning:** A message has failed processing multiple times due to transient errors and has exceeded its redelivery limit. To prevent it from blocking the main queue indefinitely, it is being moved to a Dead Letter Queue (DLQ) for manual inspection and intervention. The message is "frozen."
*   **When to Look for It:** This is a critical indicator of a persistent underlying problem, such as a misconfigured dependency, a database that is down, or an API that is consistently failing.
*   **Log Example:**
    ```log
    ERROR: [FREEZE] msg_id: msg-09876543-21fe-dcba-9876-fedcba098765 | redelivery_attempts: 5 | last_error: "Connection timeout to external API: https://payment.provider.com/api/v2/charge" | target_dlq: arn:aws:sqs:us-east-1:123456789012:payments-queue-dlq
    ```
*   **Solution:** This requires manual intervention.
    1.  **Investigate the root cause** using the `last_error` message. Is the downstream service down? Was there a bug in our processing logic that only appears under certain conditions?
    2.  **Fix the underlying issue.** (e.g., restart a dependency, deploy a code fix).
    3.  **Decide the fate of the frozen messages.** They can be "thawed" (moved back to the main queue to be re-processed) or discarded.
    *   **Example AWS CLI command to inspect the DLQ:** `aws sqs receive-message --queue-url <your-dlq-url> --max-number-of-messages 10`

---

**`[REDELIVER]`**

*   **Meaning:** A message processing attempt failed with a transient error (e.g., temporary network blip, database deadlock, rate limit exceeded), and the consumer failed to `[ACK]` it. The broker makes the message visible again for another delivery attempt after a visibility timeout.
*   **When to Look for It:** A small number of these are normal in a distributed system. A large-scale flood of `[REDELIVER]` logs or repeated `[REDELIVER]` logs for the same `msg_id` is an early warning sign that a dependency is unhealthy and a `[FREEZE]` is likely imminent.
*   **Log Example:**
    ```log
    WARN: [REDELIVER] msg_id: msg-09876543-21fe-dcba-9876-fedcba098765 | attempt: 3 | reason: "Transient failure: Could not acquire DB lock for account 'acc_123'"
    ```
*   **Debugging Tip:** Use the `msg_id` to trace the history of attempts. High redelivery counts for many different messages often indicate a widespread platform issue. High counts for one specific message point to a data-specific issue (a "poison pill" that doesn't fail validation but causes a runtime error).

### Key Development Principles and Lessons Learned

Our development process is guided by a few hard-won lessons. These principles are not suggestions; they are core to how we build reliable software.

#### The 'Protocol-First' Strategy

We do not begin work on a new service or feature by writing implementation code. We begin by defining the data contracts and API specifications.

**Principle:** "We are not writing services; we are implementing a protocol. If the protocol is solid, the services are just details. If the protocol is weak, the services will be a house of cards."

**Actionable Mandate:**
1.  **Define Contracts:** All new message types must be defined in a shared schema registry (e.g., Protobuf, Avro). All new API endpoints must be defined with an OpenAPI/Swagger spec.
2.  **Review Contracts:** These contract definitions are the subject of the *first* code review. Implementation details are irrelevant if the contract is wrong.
3.  **Generate Code:** Use the contracts to auto-generate client models and server skeletons. This eliminates entire classes of integration errors.

This approach enables true parallel development, provides clear boundaries of responsibility, and makes integration a non-event rather than a painful final step.

#### The Radical Simplification of the Day 1 Plan

The initial project plan was complex, aiming for multiple features and high-throughput optimizations from day one. This was identified as a major risk. A strategic decision was made to radically simplify the initial goal to focus exclusively on end-to-end correctness.

**Guiding Quote:** "We will not build a beautiful, feature-rich bridge that collapses on day one. We will build a simple, ugly, but unbreakably strong footbridge first. We can add lanes later. Our first and only job is to get one person safely to the other side."

**Impact on Development:**
*   Our first milestone was not about performance, scale, or feature breadth. It was about proving that a single message could make it from producer to consumer, through the entire real infrastructure, with full observability and correctness.
*   This principle informs our prioritization: **Correctness > Observability > Performance > Feature Breadth.** Do not optimize prematurely. Do not add a new feature until the existing paths are demonstrably robust.

#### Rejection of the `RENDER_LITE_D1` Switch: A Lesson in Simplicity

During the initial build, a proposal was made to create a feature flag or environment variable (`RENDER_LITE_D1`) that would allow the application to switch between the "simple footbridge" implementation and a more complex, feature-rich code path that was already being partially built. This proposal was decisively rejected.

**The Reasoning (Project Lead):** "No. This creates two code paths we have to maintain and test forever. It’s a complexity time bomb. It violates the 'ugly footbridge' principle. The Day 1 implementation *is* the real implementation. It's not a temporary scaffold. We will refactor and build upon the simple, working version. We will not maintain parallel universes. Don't add a switch; remove the old code and replace it with better code when the time comes."

**The Principle:** Avoid feature flags for long-term architectural differences. They fragment the codebase, exponentially increase the testing matrix, and create a permanent cognitive load for all developers. The simplest path is the only path. Refactor and evolve this single path; do not create detours. If old code is no longer needed, **delete it.**