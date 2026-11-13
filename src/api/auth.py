"""API key auth for REST routes and the WebSocket.

Auth is on by default. NEVRON_API_KEY must be set unless NEVRON_API_AUTH_DISABLED=true
(local development only). With no key and auth on, the API refuses to start and every
protected request is rejected.

Browsers can't set headers on a WebSocket, so they first POST /api/v1/auth/ws-ticket
with the key and connect with ?ticket=<ticket>. Tickets are short-lived and single-use.
"""

import secrets
import time
from typing import Dict, Optional

from fastapi import Header, HTTPException, WebSocket, status

from src.api.config import api_settings


# ticket -> expiry (monotonic seconds)
_ws_tickets: Dict[str, float] = {}


def auth_disabled() -> bool:
    """Whether auth was explicitly disabled for local development."""
    return api_settings.API_AUTH_DISABLED


def key_matches(candidate: Optional[str]) -> bool:
    """Constant-time check of a candidate key against NEVRON_API_KEY."""
    expected = api_settings.API_KEY
    if not expected or not candidate:
        return False
    return secrets.compare_digest(candidate.encode(), expected.encode())


def check_auth_config() -> None:
    """Refuse to start when auth is on and no key is configured."""
    if auth_disabled():
        return
    if not api_settings.API_KEY:
        raise RuntimeError(
            "NEVRON_API_KEY is not set. Set it, or set NEVRON_API_AUTH_DISABLED=true "
            "for local development on a loopback-only bind."
        )


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias=api_settings.API_KEY_HEADER),
) -> bool:
    """FastAPI dependency: require a valid API key unless auth is disabled."""
    if auth_disabled():
        return True

    if not api_settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured on the server",
        )

    if not key_matches(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return True


def issue_ws_ticket() -> str:
    """Create a single-use WebSocket ticket."""
    now = time.monotonic()
    for ticket, expiry in list(_ws_tickets.items()):
        if expiry <= now:
            del _ws_tickets[ticket]
    ticket = secrets.token_urlsafe(32)
    _ws_tickets[ticket] = now + api_settings.WS_TICKET_TTL
    return ticket


def consume_ws_ticket(ticket: Optional[str]) -> bool:
    """Use up a ticket. True only if it existed and had not expired."""
    if not ticket:
        return False
    expiry = _ws_tickets.pop(ticket, None)
    return expiry is not None and expiry > time.monotonic()


def origin_allowed(websocket: WebSocket) -> bool:
    """Reject browser connections from origins outside CORS_ORIGINS."""
    origin = websocket.headers.get("origin")
    if origin is None:
        return True  # non-browser client
    return origin in api_settings.CORS_ORIGINS


def websocket_authorized(websocket: WebSocket) -> bool:
    """Check a WebSocket handshake before accept()."""
    if not origin_allowed(websocket):
        return False
    if auth_disabled():
        return True
    if not api_settings.API_KEY:
        return False
    if key_matches(websocket.headers.get(api_settings.API_KEY_HEADER)):
        return True
    return consume_ws_ticket(websocket.query_params.get("ticket"))
