## Foundational Principles & Project Constraints

This document outlines the core principles and immovable constraints that govern every task and interaction within this project. Adherence to these rules is not optional and is fundamental to the project's success, ensuring clarity, repeatability, and efficiency.

### The 80/20 Communication Principle

This principle is the cornerstone of our communication strategy. It dictates that we focus our efforts on the 20% of information that will yield 80% of the value or desired outcome.

**Explanation for a High School Student:**

Imagine you have a big history test tomorrow. You could try to memorize the entire 500-page textbook (100% of the information), but you'll likely forget most of it. The 80/20 principle says to instead find the most important 20%—the key dates, the major events, the most influential figures, and the main causes of conflict. By mastering that critical 20%, you'll be able to answer about 80% of the questions on the test correctly.

**In Practice:**

When providing context for a task, do not provide vague, high-level goals. Instead, provide the critical 20%—the specific error message, the problematic code snippet, the exact configuration line that is failing, and the desired output. This focused, high-value information allows the agent to solve the problem efficiently without getting lost in irrelevant details.

**Example:**

*   **Ineffective (violates 80/20):** "My Python script isn't working. It's supposed to connect to a database, but it fails. Please fix it."
*   **Effective (follows 80/20):** "My Python script fails on line 32 with the error `psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed: FATAL: password authentication failed for user "admin"`. Here is the relevant connection code snippet. The correct password is stored in the environment variable `DB_PASSWORD`. Please correct the script to use the environment variable instead of the hardcoded, incorrect password."

### Mandatory Output Structure: The 5-Section Markdown Format

Every final deliverable **must** be structured into the following five markdown sections. This standardized format is non-negotiable and ensures that solutions are easy to understand, verify, and reuse.

1.  **`As-Is`**
    *   **Purpose:** To document the initial state of the problem. This section captures the "before" picture.
    *   **Content:** It must include the original, non-working code, configuration, or error message. This provides a baseline and context for the solution.
    *   **Example:**
        ```markdown
        ### As-Is

        The current `docker-compose.yml` file attempts to mount a volume but uses incorrect syntax, causing a startup error.

        **`docker-compose.yml` (Problematic):**
        ```yaml
        version: '3.8'
        services:
          web:
            image: nginx:latest
            ports:
              - "8080:80"
            volumes:
              - ./nginx.conf:/etc/nginx/nginx.conf # This line is correct
              - ./src:/var/www/html # This is the source of the issue
        ```

        **Error Message:**
        ```sh
        ERROR: for my-project_web_1  Cannot start service web: OCI runtime create failed: ... no such file or directory: unknown
        ```
        ```

2.  **`Requirements`**
    *   **Purpose:** To clearly state the goals. This defines what "fixed" or "done" means.
    *   **Content:** A bulleted list of explicit, objective requirements.
    *   **Example:**
        ```markdown
        ### Requirements

        - The `docker-compose.yml` file must be valid and execute without errors.
        - The local `./src` directory must be correctly mounted to the `/usr/share/nginx/html` directory inside the container.
        - The NGINX service must start successfully.
        ```

3.  **`Target`**
    *   **Purpose:** To present the final, working solution. This is the "after" picture.
    *   **Content:** The complete, corrected code snippet or configuration file. This is the primary deliverable.
    *   **Example:**
        ```markdown
        ### Target

        The corrected `docker-compose.yml` specifies the correct target directory for the NGINX default web root.

        **`docker-compose.yml` (Corrected):**
        ```yaml
        version: '3.8'
        services:
          web:
            image: nginx:latest
            ports:
              - "8080:80"
            volumes:
              - ./nginx.conf:/etc/nginx/nginx.conf
              - ./src:/usr/share/nginx/html # Corrected path
        ```
        ```

4.  **`Path`**
    *   **Purpose:** To explain *how* the `Target` was reached from the `As-Is` state and *why* the changes were made.
    *   **Content:** A step-by-step explanation of the thought process, commands used for diagnosis, and the rationale behind the fix. This section is crucial for knowledge transfer.
    *   **Example:**
        ```markdown
        ### Path

        1.  **Diagnosis:** The error message `no such file or directory` during a volume mount operation often means Docker is trying to mount to a path that doesn't exist *inside the container's base image*.
        2.  **Investigation:** I checked the official NGINX Docker image documentation (and could also verify by running `docker run --rm nginx:latest ls /var/www`). The default HTML root directory in the standard NGINX image is `/usr/share/nginx/html`, not `/var/www/html`.
        3.  **Solution:** The volume mount path in `docker-compose.yml` was updated from `./src:/var/www/html` to `./src:/usr/share/nginx/html` to match the correct directory within the NGINX container. This ensures the local source code correctly overwrites the default NGINX welcome page.
        ```

5.  **`Citations`**
    *   **Purpose:** To provide references and credit sources of information. This allows for future verification and deeper research.
    *   **Content:** Links to official documentation, Stack Overflow answers, blog posts, or internal wikis that were instrumental in finding the solution.
    *   **Example:**
        ```markdown
        ### Citations

        - [Official NGINX Image on Docker Hub](https://hub.docker.com/_/nginx) (See "Hosting some simple static content" section)
        - [Docker Compose `volumes` documentation](https://docs.docker.com/compose/compose-file/compose-file-v3/#volumes)
        ```

### The "Why" Section: Explaining Rationale

While not a standalone top-level section, providing the "Why" is a mandatory component of the `Path` section. Simply presenting a solution is insufficient. You must explain the underlying reasoning for the change.

*   **Purpose:** To build a durable knowledge base. Understanding *why* a fix works prevents the team from re-introducing the same bug or making similar mistakes in other contexts. It turns a simple fix into a learning opportunity.
*   **Example:**
    *   **Weak (Lacks "Why"):** "I changed the volume mount to `/usr/share/nginx/html`."
    *   **Strong (Includes "Why"):** "I changed the volume mount to `/usr/share/nginx/html` **because** that is the default document root directory within the official NGINX Docker image. The previous path, `/var/www/html`, is common in traditional Apache setups but does not exist by default in this container, which was the cause of the 'no such file or directory' error."

### System Operational Constraints

These are hard-coded limitations of the system that cannot be circumvented.

#### Prohibition of Local File Access (`@` syntax)

The agent operates in a secure, isolated environment and **cannot** access the user's local filesystem. Attempts to reference local files using the `@` syntax or any other file path notation will fail.

