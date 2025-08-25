## Foundational Principles & Project Constraints

This document outlines the core operational principles and rigid constraints that govern project execution and communication. Adherence to these rules is mandatory to ensure consistency, clarity, and security.

### 1. The '@' Local File Access Prohibition

This is a fundamental security and operational boundary. The agent is explicitly forbidden from accessing the user's local filesystem or any resources referenced using the `@` symbol.

**Rule:** The agent must never attempt to read or interpret file paths prefixed with `@` (e.g., `@my_file.py`, `@./config/settings.yaml`). This syntax is unsupported and considered out-of-bounds.

**Agent's Corrective Response:** When a user provides a prompt containing an `@`-prefixed path, the agent must:
1.  Immediately identify the invalid request.
2.  Do not attempt to access the resource.
3.  Politely inform the user of the limitation.
4.  Instruct the user to provide the necessary context by copying and pasting the file's content directly into the chat prompt.

#### Example Interaction

**Incorrect User Prompt:**
> "Review the Dockerfile at `@project/Dockerfile` and suggest optimizations for layer caching."

**Correct Agent Response:**
> "I cannot access local file paths like `@project/Dockerfile`. To help you optimize it, please paste the full content of your Dockerfile directly into our chat."

### 2. The '80/20' or 'Explain to a High School Student' Communication Principle

This principle governs all communication, particularly when explaining technical concepts. The goal is to prioritize long-term business value by making knowledge accessible to a broad audience, not just technical experts.

**Core Concept:** All explanations must be simplified to convey the most critical 80% of the information using only 20% of the technical jargon. The "acid test" is whether an intelligent high school student or a non-technical project manager could understand the *what*, the *why*, and the *business impact* of the subject. This does not mean "dumbing down" the content, but rather focusing on clarity, purpose, and analogy over esoteric terminology.

**Application:**
*   **Summaries & Overviews:** High-level descriptions in documentation or proposals must follow this principle strictly.
*   **Technical Deep Dives:** While detailed sections can be more technical, they should still be prefaced with a simplified overview.
*   **Business Value:** Always connect technical decisions back to business outcomes (e.g., "This new database system will reduce customer wait times" instead of "We will migrate to a sharded, multi-region NoSQL cluster").

#### Example: Contrasting Communication Styles

**Bad Communication (Jargon-Heavy):**
> "We'll refactor the monolith's authentication module into a standalone microservice. We will use JWTs issued by a new IdP service, and inter-service communication will be brokered via a service mesh sidecar proxy to handle mTLS."

**Good Communication ('80/20' Compliant):**
> "We are breaking out the user login system from our main application into its own separate, independent service. This will make it more secure and easier to update. When users log in, they will get a secure digital 'ticket' (JWT) that proves who they are. All communication between our internal services will be automatically encrypted, which greatly improves our security posture."

### 3. The Mandatory 5-Section Markdown Output Structure

This is a rigid, non-negotiable project constraint for all formal solution proposals, architecture documents, and significant technical analyses. This structure enforces a logical thought process, ensuring that the problem, goals, solution, and implementation plan are all clearly documented.

All such documents **must** contain the following five sections, in this exact order, using their specific titles in Markdown.

---

**`### As-Is State`**

*   **Purpose:** To establish a baseline. This section describes the current system, architecture, or process.
*   **Content:** It must detail the existing situation, including known pain points, limitations, and relevant metrics. For example, "The current batch process takes 4 hours to run, blocking new data ingestion" is a good statement for this section.

**`### Requirements`**

*   **Purpose:** To define success. This section outlines the specific goals and constraints for the proposed work.
*   **Content:** It should be a clear, itemized list of functional and non-functional requirements. Requirements must be specific and measurable where possible (e.g., "Reduce API response time for the `/users` endpoint to under 200ms on average").

**`### Target Architecture`**

*   **Purpose:** To describe the proposed solution. This is the technical core of the document.
*   **Content:** A detailed description of the "to-be" state. This section must include concrete examples such as code snippets, configuration files, schema definitions, and descriptions of diagrams to clearly illustrate the new design.

**`### Path to Target`**

*   **Purpose:** To create an actionable plan. This section bridges the gap between the "As-Is State" and the "Target Architecture."
*   **Content:** An implementation plan, which could be a sequence of steps, a phased rollout strategy, or a list of key tasks. It should also identify potential risks, dependencies, and necessary prerequisites.

**`### Citations`**

*   **Purpose:** To provide evidence and credit sources. This ensures that all information is verifiable and builds trust in the solution.
*   **Content:** A list of all sources used to inform the document. This includes links to official documentation, relevant articles, internal wiki pages, or notes from conversations with specific team members (e.g., "Decision based on discussion with Jane Doe on 2023-10-27").

#### Example Structure Template

```markdown
### As-Is State

The current data pipeline relies on a nightly cron job running a single Python script. This script frequently fails due to memory limitations on the VM, and there is no automated alerting for failures. The process takes an average of 6 hours to complete.

### Requirements

*   The data processing time must be reduced by at least 50%.
*   The system must automatically retry on transient failures.
*   An alert must be sent to the on-call engineer if a job fails permanently.
*   The solution must be scalable to handle a 3x increase in data volume over the next year.

### Target Architecture

We will implement a serverless event-driven architecture using AWS Step Functions and Lambda. An S3 file upload will trigger a Step Function workflow.

**Step Function Definition (`sfn.json`):**
```json
{
  "Comment": "A simple state machine that processes a file.",
  "StartAt": "ProcessFile",
  "States": {
    "ProcessFile": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:ProcessFileLambda",
      "Retry": [ {
        "ErrorEquals": [ "States.Timeout" ],
        "IntervalSeconds": 3,
        "MaxAttempts": 2
      } ],
      "End": true
    }
  }
}
```
This architecture is inherently scalable and leverages built-in AWS retry and error handling logic.

### Path to Target

1.  **Phase 1: Develop & Test:**
    *   Develop the `ProcessFileLambda` function.
    *   Define and test the Step Function workflow in a development environment.
2.  **Phase 2: Deploy & Parallel Run:**
    *   Deploy the new architecture using CloudFormation.
    *   Run the new system in parallel with the old cron job for one week to validate results.
3.  **Phase 3: Decommission:**
    *   Disable the old cron job.
    *   Remove the old VM and script.

### Citations

*   [AWS Step Functions Developer Guide](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html)
*   Internal Document: [Data Processing Pain Points Q3 2023](https://confluence.example.com/...)
*   Conversation with John Smith regarding data volume projections.
```

## Core Architecture: The 'Backend-Driven' & 'Fail-Closed' Philosophy

