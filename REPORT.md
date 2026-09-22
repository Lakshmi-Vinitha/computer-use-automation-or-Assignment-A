# Computer-Use Automation System: Architectural Design & Implementation Report

## Architecture

The system architecture is organized around a fundamental operational principle: **The model discovers; the artifact codifies a reusable capability; deterministic replay executes in production.**

```
+-----------------------------------------------------------------------------------+
|                                  DISCOVERY PHASE                                  |
|  Goal + Target URL -> LLM Discovery Agent -> Observe-Decide-Validate-Act Loop    |
|                        -> Emits Capability Artifact JSON                          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                  PRODUCTION REPLAY                                |
|  Input Params + Capability Artifact -> Deterministic Replay Engine (Zero-LLM)     |
|                        -> Priority Locator Fallback Cascade                        |
|                        -> Checkpoint Assertion & Outcome Classifier                |
+-----------------------------------------------------------------------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
             [ SUCCESS / BUSINESS OUTCOME ]        [ ESCALATED / HANDOFF ]
            (Structured Result Contract)         (Live Session Handoff)
```

### Architectural Subsystems
1. **Mock Legacy Banking Surface (`mock_app/`)**: A FastAPI web application simulating a legacy back-office member-servicing terminal ("CoreBank Terminal v4.2"). It deliberately omits modern automation attributes (`data-testid`), relying instead on legacy fieldsets, HTML tables, and standard form controls. It incorporates realistic runtime states: `valid member`, `member not found`, `validation error`, `simulated slow load`, `permission denied`, and `unexpected dialog`.
2. **Surface Adapter Abstraction (`src/surfaces/`)**: Decouples perception and action from underlying window/DOM technologies. `SurfaceAdapter` defines generic operations (`observe`, `click`, `type`, `navigate`, `extract`, `screenshot`). `PlaywrightSurfaceAdapter` provides browser automation via Playwright Chromium.
3. **LLM Discovery Agent (`src/agent/`)**: An autonomous agent operating an observe → decide → validate → act loop. It converts natural language goals into structured JSON actions rather than arbitrary code scripts. Actions are passed through safety policy enforcement before execution.
4. **Capability Artifact System (`src/artifacts/`)**: Typed, versioned, Pydantic-validated JSON artifacts capturing recorded execution flows. It parameterizes runtime variables (e.g. `12345` → `{{member_id}}`) to create reusable capabilities.
5. **Deterministic Replay Engine (`src/replay/`)**: A zero-LLM execution engine that replays saved flows. It substitutes parameter placeholders, evaluates locator fallback chains, asserts checkpoints, and returns structured result contracts.
6. **Safety & Policy Guardrails (`src/safety/`)**: Enforces domain allowlists, classifies action risk (`SAFE`, `REVERSIBLE`, `RISKY`, `IRREVERSIBLE`), and scrubs sensitive PII/secrets.
7. **Human-in-the-Loop Handoff (`src/escalation/`)**: Manages live session control transfer (`RUNNING` → `PAUSED_FOR_HUMAN` → `HUMAN_CONTROL` → `AUTOMATION_CONTROL` → `RUNNING`), keeping the browser session alive while capturing intervention evidence.
8. **Observability & Evidence (`src/observability/`)**: Emits structured JSONL logs, step screenshots, and organized evidence artifacts in `evidence/`.

### Key Architectural Trade-offs & Decisions
- **Model-Free Production Replay**: We intentionally decouple discovery from replay. Replaying flows via LLMs introduces cost, non-determinism, latency, and unpredictable failures. Replaying via structured artifacts eliminates model dependency during routine production execution.
- **Structured Action Taxonomy vs. Freeform Code Generation**: Emitting structured JSON actions (`click`, `type`, `navigate`, `extract`) rather than generating Python code files ensures that safety policies can validate every action declaratively before execution.
- **Single Process / In-Memory Seams vs. Heavy Infrastructure**: We deliberately avoided introducing Kubernetes, Celery, Redis, Kafka, or external databases. In-memory seams and local filesystem evidence provide total functional completeness and rapid iteration without premature infrastructure overhead.

---

## Artifact Schema

The Capability Artifact schema (`src/artifacts/schema.py`) defines the contract between the discovery agent and production execution. It treats automation as a typed, callable capability.

