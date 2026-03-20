"""Regression detection and analysis for test results."""

import logging
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from enum import Enum
from ..models import TestSuiteResult, TestResult, MCPEvalConfig

logger = logging.getLogger(__name__)

# Default regression thresholds
DEFAULT_THRESHOLDS = {
    "pass_rate_drop": 0.0,       # Any drop in pass rate is a regression
    "cost_increase_pct": 20.0,    # 20% cost increase threshold
    "latency_increase_pct": 50.0, # 50% latency increase threshold
    "new_failures": 0,            # Any new failure is a regression
}


class RegressionCategory(str, Enum):
    """Categories for regression severity."""
    CRITICAL = "critical"    # Previously passing test now fails
    HIGH = "high"            # Critical test regressed
    MEDIUM = "medium"        # Cost or performance significantly worse
    LOW = "low"              # Minor degradation


class RegressionIssue:
    """A single regression finding."""

    def __init__(
        self,
        category: RegressionCategory,
        test_name: str,
        description: str,
        baseline_value: Optional[str] = None,
        current_value: Optional[str] = None
    ):
        self.category = category
        self.test_name = test_name
        self.description = description
        self.baseline_value = baseline_value
        self.current_value = current_value

    def __repr__(self):
        return f"RegressionIssue(category={self.category.value}, test={self.test_name})"


