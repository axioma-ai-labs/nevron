"""Tests for API key auth on REST routes and the WebSocket."""

import re

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.api.config import APISettings, api_settings
from src.api.main import create_app
from tests.api.conftest import set_auth_disabled


KEY = "test-key-123"
ORIGIN = "http://localhost:5173"


@pytest.fixture
def keyed(monkeypatch):
    """Auth on with a configured key."""
    monkeypatch.setattr(api_settings, "API_KEY", KEY)
    set_auth_disabled(monkeypatch, False)


@pytest.fixture
def no_key(monkeypatch):
    """Auth on but no key configured."""
    monkeypatch.setattr(api_settings, "API_KEY", None)
    set_auth_disabled(monkeypatch, False)


def _api_routes(app):
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith(api_settings.API_V1_PREFIX):
            for method in route.methods:
                yield method, re.sub(r"\{[^}]+\}", "x", route.path)


class TestDefaults:
    def test_defaults_are_closed(self, monkeypatch):
        for name in ("NEVRON_API_HOST", "NEVRON_API_KEY", "NEVRON_API_AUTH_DISABLED"):
            monkeypatch.delenv(name, raising=False)
        settings = APISettings(_env_file=None)
        assert settings.API_HOST == "127.0.0.1"
        assert settings.API_KEY is None
        assert settings.API_AUTH_DISABLED is False


class TestRestAuth:
    def test_every_api_route_rejects_missing_key(self, keyed):
        app = create_app()
        routes = list(_api_routes(app))
        assert len(routes) > 50
        with TestClient(app) as client:
            for method, path in routes:
                response = client.request(method, path)
                assert response.status_code == 401, f"{method} {path} -> {response.status_code}"

    def test_wrong_key_rejected(self, keyed):
        with TestClient(create_app()) as client:
            response = client.get("/api/v1/agent/status", headers={"X-API-Key": "wrong"})
        assert response.status_code == 401

    def test_right_key_accepted(self, keyed):
        with TestClient(create_app()) as client:
            response = client.get("/api/v1/agent/status", headers={"X-API-Key": KEY})
        assert response.status_code == 200

    def test_explicitly_disabled_allows_without_key(self):
        with TestClient(create_app()) as client:
            response = client.get("/api/v1/agent/status")
        assert response.status_code == 200

    def test_no_key_configured_fails_closed_per_request(self, no_key):
        client = TestClient(create_app())  # no lifespan: request-level check only
        response = client.get("/api/v1/agent/status")
        assert response.status_code == 503

    def test_no_key_configured_refuses_to_start(self, no_key):
        with pytest.raises(RuntimeError, match="NEVRON_API_KEY"):
            with TestClient(create_app()):
                pass

    def test_health_stays_open(self, keyed):
        with TestClient(create_app()) as client:
            assert client.get("/health").status_code == 200


class TestWebSocketAuth:
    def _refused(self, client, url, **kwargs):
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(url, **kwargs) as ws:
                ws.receive_json()
        return exc.value.code

    def test_missing_credentials_refused(self, keyed):
        with TestClient(create_app()) as client:
            assert self._refused(client, "/ws/c1") == 1008

    def test_wrong_header_refused(self, keyed):
        with TestClient(create_app()) as client:
            assert self._refused(client, "/ws/c1", headers={"X-API-Key": "wrong"}) == 1008

    def test_raw_key_in_query_refused(self, keyed):
        with TestClient(create_app()) as client:
            assert self._refused(client, f"/ws/c1?ticket={KEY}") == 1008

    def test_header_key_accepted(self, keyed):
        with TestClient(create_app()) as client:
            with client.websocket_connect("/ws/c1", headers={"X-API-Key": KEY}) as ws:
                assert ws.receive_json()["type"] == "connected"

    def test_ticket_is_single_use(self, keyed):
        with TestClient(create_app()) as client:
            r = client.post("/api/v1/auth/ws-ticket", headers={"X-API-Key": KEY})
            assert r.status_code == 200
            ticket = r.json()["data"]["ticket"]
            headers = {"Origin": ORIGIN}
            with client.websocket_connect(f"/ws/c1?ticket={ticket}", headers=headers) as ws:
                assert ws.receive_json()["type"] == "connected"
            assert self._refused(client, f"/ws/c2?ticket={ticket}", headers=headers) == 1008

    def test_ticket_endpoint_needs_key(self, keyed):
        with TestClient(create_app()) as client:
            assert client.post("/api/v1/auth/ws-ticket").status_code == 401

    def test_foreign_origin_refused(self, keyed):
        with TestClient(create_app()) as client:
            headers = {"X-API-Key": KEY, "Origin": "https://evil.example"}
            assert self._refused(client, "/ws/c1", headers=headers) == 1008

    def test_no_key_configured_refused(self, no_key):
        client = TestClient(create_app())
        assert self._refused(client, "/ws/c1") == 1008

    def test_connection_limit_enforced(self, keyed, monkeypatch):
        monkeypatch.setattr(api_settings, "WS_MAX_CONNECTIONS", 1)
        with TestClient(create_app()) as client:
            headers = {"X-API-Key": KEY}
            with client.websocket_connect("/ws/c1", headers=headers) as ws:
                ws.receive_json()
                assert self._refused(client, "/ws/c2", headers=headers) == 1013
