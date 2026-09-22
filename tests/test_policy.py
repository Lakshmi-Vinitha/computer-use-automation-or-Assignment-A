import pytest
from src.safety.policy import PolicyEnforcer, SafetyPolicy, ActionRiskLevel
from src.models.actions import Action, ActionType


def test_domain_allowlist():
    policy = SafetyPolicy(allowed_domains=["localhost", "app.bank.com"])
    enforcer = PolicyEnforcer(policy)

    allowed, msg = enforcer.validate_url("http://localhost:8000/members/12345")
    assert allowed is True

    allowed, msg = enforcer.validate_url("https://app.bank.com/dashboard")
    assert allowed is True

    allowed, msg = enforcer.validate_url("https://malicious-site.com/phish")
    assert allowed is False
    assert "not in allowed domains" in msg


def test_action_risk_classification():
    policy = SafetyPolicy()
    enforcer = PolicyEnforcer(policy)

    safe_action = Action(
        action_type=ActionType.CLICK,
        description="Click search submit button"
    )
    res = enforcer.validate_action(safe_action)
    assert res.is_allowed is True
    assert res.risk_level == ActionRiskLevel.SAFE

    risky_action = Action(
        action_type=ActionType.CLICK,
        description="Transfer money to external account"
    )
    res = enforcer.validate_action(risky_action)
    assert res.is_allowed is False
    assert res.risk_level == ActionRiskLevel.IRREVERSIBLE