*   **Invalid Action:** Providing a prompt like `Please analyze the bug in @./src/main.py`.
*   **Reason:** This is a security and reproducibility constraint. The agent's environment is ephemeral and has no knowledge of or access to your machine's file structure.
*   **Mandatory Workaround:** You must paste the full, relevant content of the file directly into the prompt context.

    **Correct Usage:**
    ```
    I'm getting an error in the following Python file.

    `src/main.py`:
    ```python
    # ... entire content of main.py goes here ...
    import os

    def get_user():
      # ... function code ...

    print("Running...")
    ```

    The error is `NameError: name 'os' is not defined`. Please fix the code.
    ```

#### Required Agent Response Format

The agent's final output must **always** be a JSON object that adheres to the following structure. Failure to produce this exact JSON format will cause the entire operation to fail in downstream processing.

```json
{
  "status": "success",
  "reasoning": "A brief, one-sentence summary of the task outcome. For example: 'The Python script was corrected by adding the missing import statement for the 'os' module.'",
  "markdown_body": "The complete, 5-section markdown document (`As-Is`, `Requirements`, `Target`, `Path`, `Citations`) goes here as a single string."
}
```

*   **`status`**: (string) Must be either `"success"` or `"failure"`.
*   **`reasoning`**: (string) A concise, human-readable summary of what was done or why it failed.
*   **`markdown_body`**: (string) The full, meticulously formatted markdown content as described in the section "Mandatory Output Structure." This string will contain newlines (`\n`) for formatting.

## Core Architecture: The Backend-Driven UI & The 'EinkRenderEngine' Evolution

### The Backend-Driven Philosophy: A Cure for "State Drift"

The core of our device management architecture is a **Backend-Driven UI**. This principle dictates that the central backend server is the *single source of truth* for what should be displayed on any e-ink device at any given time. The device itself is treated as a "dumb" frame buffer; it receives a pre-rendered image or a set of drawing commands from the backend and simply displays it.

This approach was chosen specifically to solve the problem of **"state drift"**.

**What is State Drift?**

State drift occurs when the information displayed on the device's screen no longer matches the true state of the data in the backend. This commonly happens in systems where the device has its own logic for managing UI state.

*   **Example of Failure:** A device displays a meeting room reservation for "10:00 AM - Alice". The user cancels the meeting via a web interface. The backend updates, but a missed network packet or a bug in the device's polling logic prevents it from updating its own display. A second user, Bob, books the room for 10:00 AM. The backend is correct, but the device on the door still incorrectly shows Alice's name, leading to confusion and double-bookings.

By making the backend responsible for generating the final display output, we eliminate the possibility of the device's local state becoming desynchronized. If the backend's data changes, it simply generates a new image and pushes it to the device. The device's only job is to display what it's told.

### Corrected Boot Sequence: Local Welcome, Remote Wake-Up

Initial implementations tied the device boot sequence directly to the backend rendering service. This resulted in long boot times where the device would show a blank screen while waiting for a network connection and the first render from the backend. A network failure during boot would leave the device in an unusable blank state indefinitely.

The corrected and current boot sequence decouples the hardware boot from the backend rendering process, providing immediate user feedback and greater resilience.

1.  **Power On & Local Display:** The device powers on and its firmware immediately loads a static, pre-compiled "welcome" image from its local flash memory (e.g., `welcome.bmp`). This image is displayed within milliseconds of booting, confirming to anyone nearby that the hardware is powered and functional. The screen might display "Connecting to service..." or a company logo.
2.  **Check-in:** The device connects to the network and makes a "check-in" or "heartbeat" API call to the backend. This call registers the device as online and ready to receive commands.
    *   **Example `check-in` command:**
        ```bash
        # Device POSTs its status to the backend upon successful boot
        curl -X POST https://api.our-service.com/v1/device/heartbeat \
          -H "Content-Type: application/json" \
          -d '{
                "deviceId": "EINK-DEV-7C8B2A",
                "firmwareVersion": "v1.2.1",
                "batteryLevel": 98,
                "status": "ready_for_render"
              }'
        ```
3.  **Idle State:** The device now enters a low-power idle loop. It does nothing but wait for a push command from the backend.
4.  **Backend-Initiated "Wake-Up":** The backend **does not** render a new screen simply because a device checked in. It only initiates a render and "awakens" the device when there is new, relevant information to display (e.g., a new calendar event, an updated nameplate, a new price tag). The backend pushes the rendered image data to the device, which then displays it and returns to its idle state. This event-driven approach is far more efficient than a constant polling model.

### The `EinkRenderEngine`: A Conscious Deferral and Path Forward

Initially, the logic for rendering bitmaps and text onto the e-ink display was implemented directly inside the main `application.cc` file. This was a deliberate decision to prioritize development speed and validate the core backend-driven concept without the architectural overhead of designing a formal rendering engine.

The inline implementation was simple, performing basic tasks like clearing the screen and drawing text at hardcoded coordinates.

```cpp
// Simplified example of early, inline rendering logic in application.cc
void handle_render_request(const RenderData& data) {
    // ... network code to receive data ...

    // Clear the entire display buffer
    EPD_Clear();

    // Draw text at fixed positions. Lacks flexibility.
    Paint_DrawString(10, 20, data.title.c_str(), &Font24, WHITE, BLACK);
    Paint_DrawString(10, 50, data.line1.c_str(), &Font16, WHITE, BLACK);
    Paint_DrawString(10, 75, data.line2.c_str(), &Font16, WHITE, BLACK);

    // Push the buffer to the physical screen
    EPD_Display(BlackImage);

    // ... code to report success back to backend ...
}
```

While effective for a proof-of-concept, this approach does not scale. As requirements grew, it became clear that this dense logic needed to be refactored into a dedicated, reusable, and testable `EinkRenderEngine` module.

The decision was made to proceed with this refactoring only when one of the following five conditions was met. These triggers represent a complexity threshold where the cost of maintaining the inline code outweighs the cost of building a proper engine.

**Triggers for Creating the `EinkRenderEngine`:**

