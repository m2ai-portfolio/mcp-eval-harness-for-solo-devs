"""SQLite storage for test results and metrics."""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..models import TestSuiteResult


class SQLiteStore:
    """Store and query test results in SQLite database."""

    def __init__(self, db_path: str = "./eval-cache.db"):
        """
        Initialize SQLite store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create test_suites table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_suites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    suite_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    git_commit TEXT,
                    total_tests INTEGER NOT NULL,
                    passed INTEGER NOT NULL,
                    failed INTEGER NOT NULL,
                    errors INTEGER NOT NULL,
                    skipped INTEGER NOT NULL,
                    total_duration REAL NOT NULL,
                    total_cost REAL,
                    data TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_suite_name_timestamp
                ON test_suites(suite_name, timestamp DESC)
            """)

            conn.commit()

    def save_suite_result(self, result: TestSuiteResult) -> int:
        """
        Save test suite result to database.

        Args:
            result: Test suite result to save

        Returns:
            Database ID of saved result
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Serialize full result to JSON
            data_json = json.dumps(result.model_dump(mode='json'), default=str)

            cursor.execute("""
                INSERT INTO test_suites (
                    suite_name, timestamp, total_tests, passed, failed,
                    errors, skipped, total_duration, total_cost, data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.suite_name,
                result.timestamp.isoformat(),
                result.total_tests,
                result.passed,
                result.failed,
                result.errors,
                result.skipped,
                result.total_duration,
                result.total_cost,
                data_json,
            ))

            conn.commit()
            return cursor.lastrowid

    def get_suite_result(self, suite_id: int) -> Optional[TestSuiteResult]:
        """
        Get test suite result by ID.

        Args:
            suite_id: Database ID of the suite

        Returns:
            TestSuiteResult if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM test_suites WHERE id = ?", (suite_id,))
            row = cursor.fetchone()

            if row:
                data = json.loads(row[0])
                return TestSuiteResult(**data)

            return None

    def get_latest_baseline(self, suite_name: str) -> Optional[TestSuiteResult]:
        """
        Get the most recent test suite result for a given suite name.

        Args:
            suite_name: Name of the test suite

        Returns:
            TestSuiteResult if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT data FROM test_suites
                WHERE suite_name = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (suite_name,))
            row = cursor.fetchone()

            if row:
                data = json.loads(row[0])
                return TestSuiteResult(**data)

            return None

    def get_cost_history(self, suite_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get cost history for a test suite.

        Args:
            suite_name: Name of the test suite
            limit: Maximum number of entries to return

        Returns:
            List of cost history records
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, total_tests, total_cost, total_duration
                FROM test_suites
                WHERE suite_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (suite_name, limit))

            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "total_tests": row[2],
                    "total_cost": row[3],
                    "total_duration": row[4],
                }
                for row in rows
            ]

    def get_performance_history(self, suite_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get performance history for a test suite.

        Args:
            suite_name: Name of the test suite
            limit: Maximum number of entries to return

        Returns:
            List of performance history records
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, total_tests, total_duration, passed, failed, errors
                FROM test_suites
                WHERE suite_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (suite_name, limit))

            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "total_tests": row[2],
                    "total_duration": row[3],
                    "passed": row[4],
                    "failed": row[5],
                    "errors": row[6],
                }
                for row in rows
            ]

    def compare_runs(self, baseline_id: int, current_id: int) -> Dict[str, Any]:
        """
        Compare two test suite runs.

        Args:
            baseline_id: Database ID of baseline run
            current_id: Database ID of current run

        Returns:
            Dictionary with comparison data
        """
        baseline = self.get_suite_result(baseline_id)
        current = self.get_suite_result(current_id)

        if not baseline or not current:
            raise ValueError("One or both suite results not found")

        # Calculate baseline metrics
        baseline_cost = 0.0
        baseline_tokens = 0
        baseline_time_ms = 0

        for result in baseline.test_results:
            if result.performance:
                baseline_cost += result.performance.estimated_cost_usd
                baseline_tokens += result.performance.token_usage.total_tokens
                baseline_time_ms += result.performance.total_time_ms

        # Calculate current metrics
        current_cost = 0.0
        current_tokens = 0
        current_time_ms = 0

        for result in current.test_results:
            if result.performance:
                current_cost += result.performance.estimated_cost_usd
                current_tokens += result.performance.token_usage.total_tokens
                current_time_ms += result.performance.total_time_ms

        # Calculate deltas
        return {
            "baseline": {
                "id": baseline_id,
                "suite_name": baseline.suite_name,
                "timestamp": baseline.timestamp.isoformat(),
                "cost": baseline_cost,
                "tokens": baseline_tokens,
                "time_ms": baseline_time_ms,
            },
            "current": {
                "id": current_id,
                "suite_name": current.suite_name,
                "timestamp": current.timestamp.isoformat(),
                "cost": current_cost,
                "tokens": current_tokens,
                "time_ms": current_time_ms,
            },
            "deltas": {
                "cost": current_cost - baseline_cost,
                "cost_pct": ((current_cost - baseline_cost) / baseline_cost * 100) if baseline_cost > 0 else 0,
                "tokens": current_tokens - baseline_tokens,
                "tokens_pct": ((current_tokens - baseline_tokens) / baseline_tokens * 100) if baseline_tokens > 0 else 0,
                "time_ms": current_time_ms - baseline_time_ms,
                "time_pct": ((current_time_ms - baseline_time_ms) / baseline_time_ms * 100) if baseline_time_ms > 0 else 0,
            },
        }

    def list_suites(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List recent test suite runs.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of suite metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, suite_name, timestamp, total_tests, passed, failed, total_cost
                FROM test_suites
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "suite_name": row[1],
                    "timestamp": row[2],
                    "total_tests": row[3],
                    "passed": row[4],
                    "failed": row[5],
                    "total_cost": row[6],
                }
                for row in rows
            ]