```json
{
  "artifact_id": "member_balance_lookup",
  "name": "Member Savings Balance Lookup & Servicing",
  "version": "1.0.0",
  "description": "Look up member 12345 and read savings account balance",
  "target_app": "http://localhost:8000",
  "input_schema": {
    "type": "object",
    "properties": {
      "member_id": { "type": "string", "default": "12345" }
    },
    "required": ["member_id"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "savings_balance": { "type": "string" },
      "status": { "type": "string" }
    }
  },
  "steps": [
    {
      "step_id": "step_1",
      "action": {
        "action_type": "type",
        "locator": {
          "role_name": null,
          "label": "MEMBER ID NUM:",
          "css": "#member_id_input"
        },
        "value": "{{member_id}}",
        "description": "Type member ID"
      },
      "input_reference": "{{member_id}}",
      "timeout_ms": 5000,
      "retry_policy": { "max_retries": 2, "backoff_ms": 1000 }
    }
  ],
  "checkpoint": {
    "condition_type": "text_present",
    "value": "SAVINGS ACCOUNT"
  },
  "safety_policy": { ... }
}
```

### Schema Design Principles
1. **Parameterization (`{{member_id}}`)**: Runtime values used during discovery are extracted into parameterized placeholders (`{{param_name}}`). During replay, `parameterize_step()` resolves placeholders against caller-supplied inputs.
2. **Multi-Strategy Locators**: Locators store redundant strategies (`role_name`, `label`, `text`, `css`, `xpath`). Replay does not rely on a single selector; if a CSS class changes, the locator falls back to label or accessibility role.
3. **Explicit Checkpoints**: Checkpoints assert business state post-execution (e.g. `text_present: "SAVINGS ACCOUNT"`), preventing false positives where clicks succeed but the page fails to update.

---

## Determinism & Error Handling

### Deterministic Replay Strategy
Replay achieves 100% determinism by eliminating LLM inference. Given an artifact and input parameters, the engine executes steps sequentially using a deterministic locator priority cascade:

$$\text{Role/Name} \longrightarrow \text{Label} \longrightarrow \text{Text} \longrightarrow \text{CSS Selector} \longrightarrow \text{XPath}$$

`PlaywrightSurfaceAdapter._resolve_working_locator()` evaluates candidates against the active DOM in priority order, selecting the first matching strategy.

### Error Taxonomy & Status Contracts
A critical design choice is the clean separation between **expected business outcomes** and **runtime failures**.

| Result Status | Condition | Example Scenario |
| :--- | :--- | :--- |
| `SUCCESS` | All steps executed & checkpoint asserted | Member found, balance `$12,450.00` extracted |
| `BUSINESS_OUTCOME` | Valid domain state, target record missing or restricted | `MEMBER_NOT_FOUND` (ID `99999`) or `PERMISSION_DENIED` (ID `77777`) |
| `RECOVERABLE_ERROR` | Transient failure resolved via bounded retry | Slow load / temporary spinner resolved within 2 retries |
| `HARD_FAILURE` | Unrecoverable locator failure or checkpoint break | Selector missing, broken DOM, network crash |
| `ESCALATED` | Policy block or risky step requiring operator | Sub-account creation review requiring human sign-off |

When a search for non-existent member `99999` is replayed, the system returns `BUSINESS_OUTCOME` with code `MEMBER_NOT_FOUND`. It does not treat a missing record as an automation crash.

---

## Heterogeneity & Multi-Tenant

### Extension to Heterogeneous Computer Surfaces
The `SurfaceAdapter` base class decouples perception and action from browser DOMs. To support non-web surfaces:
- **Legacy Web App (No Clean DOM)**: `PlaywrightSurfaceAdapter` extracts visual text and accessibility trees rather than relying on element IDs.
- **Accessibility-Tree Automation**: A `DesktopAccessibilityAdapter` can implement `SurfaceAdapter` using OS Accessibility APIs (e.g. Windows UI Automation or macOS Accessibility API), querying element roles and names directly.
- **Screenshot / Coordinate Automation**: A `VisionCoordinateAdapter` can implement `SurfaceAdapter` using screenshot capture + OCR / visual object detection to return coordinates for `click(x, y)` and `type(text)`.

### Multi-Tenant Reuse & Layered Overrides
In enterprise financial software, hundreds of institutions run the same core vendor product (e.g., Jack Henry, FIS, CoreBank) with tenant-specific branding, custom routes, or localized form fields.

