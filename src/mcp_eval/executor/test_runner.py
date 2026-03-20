"""Test execution engine for running test cases against MCP agents."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from ..models import (
    TestCase,
    TestResult,
    PerformanceMetrics,
    TokenUsage,
    ComparisonResult,
    MCPEvalConfig,
)
from .mcp_client import MCPClient


class TestRunner:
    """Executes test cases against MCP agents."""

    def __init__(self, config: MCPEvalConfig, client: Optional[MCPClient] = None):
        """
        Initialize test runner.

        Args:
            config: MCP evaluation configuration
            client: Optional pre-configured MCPClient (for testing)
        """
        self.config = config
        self.client = client

    async def run_test(self, test_case: TestCase, test_path: str = "") -> TestResult:
        """
        Execute a single test case.

        Args:
            test_case: The test case to execute
            test_path: Path to the test file (for result tracking)

        Returns:
            TestResult with execution details
        """
        start_time = time.time()
        execution_trace = []
        tool_calls_made = []
        resources_accessed = []
        error_message = None
        agent_response = ""

        try:
            # Create client if not provided
            client = self.client
            if client is None:
                client = MCPClient(self.config, mock_mode=True)

            # Run setup commands if any
            if test_case.setup_commands:
                execution_trace.append(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event": "setup_start",
                        "commands": test_case.setup_commands,
                    }
                )
                # In real implementation, would execute these commands
                execution_trace.append(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event": "setup_complete",
                    }
                )

            # Connect to agent
            async with client:
                execution_trace.append(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event": "connection_established",
                    }
                )

                # Process conversation turns
                total_prompt_tokens = 0
                total_completion_tokens = 0
                tool_execution_time_ms = 0

                for i, turn in enumerate(test_case.conversation):
                    if turn.role == "user":
                        turn_start = time.time()

                        execution_trace.append(
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "event": "prompt_sent",
                                "turn": i + 1,
                                "content": turn.content[:100] + "..."
                                if len(turn.content) > 100
                                else turn.content,
                            }
                        )

                        # Send prompt to agent
                        result = await client.send_prompt(
                            prompt=turn.content,
                            tools=None,  # Could be extracted from test case metadata
                        )

                        turn_end = time.time()

                        agent_response = result["response"]
                        tool_calls_made.extend(result["tool_calls"])
                        resources_accessed.extend(result["resources_accessed"])

                        # Update token counts
                        tokens = result["tokens"]
                        total_prompt_tokens += tokens.get("prompt", 0)
                        total_completion_tokens += tokens.get("completion", 0)

                        # Track tool execution time
                        for tool_call in result["tool_calls"]:
                            tool_execution_time_ms += tool_call.get("duration_ms", 0)

                        execution_trace.append(
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "event": "response_received",
                                "turn": i + 1,
                                "duration_ms": int((turn_end - turn_start) * 1000),
                                "tokens": tokens,
                                "tool_calls": len(result["tool_calls"]),
                            }
                        )

            # Run teardown commands if any
            if test_case.teardown_commands:
                execution_trace.append(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event": "teardown_start",
                        "commands": test_case.teardown_commands,
                    }
                )
                # In real implementation, would execute these commands
                execution_trace.append(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event": "teardown_complete",
                    }
                )

            end_time = time.time()

            # Calculate metrics
            performance = self._calculate_metrics(
                start_time=start_time,
                end_time=end_time,
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens,
                tool_execution_time_ms=tool_execution_time_ms,
            )

            # For now, create a simple comparison result (actual comparison is Feature 3)
            comparison_results = []
            if test_case.expectations:
                comparison_results.append(
                    ComparisonResult(
                        passed=True,  # Placeholder
                        expectation_type=test_case.expectations[0].type,
                        expected=test_case.expectations[0].value,
                        actual=agent_response,
                        score=1.0,
                        details="Comparison not yet implemented (Feature 3)",
                    )
                )

            return TestResult(
                test_name=test_case.metadata.name,
                status="passed" if not error_message else "error",
                comparison_results=comparison_results,
                performance=performance,
                error_message=error_message,
                execution_time=end_time - start_time,
                timestamp=datetime.now(timezone.utc),
            )

        except TimeoutError as e:
            error_message = str(e)
            execution_trace.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event": "timeout_error",
                    "error": error_message,
                }
            )
            return TestResult(
                test_name=test_case.metadata.name,
                status="error",
                comparison_results=[],
                performance=None,
                error_message=error_message,
                execution_time=time.time() - start_time,
                timestamp=datetime.now(timezone.utc),
            )

        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            execution_trace.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event": "execution_error",
                    "error": error_message,
                }
            )
            return TestResult(
                test_name=test_case.metadata.name,
                status="error",
                comparison_results=[],
                performance=None,
                error_message=error_message,
                execution_time=time.time() - start_time,
                timestamp=datetime.now(timezone.utc),
            )

    async def run_test_with_timeout(
        self, test_case: TestCase, timeout: Optional[int] = None, test_path: str = ""
    ) -> TestResult:
        """
        Execute test with timeout handling.

        Args:
            test_case: The test case to execute
            timeout: Timeout in seconds (uses test case or config default if None)
            test_path: Path to the test file

        Returns:
            TestResult with execution details
        """
        # Determine timeout value
        if timeout is None:
            timeout = test_case.metadata.timeout or self.config.default_timeout

        try:
            # Run test with timeout
            result = await asyncio.wait_for(
                self.run_test(test_case, test_path), timeout=timeout
            )
            return result

        except asyncio.TimeoutError:
            return TestResult(
                test_name=test_case.metadata.name,
                status="error",
                comparison_results=[],
                performance=None,
                error_message=f"Timeout after {timeout} seconds",
                execution_time=float(timeout),
                timestamp=datetime.now(timezone.utc),
            )

    def _calculate_metrics(
        self,
        start_time: float,
        end_time: float,
        prompt_tokens: int,
        completion_tokens: int,
        tool_execution_time_ms: int,
    ) -> PerformanceMetrics:
        """
        Calculate performance metrics from execution data.

        Args:
            start_time: Start timestamp
            end_time: End timestamp
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens used
            tool_execution_time_ms: Time spent executing tools

        Returns:
            PerformanceMetrics object
        """
        total_time_ms = int((end_time - start_time) * 1000)
        response_time_ms = total_time_ms - tool_execution_time_ms
        total_tokens = prompt_tokens + completion_tokens

        # Calculate estimated cost (simple example, would use cost_models from config)
        # Using rough GPT-4 pricing: $0.03/1K prompt tokens, $0.06/1K completion tokens
        estimated_cost_usd = (prompt_tokens * 0.03 / 1000) + (completion_tokens * 0.06 / 1000)

        return PerformanceMetrics(
            response_time_ms=max(0, response_time_ms),
            tool_execution_time_ms=tool_execution_time_ms,
            total_time_ms=total_time_ms,
            token_usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            estimated_cost_usd=round(estimated_cost_usd, 6),
        )