1.  **Pagination:** The need to display content that spans multiple "pages" on the device (e.g., a long agenda or a multi-page document). An engine is required to manage state, calculate page breaks, and render consistent headers/footers.
2.  **Partial Refresh:** The requirement to update only a small region of the screen (like a clock or status indicator) without the disruptive full-screen flash. This requires complex buffer management and precise coordinate calculations that are too messy for the main application file and are a classic responsibility of a dedicated rendering engine.
3.  **Theming:** The request to support multiple visual styles (e.g., dark mode, different font packs, brand-specific color schemes). A render engine can be designed to accept a theme configuration and apply it, whereas the inline approach leads to an impossible-to-maintain forest of `if/else` statements for styling.
4.  **Complex Lists and Dynamic Layouts:** The need to render lists where items have variable heights, icons, or word-wrapping text. Calculating the position of each element dynamically requires a true layout and rendering engine; hardcoded coordinates are no longer sufficient.
5.  **Formal Unit Testing:** The moment we require automated unit tests for the rendering logic. It is nearly impossible to test the rendering code in `application.cc` in isolation. A separate `EinkRenderEngine` class could be instantiated in a test harness, fed mock data, and have its output (e.g., a raw bitmap buffer) asserted against an expected result, ensuring rendering bugs are caught before deployment.

## The Hardware/Backend Contract: Protocol, Routing, and Device Identity

The communication between the backend and the hardware devices is conducted via a standardized JSON-based messaging protocol. Routing is handled explicitly through a device identifier, which is contractually defined as the device's **MAC address**.

### Communication Protocol and Message Types

All messages share a common envelope structure. The backend sends commands to devices, and devices respond with acknowledgements or errors.

*   **Routing Field:** `to: ["device-id"]`
    *   All commands sent from the backend to a device **must** include a `to` field.
    *   This field is a JSON array of strings.
    *   Each string in the array is the unique `device-id` (MAC address) of a target device. `["AA:BB:CC:11:22:33"]`
*   **Message Type Field:** `type: "namespace.action"`
    *   Identifies the purpose of the message.

#### Message: `ui.render`

Sent by the backend to instruct a device to display a specific UI.

*   **Direction:** Backend -> Device
*   **Canonical Example:**
    ```json
    {
      "type": "ui.render",
      "to": ["AA:BB:CC:11:22:33"],
      "payload": {
        "template": "meeting_room",
        "data": {
          "room_name": "Project Phoenix",
          "status": "In Use",
          "organizer": "工牌1024 · 张伟",
          "end_time": "15:30"
        }
      }
    }
    ```

#### C++ `RenderPayload` Struct Definition

The device firmware must be able to deserialize the `payload` object from a `ui.render` message. The canonical C++ struct for this is defined as follows. This allows for flexible data types within the payload.

```cpp
#include <string>
#include <map>
#include <variant>

// A flexible type to hold different data values like strings, numbers, or booleans.
using PayloadValue = std::variant<int, double, std::string, bool>;

/**
 * @brief Represents the deserialized payload of a `ui.render` message.
 *
 * This struct is the target for JSON deserialization in the device's C++ firmware.
 */
struct RenderPayload {
    // The name of the UI template to render, e.g., "meeting_room", "weather".
    // Corresponds to the "template" key in the JSON payload.
    std::string template_name;

    // A map of key-value pairs providing data to populate the template.
    // Corresponds to the "data" object in the JSON payload.
    std::map<std::string, PayloadValue> data;
};
```

#### Message: `device.control`

Sent by the backend to execute a system-level command on a device.

*   **Direction:** Backend -> Device
*   **Canonical Example:** Command to set screen brightness.
    ```json
    {
      "type": "device.control",
      "to": ["DD:EE:FF:44:55:66"],
      "payload": {
        "action": "set_brightness",
        "value": 80
      }
    }
    ```

#### Message: `ui.ack`

Sent by a device to confirm successful execution of a command.

*   **Direction:** Device -> Backend
*   **Context:** The source `device-id` is inferred by the backend from the communication channel's identifier (e.g., MQTT Client ID, which is set to the device MAC address).
*   **Canonical Example:**
    ```json
    {
      "type": "ui.ack",
      "payload": {
        "acked_type": "ui.render",
        "status": "success",
        "render_time_ms": 125
      }
    }
    ```

#### Message: `ui.error`

Sent by a device to report a failure in executing a command.

*   **Direction:** Device -> Backend
*   **Context:** Source `device-id` is inferred from the connection.
*   **Canonical Example:** An error due to insufficient device memory.
    ```json
    {
      "type": "ui.error",
      "payload": {
        "failed_type": "ui.render",
        "error_code": 507,
        "message": "Insufficient memory to render template 'high_res_image'"
      }
    }
    ```
    *   **Common Error:** `message: "Template 'unknown_template' not found on device."` This occurs when the `template` name in a `ui.render` payload does not exist in the device's firmware.

### The `devices.yaml` Contract

Device identity, metadata, and privacy are managed by a central configuration file in the backend. This file is the single source of truth for recognized devices.

*   **Location:** The file must be located at `backend/data/devices.yaml`.
*   **Schema:** The file is a YAML dictionary where the key is the device's MAC address (in uppercase string format) and the value is an object containing metadata.

    ```yaml
    # schema:
    <MAC_ADDRESS_STRING>:
      badge: <string>  # Employee badge ID, e.g., "1024"
      owner: <string>  # The name of the person associated with the device
      group: <string>  # The functional or organizational group, e.g., "dev", "hr"
    ```

*   **Concrete Example:**
    ```yaml
    # backend/data/devices.yaml

    AA:BB:CC:11:22:33:
      badge: "1024"
      owner: "张伟"
      group: "backend-dev"

    DD:EE:FF:44:55:66:
      badge: "3080"
      owner: "李静"
      group: "frontend-dev"
    ```

*   **Dual Purpose:**
    1.  **Identity Mapping:** It maps the non-human-friendly `device-id` (MAC address) to human-readable information (`badge`, `owner`). This data is used by the backend to enrich UI payloads.
    2.  **Privacy and Security:** It functions as an **allow-list**. Only devices registered in this file will have their identifying information displayed on any UI. Devices not present in this file are treated as "unregistered" or "anonymous" to protect privacy.

### UI Display Rule for Identity

To ensure a consistent and privacy-aware user experience, the following display rule for device identifiers **must** be enforced across all UIs (e.g., on meeting room screens, dashboards).

*   **For Registered Devices:**
    *   A device is considered "registered" if its MAC address exists as a key in `devices.yaml`.
    *   The identifier must be displayed using the exact format: `工牌{badge} · {owner}`.
    *   **Example:** For device `AA:BB:CC:11:22:33` from the YAML example above, the UI must display: `工牌1024 · 张伟`

