import pytest
from src.safety.redaction import redact_text, redact_sensitive_data


def test_ssn_redaction():
    text = "Member John Doe has SSN 123-45-6789 on record."
    redacted = redact_text(text)
    assert "123-45-6789" not in redacted
    assert "***-**-****" in redacted


def test_api_key_redaction():
    text = "Connecting with API key sk-proj-1234567890abcdef1234567890 to service."
    redacted = redact_text(text)
    assert "sk-proj-1234567890abcdef1234567890" not in redacted
    assert "[REDACTED_API_KEY]" in redacted


def test_nested_dict_redaction():
    data = {
        "user": "jane_doe",
        "ssn": "987-65-4321",
        "password": "SuperSecretPassword123!",
        "details": {
            "token": "bearer_abc123xyz"
        }
    }
    redacted = redact_sensitive_data(data)
    assert redacted["ssn"] == "[REDACTED]"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["details"]["token"] == "[REDACTED]"