```
                    +------------------------------------+
                    |     Base Vendor Capability         |
                    | (CoreBank Member Lookup Flow v1.0) |
                    +-----------------+------------------+
                                      |
                                      v
                    +------------------------------------+
                    |    Tenant / Version Overrides      |
                    | - Route Prefix: /tenant-a/search   |
                    | - Selector: #custom_member_field   |
                    +-----------------+------------------+
                                      |
                                      v
                    +------------------------------------+
                    |  Resolved Multi-Tenant Execution   |
                    +------------------------------------+
```

- **Base Capability Artifact**: Captures the standard workflow steps, logic, input/output schemas, and baseline locators.
- **Tenant Override Layer**: Contains key-value overlays for tenant-specific routes (`target_app`), custom locator overrides, or extra verification rules.
- **Runtime Resolution**: At execution, the replay engine merges `Base Artifact + Tenant Overrides`, allowing a single discovery run on the vendor application to serve hundreds of tenant institutions without re-recording.

---

## Escalation & Handoff

When automation encounters a risky step (e.g., sub-account creation confirmation) or becomes stuck, it initiates a human-in-the-loop escalation.

### Live Session Handoff State Machine

$$\text{RUNNING} \longrightarrow \text{PAUSED\_FOR\_HUMAN} \longrightarrow \text{HUMAN\_CONTROL} \longrightarrow \text{AUTOMATION\_CONTROL} \longrightarrow \text{RUNNING}$$

1. **Detection & Pause**: `HandoffManager` pauses execution, captures an intervention request containing run ID, goal, step name, escalation reason, current URL, state summary, and viewport screenshot.
2. **Context Routing**: The request is persisted to `evidence/handoff/<run_id>/` and logged for operator inspection.
3. **Session Preservation**: The Playwright browser context remains open and active. Control transitions to `HUMAN_CONTROL`.
4. **Human Interaction & Resume**: A human operator inspects the live browser session, performs required manual actions or sign-offs, and issues a resume signal. Control transitions to `AUTOMATION_CONTROL` and then `RUNNING`, recording operator notes into the run evidence log.

---

## Safety

### Policy Model & Risk Classification
The `PolicyEnforcer` evaluates actions against a configurable `SafetyPolicy`:
- **Domain & Route Allowlists**: Prevents the agent from navigating outside permitted hostnames (`localhost`, `127.0.0.1`).
- **Action Risk Classification**:
  - `SAFE`: Navigation, text extraction, visual observation.
  - `REVERSIBLE`: Form field typing, search queries.
  - `RISKY / IRREVERSIBLE`: Sub-account creation, money transfers, account deletions. Irreversible actions automatically trigger human escalation.

### Financial Data & PII Redaction
To comply with financial data privacy standards:
- Secrets (API keys, passwords) are restricted to environment variables (`.env`) and excluded via `.gitignore`.
- Structured loggers and evidence collectors pass all text and data through `redact_sensitive_data()`.
- Patterns for Social Security Numbers (`***-**-****`), API keys (`sk-[REDACTED]`), passwords, and authentication tokens are automatically scrubbed from JSONL logs, summary files, and capability artifacts.

---

## Cuts

### What Was Deliberately Omitted
1. **Heavy Infrastructure Plumbing**: Omitted Redis queues, Celery workers, Kafka streams, and Kubernetes deployments in favor of clean in-memory seams and local filesystem evidence.
2. **Real-Time Co-Browsing UI Dashboard**: Replaced a full web-socket co-browsing interface with a CLI/event-driven handoff control model. The live browser session is preserved directly via Playwright's active browser context.
3. **Open-Ended Unbounded LLM Fallbacks**: Avoided open-ended LLM retry loops during deterministic replay to guarantee predictable execution behavior.

### What Would Be Built Next
1. **Visual Drift Detection & Auto-Healing**: Introduce a single-step LLM auto-healing fallback on locator breakage during replay, updating the artifact with newly discovered locators if approved.
2. **Desktop & Accessibility Surface Adapters**: Implement `DesktopAccessibilityAdapter` using Windows UI Automation to demonstrate cross-platform execution on native legacy desktop apps.
3. **Capability Catalog & Tool API**: Expose saved capability artifacts as an OpenAPI service catalog, allowing external AI agents to invoke stored capabilities dynamically as structured functions.
