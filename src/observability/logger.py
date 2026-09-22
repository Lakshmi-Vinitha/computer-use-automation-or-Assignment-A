"""
Structured JSONL logging and console logging with automatic PII/secret redaction.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from src.safety.redaction import redact_sensitive_data


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return redact_sensitive_data(original)


class JSONLFileLogger:
    def __init__(self, log_filepath: str):
        self.log_filepath = log_filepath

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": redact_sensitive_data(data)
        }
        with open(self.log_filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")


def setup_logger(name: str = "computer_use", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = RedactingFormatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
