import pytest
from src.artifacts.schema import (
    CapabilityArtifact,
    StepDefinition,
    CheckpointCondition,
    resolve_placeholders,
    parameterize_step
)
from src.models.actions import Action, ActionType, Locator


def test_artifact_serialization():
    step = StepDefinition(
        step_id="step_1",
        action=Action(
            action_type=ActionType.TYPE,
            locator=Locator(label="MEMBER ID NUM:"),
            value="{{member_id}}",
            description="Type member ID"
        ),
        input_reference="{{member_id}}"
    )
    artifact = CapabilityArtifact(
        artifact_id="test_lookup",
        name="Test Lookup",
        description="Lookup member details",
        target_app="http://localhost:8000",
        steps=[step],
        checkpoint=CheckpointCondition(condition_type="text_present", value="SAVINGS ACCOUNT")
    )

    json_str = artifact.to_json()
    assert "test_lookup" in json_str
    assert "{{member_id}}" in json_str

    deserialized = CapabilityArtifact.from_json(json_str)
    assert deserialized.artifact_id == "test_lookup"
    assert deserialized.steps[0].action.value == "{{member_id}}"


def test_parameter_substitution():
    text = "Look up member {{member_id}} in {{domain}}"
    params = {"member_id": "12345", "domain": "corebank.local"}
    resolved = resolve_placeholders(text, params)
    assert resolved == "Look up member 12345 in corebank.local"


def test_parameterize_step():
    step = StepDefinition(
        step_id="step_1",
        action=Action(
            action_type=ActionType.TYPE,
            locator=Locator(css="#member_id_input"),
            value="{{member_id}}",
            description="Type member ID"
        ),
        input_reference="{{member_id}}"
    )
    param_step = parameterize_step(step, {"member_id": "99999"})
    assert param_step.action.value == "99999"
    assert param_step.input_reference == "99999"
