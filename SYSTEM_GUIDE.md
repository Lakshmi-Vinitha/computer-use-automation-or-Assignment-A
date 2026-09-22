# Computer-Use Automation System: Comprehensive Architecture, Operations & Enterprise Application Guide

---

## Executive Summary

The **Computer-Use Automation System** is an enterprise-grade AI automation architecture built to bridge modern digital workflows with legacy back-office software (core banking terminals, mainframe portals, legacy ERPs/CRMs). 

In traditional enterprise environments, over 70% of back-office workflows rely on legacy software where **no REST/GraphQL APIs exist** and element structures lack modern automation attributes (`data-testid`). Building custom API layers or replacing these legacy mainframes costs millions of dollars and takes years.

This system solves this challenge via a **Dual-Phase Computer-Use Architecture**:
1. **Discovery Phase (LLM-Driven)**: An AI agent perceives the legacy application surface, reasons over accessibility trees and visual text, executes natural language goals, and codifies successful workflows into typed, parameterizable **Capability Artifacts** (`artifacts/member_balance.json`).
2. **Production Phase (Zero-LLM Replay)**: In production, saved capability artifacts are replayed **deterministically without LLM calls**. Replay achieves sub-second execution speeds, zero API token costs, 100% predictable execution, multi-strategy selector fallbacks, explicit business outcome classification, and human-in-the-loop session handoffs.

---

## 1. System Architecture

```
                                  +---------------------------------------+
                                  |     Goal + Target URL + Safety Policy |
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |         DISCOVERY AGENT (LLM)         |
                                  |     Observe -> Decide -> Validate -> Act|
                                  +-------------------+-------------------+
                                                      |
                                                      v Emits Artifact
                                  +---------------------------------------+
                                  |       CAPABILITY ARTIFACT (JSON)      |
                                  | Parameterized ({{member_id}}), Typed |
                                  +-------------------+-------------------+
                                                      |
                                                      v Replayed By
                                  +---------------------------------------+
                                  |      DETERMINISTIC REPLAY ENGINE      |
                                  | (Zero-LLM, Cascade Locator Fallbacks) |
                                  +-------------------+-------------------+
                                                      |
                   +----------------------------------+----------------------------------+
                   |                                  |                                  |
                   v                                  v                                  v
        +--------------------+              +--------------------+              +--------------------+
        |   SUCCESS RESULT   |              |  BUSINESS OUTCOME  |              |  ESCALATED HANDOFF |
        | Extracted Outputs  |              | MEMBER_NOT_FOUND   |              | Live Session       |
        | Checkpoint Passed  |              | PERMISSION_DENIED  |              | Operator Handoff   |
        +--------------------+              +--------------------+              +--------------------+
```

---

## 2. Component-by-Component Technical Explanation

### 2.1 Mock Legacy Banking Application (`mock_app/main.py`)
- **Purpose**: Simulates a legacy back-office banking terminal ("CoreBank Servicing Terminal v4.2").
- **Design Intent**: Built using FastAPI with retro styling, fieldsets, and standard HTML tables. It intentionally lacks `data-testid` attributes to emulate legacy enterprise software.
- **Supported Runtime States**:
  - `valid member` (e.g. ID `12345`): Displays member profile and active savings account balance (`$12,450.00`).
  - `member not found` (e.g. ID `99999`): Displays explicit status message `MEMBER_NOT_FOUND`.
  - `validation error` (e.g. blank/non-numeric): Displays `VALIDATION_ERROR`.
  - `simulated slow loading` (`?delay=2`): Delays HTTP response to test load handling.
  - `permission denied` (e.g. ID `77777`): Displays `PERMISSION_DENIED`.
  - `unexpected dialog` (`?dialog=true`): Renders a modal overlay requiring dismissal.
  - `sub-account creation form`: Multi-field form terminating in a Pre-Commitment Review screen without executing irreversible financial transactions.

