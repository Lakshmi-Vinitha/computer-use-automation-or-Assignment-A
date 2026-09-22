"""
Error taxonomy and replay execution result status specifications.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ErrorCategory(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    UNEXPECTED_DIALOG = "UNEXPECTED_DIALOG"
    SESSION_TIMEOUT = "SESSION_TIMEOUT"
    TRANSIENT_LOAD_ERROR = "TRANSIENT_LOAD_ERROR"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    CHECKPOINT_FAILURE = "CHECKPOINT_FAILURE"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ReplayStatus(str, Enum):
    SUCCESS = "SUCCESS"
    BUSINESS_OUTCOME = "BUSINESS_OUTCOME"
    RECOVERABLE_ERROR = "RECOVERABLE_ERROR"
    HARD_FAILURE = "HARD_FAILURE"
    ESCALATED = "ESCALATED"


class ErrorDetail(BaseModel):
    step_id: Optional[str] = None
    step_index: Optional[int] = None
    expected_state: str
    observed_state: str
    error_category: ErrorCategory
    message: str
    screenshot_path: Optional[str] = None


class ReplayResult(BaseModel):
    status: ReplayStatus
    capability_id: str
    business_code: Optional[str] = Field(default=None, description="e.g. MEMBER_NOT_FOUND")
    outputs: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[ErrorDetail] = None
    execution_time_seconds: float = 0.0
    evidence_dir: Optional[str] = None