Our core architecture is built upon two interconnected philosophies designed to maximize stability, security, and predictability: **"Backend-Driven"** state management and a **"Fail-Closed"** safety posture. This model treats the backend as the authoritative "brain" and the physical hardware as a "limb" that executes commands but holds no persistent state of its own.

### The 'Backend-Driven' Philosophy: Eliminating State Drift

The primary problem this philosophy solves is **state drift**. This occurs when the state displayed on the hardware becomes desynchronized from the true state held by the backend. This can happen due to network interruptions, dropped packets, or race conditions during boot-up, leading to confusing or incorrect user experiences (e.g., a device showing an "Available" status when it's actually reserved).

Our solution establishes a strict hierarchy:

*   **The Brain (Backend):** The backend is the single source of truth for all application logic and display content. It maintains the canonical state of all connected devices.
*   **The Limb (Hardware):** The hardware is a stateless rendering engine. It executes commands received from the backend but never makes independent decisions about what to display or how to behave (with one key exception: the initial boot sequence). It trusts the backend implicitly, but only after validating the commands it receives.

#### Corrected Boot Sequence and the 'wake' Event

To prevent race conditions where the backend might try to render content to a device that isn't ready, we enforce a strict, event-driven boot and initialization sequence. The hardware *never* attempts to fetch its own state; it waits to be told what to do.

1.  **Power On & Firmware Load:** The hardware powers on and loads its internal firmware.
2.  **Display Local Welcome Page:** The device immediately displays a static, locally-stored `welcome.html` page. This page is self-contained and requires no network connectivity. Its sole purpose is to provide immediate visual feedback to an operator that the hardware is powered on and booting. It typically contains only a logo and a "System initializing..." message.
3.  **Network Handshake:** The hardware connects to the network and establishes a secure WebSocket connection to the backend orchestrator service.
4.  **The `device:wake` Event:** Once the connection is established and the hardware's rendering engine is fully initialized, it sends a single, specific event to the backend.

    **Example `device:wake` payload:**
    ```json
    {
      "event": "device:wake",
      "payload": {
        "deviceId": "HW-UNIT-78A4F8",
        "firmwareVersion": "v2.1.3",
        "ipAddress": "192.168.1.102",
        "screenResolution": "1920x1080"
      }
    }
    ```
5.  **Backend Assumes Control:** The backend only begins sending rendering commands (e.g., `render_template`, `update_data`) to a device **after** it has received the `device:wake` event for that specific `deviceId`. This guarantees the "limb" is ready to receive instructions from the "brain" and prevents the backend from sending commands into a void.

### The 'Fail-Closed' Safety Pattern

The "Fail-Closed" principle complements the Backend-Driven model. It dictates that in any state of ambiguity, error, or communication loss, the system defaults to a secure, non-interactive, and safe state.

*   **Connection Loss:** If the WebSocket connection to the backend is severed for more than a configured timeout (e.g., 15 seconds), the hardware's firmware is mandated to immediately stop rendering any backend-provided content and revert to displaying the static, local `welcome.html` page. It will then continuously try to re-establish the connection. This prevents the device from displaying stale, potentially incorrect information.
*   **Invalid Commands:** If the hardware receives a command from the backend that it cannot validate, it **must** drop the command entirely and log the error. It will not attempt to render a partially-valid command or enter an undefined state. This is enforced by the validation pipeline.

### The Three-Stage Validation Pipeline

To enforce the Fail-Closed pattern, every single command received from the backend must pass through a strict, three-stage validation pipeline on the hardware *before* being processed. The order of these stages is critical for efficiency and clear error diagnosis.

#### Stage 1: Schema Validation

This is a cheap, fast check to ensure the command's structure is fundamentally correct. It validates data types, required fields, and object structure against a predefined JSON schema.

*   **Purpose:** Catch malformed data, typos in keys, or incorrect data types sent by the backend.
*   **Example Invalid Command (missing `items` array):**
    ```json
    {
      "command": "render_list",
      "payload": {
        "title": "Available Rooms"
      }
    }
    ```
*   **Result:** The command is immediately rejected.
*   **Log Message:**
    ```
    ERROR: Command dropped. Reason: Schema validation failed. Path 'payload.items' is a required property. Identifier: DROP_INVALID
    ```

#### Stage 2: Mode Whitelist Validation

Only if a command passes schema validation does it proceed to this stage. Here, the hardware checks if the received command is permissible in its current operating mode. The backend sets the device's mode (e.g., `KIOSK_INTERACTIVE`, `KIOSK_STATIC`, `MAINTENANCE`).

*   **Purpose:** Prevent logically incorrect operations, such as trying to play a video on a device meant to show only static images.
*   **Why this order is critical:** There is no point checking the mode-appropriateness of a command that is already structurally invalid (`DROP_INVALID`). By checking the schema first, we ensure that `DROP_BY_MODE` errors are always for structurally valid but contextually incorrect commands, which makes debugging far easier.

*   **Mode-Command Whitelists:**

    *   **Mode: `KIOSK_STATIC`**
        *   `render_template`
        *   `update_data`
    *   **Mode: `KIOSK_INTERACTIVE`**
        *   `render_template`
        *   `update_data`
        *   `show_dialog`
        *   `get_user_input`
    *   **Mode: `DIGITAL_SIGNAGE`**
        *   `render_template`
        *   `play_video`
        *   `set_playlist`
    *   **Mode: `MAINTENANCE`**
        *   `reboot`
        *   `run_diagnostics`
        *   `get_logs`

*   **Example Invalid Command by Mode:** A device in `KIOSK_STATIC` mode receives the following structurally valid command:
    ```json
    {
      "command": "play_video",
      "payload": {
        "url": "http://example.com/video.mp4"
      }
    }
    ```
*   **Result:** The command is rejected because `play_video` is not in the `KIOSK_STATIC` whitelist.
*   **Log Message:**
    ```
    WARN: Command dropped. Reason: Command 'play_video' not permitted in current mode 'KIOSK_STATIC'. Identifier: DROP_BY_MODE
    ```

#### Stage 3: Content Sanitization

This final, most resource-intensive check is only performed on commands that are both structurally valid and mode-appropriate. It inspects the actual content of the payload to enforce hard limits, preventing buffer overflows, denial-of-service through resource exhaustion, or layout-breaking content.

*   **Purpose:** Sanitize content strings and arrays to ensure they fit within UI and system memory constraints.

*   **Precise Sanitization Limits:**

| Parameter Path | Limit Type | Value | Action on Violation |
| :--- | :--- | :--- | :--- |
| `payload.title` | Max String Length | `128` characters | Truncate with `...` |
| `payload.body` | Max String Length | `1024` characters | Truncate with `...` |
| `payload.items` | Max Array Count | `50` items | Truncate array |
| `payload.items[].label` | Max String Length | `256` characters | Truncate with `...` |
| `payload.url` | Max String Length | `2048` characters | Drop Command |

*   **Example:** If a `render_list` command contains `60` items in its `payload.items` array, the hardware will process only the first `50` and discard the remaining `10`. If a `payload.url` exceeds 2048 characters, the entire command is dropped as this is a potential security or stability risk.

## Protocol Deep Dive: Message Contracts & Routing

All communication between the backend and devices happens over a persistent connection (e.g., WebSocket) using a simple, JSON-based messaging protocol. Messages from the backend specify a target device, and devices respond with acknowledgments or errors, allowing for a reliable, asynchronous request/response flow.

To ensure requests can be tracked, all messages initiated by the backend (`ui.render`, `device.control`) **must** include a unique `message_id`. All corresponding responses from the device (`ui.ack`, `ui.error`) **must** reference this ID in a `correlation_id` field.

### Message Routing: The `to` field and `device-id`

All commands sent from the backend to a device are routed using the `to` field. This field is critical for ensuring the message reaches the correct destination.

*   **Field**: `to`
*   **Type**: `Array` of `String`
*   **Format**: The array contains one or more `device-id` strings. Although the format is an array to support future multicasting, current implementations typically target a single device per message.
*   **`device-id` Definition**: The device identifier is the **lowercase, colon-separated MAC address** of the device's primary network interface (e.g., `eth0` or `wlan0`).

**Correct `device-id` format:**

```
b8:27:eb:12:34:56
```

**Example `to` field in a message:**

```json
{
  "to": ["b8:27:eb:12:34:56"]
}
```

---

### Message Type: `ui.render`

This is the primary message for controlling a device's display. It instructs the device to render a specific screen layout (`page_type`) and populates it with content (`slots`).

*   **Direction**: Backend -> Device
*   **Description**: This message uses a "Page Type + Slot Content" Domain-Specific Language (DSL). The `page_type` refers to a pre-defined layout template on the device firmware (e.g., `two_line_text`, `image_with_caption`). The `slots` object is a key-value map where keys are the named content areas in the template and values are the content to be inserted. The device firmware is responsible for knowing how to render each `page_type` and its associated slots.

**Canonical `ui.render` Example:**
This command tells the device to use the `two_line_with_status` template, populating the `line1`, `line2`, and `status_icon` slots with the provided text and icon name.

```json
{
  "type": "ui.render",
  "message_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "to": ["b8:27:eb:12:34:56"],
  "payload": {
    "page_type": "two_line_with_status",
    "slots": {
      "line1": "Conference Room 3B",
      "line2": "In Use: Project Phoenix Standup",
      "status_icon": "icon_busy"
    }
  }
}
```

---

### Message Type: `device.control`

This message is used for commands that do not affect the UI, such as administrative or maintenance tasks.

*   **Direction**: Backend -> Device
*   **Description**: The `action` field specifies the command to execute (e.g., `reboot`), and the optional `params` object provides any necessary arguments. The device firmware must explicitly support the requested action.

**Canonical `device.control` Example:**
This command instructs the device to reboot after a 5-second delay.

```json
{
  "type": "device.control",
  "message_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "to": ["c0:ee:fb:a1:b2:c3"],
  "payload": {
    "action": "reboot",
    "params": {
      "delay_ms": 5000
    }
  }
}
```

---

### Message Type: `ui.ack`

A positive acknowledgment sent from the device to confirm successful processing of a backend command.

*   **Direction**: Device -> Backend
*   **Description**: The `correlation_id` is mandatory and must contain the `message_id` of the original message being acknowledged. The `from` field identifies the device sending the acknowledgment using its `device-id`. The `payload` for an ack is typically empty.

**Canonical `ui.ack` Example:**

```json
{
  "type": "ui.ack",
  "from": "b8:27:eb:12:34:56",
  "correlation_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "payload": {}
}
```

---

### Message Type: `ui.error`

An error message sent from the device when it fails to process a backend command. This is essential for debugging.

*   **Direction**: Device -> Backend
*   **Description**: Like `ui.ack`, this message includes the `from` identifier and the `correlation_id` of the failed command. The payload contains a structured `code` for programmatic error handling and a descriptive `message` for logging and human inspection.

**Canonical `ui.error` Example:**
This error indicates that the device received a `ui.render` command with a `page_type` it doesn't recognize.

```json
{
  "type": "ui.error",
  "from": "b8:27:eb:12:34:56",
  "correlation_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "payload": {
    "code": "UNKNOWN_PAGE_TYPE",
    "message": "Device does not recognize page_type 'detailed_graph'. Supported types: ['two_line_with_status', 'image_only']."
  }
}
```

---

### Structured Error Codes

The following error codes should be used in the `code` field of `ui.error` messages.

| Error Code             | Description                                                                                             | Example `message`                                                                         |
| :--------------------- | :------------------------------------------------------------------------------------------------------ | :---------------------------------------------------------------------------------------- |
| `INVALID_PAYLOAD`      | The received JSON is malformed, not valid JSON, or is missing a required top-level field like `type`.     | "Payload is not valid JSON or required field 'type' is missing."                          |
| `RATE_LIMITED`         | The device is receiving commands too frequently and has temporarily blocked the client.                   | "Rate limit exceeded. Please wait 30 seconds before sending new commands."                |
| `UNKNOWN_PAGE_TYPE`    | The `page_type` in a `ui.render` payload is not recognized by the device firmware.                        | "Device does not recognize page_type 'three_line_summary'."                               |
| `INVALID_SLOT_CONTENT` | A required slot for a given `page_type` is missing, or the content format is invalid.                   | "Slot 'line1' is required for page_type 'two_line_with_status' but was not provided."     |
| `UNSUPPORTED_ACTION`   | The `action` in a `device.control` payload is not supported by the device.                              | "Action 'format_disk' is not supported on this device model."                             |
| `DEVICE_BUSY`          | The device cannot process the command because it is performing a long-running, blocking operation.        | "Cannot process command, device is currently performing a firmware update."               |
| `INTERNAL_ERROR`       | A generic, unexpected error occurred on the device. The message should contain diagnostic info if able. | "Internal device error: NullPointerException at ScreenManager.java:123."                  |

## Reliability Patterns: The ACK-Freeze Safety Valve

The ACK-Freeze Safety Valve is a critical flow control and device protection mechanism built into the command dispatch system. Its purpose is to automatically handle unresponsive devices, preventing the system from wasting resources on, or further destabilizing, a device that is struggling. It distinguishes between transient network blips and more persistent device failures through a three-step escalation process.

### The Three-Step Escalation Sequence

The entire process begins when a command is dispatched to a device and the system awaits an acknowledgment (ACK) that the command has been received and is being processed.

#### Step 1: Initial Timeout and Single Retry

When a command is sent, the system opens a 3-second window to receive an ACK from the device.

*   **Success Scenario:** The target device sends back an ACK within 3 seconds. The command is considered successfully dispatched, and processing continues as normal.
*   **Failure Scenario (Transient):** If the 3-second timeout is exceeded, the system assumes a transient network issue or a momentary lapse in the device's responsiveness. It will immediately attempt **one single retry**, sending the exact same command again and opening a new 3-second ACK window.

**Example Log Flow (Simplified):**
```log
# Attempt 1
INFO  [Dispatch] Sending command 'show interface status' to device=switch-leaf-101.rack3
... 3 seconds pass ...
WARN  [Dispatch] ACK Timeout for command 'show interface status' on device=switch-leaf-101.rack3. Retrying (1/1).

# Attempt 2 (Automatic Retry)
INFO  [Dispatch] Sending command 'show interface status' to device=switch-leaf-101.rack3
... ACK received within 3 seconds ...
INFO  [Dispatch] ACK Received for command 'show interface status' on device=switch-leaf-101.rack3.
```

If the retry is successful, the incident is logged as a warning, but the system takes no further punitive action.

#### Step 2: The 30-Second 'Freeze'

If the single retry attempt *also* fails to receive an ACK within its 3-second window, the system concludes that the device is suffering from a more serious, persistent issue. It is not a transient blip.

At this point, the safety valve engages, and the device is placed into a **'Frozen'** state for **30 seconds**. This action is logged with a very specific, critical message format that is essential for monitoring and alerting.

**The Canonical Freeze Log Message:**
```log
CRITICAL [FREEZE] device=switch-leaf-101.rack3 seconds=30 reason=ack-timeout
```

*   `device`: The identifier of the device being frozen.
*   `seconds`: The duration of the freeze. This is currently a fixed value of 30 seconds.
*   `reason`: The trigger for the freeze. In this case, `ack-timeout` indicates it was due to repeated failures to get a command acknowledgment.

The primary purpose of the 'Freeze' is to give the struggling device a "cool-down" period. Relentlessly sending more commands to a device with high CPU or a struggling control plane will only worsen the situation. The freeze enforces a mandatory pause.

#### Step 3: The 'Punishment' Phase (Life During a Freeze)

While a device is in the 'Frozen' state, the command dispatch system treats it differently:

1.  **Command Rejection:** Any standard operational or configuration commands (e.g., `show running-config`, `configure terminal`) sent to the frozen device are **immediately rejected** by the dispatcher. They are not queued or retried. The calling service or user will receive an immediate error.

    **Example Error Message:**
    ```
    Error: Command failed. Device 'switch-leaf-101.rack3' is currently in a frozen state. Try again in 30 seconds.
    ```

2.  **Allowed Commands (Health-Checks):** The freeze is not a total communication blackout. The system allows a minimal, whitelisted set of lightweight, read-only commands to be sent. The primary purpose of these commands is to check if the device has recovered. The canonical health-check command allowed during a freeze is `net.banner`.

    **Example `net.banner` command:**
    ```bash
    # This command would be allowed even during a freeze
    run-command --device switch-leaf-101.rack3 --command net.banner
    ```
    This command typically establishes a TCP connection to the device's management port (e.g., SSH on port 22) and reads the initial login banner, proving that the device's IP stack and SSH daemon are responsive without requiring a full login or intensive processing.

### Post-Freeze Behavior and Recovery

After the 30-second timer expires, the 'frozen' flag is automatically cleared from the device's state. The device is returned to the normal pool and is considered active again.

Crucially, **the device is not given any special treatment**. The very next command sent to it is subject to the same Step 1 (3-second ACK timeout) process. If it fails again, the entire 3-step escalation cycle will repeat, leading to another 30-second freeze. Frequent, recurring `[FREEZE]` logs for the same device are a strong indicator of a chronic underlying problem that requires manual intervention.

### Troubleshooting and Actionable Guidance

When you see a `[FREEZE]` log message, it is a high-fidelity signal that a device is in distress.

1.  **Immediate Triage:** Do not ignore this log. It is not a transient warning.
2.  **Correlate Timestamps:** Check the device's own logs and monitoring systems (CPU, memory, log files) for events that occurred around the time of the freeze log. Look for high CPU utilization, control-plane process crashes, or memory exhaustion.
3.  **Manual Connectivity Test:** From the control node, attempt to connect to the device manually. This bypasses the application logic and tests the raw network path and device responsiveness.
    ```bash
    # Test L3 reachability
    ping switch-leaf-101.rack3

    # Test management port and SSH daemon responsiveness
    ssh -v admin@switch-leaf-101.rack3
    ```
4.  **Check Intermediaries:** If the device itself seems healthy, investigate intermediary network elements like firewalls or access-control lists (ACLs) that might be dropping packets between the control system and the target device. The ACK packet (device-to-system) could be the one getting dropped.

## Hardware Integration & Performance Constraints

The physical constraints of the E-Ink display and associated processing hardware impose strict limitations on rendering frequency and API interaction. Failure to respect these constraints leads to poor user experience, device instability, and misleading monitoring alerts.

### E-Ink Rendering Strategy: Full Refresh and Merge Throttling

Due to the physical properties of E-Ink displays, rapid, partial updates are not feasible and lead to severe "ghosting," where remnants of the previous image persist. To ensure a clean display, Phase 1 development standardized on a two-part rendering strategy:

1.  **Full-Screen Bitmap Generation:** Every UI change triggers a full-screen render. The backend generates a complete 800x600 pixel monochrome bitmap representing the new desired state. There are no partial updates.

2.  **Mandatory 500ms Merge Throttling:** After a new bitmap is generated, the system enforces a mandatory, non-negotiable **500ms** delay before it can be merged and sent to the device for rendering. This throttling is essential to give the E-Ink screen's physical particles sufficient time to settle, preventing ghosting and visual artifacts.

This means that even if the backend can generate frames faster, the device's display cannot be updated more than twice per second. This physical limitation directly informs the API rate limits.

**Example Implementation (Illustrative Pseudocode):**

```go
const MERGE_THROTTLE_DURATION = 500 * time.Millisecond
var lastRenderTime time.Time

// This function is called every time a UI update is requested
func queueFrameForRender(newFrame *Bitmap) {
    // Calculate when the next frame is allowed to be rendered
    nextAllowedRenderTime := lastRenderTime.Add(MERGE_THROTTLE_DURATION)

    // If the throttle period has not passed, sleep for the remaining duration
    if time.Now().Before(nextAllowedRenderTime) {
        time.Sleep(time.Until(nextAllowedRenderTime))
    }

    // Send the frame to the device screen
    sendToDeviceDisplay(newFrame)
    lastRenderTime = time.Now()
}
```

### Backend API Rate Limiting

To protect the hardware and ensure stability, the backend enforces strict Queries Per Second (QPS) limits on its primary endpoints. Attempts to exceed these limits will result in requests being dropped.

*   **`ui.render` Endpoint:** A hard limit of **≤ 2 QPS** is enforced. This aligns directly with the 500ms E-Ink merge throttling, as any higher rate is physically impossible for the screen to display cleanly.
*   **`device.control` Endpoint:** A higher limit of **≤ 5 QPS** is allowed for non-display actions like LED blinking or sound playback.

**Example Command Subject to Rate Limiting:**

```bash
# This command will be dropped if called more than twice per second for the same device
grpcurl -d '{"device_id": "dev-123", "ui_component": "welcome_screen"}' \
  api.example.com:443 com.example.v1.UI/Render
```

### Backpressure Strategy: Bounded Queues and Oldest Frame Dropping

When the system receives requests faster than the enforced rate limits, it employs a backpressure mechanism to maintain responsiveness rather than crashing or becoming unresponsive.

The system uses **bounded queues** for incoming `ui.render` requests. When this queue becomes full, the **oldest frame** in the queue is dropped to make room for the newest one. This "head drop" strategy is critical for user experience. It ensures that what the user eventually sees on screen is the most recent state, preventing the device from displaying a backlog of stale frames and feeling "laggy."

**Scenario Walkthrough:**

1.  A user rapidly taps a button, generating five `ui.render` requests in under a second: `R1, R2, R3, R4, R5`.
2.  The processing queue has a size of 3.
3.  `R1`, `R2`, and `R3` fill the queue: `[R1, R2, R3]`.
4.  `R4` arrives. The queue is full. The oldest frame, `R1`, is dropped. The queue becomes: `[R2, R3, R4]`.
5.  `R5` arrives. The queue is full. The oldest frame, `R2`, is dropped. The queue becomes: `[R3, R4, R5]`.
6.  The device's rendering loop will process `R3`, `R4`, and `R5` in sequence (respecting the 500ms throttle), having completely skipped the intermediate states of `R1` and `R2`.

### Debugging Insight: Distinguishing 'Throttled' from 'Offline'

**Problem:** During initial load testing, monitoring systems triggered a high volume of "Device Offline" alerts. However, manual checks confirmed the devices were online and operational.

**Root Cause Analysis:** The API gateway's response logic was binary. It returned `SUCCESS` or `FAILURE`. A request dropped due to rate-limiting returned the same generic `FAILURE` status as a request that failed because the device was truly unreachable (e.g., a TCP timeout). The monitoring system could not differentiate between an expected operational state (throttling under load) and a critical fault (device offline).

**Error Message Logged Incorrectly:**
```log
ERROR: Failed to process ui.render for dev-123. Marking device as offline._
```

**Solution: Tristate Return Value**

The fix was to refactor the request processing logic to return one of three distinct states, allowing for more intelligent client-side handling and monitoring.

1.  **`SUCCESS`**: The request was accepted and sent to the device.
2.  **`FAILURE`**: A critical, non-recoverable error occurred (e.g., network timeout, invalid request payload). **This state should trigger alerts.**
3.  **`THROTTLED`**: The request was intentionally dropped due to backpressure (rate limit exceeded). **This is an expected state under high load and should not trigger a "device offline" alert.** It should be logged as a `WARN` or `INFO` and tracked via metrics to monitor queue health.

**Example of Improved Logic (Illustrative Go Code):**
```go
// Define the tristate enumeration
type Status int
const (
    SUCCESS   Status = 0
    FAILURE   Status = 1
    THROTTLED Status = 2 // The new state to distinguish rate-limiting
)

// The API handler can now return a more specific status
func HandleRequest(ctx context.Context, req *Request) (*Response, Status) {
    if isQueueFull(req.DeviceID) {
        log.Warn("Request for device %s throttled due to QPS limit.", req.DeviceID)
        return nil, THROTTLED
    }

    err := sendToDevice(req)
    if err != nil {
        log.Error("Device %s appears to be offline: %v", req.DeviceID, err)
        return nil, FAILURE
    }

    return &Response{Ack: true}, SUCCESS
}
```

## Architectural Evolution & Key Decisions

The project's architecture did not emerge fully formed but was the result of deliberate, strategic simplifications and deferred decisions aimed at accelerating the delivery of a stable core product. The initial vision was significantly more ambitious, but a key decision was made to radically simplify the Day 1 plan to focus exclusively on the core experience: rendering calendar and task data to an E-ink display.

### Deliberate Deferral of Complex Features

The most significant architectural decision was to postpone all complex meeting and audio-related functionality. The original roadmap included features like real-time audio transcription from device microphones and deep integration with calendar services for joining meetings directly. This was scoped down to a simple, read-only display of calendar events.

*   **Initial Plan:** A complex system involving audio processing pipelines, WebSocket communication for real-time updates, and stateful services to manage meeting contexts.
*   **Day 1 Plan (Simplified):** A stateless backend service that polls a calendar API at a regular interval, generates a static image, and serves it over a simple HTTP endpoint. This reduced backend complexity by an order of magnitude, eliminating the need for real-time infrastructure and complex state management. This decision was critical for meeting the initial launch timeline.

### The `EinkRenderEngine` Debate and Trigger Conditions

A central debate during initial planning was whether to build a sophisticated, component-based `EinkRenderEngine` from the start. Such an engine would treat elements like "the clock," "the date," or "a single calendar event" as independent, reusable components.

The decision was made to **deliberately defer its creation**. The Day 1 implementation uses a simpler, monolithic script that draws directly onto a PIL (Pillow) image canvas. This approach was faster to implement and sufficient for the initial MVP.

However, the team defined five specific trigger conditions that would necessitate the development of the full `EinkRenderEngine`. The presence of any of these requirements in a future product cycle will activate the plan to build it.

1.  **Pagination:** The need to display content that exceeds a single screen (e.g., a long task list or a full day's agenda). A proper engine is required to manage state, calculate page breaks, and render distinct "pages" of content.
2.  **Partial Refresh:** To take advantage of the E-ink display's ability to update only a small portion of the screen (e.g., for a ticking clock or weather update) without a full, flashing refresh. This requires a component-aware engine that knows the exact coordinates (`(x, y)` position and `width, height`) of the element being updated.
3.  **Theming:** To support user-selectable themes (e.g., dark/light mode, different typefaces, compact vs. spacious layouts). A rendering engine would allow for the dynamic application of style rules to components, whereas the current script has hardcoded fonts, sizes, and positions.
4.  **Complex List Styles:** For rendering structured lists beyond simple lines of text, such as bulleted lists, numbered lists, or to-do items with checkboxes. A layout engine is needed to correctly calculate indentation and item spacing.
5.  **Robust Unit Testing:** The current monolithic rendering script is difficult to test in isolation. A component-based `EinkRenderEngine` would allow for individual UI components to be unit-tested (e.g., "Does the calendar component correctly render an all-day event?").

### "Here Be Dragons": The `last_render_cache` Bug

A critical, hard-to-find bug early in development serves as a cautionary tale. It highlights how minor errors in core utility code can have significant, non-obvious impacts on the system.

*   **File:** `backend/core/utils/last_render_cache.py`
*   **Bug:** A variable name typo. The code intended to check a timestamp in a dictionary but used the wrong key due to a typo.
    ```python
    # Hypothetical example of the bug
    # BUG: The key should be 'last_render_timestamp'
    if cache.get('last_render_timestmap', 0) < new_data_timestamp:
        # Logic to trigger a new render
        ...
    ```
*   **Symptom:** The device screen would not update even when new calendar data was available. The backend logs showed that the data was being fetched correctly, but the final image was never re-generated because the cache-invalidation check was silently failing due to the typo.
*   **Solution:** Correcting the dictionary key `last_render_timestmap` to `last_render_timestamp`.
*   **Lesson:** This module is critical to the device's core refresh logic. Any changes must be met with extreme scrutiny and accompanied by integration tests that specifically verify the cache invalidation and re-rendering workflow. The subtlety of this bug marks this file as a "here be dragons" area of the codebase.

## Configuration, Data Management, and Migration

The system's configuration and persistent data are managed through a combination of a human-readable YAML file for device identity and a robust SQLite database for time-series sensor data. This design separates sensitive, static mapping information from high-volume, transactional data.

### Device Registry: `devices.yaml`

The `devices.yaml` file is the central, human-managed registry that maps physical device hardware to logical identifiers. It acts as a critical privacy layer, as it is the **only** component in the system that links a non-identifiable MAC address to a specific person, asset, or group.

*   **Location:** `backend/data/devices.yaml`
*   **Purpose:**
    1.  **Mapping:** Translates opaque hardware MAC addresses into meaningful `badge`, `owner`, and `group` identifiers used throughout the system's business logic and APIs.
    2.  **Privacy:** Isolates Personally Identifiable Information (PII). The main sensor database only stores MAC addresses, not who they belong to. Anonymized data analysis can be performed on the database without accessing this file.
*   **Schema:** The file is a dictionary where the key is the device's MAC address (lowercase, with colons) and the value is an object containing metadata.

| Key       | Type   | Description                                                               | Required |
| :-------- | :----- | :------------------------------------------------------------------------ | :------- |
| `badge`   | String | A unique, human-friendly identifier for the device (e.g., a tag number).  | Yes      |
| `owner`   | String | The name of the person or entity associated with the device.              | Yes      |
| `group`   | String | A logical grouping for categorization and filtering (e.g., "dev-team"). | Yes      |

*   **Example `devices.yaml`:**
    ```yaml
    # backend/data/devices.yaml
    #
    # This file maps hardware MAC addresses to their owners and logical groups.
    # It is manually edited and is critical for device identification.
    #
    "aa:bb:cc:dd:ee:ff":
      badge: "blue-badge-01"
      owner: "Alice"
      group: "dev-team"

    "11:22:33:44:55:66":
      badge: "red-badge-07"
      owner: "Bob"
      group: "qa-team"

    "f0:e1:d2:c3:b4:a5":
      badge: "asset-tag-9915"
      owner: "Conference Room Projector"
      group: "shared-assets"
    ```
*   **Management:** This file is intended to be updated manually. When a new device is provisioned or an existing one is re-assigned, an administrator must edit this file and restart the backend service for the changes to take effect. Failure to add a device here will result in its data being rejected or ignored.

    *   **Common Error:** If the backend logs show `WARN: Received data from unregistered MAC address 'XX:XX:XX:XX:XX:XX'`, it means the device's MAC address is missing from `devices.yaml`.
    *   **Solution:** Add a new entry for the MAC address in the `devices.yaml` file and restart the backend.

### Data Storage & Migration Strategy

The system has undergone a critical storage migration to improve scalability, reliability, and data integrity.

#### Initial State: Scattered JSON Files

Originally, sensor data was stored as individual JSON files on the filesystem. For each device, data was appended to a file named after its MAC address (e.g., `backend/data/readings/aa:bb:cc:dd:ee:ff.json`).

*   **Problems with this approach:**
    *   **Performance:** Inefficient for queries. Answering "how many readings from the 'dev-team' group were there yesterday?" required opening and parsing dozens of files.
    *   **Concurrency:** High risk of race conditions and data corruption when multiple processes or threads tried to write to the same file simultaneously.
    *   **Data Integrity:** No transactional guarantees. A partial write due to a crash could corrupt an entire JSON file.
    *   **Scalability:** Poorly handles a large number of devices or high-frequency data, potentially hitting filesystem limits on the number of files in a directory.

#### Target State: Unified SQLite Database with WAL

The current, improved architecture uses a single SQLite database file to store all sensor data.

*   **Location:** `backend/data/sensor_data.db`
*   **Mode:** Write-Ahead Logging (WAL) is enabled. This is crucial for performance and concurrency. You will see `sensor_data.db-wal` and `sensor_data.db-shm` files alongside the main database file during operation.
*   **Benefits:**
    *   **Atomic Transactions (ACID):** Writes are all-or-nothing, preventing data corruption.
    *   **High Concurrency:** WAL mode allows readers to operate without being blocked by writers, and vice-versa, which is essential for a system that is simultaneously ingesting data and serving API requests.
    *   **Indexing and Performance:** SQL queries with proper indexes are orders of magnitude faster than parsing flat files.
    *   **Simplicity:** A single, portable file makes backups and management trivial.

#### Rollback-Safe Migration Path

The migration from JSON files to SQLite was performed using a **dual-write and shadow-read** strategy to ensure zero downtime and provide a safe, immediate rollback path.

1.  **Dual-Write Phase:**
    *   A new version of the application was deployed. When new sensor data was received, the application wrote it to **both** the new `sensor_data.db` and the old `*.json` files.
    *   **Purpose:** This ensured that the legacy data store remained perfectly up-to-date. If a critical bug was found in the new SQLite-aware code, we could immediately roll back to the previous application version, which would read from the JSON files without any data loss.
    *   **Pseudo-code for the write operation:**
        ```python
        def save_sensor_data(data):
            # Attempt to write to the new primary data store first.
            try:
                db_connection.execute(
                    "INSERT INTO readings (...) VALUES (...)", data
                )
                db_connection.commit()
            except Exception as e:
                log.error(f"FATAL: Write to SQLite failed: {e}. Aborting.")
                # If the primary store fails, we must not write to the secondary
                # to avoid data inconsistency.
                raise e

            # If primary write succeeds, write to the legacy store for rollback safety.
            try:
                # This function opens a *.json file and appends the data
                write_to_legacy_json_file(data)
            except Exception as e:
                # This is a non-fatal error, as the primary source of truth
                # has the data. But it requires an alert.
                log.warning(f"Secondary (JSON) write failed: {e}. Data is safe in SQLite.")
        ```

2.  **Shadow-Read & Verification Phase:**
    *   During the dual-write phase, all application reads (e.g., for API endpoints) **continued to use the old JSON files** as the source of truth.
    *   The SQLite database was being populated in the background but was not yet "live".
    *   We ran offline verification scripts to compare the data in the SQLite database against the JSON files to ensure the writing logic was correct and data was consistent.

3.  **Cutover Phase:**
    *   Once we were confident in the new system's stability and data integrity, we deployed a final change.
    *   This change involved flipping a single configuration flag: `USE_LEGACY_STORAGE: false`.
    *   The application logic then switched to performing **all reads and writes exclusively with the SQLite database**. The code paths for JSON interaction were disabled.

4.  **Cleanup Phase:**
    *   After the new system ran successfully for a stabilization period (e.g., one week), the old `*.json` files were backed up and then deleted from the production server to reclaim disk space. The dual-write logic was removed from the codebase.

## Observability and System Evolution Roadmap

### Directional Log Prefixes for Message Tracing

To provide clear, traceable, and debuggable message flows through our asynchronous pipeline, we use a set of standardized log prefixes. Each prefix indicates the disposition of a message at a specific stage. A developer can trace a single message's entire lifecycle by filtering logs for its correlation ID and observing the sequence of these prefixes.

A complete, successful message lifecycle is `[SEND]` -> `[ACK]`. Any deviation from this pattern indicates a potential issue or a specific, designed behavior.

---

#### `[SEND]`

*   **Meaning**: A component is attempting to publish a message to the message bus (e.g., RabbitMQ, Kafka). This is the first step in inter-service communication.
*   **Context**: This log appears at the moment a service's producer logic is invoked, right before the message is handed off to the message bus client library.
*   **Why It's Important**: This log confirms that the business logic to create and send a message was executed. If you see a `[SEND]` from Service A but the message never arrives at Service B, the problem likely lies in the network, the message bus configuration, or the bus itself.
*   **Example Log Line**:
    ```log
    INFO: [SEND] corr_id=e4f5a2b1-12a8-44b2-9a8b-3d6f7c8e9d0a | Attempting to send user_request to topic 'nlp-jobs'. Payload size: 512 bytes.
    ```
*   **Debugging**:
    *   **Problem**: You see a `[SEND]` log, but the consuming service never logs a receipt.
    *   **Solution**:
        1.  Verify the topic/queue name in the log matches the consumer's configuration.
        2.  Check the message bus's management UI to see if the message is sitting in the queue (or was never published successfully).
        3.  Inspect broker logs for connection errors from the producing service.

---

#### `[ACK]`

*   **Meaning**: A message has been successfully received, processed, and explicitly **acknowledged**. The message will now be permanently removed from the queue. This marks the end of a successful processing journey.
*   **Context**: This is the final log entry in a consumer's successful processing workflow.
*   **Why It's Important**: This provides a definitive confirmation of end-to-end success. The absence of an `[ACK]` for a sent message indicates a failure or delay somewhere in the consumer or transport layer.
*   **Example Log Line**:
    ```log
    INFO: [ACK] corr_id=e4f5a2b1-12a8-44b2-9a8b-3d6f7c8e9d0a | Successfully processed 'nlp-jobs' message. Acknowledging and removing from queue.
    ```
*   **Debugging**:
    *   **Problem**: A message was sent, but you never see an `[ACK]` log.
    *   **Solution**: Look for other log types (`[DROP_INVALID]`, `[FREEZE]`, or application errors) in the consuming service's logs that share the same correlation ID. This will tell you *why* the message was not acknowledged.

---

#### `[DROP_INVALID]`

*   **Meaning**: A message was received but was immediately **dropped** because it failed a structural or semantic validation check. This is a non-recoverable error for this message. The message is acknowledged to prevent redelivery.
*   **Context**: This happens very early in the consumer's logic, typically right after deserialization and before any core business logic is executed.
*   **Why It's Important**: This indicates a contract violation between services. The producer is sending malformed or unexpected data.
*   **Example Log Line**:
    ```log
    WARN: [DROP_INVALID] corr_id=c8a9f0b3-e5d4-4f3c-8a1b-9e0d1a2b3c4d | Dropping message from 'user_requests'. Reason: Schema validation failed. Missing required field 'session_id'. Payload: {"user_text": "hello world"}
    ```
*   **Debugging**:
    *   **Problem**: Messages are being dropped with validation errors.
    *   **Solution**:
        1.  Examine the `Reason` and `Payload` in the log. This tells you exactly what is wrong.
        2.  Check the code of the producing service. A recent deployment may have changed the message structure.
        3.  Ensure both producer and consumer are aligned on the same data contract/schema version.

---

#### `[DROP_BY_MODE]`

*   **Meaning**: A message was received and is perfectly valid, but it was intentionally **dropped** due to the system's current operational mode (set by a feature flag or configuration). This is **not an error**, but a designed behavior.
*   **Context**: Used for canary releases, A/B testing, or safe-mode operations where certain message types are temporarily ignored.
*   **Why It's Important**: Clearly distinguishes intentional drops from error-based drops (`[DROP_INVALID]`), preventing false alarms during planned operational changes.
*   **Example Log Line**:
    ```log
    INFO: [DROP_BY_MODE] corr_id=f1b2c3d4-a5e6-4b7c-8d9e-1a2b3c4d5e6f | Dropping message of type 'audio_stream'. Reason: Service is running in 'text_only_mode'.
    ```
*   **Debugging**:
    *   **Problem**: Messages are being dropped unexpectedly, but the log indicates it's due to system mode.
    *   **Solution**: Check the service's configuration files (e.g., `config.yaml`, `.env`) or its runtime configuration source (e.g., Consul, LaunchDarkly) to see why the operational mode is set. This behavior is by design, so the "fix" is to change the configuration if the mode is incorrect.

---

#### `[FREEZE]`

*   **Meaning**: A message processing attempt failed due to a **transient, recoverable error** (e.g., downstream service timeout, temporary database deadlock). The message is **not** acknowledged (nack'd) and will be automatically redelivered by the message bus after a visibility timeout.
*   **Context**: This occurs in `catch` blocks that handle specific, transient exceptions like network timeouts or HTTP 503 errors from a downstream API.
*   **Why It's Important**: This is the core of our resiliency pattern. It prevents data loss from temporary glitches without needing a complex external retry mechanism.
*   **Example Log Line**:
    ```log
    ERROR: [FREEZE] corr_id=a7b8c9d0-e1f2-4a3b-8c4d-5e6f7a8b9c0d | Failed to process message. Reason: Connection to 'user-profile-db' timed out. Freezing message for redelivery. Attempt 2 of 5.
    ```
*   **Debugging**:
    *   **Problem**: Logs are filling up with `[FREEZE]` messages.
    *   **Solution**: The error is not in the service itself, but in a dependency. Check the health of the downstream system mentioned in the `Reason` (e.g., a database, another microservice). If the `[FREEZE]` logs persist, the "transient" issue may have become a hard outage requiring intervention.

---

#### `[REDELIVER]`

*   **Meaning**: A log indicating that the service is now processing a message that was previously frozen. This is the log entry for a retry attempt.
*   **Context**: This will be the first log line for a specific message attempt after the initial one failed with `[FREEZE]`.
*   **Why It's Important**: Helps trace the full lifecycle of a retried message. You can count the `[REDELIVER]` entries for a correlation ID to see how many attempts were made before success (`[ACK]`) or final failure (e.g., being sent to a Dead Letter Queue).
*   **Example Log Line**:
    ```log
    INFO: [REDELIVER] corr_id=a7b8c9d0-e1f2-4a3b-8c4d-5e6f7a8b9c0d | Re-attempting processing of frozen message. Attempt 3 of 5.
    ```
*   **Debugging**:
    *   **Problem**: You see a repeated loop of `[REDELIVER]` -> `[FREEZE]` for the same `corr_id`.
    *   **Solution**: This indicates the transient error is not resolving itself. The downstream dependency is likely still down or unhealthy. After the maximum number of retries, the message should be routed to a Dead Letter Queue (DLQ) for manual inspection.

***

### Stage 2: The Full Conversation Pipeline

The current text-based pipeline is the foundation for our ultimate goal: a real-time, voice-first conversational AI. The "Stage 2" architecture integrates three new core service components. Understanding this roadmap provides context for current development and future integration points.

The end-to-end user interaction flow in Stage 2 will be:

**`User Audio Stream -> [ASR Service] -> Text -> [LLM Service] -> Text -> [TTS Service] -> AI Audio Stream`**

---

#### 1. ASR (Automatic Speech Recognition) Service

*   **Purpose**: To transcribe the user's spoken audio into text in real-time. This service will be the new entry point for the entire conversation pipeline.
*   **Inputs**: A stream of raw audio chunks from the client (e.g., Opus-encoded audio packets over a WebSocket).
*   **Outputs**: A stream of JSON objects containing transcribed text. The output will differentiate between interim (in-progress) and final (user has finished speaking) results.
    *   **Example Output**: `{"text": "hello wor", "is_final": false, "confidence": 0.91}`
    *   **Example Output**: `{"text": "hello world", "is_final": true, "confidence": 0.95}`
*   **Integration**:
    *   The ASR service will listen for incoming WebSocket connections from clients.
    *   Upon receiving a **final** transcript (`is_final: true`), it will publish this text to the `llm-jobs` message queue (the same queue our current text pipeline consumes from). This makes the integration seamless.
*   **Technical Considerations**:
    *   **VAD (Voice Activity Detection)**: The service must intelligently detect the end of a user's utterance to know when to produce a final transcript.
    *   **Latency**: The time between the user finishing speaking and the final transcript being published is a critical performance metric.

---

#### 2. LLM (Large Language Model) Service

*   **Purpose**: To act as the "brain" of the conversation. It takes the transcribed user text, maintains conversational context, and generates a coherent, intelligent response. This is the evolution of our current "NLP Engine".
*   **Inputs**:
    1.  A text transcript from the ASR service (via the `llm-jobs` queue).
    2.  The conversation ID, used to retrieve conversation history from a state store (e.g., Redis).
*   **Outputs**: A JSON object containing the complete, final text response to be spoken to the user.
    *   **Example Output**: `{"response_text": "Hello! How can I help you today?", "conversation_id": "a7b8c9d0..."}`
*   **Integration**:
    *   It consumes text jobs from the `llm-jobs` queue.
    *   It fetches/updates conversation history in a Redis cache.
    *   It publishes its textual response to a new `tts-jobs` topic on the message bus.
*   **Technical Considerations**:
    *   **State Management**: Robustly handling conversation history is key to context-aware responses.
    *   **Prompt Engineering**: Significant effort will be required to design prompts that guide the LLM to produce desirable, safe, and efficient responses.
    *   **Model Selection**: We will need to choose between third-party LLM APIs (like OpenAI, Anthropic) and a potentially fine-tuned, self-hosted model, trading off cost, latency, and control.

---

#### 3. TTS (Text-to-Speech) Service

*   **Purpose**: To convert the text response generated by the LLM service into natural-sounding, audible speech.
*   **Inputs**: A JSON job from the `tts-jobs` queue containing the text to be synthesized.
    *   **Example Input**: `{"text_to_speak": "Hello! How can I help you today?", "voice_id": "narration-en-US-1"}`
*   **Outputs**: A stream of audio chunks (e.g., MP3 or Opus) sent back to the original client over the appropriate WebSocket connection.
*   **Integration**:
    *   It consumes jobs from the `tts-jobs` queue.
    *   It will need a mechanism to map a job back to the client's open WebSocket connection (e.g., via a connection manager or routing layer).
    *   It synthesizes the audio and streams it directly to the client.
*   **Technical Considerations**:
    *   **Time-To-First-Byte (TTFB)**: The time it takes from the TTS service receiving the text to the client receiving the *first* audio chunk is critical for perceived responsiveness. We will need a streaming TTS provider to minimize this "think time."
    *   **Caching**: Common phrases ("Hello," "I'm sorry, I didn't understand") can be pre-synthesized and cached to reduce latency and cost.