### 2.2 Surface Adapter Abstraction (`src/surfaces/`)
- **Abstract Base Class (`SurfaceAdapter`)**: Defines generic operations (`observe`, `click`, `type`, `navigate`, `extract`, `screenshot`) to decouple agent perception and action from browser DOMs.
- **Playwright Implementation (`PlaywrightSurfaceAdapter`)**: Operates web browsers using Playwright Chromium. It extracts page titles, URLs, visible text summaries, form labels, element accessibility roles, and viewport screenshots.

### 2.3 Discovery Agent (`src/agent/discovery.py`)
- **Observe-Decide-Validate-Act Loop**: Receives natural language goals and current page observations, querying OpenAI (`gpt-4o-mini`) to decide the single next structured action (`type`, `click`, `extract`, `navigate`, `finish`, `escalate`).
- **Safety Pre-Validation**: Every proposed action is passed to the `PolicyEnforcer` before execution.
- **Offline Fallback Driver**: Includes a deterministic fallback driver for offline verification when `OPENAI_API_KEY` is not present.
- **Artifact Codification**: Replaces concrete inputs (e.g. `12345`) with parameterized placeholders (`{{member_id}}`) upon goal completion.

### 2.4 Capability Artifact Schema (`src/artifacts/schema.py`)
- **Pydantic Contract**: A versioned JSON representation of a recorded capability containing:
  - `artifact_id`: Unique identifier (e.g. `member_balance_lookup`).
  - `input_schema` & `output_schema`: JSON schema definitions of inputs and outputs.
  - `steps`: Ordered list of `StepDefinition` items with locator strategies, parameterized inputs (`{{member_id}}`), and retry policies.
  - `checkpoint`: Assertion condition (e.g. `text_present: "SAVINGS ACCOUNT"`).
  - `safety_policy`: Embedded allowlists and risk classifications.

### 2.5 Deterministic Replay Engine (`src/replay/engine.py`)
- **Zero-LLM Execution**: Replays capability artifacts using caller-supplied inputs (e.g. `member_id = "12345"`).
- **Locator Priority Cascade**: Evaluates element selectors in order:
  $$\text{Role/Name} \longrightarrow \text{Label} \longrightarrow \text{Text} \longrightarrow \text{CSS Selector} \longrightarrow \text{XPath}$$
- **Checkpoint Assertion**: Asserts state post-execution to prevent false positives.
- **Outcome Classification**: Returns a `ReplayResult` contract with statuses: `SUCCESS`, `BUSINESS_OUTCOME`, `RECOVERABLE_ERROR`, `HARD_FAILURE`, or `ESCALATED`.

### 2.6 Safety & Policy Guardrails (`src/safety/`)
- **Policy Enforcement**: Checks target URLs against domain allowlists (`localhost`, `127.0.0.1`) and classifies action risk (`SAFE`, `REVERSIBLE`, `RISKY`, `IRREVERSIBLE`).
- **Data Redaction**: Scrubs SSNs (`***-**-****`), API keys (`sk-[REDACTED]`), passwords, and session tokens from all logs, JSON summaries, and artifacts.

### 2.7 Human-in-the-Loop Handoff (`src/escalation/handoff.py`)
- **Live Session State Machine**:
  $$\text{RUNNING} \longrightarrow \text{PAUSED\_FOR\_HUMAN} \longrightarrow \text{HUMAN\_CONTROL} \longrightarrow \text{AUTOMATION\_CONTROL} \longrightarrow \text{RUNNING}$$
- Maintains active Playwright browser sessions while generating intervention requests in `evidence/handoff/`, allowing human operators to inspect screenshots, perform manual steps, and issue resume signals.

### 2.8 Observability & Evidence (`src/observability/`)
- Generates redacting JSONL event logs, step screenshots, and summary files under `evidence/` (`discovery/`, `replay-success/`, `replay-error/`, `handoff/`).

---

## 3. Real-World Applications & Industry Use Cases

### 3.1 Core Banking & Credit Union Servicing
- **Problem**: Core banking systems (Fiserv, Jack Henry, FIS) lack APIs for front-line teller workflows.
- **Solution**: Automates member lookups, balance verification, address changes, fee waivers, and sub-account setup across legacy web/terminal screens.

