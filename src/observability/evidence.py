"""
Evidence Collector for storing structured logs, screenshots, artifacts, and execution reports.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from src.observability.logger import JSONLFileLogger
from src.safety.redaction import redact_sensitive_data


class EvidenceCollector:
    def __init__(self, run_type: str = "discovery", run_id: Optional[str] = None, base_dir: str = "evidence"):
        self.run_id = run_id or f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        self.run_type = run_type # discovery, replay-success, replay-error, handoff
        self.run_dir = os.path.join(base_dir, run_type, self.run_id)
        self.screenshots_dir = os.path.join(self.run_dir, "screenshots")
        
        os.makedirs(self.screenshots_dir, exist_ok=True)
        self.jsonl_logger = JSONLFileLogger(os.path.join(self.run_dir, "run_log.jsonl"))

    def log_step(self, step_name: str, details: Dict[str, Any]) -> None:
        self.jsonl_logger.log_event("STEP_EXECUTION", {
            "step": step_name,
            "details": details
        })

    def save_screenshot(self, name: str, image_bytes: bytes) -> str:
        filename = f"{name}.png"
        filepath = os.path.join(self.screenshots_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return filepath

    def save_artifact(self, artifact_json_str: str) -> str:
        filepath = os.path.join(self.run_dir, "artifact.json")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(artifact_json_str)
        return filepath

    def save_summary(self, summary_data: Dict[str, Any]) -> str:
        filepath = os.path.join(self.run_dir, "summary.json")
        clean_summary = redact_sensitive_data(summary_data)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json.dumps(clean_summary, indent=2))
        return filepath
