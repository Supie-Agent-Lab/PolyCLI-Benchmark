## 1. Foundational Architecture: The 'Backend-Driven' Philosophy and Key Decisions

The foundational principle of our system is a **Backend-Driven UI**. This is not merely a preference but a core architectural mandate designed to solve the critical issue of "state drift" between the client (the e-ink display device) and the backend server. The backend serves as the absolute Single Source of Truth (SSoT) for what the user sees.

### The Problem: State Drift and Its Consequences

State drift occurs when the client's understanding of the system's state diverges from the backend's actual state. In a traditional model where the client fetches data and then applies its own logic to render a UI, this is a common and dangerous failure mode.

**Concrete Example of State Drift:**

1.  **Initial State:** A smart plug is `ON`. The client device correctly displays "Status: ON".
2.  **External Change:** A user turns the plug `OFF` via a separate mobile app, which communicates directly with the backend. The backend state is now correctly `OFF`.
3.  **Network Blip:** The client device misses the push notification from the backend due to a temporary WiFi disconnection.
4.  **Drift:** The client's internal state is still `{"status": "ON"}`. It continues to display "Status: ON" to the user, which is now dangerously incorrect. If the UI has a toggle button, pressing it would send a "turn off" command for a device that is already off, leading to unpredictable behavior and user confusion.

This architecture explicitly forbids client-side state management to prevent such scenarios. The client is a "dumb" renderer; it holds no long-term state and applies no business logic.

### The Solution: Backend as the Single Source of Truth (SSoT)

The backend is responsible for not just providing data, but for providing an explicit, declarative representation of the UI to be rendered.

**Pattern:** The client polls or receives a push from the backend. The payload is not raw data, but a structured JSON object that describes UI components, their content, and their layout.

**Example Backend Response Payload:**

```json
{
  "schema_version": "1.1",
  "screen_id": "device_control_thermostat_28ac",
  "render_instructions": [
    {
      "component": "header",
      "properties": {
        "text": "Living Room Thermostat"
      }
    },
    {
      "component": "large_text",
      "properties": {
        "value": "21.5",
        "unit": "°C",
        "icon": "thermometer-half"
      }
    },
    {
      "component": "status_line",
      "properties": {
        "text": "Status: Heating to 22°C",
        "color": "orange"
      }
    },
    {
      "component": "horizontal_rule"
    },
    {
      "component": "button_grid",
      "properties": {
        "buttons": [
          { "label": "-", "action": "DECREMENT_TEMP" },
          { "label": "+", "action": "INCREMENT_TEMP" }
        ]
      }
    }
  ]
}
```

The client's sole responsibility is to parse this structure and call the corresponding local rendering functions for each component. It does not know *why* the status is "Heating" or what `DECREMENT_TEMP` does; it only knows how to render the components and associate an action string with a button press.

---

### The `EinkRenderEngine` Architectural Debate and Deferral

A significant architectural debate centered on whether to build a formal, abstract `EinkRenderEngine` on the client from day one. This proposed engine would handle complex layout calculations, asset caching, and diff-based partial screen updates.

**Decision:** We have **explicitly decided to defer** the creation of a formal `EinkRenderEngine`.

**Reasoning:** The current approach of a simple, top-to-bottom renderer that re-draws the full screen on every update is sufficient for our immediate needs. It is vastly simpler to implement and debug. Building a complex engine now would be a case of premature optimization and would violate the project principle of avoiding over-engineering (see rejection of `RENDER_LITE_D1` below).

We will only undertake the creation of the `EinkRenderEngine` when one or more of the following trigger conditions are met:

1.  **Complex Dynamic Layouts:** The backend needs to specify layouts that cannot be achieved with a simple vertical stack (e.g., nested columns, grids with dynamic spanning, absolute positioning).
2.  **Partial Update Performance:** Full-screen refreshes become a noticeable source of latency or unacceptable screen flashing, and the backend needs to an atomically send "diff" of the UI to be patched onto the existing display.
3.  **Multiple Interactive Regions:** The UI requires two or more non-adjacent, independently updatable, interactive elements on the same screen (e.g., a live stock ticker at the top and a weather widget at the bottom).
4.  **Multi-Display API Fragmentation:** We must support more than two e-ink display models with fundamentally different drawing paradigms or APIs, making a hardware abstraction layer (HAL) within a render engine a necessity.
5.  **Client-Side Animations:** The product requirements evolve to include complex transitions or animations (e.g., animated charts, page-swipe transitions) that are impractical to control from the backend on a per-frame basis.

---

### Rejected Approach: The `RENDER_LITE_D1` Runtime Switch

During initial design, a proposal was made to introduce a runtime configuration switch to support a hypothetical less-capable display, "Model D1".

**The Proposal:**

A flag in a local configuration file, e.g., `device_config.ini`:

```ini
# RENDER_MODE can be 'FULL' or 'LITE_D1'
RENDER_MODE=LITE_D1
```

The client-side C++ code would then branch its logic:

```cpp
// THIS IS A REJECTED PATTERN -- DO NOT IMPLEMENT
void display::render_screen(const Json::Value& payload) {
    if (config.getRenderMode() == "LITE_D1") {
        // Render a simplified, text-only version of the UI
        render_simplified_header(payload["header"]);
        // no icons, no complex fonts...
    } else {
        // Render the full, graphical UI
        render_full_header(payload["header"]);
        // render icons, etc...
    }
}
```

**Decision and Justification:**

This proposal was unequivocally **rejected**. The key driving reason, as captured from the project lead, was that it "**adds hardware complexity** and conditional logic to the client, which directly violates our Single Source of Truth philosophy."

This rejection established a critical project principle: **The client must be ignorant of hardware variations.**

*   **The Problem with the Switch:** This approach re-introduces state and logic onto the client. The client now needs to know "who it is" and alter its behavior accordingly. This is a slippery slope back to the state drift problem.
*   **The Correct Architectural Pattern:** The client should announce its identity to the backend on its initial request (e.g., via an HTTP header: `X-Device-Model: D1`). The **backend** is then responsible for tailoring the JSON response payload to the capabilities of that specific device. The `D1` client would receive a simpler `render_instructions` payload that it can render without any conditional logic. The `D1-Pro` client would receive a richer payload. The client code remains simple and universal.

## 2. The Communication Protocol: Message Contracts and Routing