*   **For Unregistered Devices:**
    *   A device is "unregistered" if its MAC address is not found in `devices.yaml`.
    *   **No identifying information of any kind should be displayed for the device.** The UI can show a generic status (e.g., "Reserved") but must not display the MAC address or any other potential identifier. This is a critical privacy requirement.

## Reliability Pattern 1: The ACK-Freeze Safety Valve

This pattern is a critical flow control and self-healing mechanism designed to handle unresponsive or intermittently available devices. It prevents the command queue from overwhelming a struggling device, giving it time to recover while still allowing for basic health monitoring. The entire process is driven by the acknowledgment (ACK) of commands.

The core principle is a three-step escalation sequence for any command requiring an ACK.

### The Three-Step Escalation Sequence

#### Step 1: Normal Operation - Command with an `id`

All commands that require a confirmation of receipt and execution are sent with a unique `id` field. This `id` is a correlation identifier that the system uses to match a response to its original request.

**Example Command Sent to Device:**
A command to set a configuration value is sent. The `id` is a unique UUID generated by the command issuer.

```json
{
  "id": "a4b1c2d3-e4f5-4a6b-8c7d-9e8f7a6b5c4d",
  "method": "config.set",
  "params": {
    "key": "network.wifi.enabled",
    "value": true
  }
}
```

**Expected Device Acknowledgment (ACK):**
A healthy device will process the command and return a response object containing the same `id`. The presence of this response serves as the ACK.

```json
{
  "id": "a4b1c2d3-e4f5-4a6b-8c7d-9e8f7a6b5c4d",
  "result": "ok"
}
```

The system waits for this ACK for a specific duration. If received, the command is considered successful, and the transaction is complete.

---

#### Step 2: First-Line Defense - A Single Retry on Timeout

If the expected ACK is not received within **3 seconds**, the system assumes the packet was lost or the device is slow to respond. It does not immediately assume failure.

Instead, it performs **one and only one** automatic retry. The retry sends the exact same command payload, including the original `id`.

**Triggering Event:** No response with `id: "a4b1c2d3-..."` received after 3 seconds.

**System Log on Timeout:**
```log
[WARN] device=DVC-C4E9F1 command_id=a4b1c2d3-e4f5-4a6b-8c7d-9e8f7a6b5c4d - ACK timeout after 3s. Retrying once.
```

**Action:** The system resends the command.

```sh
# Conceptual representation of the command being resent
send-command --device DVC-C4E9F1 --payload '{"id": "a4b1c2d3-...", "method": "config.set", ...}'
```

The system now starts a *new* 3-second timer, awaiting an ACK for the retried command. If the ACK is received this time, the operation succeeds, and the system returns to normal.

---

#### Step 3: The Safety Valve - The 30-Second Freeze

If the retried command *also* fails to receive an ACK within its 3-second window, the system escalates to its final defensive posture. It declares the device "unresponsive" and activates a **30-second freeze**.

This is the safety valve. It immediately stops sending any further high-level commands to the device. The assumption is that the device is overloaded, in a bad state, or network connectivity is severely degraded. Bombarding it with more commands would only worsen the situation.

**Triggering Event:** No response with `id: "a4b1c2d3-..."` received after the second 3-second timeout.

**Canonical Log Message for a Freeze Event:**
Upon initiating the freeze, the system MUST log the following canonical message. This specific format is used for alerting and metrics.

```log
[FREEZE] device=DVC-C4E9F1 seconds=30 reason=ack-timeout
```

*   `device`: The identifier of the device being frozen.
*   `seconds`: The duration of the freeze.
*   `reason`: The trigger for the freeze. In this pattern, it is always `ack-timeout`.

### The 'Punishment' Phase: Behavior During a Freeze

Once a device is in a frozen state, its interaction with the system is severely limited for the 30-second duration.

*   **Blocked Commands:** The command queue will immediately reject any new commands destined for the frozen device. This includes configuration changes (`config.set`), data requests (`data.get_latest`), or state-changing actions (`system.reboot`).
    *   **Example Error Message:** If a user or automated process attempts to send a command to a frozen device, the system will immediately return an error without attempting to transmit it.
    ```json
    {
      "error": {
        "code": -32001,
        "message": "Device is in a temporary freeze state due to unresponsiveness. Try again in 22 seconds.",
        "data": {
          "device": "DVC-C4E9F1",
          "state": "frozen",
          "reason": "ack-timeout",
          "retry_after_seconds": 22
        }
      }
    }
    ```

*   **Allowed Commands (The "Health Check" Whitelist):** The freeze does not mean a total communication blackout. A small, explicit whitelist of minimal, non-intrusive commands is still allowed. The primary use case is for basic health checks. The canonical whitelisted command is `net.banner`.
    *   **Purpose:** The `net.banner` command is a lightweight "ping" equivalent. It simply asks the device to respond with its identity, requiring minimal processing power. Allowing it enables our monitoring system to distinguish between a device that is completely offline versus one that is online but too overloaded to handle complex commands.
    *   **Example Allowed Command:**
        ```json
        {
          "id": "health-check-999",
          "method": "net.banner",
          "params": {}
        }
        ```
    *   This command is allowed to be sent even during the freeze. If it succeeds, we gain confidence the device is still on the network. If it fails, it reinforces the "unresponsive" diagnosis.

### Exiting the Freeze

After 30 seconds, the freeze is automatically lifted. The system logs this event and resumes normal operation, allowing all commands to be sent to the device again.

**System Log on Unfreeze:**
```log
[INFO] device=DVC-C4E9F1 - Freeze period ended. Resuming normal command processing.
```

If the device remains unresponsive, it will likely re-enter the ACK-Freeze pattern on the very next command sent, ensuring it remains protected from command flooding.

## Reliability Pattern 2: The 'Fail-Closed' Validation & Sanitization Pipeline

Our system's resilience depends on a strict, multi-stage validation pipeline that processes all incoming commands. This pipeline operates on a 'Fail-Closed' principle: a message is rejected by default and must explicitly pass every stage in a specific sequence to be processed. Any failure at any stage results in the message being immediately dropped and logged with a precise reason.

### The Correct Pipeline Sequence

The sequence of validation is critical. Executing these steps out of order can lead to misdiagnosed errors and significantly increase debugging time. The only correct sequence is:

