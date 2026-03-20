"""JSON export for metrics and results."""

import json
from pathlib import Path
from ..models import TestSuiteResult


class JSONExporter:
    """Export metrics and results to JSON format."""

    def export_suite_result(self, result: TestSuiteResult, output_path: str):
        """
        Export full test suite result to JSON file.

        Args:
            result: Test suite result to export
            output_path: Path to output JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict using Pydantic's model_dump
        data = result.model_dump(mode='json')

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

    def export_metrics_summary(self, result: TestSuiteResult, output_path: str):
        """
        Export metrics summary (aggregated data only) to JSON file.

        Args:
            result: Test suite result to summarize
            output_path: Path to output JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Calculate aggregated metrics
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        total_cost = 0.0
        response_times = []
        tool_times = []

        for test_result in result.test_results:
            if test_result.performance:
                perf = test_result.performance
                total_prompt_tokens += perf.token_usage.prompt_tokens
                total_completion_tokens += perf.token_usage.completion_tokens
                total_tokens += perf.token_usage.total_tokens
                total_cost += perf.estimated_cost_usd
                response_times.append(perf.response_time_ms)
                tool_times.append(perf.tool_execution_time_ms)

        # Calculate stats
        def calc_stats(values):
            if not values:
                return {"min": 0, "max": 0, "avg": 0}
            return {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values)
            }

        summary = {
            "suite_name": result.suite_name,
            "timestamp": result.timestamp.isoformat(),
            "test_counts": {
                "total": result.total_tests,
                "passed": result.passed,
                "failed": result.failed,
                "errors": result.errors,
                "skipped": result.skipped,
            },
            "duration": {
                "total_seconds": result.total_duration,
            },
            "tokens": {
                "prompt": total_prompt_tokens,
                "completion": total_completion_tokens,
                "total": total_tokens,
            },
            "cost": {
                "total_usd": round(total_cost, 6),
            },
            "performance": {
                "response_time_ms": calc_stats(response_times),
                "tool_execution_time_ms": calc_stats(tool_times),
            },
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
