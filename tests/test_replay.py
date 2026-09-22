import asyncio
import time
import pytest
import uvicorn
import threading
from mock_app.main import app
from src.agent.discovery import DiscoveryAgent
from src.replay.engine import DeterministicReplayEngine
from src.models.taxonomy import ReplayStatus


def run_mock_server():
    uvicorn.run(app, host="127.0.0.1", port=8005, log_level="error")


@pytest.fixture(scope="module", autouse=True)
def server():
    server_thread = threading.Thread(target=run_mock_server, daemon=True)
    server_thread.start()
    time.sleep(1.5) # Wait for server startup
    yield server_thread


@pytest.mark.asyncio
async def test_end_to_end_discovery_and_replay():
    target_url = "http://127.0.0.1:8005"
    goal = "Look up member 12345 and read savings account balance"

    # 1. Run Discovery
    agent = DiscoveryAgent()
    artifact = await agent.run(goal=goal, target_url=target_url)

    assert artifact.artifact_id == "member_balance_lookup"
    assert len(artifact.steps) > 0

    # 2. Run Replay (Success case)
    engine = DeterministicReplayEngine()
    result_success = await engine.execute(artifact, input_parameters={"member_id": "12345"})

    assert result_success.status == ReplayStatus.SUCCESS
    assert result_success.outputs.get("savings_balance") == "$12,450.00"

    # 3. Run Replay (Business Outcome - Member Not Found)
    result_not_found = await engine.execute(artifact, input_parameters={"member_id": "99999"})

    assert result_not_found.status == ReplayStatus.BUSINESS_OUTCOME
    assert result_not_found.business_code == "MEMBER_NOT_FOUND"

    # 4. Run Replay (Business Outcome - Permission Denied)
    result_permission = await engine.execute(artifact, input_parameters={"member_id": "77777"})

    assert result_permission.status == ReplayStatus.BUSINESS_OUTCOME
    assert result_permission.business_code == "PERMISSION_DENIED"
