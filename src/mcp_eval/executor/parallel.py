"""Parallel test execution with concurrency limits."""

import asyncio
from typing import List
from datetime import datetime, timezone
from ..models import TestCase, TestResult, TestSuiteResult, MCPEvalConfig
from .test_runner import TestRunner


class ParallelExecutor:
    """Execute multiple tests concurrently with limits."""

    def __init__(self, config: MCPEvalConfig, runner: TestRunner):
        """
        Initialize parallel executor.

        Args:
            config: MCP evaluation configuration
            runner: TestRunner instance to use for execution
        """
        self.config = config
        self.runner = runner
        self.semaphore = asyncio.Semaphore(config.parallel_tests)

    async def execute_suite(
        self, test_cases: List[tuple[TestCase, str]]
    ) -> TestSuiteResult:
        """
        Execute all test cases with concurrency limit.

        Args:
            test_cases: List of tuples (TestCase, test_path)

        Returns:
            TestSuiteResult with aggregated metrics
        """
        start_time = asyncio.get_event_loop().time()

        # Execute tests in parallel with semaphore limit
        tasks = [
            self._execute_with_limit(test_case, test_path)
            for test_case, test_path in test_cases
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert any exceptions to error TestResults
        processed_results: List[TestResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                test_case, test_path = test_cases[i]
                processed_results.append(
                    TestResult(
                        test_name=test_case.metadata.name,
                        status="error",
                        comparison_results=[],
                        performance=None,
                        error_message=f"Execution failed: {str(result)}",
                        execution_time=0.0,
                        timestamp=datetime.now(timezone.utc),
                    )
                )
            else:
                processed_results.append(result)

        end_time = asyncio.get_event_loop().time()

        # Aggregate results
        passed = sum(1 for r in processed_results if r.status == "passed")
        failed = sum(1 for r in processed_results if r.status == "failed")
        errors = sum(1 for r in processed_results if r.status == "error")
        skipped = sum(1 for r in processed_results if r.status == "skipped")

        # Calculate total cost
        total_cost = 0.0
        for result in processed_results:
            if result.performance:
                total_cost += result.performance.estimated_cost_usd

        return TestSuiteResult(
            suite_name="Test Suite",
            total_tests=len(test_cases),
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            test_results=processed_results,
            total_duration=end_time - start_time,
            total_cost=round(total_cost, 6) if total_cost > 0 else None,
            timestamp=datetime.now(timezone.utc),
        )

    async def _execute_with_limit(
        self, test_case: TestCase, test_path: str = ""
    ) -> TestResult:
        """
        Execute single test within semaphore limit.

        Args:
            test_case: Test case to execute
            test_path: Path to test file

        Returns:
            TestResult from execution
        """
        async with self.semaphore:
            return await self.runner.run_test_with_timeout(test_case, test_path=test_path)
