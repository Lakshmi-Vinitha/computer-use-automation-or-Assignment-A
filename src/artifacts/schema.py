"""
Capability Artifact Pydantic schema and parameter substitution utilities.
Represents a recorded, typed, reusable computer-use flow.
"""

import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.models.actions import Action, Locator
from src.safety.policy import SafetyPolicy


class RetryPolicy(BaseModel):
    max_retries: int = 2
    backoff_ms: int = 1000
    recoverable_categories: List[str] = Field(
        default_factory=lambda: ["TRANSIENT_LOAD_ERROR", "UNEXPECTED_DIALOG"]
    )


class CheckpointCondition(BaseModel):
    condition_type: str = Field(..., description="url_contains, text_present, element_visible, status_code")
    value: str = Field(..., description="Target string or locator value to assert")
    extract_key: Optional[str] = Field(default=None, description="Optional key to map extracted data into outputs")


class StepDefinition(BaseModel):
    step_id: str
    action: Action
    target: Optional[Locator] = None
    input_reference: Optional[str] = Field(default=None, description="Parameter placeholder e.g. {{member_id}}")
    expected_state: str = Field(default="", description="Description of expected state post-step")
    timeout_ms: int = 5000
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    output_key: Optional[str] = Field(default=None, description="Key to store extracted output under")


class CapabilityArtifact(BaseModel):
    artifact_id: str
    name: str
    version: str = "1.0.0"
    description: str
    target_app: str
    input_schema: Dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "member_id": {"type": "string", "description": "5-digit member account ID", "default": "12345"}
            },
            "required": ["member_id"]
        }
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "savings_balance": {"type": "string", "description": "Extracted savings balance"},
                "status": {"type": "string", "description": "Execution outcome status"}
            }
        }
    )
    steps: List[StepDefinition]
    checkpoint: CheckpointCondition
    safety_policy: SafetyPolicy = Field(default_factory=SafetyPolicy)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "CapabilityArtifact":
        return cls.model_validate_json(json_str)

    @classmethod
    def from_file(cls, filepath: str) -> "CapabilityArtifact":
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    def save_to_file(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())


def resolve_placeholders(text: str, parameters: Dict[str, Any]) -> str:
    """Replace {{param_name}} placeholders with values from parameters dictionary."""
    if not isinstance(text, str):
        return text

    def replace_match(match):
        key = match.group(1).strip()
        if key in parameters:
            return str(parameters[key])
        return match.group(0)

    return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", replace_match, text)


def parameterize_step(step: StepDefinition, parameters: Dict[str, Any]) -> StepDefinition:
    """Return a copy of step with parameter placeholders substituted for execution."""
    step_copy = step.model_copy(deep=True)
    if step_copy.input_reference:
        resolved = resolve_placeholders(step_copy.input_reference, parameters)
        step_copy.input_reference = resolved
        step_copy.action.value = resolved
    elif step_copy.action.value:
        step_copy.action.value = resolve_placeholders(step_copy.action.value, parameters)
        
    return step_copy