The communication layer between the backend services and UI clients utilizes a simple, JSON-based messaging protocol, typically transported over WebSockets. All messages share a common envelope that facilitates routing and identification.

### Message Envelope and Routing

Every message, regardless of its type, conforms to a standard envelope structure. The `to` field is crucial for routing messages to one or more specific recipients. The message broker or gateway is responsible for parsing this field and dispatching the message accordingly.

*   `type` (string): A unique identifier for the message's purpose (e.g., `ui.render`).
*   `from` (string): The unique ID of the sender client/service.
*   `to` (array of strings): A list of recipient IDs. A message can be multicast to multiple clients.
*   `message_id` (string, optional): A unique ID for this specific message instance, useful for acknowledgements and debugging.
*   `payload` (object): A JSON object containing data specific to the message type.

#### Routing Mechanism: `to: ["device-id"]`

The `to` field is an array of strings, where each string is the unique identifier of a target client or device.

*   **Unicast:** To send a message to a single specific device, its ID is placed in the array.
    ```json
    "to": ["hvac-unit-789"]
    ```
*   **Multicast:** To send the same message to a known group of devices, their IDs are all included.
    ```json

    "to": ["thermostat-living-room", "thermostat-bedroom-1", "thermostat-bedroom-2"]
    ```
*   **Broadcast (Convention):** While not a protocol feature, a conventional recipient ID like `all_ui_clients` might be used to signify a broadcast, which the message broker would then handle by sending to all connected clients of a certain type.

### Message Contracts

#### 1. `ui.render`

This message is sent from a backend service to a UI client. Its purpose is to command the UI to render or update a specific view with a given set of data and components.

**Canonical Example:**

```json
{
  "type": "ui.render",
  "from": "backend-renderer-service-01",
  "to": ["ui-client-dashboard-abc-123"],
  "message_id": "msg-render-xyz-789",
  "payload": {
    "page_id": "device_details",
    "layout_type": "two_column",
    "components": [
      {
        "id": "temp_current",
        "type": "Label",
        "properties": {
          "text": "Current Temperature",
          "value": "21.5 °C"
        }
      },
      {
        "id": "temp_setpoint",
        "type": "Slider",
        "properties": {
          "label": "Setpoint",
          "min": 15,
          "max": 30,
          "step": 0.5,
          "value": 22.0
        }
      },
      {
        "id": "btn_mode_cool",
        "type": "Button",
        "properties": {
          "text": "Cooling Mode",
          "action": "set_mode",
          "action_payload": {"mode": "cool"}
        }
      }
    ]
  }
}
```

#### C++ `RenderPayload` Struct Definition

The backend C++ service that generates `ui.render` messages uses the following structs for type safety and serialization. This definition is the source of truth for the `payload` structure.

```cpp
#include <string>
#include <vector>
#include <map>
#include <variant>

// Using std::variant for properties that can have different types
using PropertyValue = std::variant<std::string, int, double, bool, std::map<std::string, std::string>>;

// Represents a single UI component like a button or a label
struct Component {
    std::string id;        // Unique identifier for the component within the page
    std::string type;      // E.g., "Label", "Button", "Slider"
    
    // Flexible map to hold component-specific properties like "text", "min", "max"
    std::map<std::string, PropertyValue> properties;
};

// The main payload for a ui.render message
struct RenderPayload {
    std::string page_id;     // The unique name of the screen or view to render
    std::string layout_type; // E.g., "grid", "list", "two_column"

    // A list of all components to be rendered on the page
    std::vector<Component> components; 
};
```
*Note: A real-world implementation would use a JSON library like `nlohmann/json` to handle serialization/deserialization between these C++ structs and the JSON strings.*

#### 2. `device.control`

This message is sent from a UI client to a backend service that directly controls a physical or virtual device. It represents a user action, like pressing a button or adjusting a slider.

**Canonical Example:**

```json
{
  "type": "device.control",
  "from": "ui-client-dashboard-abc-123",
  "to": ["hvac-unit-789"],
  "message_id": "msg-control-pqr-456",
  "payload": {
    "command": "set_temperature",
    "parameters": {
      "value": 22.5,
      "unit": "celsius"
    }
  }
}
```

#### 3. `ui.ack`

A generic acknowledgement message sent from a UI client back to the originating service to confirm the successful receipt and processing of a message. It is crucial for implementing reliable messaging patterns.

**Canonical Example:**

```json
{
  "type": "ui.ack",
  "from": "ui-client-dashboard-abc-123",
  "to": ["backend-renderer-service-01"],
  "payload": {
    "acknowledged_message_id": "msg-render-xyz-789"
  }
}
```

*Fix:* Early implementations used an empty payload. This was insufficient for correlation. The `acknowledged_message_id` was added to prevent race conditions and ensure the correct message is acknowledged.

#### 4. `ui.error`

Sent from a UI client to a backend service when it fails to process a message or encounters an internal error. This is vital for monitoring and diagnostics.

**Canonical Example:**

```json
{
  "type": "ui.error",
  "from": "ui-client-dashboard-abc-123",
  "to": ["backend-error-logger"],
  "payload": {
    "code": "UNKNOWN_PAGE_TYPE",
    "message": "The received page_id 'device_settings_v2' is not recognized by this UI client version.",
    "context": {
      "original_message_id": "msg-render-lmn-112",
      "received_page_id": "device_settings_v2",
      "client_version": "1.1.3"
    }
  }
}
```

*Workaround:* For unexpected JavaScript errors in the UI client, a generic `CLIENT_EXCEPTION` code is used. The `context.stack_trace` field is a non-standard addition used by the web dashboard to capture the JavaScript stack trace for easier debugging.

### Structured Error Codes

The `ui.error` message payload includes a `code` for programmatic error handling and aggregation.

| Code | Meaning |
| :--- | :--- |
| `UNKNOWN_PAGE_TYPE` | The `page_id` in a `ui.render` payload is not defined or supported by the UI client. |
| `UNKNOWN_COMPONENT_TYPE`| A component `type` within the `ui.render` payload is not recognized by the client's component library. |
| `INVALID_PAYLOAD_SCHEMA`| The message payload does not conform to the expected JSON schema for its `type`. Usually due to missing required fields. |
| `INVALID_PROPERTY_VALUE`| A value for a component property is of the wrong type or outside the allowed range (e.g., a slider value beyond min/max). |
| `ACK_TIMEOUT` | (Backend-generated error) The backend did not receive a `ui.ack` for a message within the expected timeframe. |
| `CONTROL_COMMAND_FAILED`| (Backend-generated error) A `device.control` command was received but failed to execute on the target device. |
| `CLIENT_EXCEPTION` | A generic catch-all for an unhandled exception that occurred on the client-side while processing a message. |

