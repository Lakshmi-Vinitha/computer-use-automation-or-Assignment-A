# Computer-Use Automation System

An end-to-end Computer-Use Automation System designed to automate legacy back-office financial software. The system uses an LLM-driven discovery agent to observe and interact with live application surfaces, records successful interactions as typed, parameterized **Capability Artifacts**, and replays them **deterministically without LLMs**, featuring robust error taxonomy, safety guardrails, and human-in-the-loop session handoff.

---

## Architecture Summary

```
                  +-------------------------------+
                  |  Goal + Target App URL + Policy|
                  +---------------+---------------+
                                  |
                                  v
                    +---------------------------+
                    |   Discovery Agent (LLM)   |
                    | Observe -> Decide -> Act  |
                    +-------------+-------------+
                                  |
                                  v  Emits
                    +---------------------------+
                    |    Capability Artifact    |
                    | JSON, Parameterized, Typed|
                    +-------------+-------------+
                                  |
                                  v Replayed By
                    +---------------------------+
                    | Deterministic Replay Engine|
                    | (Zero-LLM, Cascade Fallbacks)
                    +-------------+-------------+
                        /         |         \
                       v          v          v
                  SUCCESS     BUSINESS    HARD FAILURE /
                  (Output)    OUTCOME     ESCALATE (Handoff)
```

### Core Components
1. **Mock Legacy Banking Application (`mock_app/`)**: Built with FastAPI, simulating a legacy financial servicing terminal ("CoreBank Terminal v4.2"). Lacks test IDs and includes edge states (`valid_member`, `member_not_found`, `validation_error`, `slow_loading`, `permission_denied`, `unexpected_dialog`).
2. **Surface Adapter Layer (`src/surfaces/`)**: Abstract `SurfaceAdapter` base class with concrete `PlaywrightSurfaceAdapter` for browser interaction. Designed to support future accessibility/desktop adapters.
3. **Discovery Agent (`src/agent/`)**: LLM-driven observe → decide → validate → act agent loop. Supports OpenAI `gpt-4o-mini` with a deterministic fallback driver for offline verification.
4. **Capability Artifact Schema (`src/artifacts/`)**: Pydantic models for versioned, parameterizable (`{{member_id}}`) capability definitions with multi-strategy locator fallbacks (`role_name` → `label` → `text` → `css` → `xpath`).
5. **Deterministic Replay Engine (`src/replay/`)**: Executes recorded flows deterministically without calling LLMs. Resolves parameter placeholders, evaluates fallback locators, asserts checkpoints, and returns structured result contracts.
6. **Error Taxonomy & Handling (`src/models/taxonomy.py`)**: Distinguishes `SUCCESS`, `BUSINESS_OUTCOME` (e.g. `MEMBER_NOT_FOUND`, `PERMISSION_DENIED`), `RECOVERABLE_ERROR`, `HARD_FAILURE`, and `ESCALATED`.
7. **Safety Guardrails (`src/safety/`)**: Domain/route allowlists, action risk classifier (`SAFE`, `REVERSIBLE`, `RISKY`, `IRREVERSIBLE`), and automated PII/secret redaction.
8. **Human-in-the-Loop Handoff (`src/escalation/`)**: State machine (`RUNNING` → `PAUSED_FOR_HUMAN` → `HUMAN_CONTROL` → `AUTOMATION_CONTROL` → `RUNNING`) preserving live browser sessions when human intervention is required.
9. **Observability & Evidence (`src/observability/`)**: JSONL structured logs, step screenshots, and organized run outputs in `evidence/`.

---

## Prerequisites

- **Python**: 3.12+
- **Browser**: Chromium (managed via Playwright)
- **OpenAI API Key**: Optional for discovery (a deterministic fallback driver executes automatically if `OPENAI_API_KEY` is not provided).

---

## Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone <repo_url>
   cd computer-use-automation
   ```

2. **Create and Activate Virtual Environment**:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Environment Configuration**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Add your `OPENAI_API_KEY` to `.env` if performing live LLM discovery runs:
   ```env
   OPENAI_API_KEY=sk-proj-your-api-key-here
   TARGET_URL=http://localhost:8000
   ```

---

## How to Start the Mock Application

Start the local legacy banking mock app on port 8000:
```bash
python -m src.cli serve-mock
```
*App will be accessible at [http://localhost:8000](http://localhost:8000).*

---

## Execution & Demos

### 1. Discovery Run
Run the LLM-driven discovery agent to explore the app and emit a saved Capability Artifact:
```bash
python -m src.cli discover --goal "Look up member 12345 and read savings account balance" --target http://localhost:8000
```
*Output artifact saved to `artifacts/member_balance.json` and evidence stored in `evidence/discovery/`.*

### 2. Deterministic Replay (Success Case)
Replay the saved capability artifact deterministically with input parameters:
```bash
python -m src.cli replay --artifact artifacts/member_balance.json --input member_id=12345
```
*Expected Output: `REPLAY RESULT STATUS: SUCCESS`, `savings_balance: "$12,450.00"`.*

### 3. Error Case & Business Outcome Demos
Replay with a non-existent member ID (`99999`) to demonstrate business outcome detection:
```bash
python -m src.cli replay --artifact artifacts/member_balance.json --input member_id=99999
```
*Expected Output: `REPLAY RESULT STATUS: BUSINESS_OUTCOME`, `BUSINESS OUTCOME CODE: MEMBER_NOT_FOUND`.*

Replay with a restricted member ID (`77777`) to demonstrate permission denial:
```bash
python -m src.cli replay --artifact artifacts/member_balance.json --input member_id=77777
```
*Expected Output: `REPLAY RESULT STATUS: BUSINESS_OUTCOME`, `BUSINESS OUTCOME CODE: PERMISSION_DENIED`.*

### 4. Human-in-the-Loop Handoff Demo
Demonstrate live session escalation, state transitions, and operator control handoff:
```bash
python -m src.cli handoff --target http://localhost:8000
```
*Expected Output: Triggers `PAUSED_FOR_HUMAN` → `HUMAN_CONTROL` → `RESUMED` and saves evidence to `evidence/handoff/`.*

---

## Testing

Run the automated test suite with pytest:
```bash
pytest
```
*All 11 unit & integration tests verify artifact serialization, parameter substitution, policy allowlists, error taxonomy, redaction, and replay execution.*

---

## Project Structure

```
computer-use-automation/
├── README.md
├── REPORT.md
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .gitignore
├── mock_app/
│   ├── __init__.py
│   └── main.py                # Legacy banking mock FastAPI server
├── src/
│   ├── __init__.py
│   ├── cli.py                 # CLI commands (discover, replay, handoff, serve-mock)
│   ├── agent/
│   │   ├── __init__.py
│   │   └── discovery.py       # Observe-decide-validate-act discovery agent
│   ├── artifacts/
│   │   ├── __init__.py
│   │   └── schema.py          # Capability Artifact Pydantic model & templates
│   ├── replay/
│   │   ├── __init__.py
│   │   └── engine.py          # Zero-LLM deterministic replay engine
│   ├── surfaces/
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract SurfaceAdapter interface
│   │   └── playwright_adapter.py # Playwright browser implementation
│   ├── safety/
│   │   ├── __init__.py
│   │   ├── policy.py          # Allowlist & risk classification policy
│   │   └── redaction.py       # PII/Secret regex sanitizer
│   ├── escalation/
│   │   ├── __init__.py
│   │   └── handoff.py         # Human-in-the-loop live session handoff
│   ├── observability/
│   │   ├── __init__.py
│   │   ├── logger.py          # Redacting JSONL & console logger
│   │   └── evidence.py        # Evidence & screenshot collector
│   └── models/
│       ├── __init__.py
│       ├── actions.py         # Action & Locator models
│       └── taxonomy.py        # Error taxonomy & result contracts
├── artifacts/
│   └── member_balance.json    # Serialized reusable capability artifact
├── evidence/
│   ├── discovery/             # Logs & screenshots from discovery runs
│   ├── replay-success/        # Replay success evidence
│   ├── replay-error/          # Replay error & business outcome evidence
│   └── handoff/               # Human escalation evidence
└── tests/
    ├── __init__.py
    ├── test_artifacts.py      # Serialization & substitution tests
    ├── test_policy.py         # Policy allowlist & risk tests
    ├── test_redaction.py      # Data redaction tests
    ├── test_error_taxonomy.py # Status contract tests
    └── test_replay.py         # End-to-end integration tests
```

---

## Security Notes

- **Secrets Management**: API keys and tokens are loaded strictly from environment variables or `.env`. `.env` is included in `.gitignore`.
- **Data Redaction**: All structured logs, summary JSONs, and evidence files pass through `redact_sensitive_data()`, redacting SSNs (`***-**-****`), API keys (`sk-...`), passwords, and tokens.
- **Safety Policy**: Action policies strictly restrict navigation to allowed domains (`localhost`, `127.0.0.1`) and block irreversible financial transactions without operator sign-off.
