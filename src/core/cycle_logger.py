"""Agent Cycle Logger - Structured logging for agent runtime cycles.

This module provides a persistent logging system that captures each agent cycle
including planning, execution, learning phases with full context for monitoring
and debugging.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from loguru import logger


# Default database path
DEFAULT_DB_PATH = Path("./nevron_cycles.db")

# Maximum cycles to keep (for cleanup)
MAX_CYCLES_TO_KEEP = 1000


@dataclass
class CycleLog:
    """Structured log entry for a single agent cycle."""

    # Identification
    cycle_id: str
    timestamp: str

    # Planning phase
    planning_input_state: str
    planning_input_recent_actions: List[str]
    planning_output_action: str
    planning_output_reasoning: Optional[str] = None
    planning_duration_ms: int = 0

    # Execution phase
    action_name: str = ""
    action_params: Dict[str, Any] = field(default_factory=dict)
    execution_result: Dict[str, Any] = field(default_factory=dict)
    execution_success: bool = False
    execution_error: Optional[str] = None
    execution_duration_ms: int = 0

    # Learning phase
    reward: float = 0.0
    critique: Optional[str] = None
    lesson_learned: Optional[str] = None

    # Memory phase
    memories_stored: List[str] = field(default_factory=list)

    # Metadata
    llm_provider: str = ""
    llm_model: str = ""
    llm_tokens_used: int = 0
    total_duration_ms: int = 0
    agent_state_after: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        result = asdict(self)
        # Serialize lists and dicts as JSON strings for SQLite
        result["planning_input_recent_actions"] = json.dumps(
            result["planning_input_recent_actions"]
        )
        result["action_params"] = json.dumps(result["action_params"])
        result["execution_result"] = json.dumps(result["execution_result"])
        result["memories_stored"] = json.dumps(result["memories_stored"])
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CycleLog":
        """Create from dictionary (from database)."""
        # Deserialize JSON strings
        if isinstance(data.get("planning_input_recent_actions"), str):
            data["planning_input_recent_actions"] = json.loads(
                data["planning_input_recent_actions"]
            )
        if isinstance(data.get("action_params"), str):
            data["action_params"] = json.loads(data["action_params"])
        if isinstance(data.get("execution_result"), str):
            data["execution_result"] = json.loads(data["execution_result"])
        if isinstance(data.get("memories_stored"), str):
            data["memories_stored"] = json.loads(data["memories_stored"])
        return cls(**data)


@dataclass
class CycleStats:
    """Aggregate statistics for cycle history."""

    total_cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    total_rewards: float = 0.0
    avg_reward: float = 0.0
    action_counts: Dict[str, int] = field(default_factory=dict)
    top_actions: List[str] = field(default_factory=list)
    cycles_per_hour: float = 0.0
    last_cycle_time: Optional[str] = None


class CycleLogger:
    """Manages logging of agent cycles to SQLite database."""

    _instance: Optional["CycleLogger"] = None
    _lock = Lock()
    _initialized: bool = False

    def __new__(cls, db_path: Optional[Path] = None):
        """Singleton pattern for cycle logger."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the cycle logger.

        Args:
            db_path: Path to SQLite database file
        """
        if self._initialized:
            return

        self.db_path = db_path or DEFAULT_DB_PATH
        self._db_lock = Lock()
        self._init_database()
        self._initialized = True
        logger.info(f"CycleLogger initialized with database at {self.db_path}")

    def _init_database(self) -> None:
        """Initialize the SQLite database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cycles (
                    cycle_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    planning_input_state TEXT,
                    planning_input_recent_actions TEXT,
                    planning_output_action TEXT,
                    planning_output_reasoning TEXT,
                    planning_duration_ms INTEGER DEFAULT 0,
                    action_name TEXT,
                    action_params TEXT,
                    execution_result TEXT,
                    execution_success INTEGER DEFAULT 0,
                    execution_error TEXT,
                    execution_duration_ms INTEGER DEFAULT 0,
                    reward REAL DEFAULT 0.0,
                    critique TEXT,
                    lesson_learned TEXT,
                    memories_stored TEXT,
                    llm_provider TEXT,
                    llm_model TEXT,
                    llm_tokens_used INTEGER DEFAULT 0,
                    total_duration_ms INTEGER DEFAULT 0,
                    agent_state_after TEXT
                )
            """)

            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cycles_timestamp
                ON cycles(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cycles_action
                ON cycles(action_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cycles_success
                ON cycles(execution_success)
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper handling."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def generate_cycle_id(self) -> str:
        """Generate a unique cycle ID."""
        return f"cycle_{uuid.uuid4().hex[:12]}"

    def log_cycle(self, cycle: CycleLog) -> bool:
        """Log a cycle to the database.

        Args:
            cycle: CycleLog instance to store

        Returns:
            True if successful, False otherwise
        """
        try:
            with self._db_lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    data = cycle.to_dict()

                    columns = ", ".join(data.keys())
                    placeholders = ", ".join(["?" for _ in data])
                    values = list(data.values())

                    cursor.execute(
                        f"INSERT OR REPLACE INTO cycles ({columns}) VALUES ({placeholders})", values
                    )
                    conn.commit()

            logger.debug(f"Logged cycle {cycle.cycle_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to log cycle: {e}")
            return False

    def get_cycle(self, cycle_id: str) -> Optional[CycleLog]:
        """Get a specific cycle by ID.

        Args:
            cycle_id: The cycle ID to retrieve

        Returns:
            CycleLog if found, None otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM cycles WHERE cycle_id = ?", (cycle_id,))
                row = cursor.fetchone()

                if row:
                    return CycleLog.from_dict(dict(row))
                return None

        except Exception as e:
            logger.error(f"Failed to get cycle {cycle_id}: {e}")
            return None

    def get_recent_cycles(
        self,
        limit: int = 50,
        offset: int = 0,
        action_filter: Optional[str] = None,
        success_filter: Optional[bool] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[CycleLog]:
        """Get recent cycles with optional filtering.

        Args:
            limit: Maximum number of cycles to return
            offset: Number of cycles to skip (for pagination)
            action_filter: Filter by action name
            success_filter: Filter by success status
            start_time: Filter by start time (ISO format)
            end_time: Filter by end time (ISO format)

        Returns:
            List of CycleLog instances
        """
        try:
            conditions: List[str] = []
            params: List[Any] = []

            if action_filter:
                conditions.append("action_name = ?")
                params.append(action_filter)

            if success_filter is not None:
                conditions.append("execution_success = ?")
                params.append(1 if success_filter else 0)

            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time)

            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time)

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            query = f"""
                SELECT * FROM cycles
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [CycleLog.from_dict(dict(row)) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get recent cycles: {e}")
            return []

    def get_stats(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> CycleStats:
        """Get aggregate statistics for cycles.

        Args:
            start_time: Filter by start time (ISO format)
            end_time: Filter by end time (ISO format)

        Returns:
            CycleStats instance with aggregate data
        """
        try:
            conditions = []
            params = []

            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time)

            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time)

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get basic stats
                cursor.execute(
                    f"""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN execution_success = 1 THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN execution_success = 0 THEN 1 ELSE 0 END) as failed,
                        AVG(total_duration_ms) as avg_duration,
                        SUM(reward) as total_rewards,
                        AVG(reward) as avg_reward,
                        MAX(timestamp) as last_cycle
                    FROM cycles
                    {where_clause}
                """,
                    params,
                )
                row = cursor.fetchone()

                total = row["total"] or 0
                successful = row["successful"] or 0
                failed = row["failed"] or 0
                success_rate = (successful / total * 100) if total > 0 else 0.0

                # Get action counts
                cursor.execute(
                    f"""
                    SELECT action_name, COUNT(*) as count
                    FROM cycles
                    {where_clause}
                    GROUP BY action_name
                    ORDER BY count DESC
                """,
                    params,
                )
                action_rows = cursor.fetchall()
                action_counts = {r["action_name"]: r["count"] for r in action_rows}
                top_actions = [r["action_name"] for r in action_rows[:5]]

                # Calculate cycles per hour
                cycles_per_hour = 0.0
                if total > 0:
                    cursor.execute(
                        f"""
                        SELECT MIN(timestamp) as first_cycle
                        FROM cycles
                        {where_clause}
                    """,
                        params,
                    )
                    first_row = cursor.fetchone()
                    if first_row["first_cycle"] and row["last_cycle"]:
                        first_time = datetime.fromisoformat(
                            first_row["first_cycle"].replace("Z", "+00:00")
                        )
                        last_time = datetime.fromisoformat(row["last_cycle"].replace("Z", "+00:00"))
                        hours_diff = (last_time - first_time).total_seconds() / 3600
                        if hours_diff > 0:
                            cycles_per_hour = total / hours_diff

                return CycleStats(
                    total_cycles=total,
                    successful_cycles=successful,
                    failed_cycles=failed,
                    success_rate=success_rate,
                    avg_duration_ms=row["avg_duration"] or 0.0,
                    total_rewards=row["total_rewards"] or 0.0,
                    avg_reward=row["avg_reward"] or 0.0,
                    action_counts=action_counts,
                    top_actions=top_actions,
                    cycles_per_hour=cycles_per_hour,
                    last_cycle_time=row["last_cycle"],
                )

        except Exception as e:
            logger.error(f"Failed to get cycle stats: {e}")
            return CycleStats()

    def cleanup_old_cycles(self, keep_count: int = MAX_CYCLES_TO_KEEP) -> int:
        """Remove old cycles beyond the keep count.

        Args:
            keep_count: Number of recent cycles to keep

        Returns:
            Number of cycles deleted
        """
        try:
            with self._db_lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # Get count of cycles to delete
                    cursor.execute("SELECT COUNT(*) FROM cycles")
                    total = cursor.fetchone()[0]

                    if total <= keep_count:
                        return 0

                    # Delete oldest cycles
                    cursor.execute(
                        """
                        DELETE FROM cycles WHERE cycle_id IN (
                            SELECT cycle_id FROM cycles
                            ORDER BY timestamp ASC
                            LIMIT ?
                        )
                    """,
                        (total - keep_count,),
                    )

                    deleted = cursor.rowcount
                    conn.commit()

                    logger.info(f"Cleaned up {deleted} old cycles")
                    return deleted

        except Exception as e:
            logger.error(f"Failed to cleanup old cycles: {e}")
            return 0


# Global instance accessor
_cycle_logger: Optional[CycleLogger] = None


def get_cycle_logger(db_path: Optional[Path] = None) -> CycleLogger:
    """Get or create the global CycleLogger instance.

    Args:
        db_path: Optional path for the database

    Returns:
        CycleLogger instance
    """
    global _cycle_logger
    if _cycle_logger is None:
        _cycle_logger = CycleLogger(db_path)
    return _cycle_logger


def create_cycle_log(
    state: str,
    recent_actions: List[str],
    action: str,
    reasoning: Optional[str] = None,
) -> CycleLog:
    """Helper to create a new CycleLog with default values.

    Args:
        state: Current agent state
        recent_actions: List of recent action names
        action: Chosen action name
        reasoning: Optional reasoning for the action

    Returns:
        New CycleLog instance
    """
    cycle_logger = get_cycle_logger()
    return CycleLog(
        cycle_id=cycle_logger.generate_cycle_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        planning_input_state=state,
        planning_input_recent_actions=recent_actions,
        planning_output_action=action,
        planning_output_reasoning=reasoning,
        action_name=action,
    )
