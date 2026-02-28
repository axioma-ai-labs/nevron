"""Tool for interacting with the Gather.is platform.

Gather.is is an API-first social platform for AI agents. Agents authenticate
using Ed25519 challenge-response, then can post content, read feeds, comment
on posts, and discover other agents.

API docs: https://gather.is/help
"""

import base64
import hashlib
import logging
from typing import Dict, List, Optional

import requests
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from src.core.config import settings


class GatherTool:
    """Tool for interacting with the Gather.is agent social platform."""

    BASE_URL = "https://gather.is"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._token: Optional[str] = None
        self._private_key = None
        self._public_pem: Optional[str] = None
        self._initialize()

    def _initialize(self) -> bool:
        """Load Ed25519 keys and authenticate."""
        try:
            if not settings.GATHER_PRIVATE_KEY_PATH or not settings.GATHER_PUBLIC_KEY_PATH:
                self.logger.error("Gather key paths not configured in settings")
                return False

            with open(settings.GATHER_PRIVATE_KEY_PATH, "rb") as f:
                self._private_key = load_pem_private_key(f.read(), password=None)
            with open(settings.GATHER_PUBLIC_KEY_PATH, "r") as f:
                self._public_pem = f.read()

            self._authenticate()
            return True
        except FileNotFoundError as e:
            self.logger.error(f"Gather key file not found: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize Gather connection: {e}")
            return False

    def _authenticate(self) -> None:
        """Authenticate via Ed25519 challenge-response to get a JWT."""
        resp = requests.post(
            f"{self.BASE_URL}/api/agents/challenge",
            json={"public_key": self._public_pem},
            timeout=10,
        )
        resp.raise_for_status()
        nonce_bytes = base64.b64decode(resp.json()["nonce"])

        signature = self._private_key.sign(nonce_bytes)
        sig_b64 = base64.b64encode(signature).decode()

        resp = requests.post(
            f"{self.BASE_URL}/api/agents/authenticate",
            json={"public_key": self._public_pem, "signature": sig_b64},
            timeout=10,
        )
        resp.raise_for_status()
        self._token = resp.json()["token"]
        self.logger.debug("Authenticated with Gather.is")

    def _headers(self) -> Dict[str, str]:
        """Return authorization headers, re-authenticating if needed."""
        if not self._token:
            self._authenticate()
        return {"Authorization": f"Bearer {self._token}"}

    def _solve_pow(self, purpose: str = "post") -> tuple:
        """Solve proof-of-work challenge required for posting."""
        resp = requests.post(
            f"{self.BASE_URL}/api/pow/challenge",
            json={"purpose": purpose},
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        challenge = data["challenge"]
        difficulty = data["difficulty"]

        target_bytes = difficulty // 8
        target_bits_remaining = difficulty % 8

        for i in range(50_000_000):
            nonce = str(i)
            h = hashlib.sha256(f"{challenge}:{nonce}".encode()).digest()
            ok = all(h[j] == 0 for j in range(target_bytes))
            if ok and target_bits_remaining > 0:
                mask = 0xFF << (8 - target_bits_remaining)
                if h[target_bytes] & mask != 0:
                    ok = False
            if ok:
                self.logger.debug(f"PoW solved: difficulty={difficulty}, iterations={i}")
                return challenge, nonce

        raise RuntimeError(f"Failed to solve PoW (difficulty={difficulty})")

    def get_profile(self) -> Optional[Dict]:
        """Get the authenticated agent's profile."""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/api/agents/me",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return None

    def fetch_feed(self, limit: int = 25, sort: str = "recent") -> List[Dict]:
        """Fetch posts from the Gather.is feed.

        Args:
            limit: Number of posts to fetch (max 50)
            sort: Sort order — "recent", "hot", or "top"
        """
        try:
            resp = requests.get(
                f"{self.BASE_URL}/api/posts",
                params={"limit": limit, "sort": sort},
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("posts", [])
        except Exception as e:
            self.logger.error(f"Failed to fetch feed: {e}")
            return []

    def publish_post(
        self,
        title: str,
        summary: str,
        body: str,
        tags: Optional[List[str]] = None,
    ) -> Optional[Dict]:
        """Publish a post to Gather.is.

        Args:
            title: Post title (max 200 chars)
            summary: Short summary shown in feed (max 500 chars)
            body: Full post body (max 10,000 chars)
            tags: 1-5 topic tags
        """
        try:
            challenge, nonce = self._solve_pow()
            post_data = {
                "title": title,
                "summary": summary,
                "body": body,
                "tags": tags or ["nevron"],
                "pow_challenge": challenge,
                "pow_nonce": nonce,
            }
            resp = requests.post(
                f"{self.BASE_URL}/api/posts",
                json=post_data,
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"Failed to publish post: {e}")
            return None

    def post_comment(self, post_id: str, body: str) -> Optional[Dict]:
        """Comment on an existing post.

        Args:
            post_id: The ID of the post to comment on
            body: Comment text
        """
        try:
            resp = requests.post(
                f"{self.BASE_URL}/api/posts/{post_id}/comments",
                json={"body": body},
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"Failed to post comment: {e}")
            return None

    def discover_agents(self, query: Optional[str] = None) -> List[Dict]:
        """Discover other agents on the platform.

        Args:
            query: Optional name filter
        """
        try:
            params = {}
            if query:
                params["q"] = query
            resp = requests.get(
                f"{self.BASE_URL}/api/agents",
                params=params,
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("agents", [])
        except Exception as e:
            self.logger.error(f"Failed to discover agents: {e}")
            return []

    def check_inbox(self) -> List[Dict]:
        """Check the agent's inbox for notifications."""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/api/inbox",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("messages", [])
        except Exception as e:
            self.logger.error(f"Failed to check inbox: {e}")
            return []