class RegressionDetector:
    """Detect regressions by comparing current results against baselines."""

    def __init__(self, config: MCPEvalConfig = None, thresholds: dict = None):
        """
        Initialize regression detector.

        Args:
            config: Optional MCPEvalConfig with regression settings
            thresholds: Optional dict of threshold overrides
        """
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        if config and config.regression_thresholds:
            self.thresholds.update(config.regression_thresholds)

    def get_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception as e:
            logger.debug(f"Could not get git commit: {e}")
            return None

    def detect_regressions(
        self,
        baseline: TestSuiteResult,
        current: TestSuiteResult
    ) -> Tuple[bool, List[RegressionIssue]]:
        """
        Compare current results against baseline and detect regressions.

        Args:
            baseline: Baseline test suite results
            current: Current test suite results

        Returns:
            Tuple of (has_regression, list_of_issues)
        """
        issues = []

        # Create lookup maps
        baseline_results = {r.test_name: r for r in baseline.test_results}
        current_results = {r.test_name: r for r in current.test_results}

        # 1. Check for newly failing tests
        for name, curr in current_results.items():
            base = baseline_results.get(name)
            if base and base.status == "passed" and curr.status != "passed":
                # Check if it's a critical test
                category = RegressionCategory.CRITICAL
                issues.append(RegressionIssue(
                    category=category,
                    test_name=name,
                    description=f"Test was PASSING in baseline but now FAILS",
                    baseline_value="PASS",
                    current_value="FAIL"
                ))

        # 2. Check pass rate
        baseline_rate = baseline.passed / baseline.total_tests if baseline.total_tests > 0 else 0
        current_rate = current.passed / current.total_tests if current.total_tests > 0 else 0
        rate_drop = baseline_rate - current_rate

        if rate_drop > self.thresholds.get("pass_rate_drop", 0):
            issues.append(RegressionIssue(
                category=RegressionCategory.HIGH,
                test_name="<suite>",
                description=f"Pass rate dropped from {baseline_rate:.1%} to {current_rate:.1%}",
                baseline_value=f"{baseline_rate:.1%}",
                current_value=f"{current_rate:.1%}"
            ))

        # 3. Check cost increase
        baseline_cost = baseline.total_cost or 0.0
        current_cost = current.total_cost or 0.0

        if baseline_cost > 0:
            cost_change_pct = ((current_cost - baseline_cost) / baseline_cost) * 100
            if cost_change_pct > self.thresholds.get("cost_increase_pct", 20):
                issues.append(RegressionIssue(
                    category=RegressionCategory.MEDIUM,
                    test_name="<suite>",
                    description=f"Cost increased by {cost_change_pct:.1f}%",
                    baseline_value=f"${baseline_cost:.4f}",
                    current_value=f"${current_cost:.4f}"
                ))

        # 4. Check latency per test
        for name, curr in current_results.items():
            base = baseline_results.get(name)
            if base and base.performance and curr.performance:
                base_time = base.performance.total_time_ms
                curr_time = curr.performance.total_time_ms
                if base_time > 0:
                    latency_change = ((curr_time - base_time) / base_time) * 100
                    if latency_change > self.thresholds.get("latency_increase_pct", 50):
                        issues.append(RegressionIssue(
                            category=RegressionCategory.LOW,
                            test_name=name,
                            description=f"Latency increased by {latency_change:.1f}%",
                            baseline_value=f"{base_time}ms",
                            current_value=f"{curr_time}ms"
                        ))

        # 5. Check for missing tests (tests in baseline but not in current)
        for name in baseline_results:
            if name not in current_results:
                issues.append(RegressionIssue(
                    category=RegressionCategory.MEDIUM,
                    test_name=name,
                    description="Test exists in baseline but missing from current run"
                ))

        # Determine if there's a high-severity regression
        has_regression = any(
            i.category in (RegressionCategory.CRITICAL, RegressionCategory.HIGH)
            for i in issues
        )

        return has_regression, issues

    def generate_report(
        self,
        baseline: TestSuiteResult,
        current: TestSuiteResult,
        issues: List[RegressionIssue]
    ) -> str:
        """
        Generate a formatted regression report string.

        Args:
            baseline: Baseline test suite results
            current: Current test suite results
            issues: List of regression issues

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("REGRESSION REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Summary
        has_regression = any(
            i.category in (RegressionCategory.CRITICAL, RegressionCategory.HIGH)
            for i in issues
        )
        status = "REGRESSION DETECTED" if has_regression else "NO CRITICAL REGRESSIONS"
        lines.append(f"Status: {status}")
        lines.append(f"Total Issues: {len(issues)}")
        lines.append("")

        # Baseline info
        lines.append("Baseline:")
        lines.append(f"  Suite: {baseline.suite_name}")
        lines.append(f"  Commit: {baseline.git_commit or 'unknown'}")
        lines.append(f"  Timestamp: {baseline.timestamp.isoformat()}")
        lines.append(f"  Pass Rate: {baseline.passed}/{baseline.total_tests} ({baseline.passed/baseline.total_tests:.1%})")
        lines.append(f"  Cost: ${baseline.total_cost or 0:.6f}")
        lines.append("")

        # Current info
        lines.append("Current:")
        lines.append(f"  Suite: {current.suite_name}")
        lines.append(f"  Commit: {current.git_commit or 'unknown'}")
        lines.append(f"  Timestamp: {current.timestamp.isoformat()}")
        lines.append(f"  Pass Rate: {current.passed}/{current.total_tests} ({current.passed/current.total_tests:.1%})")
        lines.append(f"  Cost: ${current.total_cost or 0:.6f}")
        lines.append("")

        # Issues by category
        if issues:
            lines.append("Issues:")
            lines.append("")

            # Group by category
            by_category = {}
            for issue in issues:
                cat = issue.category.value
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(issue)

            # Display in order: critical, high, medium, low
            for cat in ["critical", "high", "medium", "low"]:
                if cat in by_category:
                    lines.append(f"  [{cat.upper()}]")
                    for issue in by_category[cat]:
                        lines.append(f"    - {issue.test_name}: {issue.description}")
                        if issue.baseline_value and issue.current_value:
                            lines.append(f"      Baseline: {issue.baseline_value} -> Current: {issue.current_value}")
                    lines.append("")
        else:
            lines.append("No issues detected.")
            lines.append("")

        # Recommendations
        lines.append("Recommendations:")
        if has_regression:
            lines.append("  - Review failing tests and fix issues before merging")
            lines.append("  - Check recent code changes for potential causes")
            lines.append("  - Consider rolling back if critical functionality is broken")
        else:
            lines.append("  - All checks passed, safe to proceed")
        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def get_exit_code(self, issues: List[RegressionIssue]) -> int:
        """
        Return CI/CD exit code based on issues.

        Args:
            issues: List of regression issues

        Returns:
            0 for pass, 1 for regression detected
        """
        has_critical = any(
            i.category in (RegressionCategory.CRITICAL, RegressionCategory.HIGH)
            for i in issues
        )
        return 1 if has_critical else 0


class BaselineManager:
    """Manage baseline results for regression comparison."""

    def __init__(self, store, config: MCPEvalConfig = None):
        """
        Initialize baseline manager.

        Args:
            store: Storage backend (SQLiteStore or FileSystemStore)
            config: Optional MCPEvalConfig
        """
        self.store = store
        self.config = config
        self.strategy = config.baseline_strategy if config else "main_branch"

    def save_baseline(self, result: TestSuiteResult, label: str = None):
        """
        Save current results as a baseline.

        Args:
            result: Test suite result to save as baseline
            label: Optional label for the baseline
        """
        # Add git commit if available and not already set
        if not result.git_commit:
            detector = RegressionDetector()
            result.git_commit = detector.get_git_commit()

        # Save to store
        suite_id = self.store.save_suite_result(result)
        logger.info(f"Saved baseline for {result.suite_name} with ID {suite_id}")

        if label:
            logger.info(f"Baseline labeled as: {label}")

        return suite_id

    def get_baseline(self, suite_name: str) -> Optional[TestSuiteResult]:
        """
        Get the appropriate baseline based on strategy.

        Args:
            suite_name: Name of the test suite

        Returns:
            Baseline TestSuiteResult or None if not found
        """
        # For now, just get the latest baseline
        # In a full implementation, this would check git branches, tags, etc.
        return self.store.get_latest_baseline(suite_name)

    def list_baselines(self, suite_name: str = None, limit: int = 10) -> List[dict]:
        """
        List available baselines.

        Args:
            suite_name: Optional suite name filter
            limit: Maximum number of entries to return

        Returns:
            List of baseline metadata dicts
        """
        if suite_name:
            return self.store.get_performance_history(suite_name, limit=limit)
        else:
            return self.store.list_suites(limit=limit)
