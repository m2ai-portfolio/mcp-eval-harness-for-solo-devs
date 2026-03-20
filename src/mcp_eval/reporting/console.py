"""Rich terminal output for test results and cost reports."""

from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from ..models import TestResult, TestSuiteResult


class ConsoleReporter:
    """Rich-formatted console output for test results and cost reports."""

    def __init__(self, console: Console = None):
        """
        Initialize console reporter.

        Args:
            console: Optional Rich Console instance (creates new one if None)
        """
        self.console = console or Console()

    def print_test_result(self, result: TestResult):
        """
        Print a single test result with rich formatting.

        Args:
            result: Test result to display
        """
        # Status indicator
        if result.status == "passed":
            status_text = Text("✓ PASSED", style="bold green")
        elif result.status == "failed":
            status_text = Text("✗ FAILED", style="bold red")
        elif result.status == "error":
            status_text = Text("✗ ERROR", style="bold red")
        else:
            status_text = Text("⊘ SKIPPED", style="bold yellow")

        self.console.print(Panel(
            f"[bold cyan]{result.test_name}[/bold cyan]\n{status_text}",
            border_style="cyan" if result.status == "passed" else "red"
        ))

        # Performance metrics
        if result.performance:
            perf = result.performance
            self.console.print(f"  Duration: {result.execution_time:.3f}s")
            self.console.print(f"  Response time: {perf.response_time_ms}ms")
            self.console.print(f"  Tool execution: {perf.tool_execution_time_ms}ms")
            self.console.print(f"  Tokens: {perf.token_usage.prompt_tokens} prompt + "
                             f"{perf.token_usage.completion_tokens} completion = "
                             f"{perf.token_usage.total_tokens} total")
            self.console.print(f"  Cost: ${perf.estimated_cost_usd:.6f}")

        # Error message if present
        if result.error_message:
            self.console.print(f"  [red]Error: {result.error_message}[/red]")

        # Comparison results
        if result.comparison_results:
            self.console.print(f"\n  Comparisons:")
            for comp in result.comparison_results:
                comp_status = "✓" if comp.passed else "✗"
                comp_color = "green" if comp.passed else "red"
                self.console.print(f"    [{comp_color}]{comp_status} {comp.expectation_type.value}[/{comp_color}]")
                if comp.score is not None:
                    self.console.print(f"      Score: {comp.score:.2%}")

        self.console.print()

    def print_suite_result(self, suite_result: TestSuiteResult):
        """
        Print test suite results with summary table.

        Args:
            suite_result: Test suite result to display
        """
        self.console.print(Panel(
            f"[bold cyan]Test Suite: {suite_result.suite_name}[/bold cyan]",
            border_style="cyan"
        ))

        # Results table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Test", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Duration", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right")

        for result in suite_result.test_results:
            # Status with color
            if result.status == "passed":
                status = "[green]✓ PASS[/green]"
            elif result.status == "failed":
                status = "[red]✗ FAIL[/red]"
            elif result.status == "error":
                status = "[red]✗ ERROR[/red]"
            else:
                status = "[yellow]⊘ SKIP[/yellow]"

            # Format metrics
            duration = f"{result.execution_time:.2f}s"

            if result.performance:
                tokens = f"{result.performance.token_usage.total_tokens}"
                cost = f"${result.performance.estimated_cost_usd:.6f}"
            else:
                tokens = "N/A"
                cost = "N/A"

            table.add_row(result.test_name, status, duration, tokens, cost)

        self.console.print(table)
        self.console.print()

    def print_cost_summary(self, suite_result: TestSuiteResult):
        """
        Print cost summary for a test suite.

        Args:
            suite_result: Test suite result to summarize
        """
        self.console.print(Panel("[bold cyan]Cost Summary[/bold cyan]", border_style="cyan"))

        # Calculate totals
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        total_cost = 0.0

        for result in suite_result.test_results:
            if result.performance:
                total_prompt_tokens += result.performance.token_usage.prompt_tokens
                total_completion_tokens += result.performance.token_usage.completion_tokens
                total_tokens += result.performance.token_usage.total_tokens
                total_cost += result.performance.estimated_cost_usd

        # Create summary table
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Tests", str(suite_result.total_tests))
        table.add_row("Passed", f"[green]{suite_result.passed}[/green]")
        table.add_row("Failed", f"[red]{suite_result.failed}[/red]")
        table.add_row("Errors", f"[red]{suite_result.errors}[/red]")
        if suite_result.skipped > 0:
            table.add_row("Skipped", f"[yellow]{suite_result.skipped}[/yellow]")
        table.add_row("", "")  # Separator
        table.add_row("Total Duration", f"{suite_result.total_duration:.2f}s")
        table.add_row("Prompt Tokens", str(total_prompt_tokens))
        table.add_row("Completion Tokens", str(total_completion_tokens))
        table.add_row("Total Tokens", str(total_tokens))
        table.add_row("Total Cost", f"[bold]${total_cost:.6f}[/bold]")

        self.console.print(table)
        self.console.print()

    def print_performance_summary(self, suite_result: TestSuiteResult):
        """
        Print performance summary with min/avg/max metrics.

        Args:
            suite_result: Test suite result to summarize
        """
        self.console.print(Panel("[bold cyan]Performance Summary[/bold cyan]", border_style="cyan"))

        # Collect metrics
        response_times = []
        tool_times = []
        total_times = []

        for result in suite_result.test_results:
            if result.performance:
                response_times.append(result.performance.response_time_ms)
                tool_times.append(result.performance.tool_execution_time_ms)
                total_times.append(result.performance.total_time_ms)

        if not response_times:
            self.console.print("[yellow]No performance metrics available[/yellow]\n")
            return

        # Calculate stats
        def calc_stats(values: List[int]):
            if not values:
                return {"min": 0, "max": 0, "avg": 0}
            return {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values)
            }

        response_stats = calc_stats(response_times)
        tool_stats = calc_stats(tool_times)
        total_stats = calc_stats(total_times)

        # Create stats table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Min", justify="right")
        table.add_column("Avg", justify="right")
        table.add_column("Max", justify="right")

        table.add_row(
            "Response Time",
            f"{response_stats['min']}ms",
            f"{response_stats['avg']:.0f}ms",
            f"{response_stats['max']}ms"
        )
        table.add_row(
            "Tool Execution",
            f"{tool_stats['min']}ms",
            f"{tool_stats['avg']:.0f}ms",
            f"{tool_stats['max']}ms"
        )
        table.add_row(
            "Total Time",
            f"{total_stats['min']}ms",
            f"{total_stats['avg']:.0f}ms",
            f"{total_stats['max']}ms"
        )

        self.console.print(table)
        self.console.print()

    def print_cost_comparison(self, baseline: TestSuiteResult, current: TestSuiteResult):
        """
        Print cost comparison between two test runs.

        Args:
            baseline: Baseline test suite result
            current: Current test suite result
        """
        self.console.print(Panel(
            "[bold cyan]Cost Comparison: Baseline vs Current[/bold cyan]",
            border_style="cyan"
        ))

        # Calculate totals for baseline
        baseline_cost = 0.0
        baseline_tokens = 0
        baseline_time_ms = 0

        for result in baseline.test_results:
            if result.performance:
                baseline_cost += result.performance.estimated_cost_usd
                baseline_tokens += result.performance.token_usage.total_tokens
                baseline_time_ms += result.performance.total_time_ms

        # Calculate totals for current
        current_cost = 0.0
        current_tokens = 0
        current_time_ms = 0

        for result in current.test_results:
            if result.performance:
                current_cost += result.performance.estimated_cost_usd
                current_tokens += result.performance.token_usage.total_tokens
                current_time_ms += result.performance.total_time_ms

        # Calculate deltas
        cost_delta = current_cost - baseline_cost
        cost_pct = (cost_delta / baseline_cost * 100) if baseline_cost > 0 else 0
        tokens_delta = current_tokens - baseline_tokens
        tokens_pct = (tokens_delta / baseline_tokens * 100) if baseline_tokens > 0 else 0
        time_delta = current_time_ms - baseline_time_ms
        time_pct = (time_delta / baseline_time_ms * 100) if baseline_time_ms > 0 else 0

        # Create comparison table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Baseline", justify="right")
        table.add_column("Current", justify="right")
        table.add_column("Delta", justify="right")

        # Format cost delta with color
        if cost_delta > 0:
            cost_delta_str = f"[red]+${cost_delta:.6f} (+{cost_pct:.1f}%)[/red]"
        elif cost_delta < 0:
            cost_delta_str = f"[green]${cost_delta:.6f} ({cost_pct:.1f}%)[/green]"
        else:
            cost_delta_str = "$0.000000 (0.0%)"

        # Format tokens delta with color
        if tokens_delta > 0:
            tokens_delta_str = f"[red]+{tokens_delta} (+{tokens_pct:.1f}%)[/red]"
        elif tokens_delta < 0:
            tokens_delta_str = f"[green]{tokens_delta} ({tokens_pct:.1f}%)[/green]"
        else:
            tokens_delta_str = "0 (0.0%)"

        # Format time delta with color
        if time_delta > 0:
            time_delta_str = f"[red]+{time_delta}ms (+{time_pct:.1f}%)[/red]"
        elif time_delta < 0:
            time_delta_str = f"[green]{time_delta}ms ({time_pct:.1f}%)[/green]"
        else:
            time_delta_str = "0ms (0.0%)"

        table.add_row(
            "Total Cost",
            f"${baseline_cost:.6f}",
            f"${current_cost:.6f}",
            cost_delta_str
        )
        table.add_row(
            "Total Tokens",
            str(baseline_tokens),
            str(current_tokens),
            tokens_delta_str
        )
        table.add_row(
            "Total Time",
            f"{baseline_time_ms}ms",
            f"{current_time_ms}ms",
            time_delta_str
        )

        self.console.print(table)
        self.console.print()

        # Summary message
        if cost_delta > 0:
            self.console.print(f"[red]⚠ Cost increased by ${cost_delta:.6f} ({cost_pct:.1f}%)[/red]")
        elif cost_delta < 0:
            self.console.print(f"[green]✓ Cost decreased by ${abs(cost_delta):.6f} ({abs(cost_pct):.1f}%)[/green]")
        else:
            self.console.print("[yellow]Cost unchanged[/yellow]")

        self.console.print()

    def print_regression_report(self, baseline: TestSuiteResult, current: TestSuiteResult, issues: List):
        """
        Print a formatted regression report using Rich.

        Args:
            baseline: Baseline test suite results
            current: Current test suite results
            issues: List of RegressionIssue objects
        """
        from .regression import RegressionCategory

        # Determine if there's a critical regression
        has_regression = any(
            i.category in (RegressionCategory.CRITICAL, RegressionCategory.HIGH)
            for i in issues
        )

        # Header panel
        if has_regression:
            header_style = "red"
            status_text = "[bold red]REGRESSION DETECTED[/bold red]"
        else:
            header_style = "green"
            status_text = "[bold green]NO CRITICAL REGRESSIONS[/bold green]"

        self.console.print(Panel(
            f"[bold cyan]Regression Report[/bold cyan]\n{status_text}",
            border_style=header_style
        ))

        # Summary info
        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("", style="bold")
        summary_table.add_column("")

        summary_table.add_row("Total Issues", str(len(issues)))
        summary_table.add_row("Critical", str(sum(1 for i in issues if i.category == RegressionCategory.CRITICAL)))
        summary_table.add_row("High", str(sum(1 for i in issues if i.category == RegressionCategory.HIGH)))
        summary_table.add_row("Medium", str(sum(1 for i in issues if i.category == RegressionCategory.MEDIUM)))
        summary_table.add_row("Low", str(sum(1 for i in issues if i.category == RegressionCategory.LOW)))

        self.console.print(summary_table)
        self.console.print()

        # Baseline vs Current comparison
        self.console.print(Panel("[bold cyan]Baseline vs Current[/bold cyan]", border_style="cyan"))

        comparison_table = Table(show_header=True, header_style="bold cyan")
        comparison_table.add_column("Metric", style="bold")
        comparison_table.add_column("Baseline", justify="right")
        comparison_table.add_column("Current", justify="right")
        comparison_table.add_column("Status", justify="center")

        # Pass rate
        baseline_rate = baseline.passed / baseline.total_tests if baseline.total_tests > 0 else 0
        current_rate = current.passed / current.total_tests if current.total_tests > 0 else 0
        rate_status = "[green]✓[/green]" if current_rate >= baseline_rate else "[red]✗[/red]"

        comparison_table.add_row(
            "Pass Rate",
            f"{baseline.passed}/{baseline.total_tests} ({baseline_rate:.1%})",
            f"{current.passed}/{current.total_tests} ({current_rate:.1%})",
            rate_status
        )

        # Cost
        baseline_cost = baseline.total_cost or 0.0
        current_cost = current.total_cost or 0.0
        cost_status = "[green]✓[/green]" if current_cost <= baseline_cost * 1.2 else "[red]✗[/red]"

        comparison_table.add_row(
            "Total Cost",
            f"${baseline_cost:.6f}",
            f"${current_cost:.6f}",
            cost_status
        )

        # Duration
        duration_status = "[green]✓[/green]" if current.total_duration <= baseline.total_duration * 1.5 else "[yellow]⚠[/yellow]"

        comparison_table.add_row(
            "Duration",
            f"{baseline.total_duration:.2f}s",
            f"{current.total_duration:.2f}s",
            duration_status
        )

        # Commits
        comparison_table.add_row(
            "Git Commit",
            baseline.git_commit[:8] if baseline.git_commit else "unknown",
            current.git_commit[:8] if current.git_commit else "unknown",
            ""
        )

        self.console.print(comparison_table)
        self.console.print()

        # Issues table
        if issues:
            self.console.print(Panel("[bold cyan]Regression Issues[/bold cyan]", border_style="cyan"))

            issues_table = Table(show_header=True, header_style="bold cyan")
            issues_table.add_column("Severity", style="bold")
            issues_table.add_column("Test")
            issues_table.add_column("Issue")
            issues_table.add_column("Baseline → Current", justify="right")

            # Sort by severity
            severity_order = {
                RegressionCategory.CRITICAL: 0,
                RegressionCategory.HIGH: 1,
                RegressionCategory.MEDIUM: 2,
                RegressionCategory.LOW: 3
            }
            sorted_issues = sorted(issues, key=lambda i: severity_order[i.category])

            for issue in sorted_issues:
                # Color code by severity
                if issue.category == RegressionCategory.CRITICAL:
                    severity_style = "[bold red]CRITICAL[/bold red]"
                elif issue.category == RegressionCategory.HIGH:
                    severity_style = "[red]HIGH[/red]"
                elif issue.category == RegressionCategory.MEDIUM:
                    severity_style = "[yellow]MEDIUM[/yellow]"
                else:
                    severity_style = "[dim]LOW[/dim]"

                # Format values
                if issue.baseline_value and issue.current_value:
                    values = f"{issue.baseline_value} → {issue.current_value}"
                else:
                    values = "N/A"

                issues_table.add_row(
                    severity_style,
                    issue.test_name,
                    issue.description,
                    values
                )

            self.console.print(issues_table)
            self.console.print()

        # Recommendations
        self.console.print(Panel("[bold cyan]Recommendations[/bold cyan]", border_style="cyan"))
        if has_regression:
            self.console.print("[red]• Review failing tests and fix issues before merging[/red]")
            self.console.print("[red]• Check recent code changes for potential causes[/red]")
            self.console.print("[red]• Consider rolling back if critical functionality is broken[/red]")
        else:
            self.console.print("[green]• All checks passed, safe to proceed[/green]")

        self.console.print()
