"""
Human-in-the-loop escalation and live session handoff manager.
Manages state transitions: RUNNING -> PAUSED_FOR_HUMAN -> HUMAN_CONTROL -> AUTOMATION_CONTROL -> RUNNING.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from src.models.actions import Observation
from src.observability.evidence import EvidenceCollector
from src.observability.logger import setup_logger

logger = setup_logger(__name__)


class HandoffState(str, Enum):
    RUNNING = "RUNNING"
    PAUSED_FOR_HUMAN = "PAUSED_FOR_HUMAN"
    HUMAN_CONTROL = "HUMAN_CONTROL"
    AUTOMATION_CONTROL = "AUTOMATION_CONTROL"


class InterventionRequest(BaseModel):
    run_id: str
    goal_or_capability: str
    current_step: str
    reason: str
    screenshot_path: str
    current_url: str
    current_state_summary: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HandoffManager:
    def __init__(self, run_id: str, goal_or_capability: str, evidence_collector: EvidenceCollector):
        self.run_id = run_id
        self.goal_or_capability = goal_or_capability
        self.evidence_collector = evidence_collector
        self.state = HandoffState.RUNNING
        self.current_request: Optional[InterventionRequest] = None

    async def trigger_escalation(
        self,
        current_step: str,
        reason: str,
        observation: Observation,
        screenshot_bytes: Optional[bytes] = None
    ) -> InterventionRequest:
        """Pause automation and emit an intervention request."""
        self.state = HandoffState.PAUSED_FOR_HUMAN
        logger.warning(f"ESCALATION TRIGGERED [{self.run_id}]: {reason} at step '{current_step}'")

        screenshot_path = ""
        if screenshot_bytes:
            screenshot_path = self.evidence_collector.save_screenshot(f"handoff_{current_step}", screenshot_bytes)

        request = InterventionRequest(
            run_id=self.run_id,
            goal_or_capability=self.goal_or_capability,
            current_step=current_step,
            reason=reason,
            screenshot_path=screenshot_path,
            current_url=observation.url,
            current_state_summary=observation.visible_text_summary
        )

        self.current_request = request
        self.evidence_collector.log_step("HUMAN_ESCALATION_REQUEST", request.model_dump())
        return request

    def transfer_to_human(self) -> None:
        """Transfer session control to human operator."""
        self.state = HandoffState.HUMAN_CONTROL
        logger.info(f"Session [{self.run_id}] state: HUMAN_CONTROL. Live browser active.")
        self.evidence_collector.log_step("STATE_TRANSITION", {"state": self.state.value})

    def resume_automation(self, operator_notes: str = "Human operator resolved intervention") -> None:
        """Hand session control back to automation."""
        self.state = HandoffState.AUTOMATION_CONTROL
        logger.info(f"Session [{self.run_id}] state: AUTOMATION_CONTROL. Resuming.")
        self.evidence_collector.log_step("HUMAN_INTERVENTION_RESUMED", {
            "operator_notes": operator_notes,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.state = HandoffState.RUNNING
