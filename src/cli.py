"""
CLI Commands for Computer-Use Automation System.
Provides commands for discovery, deterministic replay, human handoff, and mock app server.
"""

import argparse
import asyncio
import json
import sys
import uvicorn
from typing import Dict, Any

from src.agent.discovery import DiscoveryAgent
from src.artifacts.schema import CapabilityArtifact
from src.replay.engine import DeterministicReplayEngine
from src.escalation.handoff import HandoffManager
from src.surfaces.playwright_adapter import PlaywrightSurfaceAdapter
from src.models.actions import Locator
from src.observability.evidence import EvidenceCollector
from src.observability.logger import setup_logger

logger = setup_logger(__name__)


def parse_kv_inputs(kv_list: list) -> Dict[str, Any]:
    params = {}
    if not kv_list:
        return params
    for item in kv_list:
        if "=" in item:
            k, v = item.split("=", 1)
            params[k.strip()] = v.strip()
    return params


async def run_discover(goal: str, target: str):
    logger.info(f"Starting Discovery Agent | Goal: '{goal}' | Target: '{target}'")
    agent = DiscoveryAgent()
    artifact = await agent.run(goal=goal, target_url=target)
    logger.info(f"Discovery Completed! Saved Capability Artifact to artifacts/member_balance.json")
    print("\n" + "="*60)
    print("DISCOVERY SUCCEEDED! Artifact generated:")
    print("="*60)
    print(artifact.to_json(indent=2))


async def run_replay(artifact_path: str, inputs_dict: Dict[str, Any]):
    logger.info(f"Starting Deterministic Replay | Artifact: '{artifact_path}' | Inputs: {inputs_dict}")
    artifact = CapabilityArtifact.from_file(artifact_path)
    engine = DeterministicReplayEngine()
    result = await engine.execute(artifact, input_parameters=inputs_dict)
    
    print("\n" + "="*60)
    print(f"REPLAY RESULT STATUS: {result.status.value}")
    print("="*60)
    if result.business_code:
        print(f"BUSINESS OUTCOME CODE: {result.business_code}")
    if result.outputs:
        print(f"OUTPUTS: {json.dumps(result.outputs, indent=2)}")
    if result.error:
        print(f"ERROR CATEGORY: {result.error.error_category.value}")
        print(f"ERROR MESSAGE: {result.error.message}")
        print(f"FAILED AT STEP: {result.error.step_id} ({result.error.step_index})")
    print(f"EVIDENCE LOCATION: {result.evidence_dir}")
    print("="*60 + "\n")


async def run_handoff_demo(target: str):
    logger.info(f"Starting Human-in-the-Loop Handoff Demo against {target}")
    surface = PlaywrightSurfaceAdapter(headless=True) # Run headless for smooth CLI execution
    await surface.initialize()
    
    collector = EvidenceCollector(run_type="handoff")
    handoff_mgr = HandoffManager(
        run_id=collector.run_id,
        goal_or_capability="Sub-Account Creation Confirmation",
        evidence_collector=collector
    )

    try:
        await surface.navigate(f"{target}/members/12345/new-subaccount")
        obs = await surface.observe()
        screenshot_bytes = await surface.screenshot()

        # Trigger escalation
        logger.info("Triggering intervention request for human approval...")
        req = await handoff_mgr.trigger_escalation(
            current_step="step_subaccount_review",
            reason="RISKY_ACTION_CONFIRMATION: Sub-account creation requires operator sign-off.",
            observation=obs,
            screenshot_bytes=screenshot_bytes
        )

        print("\n" + "!"*60)
        print("HUMAN INTERVENTION REQUIRED")
        print("!"*60)
        print(f"Run ID: {req.run_id}")
        print(f"Reason: {req.reason}")
        print(f"Current URL: {req.current_url}")
        print(f"Evidence Screenshot: {req.screenshot_path}")
        print("!"*60)

        # Transfer to human control
        handoff_mgr.transfer_to_human()
        print("\nLive session is under HUMAN_CONTROL. The session is active.")
        print("Simulating human review and approval in 1 second...")
        await asyncio.sleep(1)

        # Resume automation
        handoff_mgr.resume_automation(operator_notes="Approved sub-account parameters after visual check.")
        print("\nAUTOMATION RESUMED. Completing flow...")
        await surface.click(Locator(role_name={"role": "button", "name": "REVIEW SUB-ACCOUNT CREATION"}, css="input[type='submit']"))
        
        collector.save_summary({"status": "HANDOFF_SUCCESS", "state": handoff_mgr.state.value})
        print(f"\nHandoff Demo Completed Successfully! Evidence saved to {collector.run_dir}\n")

    finally:
        await surface.close()


def main():
    parser = argparse.ArgumentParser(description="Computer-Use Automation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Discover command
    disc_parser = subparsers.add_parser("discover", help="Run LLM Discovery Agent")
    disc_parser.add_argument("--goal", required=True, help="Goal description")
    disc_parser.add_argument("--target", default="http://localhost:8000", help="Target URL")

    # Replay command
    replay_parser = subparsers.add_parser("replay", help="Run Deterministic Replay Engine")
    replay_parser.add_argument("--artifact", required=True, help="Path to Capability Artifact JSON")
    replay_parser.add_argument("--input", nargs="*", help="Input parameters in key=value format (e.g. member_id=12345)")

    # Handoff demo command
    handoff_parser = subparsers.add_parser("handoff", help="Run Human-in-the-Loop Handoff Demo")
    handoff_parser.add_argument("--target", default="http://localhost:8000", help="Target URL")

    # Serve mock command
    subparsers.add_parser("serve-mock", help="Start Legacy Banking Mock Application")

    args = parser.parse_args()

    if args.command == "serve-mock":
        print("Starting CoreBank Servicing Terminal mock server on http://localhost:8000 ...")
        uvicorn.run("mock_app.main:app", host="0.0.0.0", port=8000, reload=False)
    elif args.command == "discover":
        asyncio.run(run_discover(args.goal, args.target))
    elif args.command == "replay":
        inputs = parse_kv_inputs(args.input)
        asyncio.run(run_replay(args.artifact, inputs))
    elif args.command == "handoff":
        asyncio.run(run_handoff_demo(args.target))


if __name__ == "__main__":
    main()
