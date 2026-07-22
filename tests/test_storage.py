from __future__ import annotations

from ets4.storage.run_store import redact_secrets


def test_secret_redaction_covers_keys_and_authorization_headers() -> None:
    message = (
        "api_key=topsecret Authorization: Bearer bearer-secret "
        "provider returned sk-example123456789"
    )
    redacted = redact_secrets(message)
    assert "topsecret" not in redacted
    assert "bearer-secret" not in redacted
    assert "sk-example123456789" not in redacted
    assert redacted.count("REDACTED") >= 3
