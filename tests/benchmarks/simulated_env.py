"""
Simulated Environment Framework.

Mock environment for testing agent capabilities without real APIs.
Supports configurable success/failure rates, failure injection, and loop scenarios.
"""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class FailureType(Enum):
    """Types of failures that can be injected."""

    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    INVALID_RESPONSE = "invalid_response"
    AUTHENTICATION_ERROR = "authentication_error"


@dataclass
class ToolResult:
    """Result from a simulated tool execution."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    latency_ms: float = 0.0
    tool_name: str = ""


@dataclass
class SimulatedAction:
    """Record of a simulated action."""

    tool: str
    params: dict[str, Any]
    result: ToolResult
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SimConfig:
    """Configuration for simulated environment."""

    # Tool success rates (0.0 to 1.0)
    tool_success_rates: dict[str, float] = field(default_factory=dict)
    # Default success rate for unknown tools
    default_success_rate: float = 0.8
    # Latency range in ms (min, max)
    latency_range: tuple[float, float] = (10.0, 100.0)
    # Enable random failures beyond configured rates
    random_failures_enabled: bool = False
    # Random failure probability (when enabled)
    random_failure_probability: float = 0.05
    # Seed for reproducibility (None for random)
    seed: int | None = None


@dataclass
class FailureInjection:
    """Scheduled failure injection."""

    after_n_actions: int
    failure_type: FailureType
    tools: list[str] | None = None  # None means all tools
    duration: int = 1  # Number of actions this failure lasts


class SimulatedEnvironment:
    """
    Mock environment for testing without real APIs.
    Configurable success/failure rates.
    """

    def __init__(self, config: SimConfig | None = None):
        """Initialize simulated environment."""
        self.config = config or SimConfig()
        if self.config.seed is not None:
            random.seed(self.config.seed)

        self._action_count = 0
        self._action_history: list[SimulatedAction] = []
        self._injected_failures: list[FailureInjection] = []
        self._active_failures: list[FailureInjection] = []
        self._custom_handlers: dict[str, Callable] = {}
        self._loop_scenarios: list[dict[str, Any]] = []

    def reset(self) -> None:
        """Reset environment state."""
        self._action_count = 0
        self._action_history = []
        self._injected_failures = []
        self._active_failures = []

    async def execute_tool(self, tool: str, params: dict[str, Any] | None = None) -> ToolResult:
        """
        Simulate tool execution with configurable outcomes.

        Args:
            tool: Name of the tool to execute
            params: Parameters for the tool

        Returns:
            ToolResult with success/failure and optional data
        """
        params = params or {}
        self._action_count += 1

        # Check for custom handler first
        if tool in self._custom_handlers:
            result = self._custom_handlers[tool](params)
            self._record_action(tool, params, result)
            return result

        # Check for injected failures
        failure = self._check_injected_failure(tool)
        if failure:
            result = self._create_failure_result(tool, failure)
            self._record_action(tool, params, result)
            return result

        # Check for random failures
        if self.config.random_failures_enabled:
            if random.random() < self.config.random_failure_probability:
                result = ToolResult(
                    success=False,
                    error="Random failure occurred",
                    tool_name=tool,
                    latency_ms=random.uniform(*self.config.latency_range),
                )
                self._record_action(tool, params, result)
                return result

        # Check success rate for this tool
        success_rate = self.config.tool_success_rates.get(tool, self.config.default_success_rate)

        latency = random.uniform(*self.config.latency_range)
        await asyncio.sleep(latency / 1000)  # Simulate network latency

        if random.random() < success_rate:
            result = ToolResult(
                success=True,
                data=self._mock_data(tool, params),
                tool_name=tool,
                latency_ms=latency,
            )
        else:
            result = ToolResult(
                success=False,
                error=self._mock_error(tool),
                tool_name=tool,
                latency_ms=latency,
            )

        self._record_action(tool, params, result)
        return result

    def inject_failure(
        self,
        after_n_actions: int,
        failure_type: FailureType,
        tools: list[str] | None = None,
        duration: int = 1,
    ) -> None:
        """
        Inject failures to test recovery.

        Args:
            after_n_actions: Trigger failure after this many actions
            failure_type: Type of failure to inject
            tools: Specific tools to fail (None for all)
            duration: How many actions the failure lasts
        """
        self._injected_failures.append(
            FailureInjection(
                after_n_actions=after_n_actions,
                failure_type=failure_type,
                tools=tools,
                duration=duration,
            )
        )

    def register_custom_handler(
        self, tool: str, handler: Callable[[dict[str, Any]], ToolResult]
    ) -> None:
        """Register a custom handler for a specific tool."""
        self._custom_handlers[tool] = handler

    def create_loop_scenario(
        self,
        repeated_action: str,
        repetition_count: int = 5,
        should_detect: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Create a scenario that should trigger loop detection.

        Args:
            repeated_action: The action to repeat
            repetition_count: How many times to repeat
            should_detect: Whether this should be detected as a loop

        Returns:
            Action sequence for testing
        """
        scenario = {
            "actions": [{"tool": repeated_action, "params": {}} for _ in range(repetition_count)],
            "should_detect_loop": should_detect,
            "loop_start_index": 0,
        }
        self._loop_scenarios.append(scenario)
        return scenario["actions"]

    def get_action_history(self) -> list[SimulatedAction]:
        """Get history of all executed actions."""
        return self._action_history.copy()

    def get_statistics(self) -> dict[str, Any]:
        """Get environment statistics."""
        if not self._action_history:
            return {
                "total_actions": 0,
                "success_rate": 0.0,
                "failure_rate": 0.0,
                "average_latency_ms": 0.0,
                "by_tool": {},
            }

        total = len(self._action_history)
        successes = sum(1 for a in self._action_history if a.result.success)
        failures = total - successes

        by_tool: dict[str, dict[str, Any]] = {}
        for action in self._action_history:
            if action.tool not in by_tool:
                by_tool[action.tool] = {"total": 0, "successes": 0, "failures": 0}
            by_tool[action.tool]["total"] += 1
            if action.result.success:
                by_tool[action.tool]["successes"] += 1
            else:
                by_tool[action.tool]["failures"] += 1

        return {
            "total_actions": total,
            "success_rate": successes / total if total > 0 else 0.0,
            "failure_rate": failures / total if total > 0 else 0.0,
            "average_latency_ms": sum(a.result.latency_ms for a in self._action_history) / total,
            "by_tool": by_tool,
        }

    def _check_injected_failure(self, tool: str) -> FailureInjection | None:
        """Check if an injected failure should be triggered."""
        # Update active failures
        self._active_failures = [
            f for f in self._active_failures if self._action_count <= f.after_n_actions + f.duration
        ]

        # Check for active failures
        for failure in self._active_failures:
            if failure.tools is None or tool in failure.tools:
                return failure

        # Check for new failures to activate
        for failure in self._injected_failures:
            if (
                self._action_count >= failure.after_n_actions
                and self._action_count < failure.after_n_actions + failure.duration
            ):
                if failure.tools is None or tool in failure.tools:
                    if failure not in self._active_failures:
                        self._active_failures.append(failure)
                    return failure

        return None

    def _create_failure_result(self, tool: str, failure: FailureInjection) -> ToolResult:
        """Create a failure result based on failure type."""
        error_messages = {
            FailureType.RATE_LIMIT: "Rate limit exceeded. Please try again later.",
            FailureType.TIMEOUT: "Request timed out.",
            FailureType.API_ERROR: "API returned an error.",
            FailureType.NETWORK_ERROR: "Network connection failed.",
            FailureType.INVALID_RESPONSE: "Invalid response received.",
            FailureType.AUTHENTICATION_ERROR: "Authentication failed.",
        }

        return ToolResult(
            success=False,
            error=error_messages.get(failure.failure_type, "Unknown error"),
            tool_name=tool,
            latency_ms=random.uniform(*self.config.latency_range),
        )

    def _record_action(self, tool: str, params: dict[str, Any], result: ToolResult) -> None:
        """Record an action in history."""
        self._action_history.append(SimulatedAction(tool=tool, params=params, result=result))

    def _mock_data(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        """Generate mock data for a tool."""
        mock_responses = {
            "search_tavily": {
                "query": params.get("query", ""),
                "results": [
                    {"title": "Result 1", "snippet": "Mock search result 1"},
                    {"title": "Result 2", "snippet": "Mock search result 2"},
                ],
            },
            "ask_perplexity": {
                "query": params.get("query", ""),
                "answer": "This is a mock answer from Perplexity.",
                "sources": ["https://example.com"],
            },
            "send_telegram_message": {
                "message_id": random.randint(1000, 9999),
                "sent": True,
            },
            "post_twitter": {
                "tweet_id": str(random.randint(10**18, 10**19)),
                "posted": True,
            },
            "mcp_tool": {
                "result": "Mock MCP tool result",
                "metadata": {},
            },
        }

        return mock_responses.get(tool, {"result": f"Mock result for {tool}", "params": params})

    def _mock_error(self, tool: str) -> str:
        """Generate mock error for a tool."""
        errors = [
            f"{tool}: Connection timeout",
            f"{tool}: Rate limit exceeded",
            f"{tool}: Invalid parameters",
            f"{tool}: Service unavailable",
            f"{tool}: Internal error",
        ]
        return random.choice(errors)


class ScenarioRunner:
    """Runner for test scenarios."""

    def __init__(self, env: SimulatedEnvironment):
        """Initialize scenario runner."""
        self.env = env
        self._results: list[dict[str, Any]] = []

    async def run_scenario(self, actions: list[dict[str, Any]]) -> list[ToolResult]:
        """
        Run a sequence of actions.

        Args:
            actions: List of action dictionaries with 'tool' and 'params'

        Returns:
            List of tool results
        """
        results = []
        for action in actions:
            result = await self.env.execute_tool(
                action.get("tool", "unknown"), action.get("params", {})
            )
            results.append(result)
        return results

    def get_scenario_results(self) -> list[dict[str, Any]]:
        """Get results from all run scenarios."""
        return self._results.copy()
