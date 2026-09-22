import pytest
from src.models.taxonomy import ReplayResult, ReplayStatus, ErrorCategory, ErrorDetail


def test_business_outcome_contract():
    result = ReplayResult(
        status=ReplayStatus.BUSINESS_OUTCOME,
        capability_id="member_balance_lookup",
        business_code="MEMBER_NOT_FOUND",
        outputs={"message": "Member record not found"}
    )
    assert result.status == ReplayStatus.BUSINESS_OUTCOME
    assert result.business_code == "MEMBER_NOT_FOUND"
    assert result.error is None


def test_hard_failure_contract():
    err = ErrorDetail(
        step_id="step_2",
        step_index=2,
        expected_state="Submit button visible",
        observed_state="Element missing",
        error_category=ErrorCategory.ELEMENT_NOT_FOUND,
        message="Submit button was not found"
    )
    result = ReplayResult(
        status=ReplayStatus.HARD_FAILURE,
        capability_id="member_balance_lookup",
        error=err
    )
    assert result.status == ReplayStatus.HARD_FAILURE
    assert result.error.error_category == ErrorCategory.ELEMENT_NOT_FOUND
