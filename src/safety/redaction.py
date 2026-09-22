"""
Data redaction utility to scrub sensitive financial data, credentials, and PII.
"""

import re
from typing import Any, Dict, List, Union

SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
API_KEY_PATTERN = re.compile(r"\b(sk-[a-zA-Z0-9_-]{20,}|key-[a-zA-Z0-9_-]{20,})\b", re.IGNORECASE)
PASSWORD_PATTERN = re.compile(r"(password|passwd|pwd|secret|auth_token|token)=['\"]?([^'\"\s]+)['\"]?", re.IGNORECASE)

SENSITIVE_KEYS = {"password", "secret", "api_key", "token", "auth_token", "ssn", "credit_card"}


def redact_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    
    # Redact SSNs
    text = SSN_PATTERN.sub("***-**-****", text)
    
    # Redact API Keys
    text = API_KEY_PATTERN.sub("[REDACTED_API_KEY]", text)
    
    # Redact Inline Passwords/Secrets
    text = PASSWORD_PATTERN.sub(r"\1=[REDACTED]", text)
    
    return text


def redact_sensitive_data(data: Any) -> Any:
    """Recursively redact sensitive keys and pattern matches from objects."""
    if isinstance(data, str):
        return redact_text(data)
    elif isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if k.lower() in SENSITIVE_KEYS:
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_sensitive_data(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    return data
