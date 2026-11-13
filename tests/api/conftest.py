"""Shared fixtures for API tests."""

import pytest

from src.api.config import api_settings


def set_auth_disabled(monkeypatch, value: bool) -> None:
    """Set API_AUTH_DISABLED when the settings model has it."""
    if "API_AUTH_DISABLED" in type(api_settings).model_fields:
        monkeypatch.setattr(api_settings, "API_AUTH_DISABLED", value)


@pytest.fixture(autouse=True)
def api_auth_settings(monkeypatch):
    """Run API tests with auth disabled unless a test sets it up itself."""
    monkeypatch.setattr(api_settings, "API_KEY", None)
    set_auth_disabled(monkeypatch, True)
    yield api_settings