### 3.2 Automated Loan Underwriting & Verification
- **Problem**: Underwriters manually copy data between credit bureau portals, legacy core systems, and spreadsheet models.
- **Solution**: Discovers data extraction paths on credit portals, codifies them into Capability Artifacts, and replays them deterministically to inject data directly into loan origination pipelines.

### 3.3 Insurance Claims Processing & Verification
- **Problem**: Claims adjusters spend hours logging into legacy policy mainframes to check policy coverage limits.
- **Solution**: Replays recorded claims-lookup capabilities to extract policy terms, deductible amounts, and active coverage states in sub-seconds.

### 3.4 Healthcare EHR Integration & Prior Authorization
- **Problem**: Hospitals run legacy Electronic Health Record (EHR) systems without FHIR API support.
- **Solution**: Automates prior authorization submissions and patient record retrieval while redacting sensitive patient PII/HIPAA data automatically.

### 3.5 Multi-Tenant Vendor Software Distribution
- **Problem**: 500 regional banks run the same vendor software, but each bank has custom branding and localized URL routes.
- **Solution**: A single **Base Vendor Artifact** is recorded once. Each bank applies a light **Tenant Override Layer** (custom route prefix, localized selector tweaks), enabling cross-tenant reuse without per-tenant re-recording.

---

## 4. How to Run Locally (Step-by-Step Guide)

### Step 1: Clone & Setup Environment
```bash
cd "/Users/chandratejaa/Desktop/Assignment A"

# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies and Playwright browser
pip install -r requirements.txt
playwright install chromium
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optionally add your `OPENAI_API_KEY` to `.env` for live LLM discovery).*

### Step 3: Start the Local Banking Mock Server
In **Terminal 1**, launch the mock banking server on port 8000:
```bash
python -m src.cli serve-mock
```
*Server runs on [http://localhost:8000](http://localhost:8000).*

### Step 4: Run Automation Demos (In Terminal 2)

#### Demo 1: Run AI Discovery Agent
```bash
python -m src.cli discover --goal "Look up member 12345 and read savings account balance" --target http://localhost:8000
```
*Emits serialized Capability Artifact to `artifacts/member_balance.json`.*

#### Demo 2: Replay Success Case (Member 12345)
```bash
python -m src.cli replay --artifact artifacts/member_balance.json --input member_id=12345
```
**Result**: `REPLAY RESULT STATUS: SUCCESS`, `outputs: {"savings_balance": "$12,450.00"}`.

#### Demo 3: Replay Business Outcome - Not Found (Member 99999)
```bash
python -m src.cli replay --artifact artifacts/member_balance.json --input member_id=99999
```
**Result**: `REPLAY RESULT STATUS: BUSINESS_OUTCOME`, `code: MEMBER_NOT_FOUND`.

#### Demo 4: Replay Business Outcome - Permission Denied (Member 77777)
```bash
python -m src.cli replay --artifact artifacts/member_balance.json --input member_id=77777
```
**Result**: `REPLAY RESULT STATUS: BUSINESS_OUTCOME`, `code: PERMISSION_DENIED`.

#### Demo 5: Human-in-the-Loop Escalation Handoff
```bash
python -m src.cli handoff --target http://localhost:8000
```
**Result**: Demonstrates `PAUSED_FOR_HUMAN` → `HUMAN_CONTROL` → `RESUMED` state transitions.

### Step 5: Run Automated Tests
```bash
pytest
```
*Runs all 11 unit and integration tests (passing in ~4.8s).*

---

## 5. Security, Data Redaction & Compliance Summary

1. **Zero Credential Exposure**: API keys and passwords are environment-bound (`.env`) and excluded from git via `.gitignore`.
2. **Automated PII Sanitization**: Loggers and evidence writers sanitize SSNs (`***-**-****`), API keys (`sk-[REDACTED]`), and credentials automatically.
3. **Allowlist Enforcement**: Actions are restricted strictly to approved domains (`localhost`, `127.0.0.1`).
4. **Audit Trail**: Every execution generates structured JSONL logs, viewport screenshots, and summary JSONs in `evidence/`.
