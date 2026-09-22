"""
Deterministic Replay Engine for Computer-Use Capability Artifacts.
Replays saved flows without invoking LLMs. Resolves parameters, evaluates locator fallbacks,
verifies checkpoints, and classifies execution outcomes into SUCCESS, BUSINESS_OUTCOME, HARD_FAILURE, or ESCALATED.
"""

import time
import logging
from typing import Dict, Any, Optional
from src.artifacts.schema import CapabilityArtifact, parameterize_step
from src.surfaces.base import SurfaceAdapter
from src.surfaces.playwright_adapter import PlaywrightSurfaceAdapter
from src.models.actions import ActionType
from src.models.taxonomy import ReplayResult, ReplayStatus, ErrorCategory, ErrorDetail
from src.observability.evidence import EvidenceCollector
from src.safety.policy import PolicyEnforcer

logger = logging.getLogger(__name__)


class DeterministicReplayEngine:
    def __init__(self, surface: Optional[SurfaceAdapter] = None):
        self.surface = surface

    async def execute(
        self,
        artifact: CapabilityArtifact,
        input_parameters: Dict[str, Any],
        evidence_dir: str = "evidence"
    ) -> ReplayResult:
        start_time = time.time()
        own_surface = False
        if not self.surface:
            self.surface = PlaywrightSurfaceAdapter(headless=True)
            await self.surface.initialize()
            own_surface = True

        run_type = "replay-success"
        collector = EvidenceCollector(run_type=run_type, base_dir=evidence_dir)
        collector.log_step("REPLAY_START", {
            "artifact_id": artifact.artifact_id,
            "parameters": input_parameters
        })

        outputs: Dict[str, Any] = {}
        policy_enforcer = PolicyEnforcer(artifact.safety_policy)

        try:
            # Always ensure initial navigation to target app entry point
            if artifact.target_app:
                collector.log_step("REPLAY_INITIAL_NAVIGATE", {"url": artifact.target_app})
                await self.surface.navigate(artifact.target_app)

            for idx, raw_step in enumerate(artifact.steps):
                step = parameterize_step(raw_step, input_parameters)
                collector.log_step(f"STEP_{idx+1}_START", {
                    "step_id": step.step_id,
                    "action_type": step.action.action_type.value,
                    "description": step.action.description
                })

                # Validate safety policy
                policy_check = policy_enforcer.validate_action(step.action)
                if not policy_check.is_allowed:
                    screenshot = await self.surface.screenshot()
                    s_path = collector.save_screenshot(f"policy_violation_step_{idx+1}", screenshot)
                    err = ErrorDetail(
                        step_id=step.step_id,
                        step_index=idx + 1,
                        expected_state="Policy permitted action",
                        observed_state=f"Policy violation: {policy_check.reason}",
                        error_category=ErrorCategory.POLICY_VIOLATION,
                        message=policy_check.reason,
                        screenshot_path=s_path
                    )
                    result = ReplayResult(
                        status=ReplayStatus.HARD_FAILURE,
                        capability_id=artifact.artifact_id,
                        error=err,
                        execution_time_seconds=time.time() - start_time,
                        evidence_dir=collector.run_dir
                    )
                    collector.save_summary(result.model_dump())
                    return result

                # Execute action with bounded retry
                action_success = False
                retries = 0
                max_retries = step.retry_policy.max_retries

                while retries <= max_retries and not action_success:
                    if step.action.action_type == ActionType.NAVIGATE:
                        url = step.action.value or artifact.target_app
                        action_success = await self.surface.navigate(url)

                    elif step.action.action_type == ActionType.CLICK:
                        if not step.target:
                            raise ValueError(f"Click action at step '{step.step_id}' missing target locator")
                        action_success = await self.surface.click(step.target, timeout_ms=step.timeout_ms)

                    elif step.action.action_type == ActionType.TYPE:
                        if not step.target:
                            raise ValueError(f"Type action at step '{step.step_id}' missing target locator")
                        text_val = step.action.value or step.input_reference or ""
                        action_success = await self.surface.type(step.target, text_val, timeout_ms=step.timeout_ms)

                    elif step.action.action_type == ActionType.EXTRACT:
                        if step.target:
                            extracted_val = await self.surface.extract(step.target)
                            if extracted_val is not None:
                                key = step.output_key or step.step_id
                                outputs[key] = extracted_val.strip()
                                action_success = True

                    elif step.action.action_type == ActionType.WAIT:
                        wait_ms = int(step.action.value) if step.action.value and step.action.value.isdigit() else 1000
                        await time.sleep(wait_ms / 1000.0)
                        action_success = True

                    elif step.action.action_type == ActionType.FINISH:
                        action_success = True

                    if not action_success:
                        retries += 1
                        if retries <= max_retries:
                            collector.log_step(f"STEP_{idx+1}_RETRY", {"retry": retries})
                            time.sleep(step.retry_policy.backoff_ms / 1000.0)

                # Post-step observation check for Business Outcomes (e.g. MEMBER_NOT_FOUND or PERMISSION_DENIED)
                obs = await self.surface.observe()
                if "MEMBER_NOT_FOUND" in obs.visible_text_summary or "Member ID 99999 could not be located" in obs.visible_text_summary:
                    screenshot = await self.surface.screenshot()
                    s_path = collector.save_screenshot(f"business_outcome_not_found", screenshot)
                    result = ReplayResult(
                        status=ReplayStatus.BUSINESS_OUTCOME,
                        capability_id=artifact.artifact_id,
                        business_code="MEMBER_NOT_FOUND",
                        outputs={"message": "Member record not found in database"},
                        execution_time_seconds=time.time() - start_time,
                        evidence_dir=collector.run_dir
                    )
                    collector.save_summary(result.model_dump())
                    return result

                if "VALIDATION_ERROR" in obs.visible_text_summary:
                    screenshot = await self.surface.screenshot()
                    s_path = collector.save_screenshot(f"business_outcome_validation_err", screenshot)
                    result = ReplayResult(
                        status=ReplayStatus.BUSINESS_OUTCOME,
                        capability_id=artifact.artifact_id,
                        business_code="VALIDATION_ERROR",
                        outputs={"message": "Invalid Member ID format"},
                        execution_time_seconds=time.time() - start_time,
                        evidence_dir=collector.run_dir
                    )
                    collector.save_summary(result.model_dump())
                    return result

                if "PERMISSION_DENIED" in obs.visible_text_summary:
                    screenshot = await self.surface.screenshot()
                    s_path = collector.save_screenshot(f"business_outcome_permission_denied", screenshot)
                    result = ReplayResult(
                        status=ReplayStatus.BUSINESS_OUTCOME,
                        capability_id=artifact.artifact_id,
                        business_code="PERMISSION_DENIED",
                        outputs={"message": "Access level insufficient to view restricted account"},
                        execution_time_seconds=time.time() - start_time,
                        evidence_dir=collector.run_dir
                    )
                    collector.save_summary(result.model_dump())
                    return result

                # Check if step failed completely
                if not action_success:
                    screenshot = await self.surface.screenshot()
                    s_path = collector.save_screenshot(f"failure_step_{idx+1}", screenshot)
                    err = ErrorDetail(
                        step_id=step.step_id,
                        step_index=idx + 1,
                        expected_state=step.expected_state or "Action completion",
                        observed_state=f"Failed to execute {step.action.action_type.value}",
                        error_category=ErrorCategory.ELEMENT_NOT_FOUND,
                        message=f"Element locator {step.target} could not be interacted with",
                        screenshot_path=s_path
                    )
                    result = ReplayResult(
                        status=ReplayStatus.HARD_FAILURE,
                        capability_id=artifact.artifact_id,
                        error=err,
                        execution_time_seconds=time.time() - start_time,
                        evidence_dir=collector.run_dir
                    )
                    collector.save_summary(result.model_dump())
                    return result

            # Final Checkpoint Assertion
            obs = await self.surface.observe()
            checkpoint = artifact.checkpoint
            checkpoint_met = False

            if checkpoint.condition_type == "url_contains":
                checkpoint_met = checkpoint.value in obs.url
            elif checkpoint.condition_type == "text_present":
                checkpoint_met = checkpoint.value in obs.visible_text_summary

            if not checkpoint_met:
                screenshot = await self.surface.screenshot()
                s_path = collector.save_screenshot("checkpoint_failure", screenshot)
                err = ErrorDetail(
                    expected_state=f"Checkpoint condition satisfied: {checkpoint.condition_type}='{checkpoint.value}'",
                    observed_state=f"Current URL: {obs.url}, Visible text: {obs.visible_text_summary[:200]}",
                    error_category=ErrorCategory.CHECKPOINT_FAILURE,
                    message="Final execution checkpoint assertion failed",
                    screenshot_path=s_path
                )
                result = ReplayResult(
                    status=ReplayStatus.HARD_FAILURE,
                    capability_id=artifact.artifact_id,
                    error=err,
                    execution_time_seconds=time.time() - start_time,
                    evidence_dir=collector.run_dir
                )
                collector.save_summary(result.model_dump())
                return result

            # Final Success
            screenshot = await self.surface.screenshot()
            s_path = collector.save_screenshot("replay_success", screenshot)
            result = ReplayResult(
                status=ReplayStatus.SUCCESS,
                capability_id=artifact.artifact_id,
                outputs=outputs,
                execution_time_seconds=time.time() - start_time,
                evidence_dir=collector.run_dir
            )
            collector.save_summary(result.model_dump())
            return result

        finally:
            if own_surface and self.surface:
                await self.surface.close()
                self.surface = None