1.  **Structural/Schema Validation:** Is the message format correct?
2.  **Mode-Based Whitelist Filtering:** Is this command allowed in the current system mode?
3.  **Content Sanitization:** Do the data payloads conform to size and length limits?

---

### Stage 1: Structural/Schema Validation

This is the first gate. It ensures that every incoming message conforms to the required JSON schema. It checks for the presence and data types of essential fields like `id`, `command`, and `params` before any logic is applied.

**Valid Message Structure:**
A message must contain the top-level keys `id`, `command`, and `params`.

```json
{
  "id": "a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890",
  "command": "ui.render",
  "params": {
    "type": "text",
    "header": { "title": "Welcome" },
    "body": { "text": "System is ready." }
  }
}
```

**Invalid Message & Error Logging:**
If a message is malformed (e.g., `params` key is missing), it is immediately dropped.

*   **Invalid Message Example:**
    ```json
    {
      "id": "f0e9d8c7-b6a5-4321-f0e9-d8c7b6a54321",
      "command": "ui.render"
      // Missing 'params' key
    }
    ```

*   **Resulting System Log:**
    The log must be specific, indicating a schema failure. This prevents developers from wasting time looking for logic or mode-related bugs.
    ```log
    [DROP_BY_SCHEMA] id=f0e9d8c7 Message failed validation: 'params' is a required property.
    ```

---

### Stage 2: Mode-Based Whitelist Filtering

After a message is confirmed to be structurally valid, the pipeline checks if the command is permitted in the device's current operational mode. This prevents unauthorized or contextually inappropriate actions.

**Initial Mode Whitelist Configuration:**
During sensitive initial states (`boot`, `welcome`, `testing`), the command surface is severely restricted. Only essential UI and network banner commands are allowed.

*   **Allowed Commands:** `ui.render(text|list)` and `device.control(net.banner)`.
*   **Configuration Example (`mode_config.yaml`):**
    ```yaml
    modes:
      boot:
        - ui.render
        - device.control
      welcome:
        - ui.render
        - device.control
      testing:
        - ui.render
        - device.control

    command_params_whitelist:
      ui.render:
        - text
        - list
      device.control:
        - net.banner
    ```

**Disallowed Command & Error Logging:**
If a message contains a command that is not on the whitelist for the current mode (e.g., a `system.reboot` attempt during `welcome` mode), it is dropped.

*   **Disallowed Message Example (during `welcome` mode):**
    ```json
    {
      "id": "b5a4c3d2-e1f0-9876-b5a4-c3d2e1f09876",
      "command": "system.reboot",
      "params": { "delay": 0 }
    }
    ```

*   **Resulting System Log:**
    The log clearly states the command was rejected due to the active mode's restrictions.
    ```log
    [DROP_BY_MODE] id=b5a4c3d2 Command 'system.reboot' not allowed in current mode 'welcome'.
    ```

---

### Stage 3: Content Sanitization

The final stage validates the content *within* the message parameters. This prevents UI overflows, denial-of-service via large payloads, and potential buffer exploits. This check is only performed on messages that have already passed schema and mode validation.

**Content Sanitization Limits:**

*   Header Title: `header.title` must be **<= 16 characters**.
*   Body Text: `body.text` must be **<= 200 characters**.
*   List Items Count: `body.items` array must contain **<= 8 items**.
*   List Item Length: Each string in the `body.items` array must be **<= 50 characters**.

**Content Violation & Error Logging:**
A message that is structurally valid and allowed by the current mode will be dropped if its content exceeds these limits.

*   **Message with Oversized Content:**
    ```json
    {
      "id": "c6b7a8d9-f0e1-2345-c6b7-a8d9f0e12345",
      "command": "ui.render",
      "params": {
        "type": "text",
        "header": { "title": "This is a very long title that will be rejected" }, // > 16 chars
        "body": { "text": "Body is fine." }
      }
    }
    ```

*   **Resulting System Log:**
    The log pinpoints the exact field and reason for the sanitization failure.
    ```log
    [DROP_BY_SANITIZE] id=c6b7a8d9 Content validation failed: 'header.title' length 29 exceeds limit 16.
    ```

---

### CRITICAL BUG: Incorrect Pipeline Order Results in Misleading Logs

A critical bug was discovered where the Mode Filter (Stage 2) was incorrectly placed before the Schema Validator (Stage 1). This masked the true source of errors, leading to significant diagnostic delays.

**Problem Scenario:** A malformed message with a missing `command` field is received.

*   **Malformed Message:**
    ```json
    {
      "id": "d7c8b9a0-1f2e-3d4c-d7c8-b9a01f2e3d4c",
      // Missing 'command' key
      "params": { "type": "text" }
    }
    ```

*   **Symptom with INCORRECT Order (Mode -> Schema):**
    1.  The Mode Whitelist filter runs first.
    2.  It attempts to read the `command` field to check it against the whitelist.
    3.  The field does not exist. The filter's error handling defaults to treating the command as "not found" or `null`.
    4.  It drops the message, logging a mode failure.

*   **Misleading Error Log:**
    ```log
    // WRONG AND MISLEADING LOG
    [DROP_BY_MODE] id=d7c8b9a0 Command '<not_found>' not allowed in current mode 'welcome'.
    ```
    This log sends the developer on a wild goose chase, investigating the mode logic or the sender's command choice, when the actual problem is a malformed JSON payload.

*   **Fix and Correct Behavior (Schema -> Mode):**
    By enforcing the correct `Schema -> Mode -> Sanitize` order:
    1.  The Schema Validator runs first and immediately detects the missing `command` field.
    2.  It drops the message and generates a precise, actionable log.

*   **Correct Error Log:**
    ```log
    // CORRECT AND ACTIONABLE LOG
    [DROP_BY_SCHEMA] id=d7c8b9a0 Message failed validation: 'command' is a required property.
    ```
This fix ensures that logs are always accurate to the point of failure, reflecting the foundational 'Fail-Closed' principle of the pipeline.

## State Management & Application Flow

The state of a device is managed through a `currentMode` property, which is reported to the backend via a WebSocket connection. This state machine dictates what a device can and cannot do at any given moment. The backend must respect this state when issuing commands.

### Device State Machine (`currentMode`)

The `currentMode` is the single source of truth for a device's operational state. Key states include:

