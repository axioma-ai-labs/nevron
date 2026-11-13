"""Auth endpoints: WebSocket tickets for browser clients."""

from typing import Dict, Union

from fastapi import APIRouter, Depends

from src.api.auth import issue_ws_ticket, verify_api_key
from src.api.config import api_settings
from src.api.schemas import APIResponse


router = APIRouter()


@router.post("/ws-ticket", response_model=APIResponse[Dict[str, Union[str, float]]])
async def create_ws_ticket(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Union[str, float]]]:
    """Issue a short-lived single-use ticket for connecting to /ws."""
    return APIResponse(
        data={"ticket": issue_ws_ticket(), "expires_in": api_settings.WS_TICKET_TTL},
        message="WebSocket ticket issued",
    )