## 3. Reliability Pattern: The ACK-Freeze Safety Valve

This mechanism is a critical safety feature designed to prevent our command-and-control (C2) system from overwhelming an unresponsive or offline device. By temporarily "freezing" a device that fails to acknowledge commands, we protect both the device from command flooding and our system from wasting resources on futile retries.

### Detailed Escalation Path

The system follows a strict, time-sensitive escalation path when a command does not receive an acknowledgment (ACK) from the target device.

1.  **Initial Command Send**: The system dispatches a command to the device.
2.  **First Timeout (3 seconds)**: The system waits **3 seconds** for an ACK. If none is received, it assumes a transient network issue and proceeds to the next step.
3.  **Single Retry**: Exactly one retry is automatically attempted. This is the same command sent a second time.
4.  **Second Timeout (3 seconds)**: The system again waits **3 seconds** for an ACK. If the retry also fails, the device is considered non-responsive.
5.  **Device Freeze (30 seconds)**: The device is placed into a "frozen" state for a fixed duration of **30 seconds**.

This entire process, from initial send to freeze, takes just over 6 seconds.

**Example Log Trace:**

```log
[INFO] Sending command { "action": "light.on", "brightness": 80 } to device=lamp-living-room
# 3 seconds pass
[WARN] No ACK received for command on device=lamp-living-room. Retrying (1/1)...
[INFO] Sending command { "action": "light.on", "brightness": 80 } to device=lamp-living-room
# 3 seconds pass
[ERROR] No ACK received after retry for device=lamp-living-room. Freezing device.
[FREEZE] device=lamp-living-room reason="No ACK received after retry" duration=30s
```

The canonical log signature for this event is `[FREEZE] device=...`. The message will always include the device identifier and may include additional context like the reason and duration.

### Behavior During the Freeze State

While a device is frozen, the system actively rejects almost all new commands intended for it. This is a hard-and-fast rule to allow the device (and its network path) time to recover.

*   **Duration**: A standard freeze lasts for exactly **30 seconds**.
*   **Command Rejection**: Any command sent to the device during this period will be immediately rejected by the C2 system without ever being transmitted to the device. The client or service attempting to send the command will receive an error.

**Example API Error Response for a Frozen Device:**

```json
{
  "status": "error",
  "error_code": "DEVICE_FROZEN",
  "message": "Device is temporarily frozen due to unresponsiveness.",
  "data": {
    "device_id": "lamp-living-room",
    "frozen_until": "2023-10-27T10:30:45Z"
  }
}
```

### The Safety Valve: The `net.banner` Health Check

There is a single, crucial exception to the command rejection rule. To allow for active diagnostics without altering the device's state, a specific "health check" command is permitted. This command is designed to be a lightweight, read-only operation that simply verifies network connectivity.

*   **Allowed Command**: `device.control`
*   **Required Parameter**: `action: "net.banner"`