*   `offline`: A virtual state tracked by the backend when no active WebSocket connection exists for the device.
*   `boot(local)`: The initial state upon power-on. The device is running local firmware instructions and has not yet successfully connected to the backend.
*   `connected(idle)`: The device has a stable WebSocket connection to the backend and is awaiting commands. This is the default "ready" state.
*   `dialog.preparing`: The device has received a command to prepare for a dialog. It is actively downloading assets (e.g., videos, images) and is not ready to accept other commands.
*   `dialog.active`: The device is currently running an interactive dialog sequence. It may be showing video, waiting for user input, etc. It cannot accept new dialog commands until the current one is finished.
*   `error`: The device has encountered an unrecoverable error and requires a reboot or manual intervention.

### Primary Application Flow: Boot to Active Dialog

This sequence is the most common operational flow for displaying content on a device.

#### 1. State: `boot(local)`

This is the initial state immediately after the device powers on or reboots.

*   **Trigger:** Device power-on.
*   **Device Responsibility:**
    1.  The device firmware **must** immediately load and display its "Render Test Page".
    2.  On this page, it **must** display the hardcoded, static text: `等待后端指令...`
    3.  This message is displayed *before* any network connection is established. It provides immediate visual feedback that the hardware is functional.
    4.  In the background, the device attempts to connect to the backend's WebSocket endpoint.
*   **Backend Responsibility:**
    *   The backend tracks the device as `offline`. It cannot send any commands and will reject any attempts to target this device.

#### 2. State: `connected(idle)`

*   **Trigger:** The device successfully establishes a WebSocket connection with the backend.
*   **Device Responsibility:**
    1.  Upon successful connection, the device immediately sends its first status update message.
    2.  It transitions its `currentMode` from the internal `boot(local)` state to `connected(idle)`.
    3.  The device firmware can now clear the `等待后端指令...` message and display a default idle screen (e.g., a company logo or an "Available" message).
    4.  It actively listens for incoming commands from the backend.
*   **Backend Responsibility:**
    1.  Receives the initial status update.
    2.  Updates the device's state from `offline` to `connected(idle)` in its central state store (e.g., Redis).
    3.  The device is now considered online and available for commands.

*   **Example:** First message from Device `dev-abc-123` to Backend upon connection.

    ```json
    {
      "type": "statusUpdate",
      "payload": {
        "deviceId": "dev-abc-123",
        "currentMode": "connected(idle)",
        "firmwareVersion": "1.2.3",
        "ipAddress": "192.168.1.100",
        "timestamp": "2023-10-27T12:00:05Z"
      }
    }
    ```

#### 3. State: `dialog.preparing`

*   **Trigger:** Backend sends a `dialog.prepare` command to an `idle` device. This pattern is used to preload assets and prevent stuttering or long load times when the dialog begins.
*   **Device Responsibility:**
    1.  Receives the command and immediately changes its state to `dialog.preparing`, reporting this back to the backend.
    2.  Begins downloading all assets specified in the command payload.
    3.  (Optional but recommended) It can send `download.progress` messages to the backend.
    4.  Once all assets are successfully downloaded and cached, it sends a `dialog.preparationComplete` message to the backend. It must not start the dialog yet.
*   **Backend Responsibility:**
    1.  Sends the `dialog.prepare` command.
    2.  Updates the device's state to `dialog.preparing`.
    3.  Waits for the `dialog.preparationComplete` message. It should implement a timeout (e.g., 60 seconds) and mark the device as errored or revert it to idle if the confirmation is not received.

*   **Example:** Backend command to initiate preparation.

    ```json
    {
      "type": "command",
      "to": ["dev-abc-123"],
      "payload": {
        "commandName": "dialog.prepare",
        "dialogId": "diag- seasonal-promo",
        "assets": [
          { "type": "video", "url": "https://cdn.example.com/promo_part1.mp4" },
          { "type": "image", "url": "https://cdn.example.com/end_screen.jpg" }
        ]
      }
    }
    ```

*   **Example:** Device confirmation that preparation is complete.

    ```json
    {
      "type": "event",
      "payload": {
        "deviceId": "dev-abc-123",
        "eventName": "dialog.preparationComplete",
        "dialogId": "diag-seasonal-promo",
        "status": "success"
      }
    }
    ```

#### 4. State: `dialog.active`

*   **Trigger:** Backend sends a `dialog.start` command, typically after receiving `dialog.preparationComplete`.
*   **Device Responsibility:**
    1.  Receives the command, updates its `currentMode` to `dialog.active`, and reports this change.
    2.  Immediately begins playback of the dialog using the pre-cached assets.
    3.  Sends events to the backend as the dialog progresses (e.g., `video.playback.ended`, `user.interaction`).
    4.  Upon completion of the sequence, it reverts its state to `connected(idle)` and sends a final `dialog.ended` event.
*   **Backend Responsibility:**
    1.  Sends the `dialog.start` command.
    2.  Updates the device's state to `dialog.active`.
    3.  Listens for events. May terminate a dialog prematurely with a `dialog.stop` command if necessary.
    4.  Upon receiving a `dialog.ended` event, it transitions the device's state back to `connected(idle)`.

### Backend Message Forwarding Logic with `to:["device-id"]`

A critical responsibility of the backend is to act as a gatekeeper, ensuring that commands are only sent to devices in an appropriate state. This prevents race conditions and undefined behavior.

When a message is received with a `to` field specifying one or more device IDs, the backend **must** perform this check for each target device:

1.  Query the central state store for the `currentMode` of the `device-id`.
2.  Apply the following forwarding rules:
    *   **IF `currentMode` is `connected(idle)`:** The device is ready. **Forward the message.**
    *   **IF `currentMode` is `dialog.preparing` or `dialog.active`:** The device is busy. **Do not forward the message.** The backend should either queue the message (if the system supports it) or reject it with an error.
    *   **IF `currentMode` is `offline`, `boot(local)`, or `error`:** The device is not available. **Do not forward the message.** Reject it immediately with an error.

*   **Example: Rejected Command**

    An external service attempts to start a new dialog while the device is already busy.

    *   **Incoming Command:**
        ```json
        {
          "type": "command",
          "to": ["dev-abc-123"],
          "payload": { "commandName": "dialog.prepare", "dialogId": "diag-urgent-alert" }
        }
        ```
    *   **Backend Check:** Backend looks up `dev-abc-123` and finds its `currentMode` is `dialog.active`.
    *   **Backend Response / Error Log:**
        ```json
        {
          "status": "error",
          "message": "Command rejected for device dev-abc-123.",
          "reason": "Device is not in 'connected(idle)' state. Current state: 'dialog.active'."
        }
        ```
