"""
Safety guardrails and policy enforcement for Computer-Use actions.
"""

from enum import Enum
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from src.models.actions import Action, ActionType


class ActionRiskLevel(str, Enum):
    SAFE = "SAFE"
    REVERSIBLE = "REVERSIBLE"
    RISKY = "RISKY"
    IRREVERSIBLE = "IRREVERSIBLE"


class SafetyPolicy(BaseModel):
    allowed_domains: List[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1"],
        description="List of hostnames/domains the agent is permitted to visit."
    )
    allowed_routes: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Path patterns permitted (e.g. ['/members/*', '/search'])"
    )
    blocked_action_types: List[ActionType] = Field(
        default_factory=list,
        description="Action types strictly prohibited"
    )
    max_steps_per_run: int = Field(default=15, description="Maximum discovery steps before stopping")
    risk_classification: Dict[str, ActionRiskLevel] = Field(
        default_factory=lambda: {
            "navigate": ActionRiskLevel.SAFE,
            "click": ActionRiskLevel.SAFE,
            "type": ActionRiskLevel.SAFE,
            "extract": ActionRiskLevel.SAFE,
            "wait": ActionRiskLevel.SAFE,
            "finish": ActionRiskLevel.SAFE,
            "escalate": ActionRiskLevel.SAFE,
            "submit_transaction": ActionRiskLevel.IRREVERSIBLE,
            "delete_account": ActionRiskLevel.IRREVERSIBLE,
        }
    )


class PolicyCheckResult(BaseModel):
    is_allowed: bool
    risk_level: ActionRiskLevel
    reason: str


class PolicyEnforcer:
    def __init__(self, policy: Optional[SafetyPolicy] = None):
        self.policy = policy or SafetyPolicy()

    def validate_url(self, url: str) -> Tuple[bool, str]:
        """Validate if a URL domain is within the allowed list."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            if not hostname:
                return False, f"Invalid URL structure: {url}"
            
            domain_allowed = any(
                allowed == "*" or hostname == allowed or hostname.endswith("." + allowed)
                for allowed in self.policy.allowed_domains
            )
            if not domain_allowed:
                return False, f"Domain '{hostname}' is not in allowed domains: {self.policy.allowed_domains}"
            
            return True, "URL allowed"
        except Exception as e:
            return False, f"URL parse error: {str(e)}"

    def validate_action(self, action: Action, current_url: Optional[str] = None) -> PolicyCheckResult:
        """Validate an action against current safety policy."""
        # 1. Action type check
        if action.action_type in self.policy.blocked_action_types:
            return PolicyCheckResult(
                is_allowed=False,
                risk_level=ActionRiskLevel.IRREVERSIBLE,
                reason=f"Action type '{action.action_type.value}' is blocked by policy."
            )

        # 2. Navigation target check
        if action.action_type == ActionType.NAVIGATE and action.value:
            allowed, msg = self.validate_url(action.value)
            if not allowed:
                return PolicyCheckResult(
                    is_allowed=False,
                    risk_level=ActionRiskLevel.RISKY,
                    reason=f"Navigation blocked: {msg}"
                )

        # 3. Risk level assessment
        action_name = action.description.lower()
        if "delete" in action_name or "transfer money" in action_name or "execute transaction" in action_name:
            risk = ActionRiskLevel.IRREVERSIBLE
            return PolicyCheckResult(
                is_allowed=False,
                risk_level=risk,
                reason="Action classified as IRREVERSIBLE. Requires human escalation."
            )

        risk = self.policy.risk_classification.get(action.action_type.value, ActionRiskLevel.SAFE)
        return PolicyCheckResult(
            is_allowed=True,
            risk_level=risk,
            reason="Action permitted by policy"
        )