This is the **only** command that will be passed through to a frozen device. The `net.banner` action requests the device to identify itself over the network, which effectively serves as a ping or a connectivity test. It does not change any user-facing state (like a light's power or color).

**Example Health Check Command:**

This is the payload you would send to probe a frozen device.

```json
{
  "target_device": "lamp-living-room",
  "command": {
    "type": "device.control",
    "params": {
      "action": "net.banner"
    }
  }
}
```

If this command succeeds (i.e., you get an ACK and a response), it's a strong indicator that the device is back online, even though the 30-second freeze period may not have elapsed yet. However, the device will remain in the frozen state until the timer expires to prevent race conditions.

### Recovery and Troubleshooting

*   **Automatic Unfreeze**: The device automatically exits the frozen state after the **30-second** timer expires. The system logs this event.
    ```log
    [UNFREEZE] device=lamp-living-room reason="Timeout expired"
    ```
*   **Common Causes for Freezes**:
    *   **Poor Network Connectivity**: Low Wi-Fi signal, Zigbee/Z-Wave mesh network issues, or high network latency.
    *   **Device Offline**: The device is unplugged, powered off, or has lost its network configuration.
    *   **Device Firmware Crash**: The device's internal software has hung and requires a power cycle.
*   **Troubleshooting Steps**:
    1.  Check the system logs for the `[FREEZE] device=...` signature to confirm the issue.
    2.  During the 30-second freeze, attempt to send the `net.banner` health check.
        *   If it fails, the device is likely still offline or disconnected. Physically check its power and network status.
        *   If it succeeds, the device is online. The issue may have been transient.
    3.  If freezes for a specific device are persistent, investigate for chronic issues like poor signal strength or a failing hardware component. A physical reboot (power cycle) of the device is often the most effective fix.

## 4. Reliability Pattern: The 'Fail-Closed' Validation & Sanitization Pipeline

Our data ingestion pipeline is a critical defense layer designed to protect the core application from malformed, unauthorized, or oversized data. It operates on a **fail-closed** principle: any data that does not explicitly pass every stage of validation is immediately rejected and logged. The pipeline consists of three mandatory stages that **must** execute in the specified sequence to ensure accurate error reporting and system stability.

### The Three-Stage Pipeline Sequence

The validation process is sequential. A payload is only passed to the next stage if it successfully clears the current one. This prevents cascading failures and ensures that log messages pinpoint the exact origin of a problem.

1.  **Stage 1: Structural / Schema Validation**
    *   **Purpose:** Verifies the fundamental structure and data types of the incoming JSON payload. It checks for the presence of all required fields (e.g., `header`, `header.mode`, `body`), correct data types (e.g., `header.title` is a string), and overall adherence to the defined JSON Schema.
    *   **Failure Log Prefix:** `[DROP_INVALID]`
    *   **Example Failure Scenario:** A client sends a payload missing the required `header.mode` field.
    *   **Sample Payload (Invalid):**
        ```json
        {
          "header": {
            "title": "Valid Title"
          },
          "body": {
            "items": ["one", "two"]
          }
        }
        ```
    *   **Resulting Log Entry:**
        ```log
        [DROP_INVALID] Payload dropped. Reason: Schema validation failed: missing required property 'mode' in 'header'. PayloadID: a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890
        ```

2.  **Stage 2: Mode-Based Whitelist Validation**
    *   **Purpose:** After confirming the payload is structurally sound, this stage performs an authorization check. It validates the value of the `header.mode` field against an internal, per-tenant whitelist of permitted modes. This ensures that the client is authorized to submit data for the specified purpose or feature.
    *   **Failure Log Prefix:** `[DROP_BY_MODE]`
    *   **Example Failure Scenario:** A client with a valid schema sends a payload with `mode: "beta_feature"` when their configuration only allows `mode: "stable"`.
    *   **Sample Payload (Correct Schema, Invalid Mode):**
        ```json
        {
          "header": {
            "mode": "beta_feature",
            "title": "Valid Title"
          },
          "body": {
            "items": ["one", "two"]
          }
        }
        ```
    *   **Resulting Log Entry:**
        ```log
        [DROP_BY_MODE] Payload dropped. Reason: Mode 'beta_feature' is not on the whitelist for client 'acme-corp'. PayloadID: f0e9d8c7-b6a5-4321-fedc-ba9876543210
        ```

3.  **Stage 3: Content Sanitization & Limit Validation**
    *   **Purpose:** As the final check, this stage enforces hard-coded content size limits on specific fields. This prevents oversized data from impacting database performance or breaking fixed-size UI components downstream. Payloads exceeding these limits are dropped.
    *   **Failure Log Prefix:** `[DROP_BY_SANITIZATION]`
    *   **Hard-Coded Limits:**
        *   `header.title`: The title string cannot exceed **16 characters**.
        *   `body.items`: The items array cannot contain more than **8 elements**.
        *   Each string element within `body.items`: Each item string cannot exceed **50 characters**.
    *   **Example Failure Scenario:** A payload passes schema and mode validation but contains a `title` that is too long.
    *   **Sample Payload (Correct Schema & Mode, Oversized Content):**
        ```json
        {
          "header": {
            "mode": "stable",
            "title": "This is a very long title that will be rejected"
          },
          "body": {
            "items": ["one", "two"]
          }
        }
        ```
    *   **Resulting Log Entry:**
        ```log
        [DROP_BY_SANITIZATION] Payload dropped. Reason: Field 'header.title' exceeded max length of 16. Actual length: 48. PayloadID: 11223344-5566-7788-9900-aabbccddeeff
        ```

### Critical Bug: The Misleading `[DROP_BY_MODE]` Log

A critical, time-wasting bug was discovered when the validation stages were executed out of order. If the **Mode-Based Whitelist (Stage 2)** runs before the **Structural/Schema Validation (Stage 1)**, it produces highly misleading logs.

**The Failure Scenario:**
1.  A malformed payload arrives, **missing the `header.mode` field** entirely.
2.  The incorrect pipeline runs the Mode-Based check first. It attempts to read `payload.header.mode`, which is `undefined`.
3.  The whitelist check for `undefined` fails, and the system logs the failure using the `[DROP_BY_MODE]` prefix.

**Why This Is a Problem:**
An engineer seeing `[DROP_BY_MODE]` will immediately start investigating system-level configuration: "Is the mode whitelist for this client correct? Was there a recent deployment that changed the allowed modes?" They will waste significant time investigating authorization and configuration issues.

The **actual root cause** is a simple malformed payload from the client (a Stage 1 failure).

**Correct Implementation (Pseudocode):**
The correct, sequential implementation prevents this ambiguity. The schema check acts as a gateway, ensuring all subsequent stages can safely assume the data structure is sound.

```javascript
function processPayload(payload) {
  const payloadId = payload.id || generateId();

  // STAGE 1: Structural/Schema Validation
  if (!isValidSchema(payload)) {
    log(`[DROP_INVALID] Payload dropped. Reason: Schema validation failed. PayloadID: ${payloadId}`);
    return;
  }

  // STAGE 2: Mode-Based Whitelist Validation
  const mode = payload.header.mode;
  if (!isModeWhitelisted(mode, context.client)) {
    log(`[DROP_BY_MODE] Payload dropped. Reason: Mode '${mode}' not whitelisted. PayloadID: ${payloadId}`);
    return;
  }

  // STAGE 3: Content Sanitization & Limit Validation
  if (!passesContentLimits(payload)) {
    log(`[DROP_BY_SANITIZATION] Payload dropped. Reason: Content exceeded size limits. PayloadID: ${payloadId}`);
    return;
  }

  // If all checks pass, proceed to core processing
  processCoreLogic(payload);
}
```

## 5. Performance Constraints & Optimizations

The system's performance is primarily dictated by two factors: the physical limitations of the E-Ink display hardware and the rate limits imposed by the backend control plane. Optimizations are focused on managing the slow refresh rate of the screen and ensuring the client does not overwhelm the backend APIs.

### 5.1. E-Ink Display Two-Phase Refresh Strategy

The E-Ink display is inherently slow and prone to "ghosting" (remnants of a previous image). To provide the best user experience while ensuring screen clarity, we employ a two-phase refresh strategy.

#### Phase 1: Full-Screen Refresh (Throttled)

This is the initial and recovery mode for screen updates. A full-screen refresh redraws the entire display area, which is effective for clearing ghosting artifacts or rendering a completely new UI layout.

*   **Trigger:** Used on initial device boot, when a fundamentally new screen template is loaded, or as a periodic fallback (e.g., every 100 partial updates) to clean up accumulated ghosting.
*   **Constraint:** Full-screen refreshes are resource-intensive and visually jarring (the screen flashes black and white). They are strictly throttled to prevent undue hardware stress and flicker.
*   **Rule:** A minimum of **500ms** must elapse between any two consecutive full-screen refresh commands. The system will reject or queue any requests that violate this timing.

**Example Command:**

```bash
# A conceptual command to trigger a full refresh
device-cli ui render --source /path/to/full_frame.png --mode full
```

#### Phase 2: Partial Refresh (Optimized)

This is the standard, high-performance operating mode. It updates only the specific rectangular regions ("dirty rects") of the screen that have changed. This is significantly faster and creates a smoother visual experience.

*   **Trigger:** Used for all routine UI updates, such as changing a sensor value, updating a clock, or toggling a status icon.
*   **Mechanism:** The client application calculates the bounding box of all changed UI elements and requests a refresh for only that specific area.
*   **Benefit:** Reduces latency, minimizes screen flicker, and lowers power consumption.

**Example Code (Conceptual):**

```python
# Assume 'display' is an object representing the E-Ink screen
# Old and new UI states are represented as image buffers

# 1. Calculate the difference between the old and new frames
diff_mask = calculate_diff(old_frame_buffer, new_frame_buffer)

# 2. Find the bounding box of all changed pixels
if diff_mask.any():
    dirty_rect = get_bounding_box(diff_mask) # Returns (x, y, width, height)

    # 3. Request a partial update for only the changed region
    display.update_partial(new_frame_buffer, region=dirty_rect)
```

### 5.2. Backend API Rate Limits

All communication with the device hardware is brokered through a backend service that imposes strict rate limits to ensure stability. Exceeding these limits will result in an HTTP `429 Too Many Requests` error, and the request will be rejected.

*   **UI Rendering (`ui.render`)**
    *   **Limit:** **≤ 2 Queries Per Second (QPS)**
    *   **Reason:** Aligned with the practical refresh capabilities of the E-Ink display and prevents overwhelming the rendering engine.
    *   **Scope:** Applies to both full and partial refresh requests.

*   **Device Control (`device.control`)**
    *   **Limit:** **≤ 5 Queries Per Second (QPS)**
    *   **Reason:** Allows for more frequent, low-latency control of non-display hardware like LEDs or status indicators.
    *   **Scope:** Applies to actions like setting LED color, playing a sound, etc.

**Example Error Message for Exceeding Limits:**

```json
{
  "error": {
    "code": 429,
    "message": "Too Many Requests. Rate limit for ui.render is 2 QPS. Please try again later.",
    "status": "RATE_LIMIT_EXCEEDED"
  }
}
```

### 5.3. Backpressure and Frame Dropping Strategy

To manage scenarios where UI update events are generated faster than the 2 QPS `ui.render` limit (e.g., during a rapid burst of sensor readings), the client implements a backpressure strategy using a bounded queue. This prevents memory leaks and ensures the system remains responsive, prioritizing the most recent data.

The strategy is "drop the oldest frame." Since the UI should always reflect the most current state, displaying an old, stale frame is less valuable than displaying the newest one.

#### Implementation Details

1.  **Bounded Queue:** A fixed-size queue (e.g., size of 3) holds pending render requests.
2.  **Enqueue Logic:** When a new frame is ready to be rendered:
    *   If the queue is full, the **oldest** frame (at the head of the queue) is dequeued and discarded.
    *   A counter for dropped frames is incremented.
    *   A warning is logged.
    *   The new frame is then enqueued at the tail.
3.  **Consumer:** A separate worker process consumes frames from the head of the queue, sending them to the `ui.render` API while respecting the 2 QPS rate limit.

**Python Code Snippet Example:**

```python
import queue
import logging
import threading
import time

# --- Configuration ---
MAX_QUEUE_SIZE = 3 # Small queue to ensure freshness
API_RATE_LIMIT_SECONDS = 0.5 # 1 / 2 QPS

# --- State ---
render_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
dropped_frames_count = 0
lock = threading.Lock()

def enqueue_frame(frame_data):
    """Adds a new frame to the render queue, dropping the oldest if full."""
    global dropped_frames_count
    try:
        render_queue.put_nowait(frame_data)
    except queue.Full:
        with lock:
            # The queue is full, implement "drop oldest"
            try:
                # 1. Remove the oldest item from the head
                oldest_frame = render_queue.get_nowait()
                # 2. Increment and log the drop
                dropped_frames_count += 1
                logging.warning(
                    f"Render queue full. Dropping oldest frame. Total dropped: {dropped_frames_count}"
                )
            except queue.Empty:
                # Should not happen in this locked block, but handle defensively
                pass
            
            # 3. Add the new item to the tail
            render_queue.put_nowait(frame_data)

def render_worker():
    """Consumes from the queue and calls the render API, respecting rate limits."""
    while True:
        frame_to_render = render_queue.get() # Blocks until a frame is available
        
        # --- API Call Logic ---
        print(f"Submitting frame '{frame_to_render}' to render API...")
        # response = api.ui.render(frame=frame_to_render)
        # handle_api_response(response)
        # --------------------

        render_queue.task_done()
        time.sleep(API_RATE_LIMIT_SECONDS) # Enforce 2 QPS rate limit

# --- Example Usage ---
#
# producer_thread = threading.Thread(target=generate_rapid_updates)
# consumer_thread = threading.Thread(target=render_worker, daemon=True)
# consumer_thread.start()
```

**Example Log Output When Dropping Frames:**

```
WARN: Render queue full. Dropping oldest frame. Total dropped: 1
WARN: Render queue full. Dropping oldest frame. Total dropped: 2
```
This logging is critical for monitoring system health and identifying periods where the event generation rate chronically exceeds the display's processing capacity.

## 6. State Management and Application Flow

The application flow and device state are managed by a strict sequence of events and states, ensuring that devices only process commands when they are in an appropriate context. This prevents race conditions and erroneous behavior on the client devices.

### Device Boot and Connection Sequence

The device's boot process is intentionally decoupled from the backend application's rendering lifecycle. The hardware is self-sufficient until explicitly activated.

1.  **Power On and Local Display**: Upon powering on, the device's own firmware is responsible for initializing its hardware and displaying a local, pre-packaged welcome page (e.g., an `index.html` file stored in its flash memory). The device does not require a network connection to complete this step. This page typically shows a static welcome message or basic status information.
2.  **Backend Connection**: The device establishes a persistent WebSocket connection to the backend server. Upon successful connection, it registers itself, and the backend begins tracking its state.
3.  **Idle State**: After connecting, the device remains on its local welcome page. It is considered `connected(idle)` by the backend. It does **not** automatically load the main application. This is a critical design choice to ensure devices can be managed and monitored without being in an active session.
4.  **"Wake-up" Event**: The backend application is only rendered on the device after receiving an explicit "wake-up" command (e.g., `APP_LOAD`). This command is typically triggered by an external action, such as an operator starting a session through a control panel or an API call.

This sequence ensures a clear separation of concerns: the hardware is responsible for being "on and ready," while the backend is responsible for initiating and managing the application experience.

### The Four-State Device Lifecycle

Every managed device progresses through a well-defined, four-state lifecycle. The backend is the source of truth for the device's current state, which is tracked as `currentMode`.

#### 1. `boot(local)`
*   **Description**: The initial state upon power-on. The device is running its onboard software and is not yet registered with the backend.
*   **Display**: Shows the locally stored welcome/standby page.
*   **Transition Trigger**: Successful WebSocket connection and registration with the backend. The backend creates a state record for the device and sets its `currentMode` to `IDLE`.

#### 2. `connected(idle)`
*   **`currentMode`**: `IDLE`
*   **Description**: The device is successfully connected and registered with the backend but is awaiting instructions. It is available in the pool of manageable devices.
*   **Display**: Continues to show the local welcome page.
*   **Transition Trigger**: An external event (API call, operator action) initiates a session. The backend sends a command to the device to load the application URL.
*   **Example Command (Backend to Device)**:
    ```json
    {
      "event": "APP_LOAD",
      "payload": {
        "url": "https://app.your-backend.com/session/xyz123",
        "sessionToken": "jwt-token-for-this-session"
      }
    }
    ```

#### 3. `dialog.preparing`
*   **`currentMode`**: `PREPARING`
*   **Description**: The device has received the `APP_LOAD` command and is actively loading the web application. The backend may use this state to pre-fetch required data for the session.
*   **Display**: The device's browser navigates to the provided URL, which should render a loading screen or "preparing session" message.
*   **Transition Trigger**: The web application on the device finishes its initialization (e.g., hydrating the UI, authenticating) and sends a "ready" message back to the backend.
*   **Example Message (Device to Backend)**:
    ```json
    {
      "event": "APP_READY",
      "payload": {
        "deviceId": "device-123-abc"
      }
    }
    ```
    Upon receiving this, the backend updates the device's `currentMode` to `ACTIVE`.

#### 4. `dialog.active`
*   **`currentMode`**: `ACTIVE`
*   **Description**: The application is fully loaded, initialized, and ready for interaction. The device is in an active session. The backend will now forward all relevant session messages to it.
*   **Display**: The main, interactive application UI.
*   **Transition Trigger**: The session ends due to user action (e.g., hang-up), operator command, or timeout. The backend sends a command to terminate the session.
*   **Example Command (Backend to Device)**:
    ```json
    {
      "event": "SESSION_TERMINATE",
      "payload": {
        "reason": "USER_DISCONNECTED"
      }
    }
    ```
    The device's application logic should handle this event by navigating back to its local welcome page (`window.location.href = 'file:///opt/app/index.html';`). The backend simultaneously reverts the device's state to `connected(idle)`.

### Backend Message Forwarding Logic

To ensure system stability, the backend's message forwarding service includes a critical check before sending any message to a device. **A message is only forwarded if the target device's `currentMode` is `ACTIVE`**.

This logic is essential for preventing commands from being sent to devices that are not in a state to handle them. For example, sending a `MUTE_MICROPHONE` event to a device that is in the `connected(idle)` state would be pointless, as it is displaying a static local page and has no application context to process the command. This could lead to client-side JavaScript errors and unpredictable behavior.

**The forwarding logic is as follows:**

1.  A message is published to the central message bus, targeting a specific `deviceId`.
2.  The forwarding service retrieves the current state object for that `deviceId`.
3.  It inspects the `currentMode` property.

**Code Example (Conceptual Pseudocode):**

```javascript
// In-memory store of device states, managed by the backend
const deviceStateStore = {
  "device-123-abc": { currentMode: "ACTIVE", connectionId: "ws-conn-xyz" },
  "device-456-def": { currentMode: "IDLE", connectionId: "ws-conn-uvw" },
};

function forwardMessageToDevice(message) {
  const { targetDeviceId, payload } = message;
  const targetDevice = deviceStateStore[targetDeviceId];

  if (!targetDevice) {
    console.error(`Attempted to send message to unknown device: ${targetDeviceId}`);
    return;
  }

  // **** THE CRITICAL CHECK ****
  if (targetDevice.currentMode === 'ACTIVE') {
    // Forward the message via the persistent connection
    websocketServer.send(targetDevice.connectionId, payload);
    console.log(`Message forwarded to ${targetDeviceId}`);
  } else {
    // Drop the message and log the event for debugging
    console.warn(
      `Message dropped for device ${targetDeviceId}. ` +
      `Reason: Device not in ACTIVE mode. Current mode: ${targetDevice.currentMode}.`
    );
  }
}
```

This state-aware forwarding is a cornerstone of the application's reliability. It gracefully handles race conditions where a session might be terminating at the exact moment an operator sends a final command, ensuring the command is safely dropped instead of being sent to a device that has already moved on.

## 7. Configuration, Data & Project Scope

This section details key configuration files, the evolution of our data storage strategy, and a critical clarification of the project's scope.

### 7.1. Device Registration: `backend/data/devices.yaml`

This file is the single source of truth for identifying and registering physical hardware devices with the system. The backend service loads this file at startup to map hardware identifiers (like MAC addresses) to user-facing information.

**Schema:**

The file is a YAML list of device objects. Each object must contain the following keys:

*   `id` (string, required): A unique UUID for the device within our system. This is the primary key.
*   `mac_address` (string, required): The physical MAC address of the device's network interface. Used for initial device identification on the network.
*   `owner` (string, optional): The name of the person or team the device is assigned to.
*   `badge` (string, optional): The employee ID or badge number associated with the owner.

**Example: `devices.yaml`**

```yaml
# A list of all known devices
# An entry must exist for a device to be recognized by the backend.
- id: "d8c3f7b1-a6b1-4c28-9a9f-39a1b1b2c3d4"
  mac_address: "AA:BB:CC:11:22:33"
  owner: "张三"
  badge: "12345"

- id: "e9f4a8c2-b7c2-5d39-bab0-4a2b2c3d4e5f"
  mac_address: "DD:EE:FF:44:55:66"
  owner: "李四"
  badge: "67890"

# This device is known to the system via its MAC address but is not
# assigned to a user. It is considered "unregistered".
- id: "f0a5b9d3-c8d3-6e4a-cbc1-5b3c3d4e5f6g"
  mac_address: "GG:HH:II:77:88:99"
  owner: ""
  badge: ""
```

**Crucial UI Contract:**

The distinction between a registered and unregistered device is handled by the presence of the `owner` and `badge` fields. This drives a strict UI display requirement:

*   **For Registered Devices** (both `owner` and `badge` are non-empty): The UI **must** format the display name as: `"工牌{badge} · {owner}"`.
    *   Example: `"工牌12345 · 张三"`
*   **For Unregistered Devices** (`owner` or `badge` field is empty or missing): The UI **must not** use the "工牌" format. It should either display nothing, a generic placeholder (e.g., "Unassigned Device"), or a technical identifier like the MAC address. This prevents displaying confusing partial information like `"工牌 · "` to the user.

### 7.2. Data Persistence: The JSON-to-SQLite Migration

The system initially stored all conversation history in a single, large `session_history.json` file. This approach was simple to implement but quickly became a major bottleneck.

**Pain Points of the JSON File Approach:**

1.  **Concurrency and Data Corruption:** The backend runs with multiple concurrent workers (Gunicorn). When two or more processes attempted to write to the JSON file simultaneously, it resulted in a race condition. This caused severe data corruption issues.
    *   **Observed Error Message:** `json.decoder.JSONDecodeError: Extra data:` would occur when one process read the file while another had only partially written its update, resulting in an invalid JSON structure.
    *   **Failed Fix:** Naive file locking with `fcntl` was attempted, but it introduced significant performance overhead and was difficult to manage reliably across stateless web workers, leading to frequent `IOError: [Errno 11] Resource temporarily unavailable` errors under load.

2.  **Performance Degradation:** Appending a new log entry required reading the entire multi-megabyte JSON file into memory, adding the new object to the list, and serializing the entire structure back to disk. This I/O-intensive operation caused API response times to skyrocket, directly impacting user experience.

**Solution: Zero-Downtime 'Dual-Write and Shadow-Read' Migration**

To move to a more robust SQLite database without service interruption, we implemented a phased migration strategy.

*   **Phase 1: Dual-Write:** We modified the data access layer to write all new log entries to **both** the legacy `session_history.json` and the new `conversations.sqlite` database. Reads continued to be served from the fast-but-unreliable in-memory cache of the JSON file. This ensured that the new database was populated with live data without affecting the user-facing application.

    ```python
    # Conceptual code in the data saving service
    def save_log_entry(entry_data):
        # Step 1: Write to the new, primary data source (SQLite)
        try:
            with sqlite3.connect("conversations.sqlite") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO conversation_logs (session_id, user_query, llm_response, timestamp) VALUES (?, ?, ?, ?)",
                    (entry_data['session_id'], entry_data['query'], entry_data['response'], entry_data['ts'])
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.critical(f"CRITICAL: Failed to write to SQLite, data may be lost! Error: {e}")
            # Trigger monitoring alert

        # Step 2: Write to the legacy data source for backward compatibility during transition
        try:
            # Note: Production code included a retry mechanism and safer file lock
            with open('session_history.json', 'r+') as f:
                history = json.load(f)
                history.append(entry_data)
                f.seek(0)
                json.dump(history, f, indent=2)
                f.truncate()
        except Exception as e:
            logger.error(f"Non-critical: Failed to write to legacy JSON file. Error: {e}")
    ```

*   **Phase 2: Shadow-Read & Verification:** We introduced a feature flag to enable "shadow reading". For a percentage of read requests, the system would fetch the data from **both** SQLite and the JSON file. The result from SQLite was returned to the user, while the two results were compared in the background. Any mismatch was logged as a high-priority warning (`"Shadow read mismatch for session_id: ..."`), allowing us to find and fix bugs in our migration logic without impacting users.

*   **Phase 3 & 4: Cutover & Decommission:** After running in shadow-read mode for a week with no discrepancies, we flipped the switch to make SQLite the sole source for all reads. The dual-write mechanism was kept for one more sprint as a safety net, after which the code paths related to `session_history.json` were removed and the file was archived.

### 7.3. Project Scope

Clarity on project scope is essential for managing stakeholder expectations and planning future work.

#### Implemented Core Functionality: The ASR→LLM→TTS Dialog Loop

The central feature delivered in this project is a complete, conversational request-response loop that defines the "smart assistant" experience. The workflow is as follows:

1.  **ASR (Automatic Speech Recognition):** User speech is captured and transcribed into text.
2.  **LLM (Large Language Model):** The transcribed text is sent to a generative AI model to formulate a response.
3.  **TTS (Text-to-Speech):** The AI-generated text response is converted back into speech and played to the user.

This loop handles single-turn and multi-turn conversations initiated by a user. It is the foundational feature of the product.

#### Explicitly Deferred Feature: Real-Time Meeting Transcription

A commonly requested feature, "real-time meeting transcription and summarization," was explicitly designated as **out of scope** for the initial release.

**Reasoning for Deferral:**

*   **Different Architectural Paradigm:** The implemented dialog loop is a **request-response** system. Real-time transcription requires a fundamentally different **streaming architecture** designed for continuous, low-latency audio processing and persistence.
*   **High Complexity:** This feature requires solving complex sub-problems not present in the dialog loop, including:
    *   **Speaker Diarization:** Accurately identifying *who* is speaking at any given time in a multi-person conversation.
    *   **Continuous ASR:** Handling a non-stop audio stream rather than a short, finite user command.
    *   **Live Summarization:** Processing a transcript as it's being generated.
*   **Strategic Focus:** The team's priority was to deliver a high-quality, reliable core dialog experience first. Tackling meeting transcription would have diluted this focus and compromised the quality of the initial release. It is a major feature that will be planned and resourced as a separate, future project.

## 8. Logging, Debugging, and Known Issues

This section provides essential information for debugging the event pipeline, understanding log output, and navigating known issues that might cause unexpected behavior.

### Glossary of Directional Log Prefixes

To effectively trace the lifecycle of an event, it's crucial to understand the prefixes used in the application logs. Each prefix indicates a specific action or state change for a given event.

*   **`[SEND]`**
    *   **Meaning:** An event has been successfully validated and is being sent to the downstream service for the first time. This is the starting point of an event's delivery attempt.
    *   **Debugging:** Look for this log to confirm that your event was generated and passed initial sanity checks. The log line will typically include the event ID and a destination identifier.
    *   **Example Log:** `[SEND] event_id="evt-12345" to_device="device-abcde" transaction_id="txn-987"`

*   **`[ACK]`**
    *   **Meaning:** Acknowledgment. The downstream service has successfully received and processed the event. This marks the successful completion of the event's lifecycle.
    *   **Debugging:** If you see a `[SEND]` followed by an `[ACK]` for the same event ID, the delivery was successful. The absence of an `[ACK]` after a `[SEND]` indicates a delivery problem.
    *   **Example Log:** `[ACK] event_id="evt-12345" from_device="device-abcde"`

*   **`[DROP_INVALID]`**
    *   **Meaning:** The event was rejected and permanently dropped before any delivery attempt was made because it failed a validation rule.
    *   **Debugging:** This indicates a problem with the event's source or generator. The log message will contain the reason for the drop. Common reasons include missing a required field (e.g., `device_id`), malformed data, or an invalid event type. This is a hard failure; the event will not be retried.
    *   **Example Log:** `[DROP_INVALID] event_id="evt-67890" reason="Missing required field: payload.data"`

*   **`[DROP_BY_MODE]`**
    *   **Meaning:** The event was valid but was intentionally dropped due to the system's current operational mode. For example, the system might be in a "maintenance" or "logging-only" mode where event dispatch is disabled.
    *   **Debugging:** If events are not being sent, check the system's operational mode. This is not an error with the event itself, but a result of system configuration.
    *   **Example Log:** `[DROP_BY_MODE] event_id="evt-abcde" reason="System in 'safe' mode"`

*   **`[FREEZE]`**
    *   **Meaning:** The event could not be delivered immediately and has been "frozen" in a persistent queue for a later retry attempt. This is a temporary failure state.
    *   **Debugging:** This is common when a destination device is temporarily offline or a downstream service is rate-limiting requests. The event is not lost. You should expect to see a corresponding `[REDELIVER]` log later. If an event is repeatedly frozen, it indicates a persistent problem with the destination.
    *   **Example Log:** `[FREEZE] event_id="evt-12345" reason="Device offline" retry_in="300s"`

*   **`[REDELIVER]`**
    *   **Meaning:** A previously frozen event is being re-sent from the retry queue. This log marks a new delivery attempt for an old event.
    *   **Debugging:** This indicates that the retry mechanism is functioning correctly. A sequence of `[FREEZE]` -> `[REDELIVER]` -> `[FREEZE]` for the same event ID points to a recurring issue that needs investigation (e.g., a device that never comes back online).
    *   **Example Log:** `[REDELIVER] event_id="evt-12345" attempt="3" transaction_id="txn-991"`

### Known Issue: Ambiguous Return from `send_to_device`

A significant bug was fixed related to how delivery failures were handled. Understanding this change is critical for interpreting system behavior, especially concerning retries.

*   **The Problem:** The original `send_to_device` function returned a simple boolean (`True` for success, `False` for failure). This was ambiguous because a `False` return could mean two very different things:
    1.  **Temporary Failure:** The device is temporarily unavailable or the push gateway is rate-limiting our requests. This should be retried with an exponential backoff strategy.
    2.  **Permanent Failure:** The device token is invalid or has been unregistered. This should **not** be retried, and the event should be permanently failed or frozen for a very long time.

    The single `False` value forced the calling code to treat both scenarios identically, leading to inefficient retries for permanently invalid devices and potentially exacerbating rate-limiting situations.

*   **The Fix:** The function's return signature was changed from a boolean to a tristate string to provide more context to the caller.

    *   `'ok'`: The event was successfully sent.
    *   `'limited'`: The event was rejected due to rate-limiting. The caller should freeze the event and retry after a calculated backoff period.
    *   `'offline'`: The event was rejected because the device is offline or the token is permanently invalid. The caller should freeze the event for a much longer duration or fail it.

*   **Impact on Code (Conceptual Example):**

    **Before (Ambiguous Handling):**
    ```python
    # old_logic.py
    if not send_to_device(event, device_token):
        # Is it a rate limit or a bad token? We don't know.
        # We are forced to treat it as a temporary failure and retry.
        print(f"[FREEZE] event_id={event.id} reason='Unknown failure'")
        schedule_for_retry(event)
    ```

    **After (Specific Handling):**
    ```python
    # new_logic.py
    result = send_to_device(event, device_token)

    if result == 'ok':
        print(f"[ACK] event_id={event.id}")
    elif result == 'limited':
        # Specific handling for rate-limiting
        print(f"[FREEZE] event_id={event.id} reason='Rate limited'")
        schedule_for_retry(event, backoff_strategy='exponential')
    elif result == 'offline':
        # Specific handling for an offline/invalid device
        print(f"[FREEZE] event_id={event.id} reason='Device offline or invalid token'")
        schedule_for_long_term_retry_or_fail(event)
    ```

### Here Be Dragons: Other Known Issues

This section contains a list of other subtle bugs and configuration pitfalls that have been discovered. Be aware of these when debugging strange behavior.

*   **Variable Typo in `pusher_config.json`:**
    *   **Symptom:** Push notification retries seem to happen much faster than configured, potentially leading to rate-limiting.
    *   **Cause:** In `pusher_config.json`, the key for setting the maximum backoff delay was incorrectly implemented in the code as `max_backoff_ms`. However, early documentation and examples referred to it as `max_backoff_milli`. Configurations using the incorrect `max_backoff_milli` key will be silently ignored, causing the service to use its hardcoded default value (e.g., `60000`ms) instead of the configured one.
    *   **Fix:** Ensure your configuration file uses the correct key: `"max_backoff_ms"`.

*   **Stale `last_seen` Timestamps:**
    *   **Symptom:** Devices that have been offline for extended periods are still being targeted for delivery attempts, filling logs with `[FREEZE]` and `[REDELIVER]` messages.
    *   **Cause:** A background job responsible for pruning expired device tokens was failing silently due to a database connection timeout. As a result, the `devices` table contained thousands of records with stale `last_seen` timestamps that should have been marked as inactive. The primary delivery logic does not check the `last_seen` field before attempting a send.
    *   **Fix:** Ensure the `device_pruning_worker` service is running and can connect to the database. Manually run the cleanup script if you suspect a large backlog of stale devices. Command: `python3 /app/scripts/prune_stale_devices.py --older-than-days 90 --dry-run`.