This strict state validation is essential for system stability and predictable device behavior.

## Data Storage Migration: From JSON to SQLite

Our initial application architecture relied on storing individual data records as distinct JSON files in a directory structure (e.g., `./data/users/user-123.json`). While simple to implement, this approach presented significant scaling and reliability challenges.

### 1. Pain Points of the JSON File-Based Storage

As application usage grew, the limitations of this model became critical blockers:

*   **Concurrency & Race Conditions:** Multiple processes or threads attempting to write to the same file or directory led to data corruption. File locking mechanisms were difficult to implement correctly and consistently across different operating systems, often resulting in deadlocks.
*   **Performance Degradation:** High I/O operations, especially on network-attached storage (NFS), resulted in severe latency. Listing directories with thousands of files (`ls`, `readdir`) became a bottleneck. Each read/write operation incurred the overhead of opening, closing, and flushing file handles.
*   **Lack of Atomicity:** Operations involving multiple records (e.g., transferring a balance between two user accounts) were not atomic. If the application crashed after updating the first file but before updating the second, the system was left in an inconsistent state.
*   **Data Aggregation & Querying:** Answering simple questions like "How many users signed up last week?" required iterating over and parsing every single user file, which was computationally expensive and slow.

### 2. The Solution: Unified SQLite Database with WAL

To resolve these issues, we migrated to a single, unified SQLite database file. This choice provided the benefits of a transactional, ACID-compliant relational database without the operational overhead of a full client-server RDBMS.

A critical component of this solution was enabling **Write-Ahead Logging (WAL)**.

*   **Why WAL?** By default, SQLite uses a rollback journal, which locks the entire database during a write transaction. This would re-introduce a concurrency bottleneck. WAL mode allows for much higher concurrency by letting reads happen simultaneously with writes. Writers append changes to a separate `.wal` file, which are later checkpointed back to the main database file. This was essential for our application's performance profile.

**Command to Enable WAL:**
This `PRAGMA` statement should be executed once per database connection to ensure WAL mode is active.

```sql
-- a.sql
PRAGMA journal_mode=WAL;
```

```bash
# Applying the PRAGMA via the command line
sqlite3 my_application.db "PRAGMA journal_mode=WAL;"

# Verifying the mode
sqlite3 my_application.db "PRAGMA journal_mode;"
-- Expected output: wal
```

### 3. The Zero-Downtime Migration Pattern: Dual-Write and Shadow-Read

A "big bang" migration was not an option due to uptime requirements. We employed a phased approach that guaranteed zero downtime and provided a simple, safe rollback path at any point before the final cutover.

The core principle was: **Write to both systems, but trust the old system for reads until the new system is fully verified.**

---

#### **Phase 1: Preparation and Initial Data Seeding**

1.  **Define the Schema:** Create the DDL for the new SQLite tables. This schema must be able to represent all data structures from the JSON files.

    *Example `schema.sql`:*
    ```sql
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        display_name TEXT,
        created_at INTEGER NOT NULL, -- Storing as UNIX timestamp
        raw_json_data TEXT -- Store the original JSON for audit/backup
    );

    CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
    ```

2.  **One-Time Seeding Script:** Write and execute a script to perform an initial bulk load. This script reads all existing JSON files and inserts them into the new SQLite database.

    *Pseudo-code for `seed_sqlite.py`:*
    ```python
    import sqlite3
    import json
    import os

    conn = sqlite3.connect('my_application.db')
    cursor = conn.cursor()

    # Create tables from schema.sql
    with open('schema.sql') as f:
        cursor.executescript(f.read())

    # Iterate and insert
    for filename in os.listdir('./data/users'):
        if filename.endswith('.json'):
            with open(os.path.join('./data/users', filename), 'r') as f:
                data = json.load(f)
                cursor.execute(
                    """
                    INSERT INTO users (user_id, email, display_name, created_at, raw_json_data)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO NOTHING;
                    """,
                    (
                        data.get('id'),
                        data.get('email'),
                        data.get('name'),
                        data.get('createdAt'),
                        json.dumps(data)
                    )
                )
    conn.commit()
    conn.close()
    ```

---

#### **Phase 2: Dual-Write Implementation**

Modify the application's data writing logic to write to **both** the new SQLite database and the legacy JSON files.

*   **Order of Operations:** The write to the **new system (SQLite) should happen first**. If it fails, the operation is aborted, and no data is written to the old system. This ensures the new database remains the most consistent source of truth. If the SQLite write succeeds but the JSON write fails, we log an error but consider the operation successful from the user's perspective.

*Example Dual-Write Logic:*
```python
import logging

def save_user_profile(user_data):
    # Phase 2: Dual-Write Enabled
    # ===============================

    # 1. Attempt to write to the new system (SQLite) first.
    try:
        conn = get_sqlite_connection() # Connection must have PRAGMA journal_mode=WAL;
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (user_id, email, ...) VALUES (?, ?, ...)
            ON CONFLICT(user_id) DO UPDATE SET email=excluded.email, ...;
            """,
            (user_data['id'], user_data['email'], ...)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"FATAL: Failed to write to SQLite for user {user_data['id']}: {e}")
        # Abort the entire operation; the new system is the source of truth.
        raise  # Re-raise the exception to signal a failure to the caller.

    # 2. If the new system write was successful, write to the legacy system.
    try:
        file_path = f"./data/users/{user_data['id']}.json"
        with open(file_path, 'w') as f:
            json.dump(user_data, f)
    except Exception as e:
        # This is a non-fatal error for the user.
        # The primary datastore (SQLite) is consistent.
        # Log this for later reconciliation.
        logging.warning(
            f"NON-FATAL: SQLite write succeeded, but legacy JSON write failed for user {user_data['id']}: {e}"
        )

    return {"status": "success"}

```
**Error Handling is Key:** A failure to write to the legacy JSON file should trigger a high-priority alert. This indicates a "data drift" that needs to be manually reconciled by re-writing the JSON file from the SQLite record.

---

#### **Phase 3: Shadow-Reading and Verification**

During this phase, application reads **continue to come exclusively from the legacy JSON files.** However, in the background, the application also performs a "shadow read" from SQLite. The results are compared, and any discrepancies are logged for analysis. This validates the integrity of the data and the write logic in the new system without impacting users.

