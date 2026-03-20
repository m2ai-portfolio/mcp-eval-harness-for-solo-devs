"""CSV export for external analysis tools."""

import csv
from pathlib import Path
from ..models import TestSuiteResult


class CSVExporter:
    """Export metrics to CSV for external analysis tools."""

    def export_test_results(self, result: TestSuiteResult, output_path: str):
        """
        Export detailed test results to CSV file.

        CSV columns: test_name, passed, response_time_ms, tool_execution_time_ms,
        total_time_ms, prompt_tokens, completion_tokens, total_tokens,
        estimated_cost_usd, timestamp

        Args:
            result: Test suite result to export
            output_path: Path to output CSV file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow([
                'test_name',
                'status',
                'passed',
                'response_time_ms',
                'tool_execution_time_ms',
                'total_time_ms',
                'execution_time_s',
                'prompt_tokens',
                'completion_tokens',
                'total_tokens',
                'estimated_cost_usd',
                'timestamp',
                'error_message',
            ])

            # Write test results
            for test_result in result.test_results:
                passed = test_result.status == "passed"

                if test_result.performance:
                    perf = test_result.performance
                    response_time = perf.response_time_ms
                    tool_time = perf.tool_execution_time_ms
                    total_time = perf.total_time_ms
                    prompt_tokens = perf.token_usage.prompt_tokens
                    completion_tokens = perf.token_usage.completion_tokens
                    total_tokens = perf.token_usage.total_tokens
                    cost = perf.estimated_cost_usd
                else:
                    response_time = 0
                    tool_time = 0
                    total_time = 0
                    prompt_tokens = 0
                    completion_tokens = 0
                    total_tokens = 0
                    cost = 0.0

                writer.writerow([
                    test_result.test_name,
                    test_result.status,
                    passed,
                    response_time,
                    tool_time,
                    total_time,
                    round(test_result.execution_time, 3),
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    cost,
                    test_result.timestamp.isoformat(),
                    test_result.error_message or '',
                ])

    def export_cost_report(self, result: TestSuiteResult, output_path: str):
        """
        Export cost-focused report to CSV file.

        CSV columns: test_name, total_tokens, estimated_cost_usd, cost_per_token

        Args:
            result: Test suite result to export
            output_path: Path to output CSV file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow([
                'test_name',
                'prompt_tokens',
                'completion_tokens',
                'total_tokens',
                'estimated_cost_usd',
                'cost_per_token',
            ])

            # Write cost data
            for test_result in result.test_results:
                if test_result.performance:
                    perf = test_result.performance
                    total_tokens = perf.token_usage.total_tokens
                    cost = perf.estimated_cost_usd
                    cost_per_token = cost / total_tokens if total_tokens > 0 else 0

                    writer.writerow([
                        test_result.test_name,
                        perf.token_usage.prompt_tokens,
                        perf.token_usage.completion_tokens,
                        total_tokens,
                        cost,
                        round(cost_per_token, 8),
                    ])

    def export_performance_report(self, result: TestSuiteResult, output_path: str):
        """
        Export performance-focused report to CSV file.

        CSV columns: test_name, response_time_ms, tool_execution_time_ms,
        total_time_ms, tokens_per_second

        Args:
            result: Test suite result to export
            output_path: Path to output CSV file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow([
                'test_name',
                'response_time_ms',
                'tool_execution_time_ms',
                'total_time_ms',
                'total_tokens',
                'tokens_per_second',
            ])

            # Write performance data
            for test_result in result.test_results:
                if test_result.performance:
                    perf = test_result.performance
                    total_time_s = perf.total_time_ms / 1000
                    tokens_per_sec = perf.token_usage.total_tokens / total_time_s if total_time_s > 0 else 0

                    writer.writerow([
                        test_result.test_name,
                        perf.response_time_ms,
                        perf.tool_execution_time_ms,
                        perf.total_time_ms,
                        perf.token_usage.total_tokens,
                        round(tokens_per_sec, 2),
                    ])