*Example Shadow-Read Logic:*
```python
def get_user_profile(user_id):
    # Phase 3: Read from Legacy, Shadow-Read/Verify from New
    # ========================================================

    # 1. Read from the legacy system. This is the data returned to the application.
    try:
        with open(f"./data/users/{user_id}.json", 'r') as f:
            legacy_data = json.load(f)
    except FileNotFoundError:
        # Handle not found case
        return None

    # 2. Perform a "shadow read" from the new system for verification.
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT raw_json_data FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            new_data = json.loads(row[0])
            # 3. Compare and log discrepancies.
            if not compare_dicts(legacy_data, new_data):
                logging.error(
                    f"[MIGRATION_VALIDATION_ERROR] Mismatch for user_id '{user_id}'. "
                    f"Legacy: {legacy_data}, SQLite: {new_data}"
                )
        else:
            logging.error(f"[MIGRATION_VALIDATION_ERROR] User '{user_id}' found in JSON but NOT in SQLite.")

    except Exception as e:
        logging.error(f"Shadow read from SQLite failed for user {user_id}: {e}")


    # 4. ALWAYS return data from the legacy system.
    return legacy_data
```
The goal is to run in this mode until the rate of `MIGRATION_VALIDATION_ERROR` messages drops to zero. This proves the new system is stable and accurate.

---

#### **Phase 4: The Cutover**

Once monitoring shows no discrepancies between the two systems for a sufficient period, the final cutover is executed. This is a low-risk change.

1.  **Flip the Read Path:** The read logic is changed to source data **only from SQLite**. The shadow-read code is removed.

    *Example of Final Read Logic:*
    ```python
    def get_user_profile_final(user_id):
        # Phase 4: Read ONLY from the new system
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT raw_json_data FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
    ```

2.  **Control with a Feature Flag:** This change should be controlled by a configuration setting or feature flag for instant rollback if any unexpected issues arise.

    *Example `config.ini`:*
    ```ini
    [data_storage]
    # Set to 'sqlite' to complete the migration. Default is 'json'.
    read_source = sqlite
    ```

---

#### **Phase 5: Cleanup**

After the new system has been running stable for a defined period (e.g., one week), the cleanup can begin.

1.  **Remove Dual-Write Code:** The code paths that write to the legacy JSON files are removed. The `save_user_profile` function is simplified to only write to SQLite.
2.  **Decommission Old Files:** The legacy JSON files can now be safely backed up to cold storage and deleted from the production filesystem.
3.  **Remove Feature Flag:** The configuration flag for switching read sources can be removed.

## Known Bugs, Rejected Paths, and Deferred Features

This section captures historical decisions, known issues, and the rationale behind the product's current state. It serves as a "lessons learned" document for current and future team members.

### Rejected Paths & Lessons Learned

This documents features and architectural approaches that were considered and explicitly rejected. Understanding the "why" behind these decisions is crucial for future architectural discussions.

*   **Rejected Feature: `RENDER_LITE_D1` Runtime Switch**
    *   **Description:** A proposal was made to create a runtime flag (`--render-mode=lite`) that would enable a fallback, CPU-only rendering pipeline. The goal was to support environments where dedicated GPUs were unavailable or drivers were misconfigured.
    *   **Reason for Rejection:** The feature was rejected to enforce a standard hardware requirement and avoid significant testing and maintenance overhead. The primary stakeholder's guiding principle was quoted as: **"Let's not build for every eventuality. We'd rather enforce a hardware baseline than introduce complexity to support edge cases we can't reliably test."**
    *   **Lesson Learned:** Supporting a wide array of hardware configurations, especially low-spec ones, adds a disproportionate amount of complexity to the codebase and QA process. Enforcing clear, specific minimum hardware requirements leads to a more stable, predictable, and maintainable product. It is better to have the application fail explicitly on unsupported hardware than to have it run poorly or with subtle, hard-to-diagnose bugs.

### Deferred Day 1 Features

To ensure a focused and stable initial launch, several major features were intentionally postponed. These items remain on the long-term roadmap but were not part of the initial MVP scope.

*   **Real-time Meeting Listening & Transcription:** This was the most significant feature deferred from the Day 1 plan. The original vision included functionality for the agent to join a meeting (e.g., via a Zoom or Google Meet link), listen to the audio stream in real-time, and generate live summaries. It was postponed due to the high technical complexity involved with:
    *   Managing real-time audio streams.
    *   Integrating with multiple third-party meeting platforms.
    *   The state management required for a live, continuous context.
*   **Advanced Data Source Connectors:** While the Day 1 release supported file uploads, native connectors for live data sources (e.g., Databases, Salesforce, Jira APIs) were deferred to a future release to simplify the initial data ingestion model.
*   **Multi-User Collaboration & Workspaces:** The initial system was built as a single-user experience. Features for team collaboration, including shared contexts, multi-tenancy, and role-based access controls, were explicitly scoped out for a future "Teams" version.

### Known Bugs & "Here Be Dragons"

This section lists known, non-blocking defects in the codebase. Developers working in these areas should be aware of these issues to avoid confusion or wasted time.

*   **Critical: Uncontrolled Cache Growth Due to Variable Typo**
    *   **File:** `backend/core/utils/last_render_cache.py`
    *   **Defect:** In the `purge_expired_cache` function, there is a critical typo in a variable name. The code attempts to access `config.CACHE_SETTINGS['cache_entry_tll']` (note the double 'l') when the correct key is `cache_entry_ttl`.
    *   **Impact:** This typo causes a `KeyError` which is silently caught by a broad exception handler. As a result, the logic to purge expired cache entries **never runs**. The `last_render_cache` will grow indefinitely for the lifetime of the process, eventually leading to high memory usage and potential OOM (Out Of Memory) errors on long-running backend instances.
    *   **Example Code Snippet:**
        ```python
        # File: backend/core/utils/last_render_cache.py

        def purge_expired_cache(cache: dict):
            # ...
            try:
                # BUG IS HERE: 'tll' instead of 'ttl'
                ttl = config.CACHE_SETTINGS['cache_entry_tll'] 
                if (now() - entry.timestamp) > ttl:
                    keys_to_delete.append(key)
            except Exception:
                # This exception handler hides the KeyError, making the bug silent.
                pass
            # ...
        ```
    *   **Solution:** Correct the typo from `cache_entry_tll` to `cache_entry_ttl`. As a temporary production workaround before the fix is deployed, a scheduled weekly restart of the backend service has been implemented to clear the process memory.