"""Command-line interface for MCP Eval Harness."""

import click
import json
import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from .parser import parse_test_case, parse_test_suite
from .parser.yaml_validator import YAMLValidationError
from .parser.markdown import MarkdownParseError
from .config import load_config, ConfigError
from .executor import MCPClient, TestRunner, ParallelExecutor
from .comparison import compare_result
from .models import Expectation, ExpectationType
from .storage.sqlite import SQLiteStore
from .reporting import RegressionDetector, BaselineManager, ConsoleReporter

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """MCP Eval Harness - A testing framework for MCP servers."""
    pass


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def parse(file: str, output_json: bool):
    """
    Parse and display a test case file.

    FILE: Path to markdown test case file
    """
    try:
        test_case = parse_test_case(file)

        if output_json:
            # Output as JSON
            console.print(json.dumps(test_case.model_dump(), indent=2, default=str))
        else:
            # Pretty print with Rich
            console.print(Panel(f"[bold cyan]Test Case: {test_case.metadata.name}[/bold cyan]"))

            # Metadata
            console.print("\n[bold]Metadata:[/bold]")
            meta_table = Table(show_header=False, box=None)
            meta_table.add_column("Key", style="cyan")
            meta_table.add_column("Value")

            meta_table.add_row("Name", test_case.metadata.name)
            if test_case.metadata.description:
                meta_table.add_row("Description", test_case.metadata.description)
            meta_table.add_row("Tags", ", ".join(test_case.metadata.tags) or "none")
            meta_table.add_row("Timeout", f"{test_case.metadata.timeout}s")
            meta_table.add_row("Retries", str(test_case.metadata.retries))
            meta_table.add_row("Critical", str(test_case.metadata.critical))
            if test_case.metadata.cost_threshold:
                meta_table.add_row("Cost Threshold", f"${test_case.metadata.cost_threshold}")

            console.print(meta_table)

            # Conversation
            console.print(f"\n[bold]Conversation ({len(test_case.conversation)} turns):[/bold]")
            for i, turn in enumerate(test_case.conversation, 1):
                role_color = "green" if turn.role == "user" else "blue"
                console.print(f"\n[{role_color}]Turn {i} ({turn.role}):[/{role_color}]")
                console.print(Panel(turn.content, border_style=role_color))

            # Expectations
            if test_case.expectations:
                console.print(f"\n[bold]Expectations ({len(test_case.expectations)}):[/bold]")
                for i, exp in enumerate(test_case.expectations, 1):
                    console.print(f"\n[yellow]Expectation {i} ({exp.type.value}):[/yellow]")
                    exp_text = exp.value
                    if exp.threshold:
                        exp_text += f"\n[dim](threshold: {exp.threshold})[/dim]"
                    console.print(Panel(exp_text, border_style="yellow"))

            # Setup/Teardown
            if test_case.setup_commands:
                console.print(f"\n[bold]Setup Commands ({len(test_case.setup_commands)}):[/bold]")
                for cmd in test_case.setup_commands:
                    console.print(f"  [cyan]$ {cmd}[/cyan]")

            if test_case.teardown_commands:
                console.print(f"\n[bold]Teardown Commands ({len(test_case.teardown_commands)}):[/bold]")
                for cmd in test_case.teardown_commands:
                    console.print(f"  [cyan]$ {cmd}[/cyan]")

            console.print(f"\n[green]✓ Successfully parsed test case from {file}[/green]")

    except (YAMLValidationError, MarkdownParseError) as e:
        console.print(f"[red]✗ Parse error:[/red] {str(e)}", style="bold")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]✗ Unexpected error:[/red] {str(e)}", style="bold")
        raise click.Abort()


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--verbose", "-v", is_flag=True, help="Show detailed validation results")
def validate(directory: str, verbose: bool):
    """
    Validate all test cases in a directory.

    DIRECTORY: Path to directory containing test markdown files
    """
    try:
        test_cases = []
        errors = []

        test_dir = Path(directory)
        md_files = list(test_dir.glob("*.md"))

        if not md_files:
            console.print(f"[yellow]No markdown files found in {directory}[/yellow]")
            return

        console.print(f"[cyan]Validating {len(md_files)} test files...[/cyan]\n")

        for md_file in md_files:
            try:
                test_case = parse_test_case(str(md_file))
                test_cases.append((md_file.name, test_case))
                if verbose:
                    console.print(f"[green]✓ {md_file.name}[/green]")
            except (YAMLValidationError, MarkdownParseError) as e:
                errors.append((md_file.name, str(e)))
                console.print(f"[red]✗ {md_file.name}[/red]")
                if verbose:
                    console.print(f"  [dim]{str(e)}[/dim]")

        # Summary
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Valid: [green]{len(test_cases)}[/green]")
        console.print(f"  Invalid: [red]{len(errors)}[/red]")

        if errors and not verbose:
            console.print("\n[yellow]Run with --verbose to see error details[/yellow]")

        if errors:
            raise click.Abort()

    except Exception as e:
        console.print(f"[red]✗ Unexpected error:[/red] {str(e)}", style="bold")
        raise click.Abort()


@cli.command()
@click.option("--config", "-c", default="./mcp-eval.yaml", help="Path to config file")
def show_config(config: str):
    """
    Display current configuration.
    """
    try:
        cfg = load_config(config)
        console.print(Panel("[bold cyan]MCP Eval Configuration[/bold cyan]"))
        console.print(json.dumps(cfg.model_dump(), indent=2, default=str))
    except ConfigError as e:
        console.print(f"[red]✗ Config error:[/red] {str(e)}", style="bold")
        raise click.Abort()


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--config", "-c", default="./mcp-eval.yaml", help="Path to config file")
@click.option("--parallel", "-p", is_flag=True, help="Run tests in parallel")
@click.option("--parallel-limit", type=int, help="Override parallel test limit")
@click.option("--timeout", type=int, help="Override default timeout (seconds)")
@click.option("--output", "-o", help="Output directory for results")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def run(path: str, config: str, parallel: bool, parallel_limit: int, timeout: int, output: str, output_json: bool):
    """
    Run tests against an MCP agent.

    PATH: Path to test file or directory
    """
    try:
        # Load configuration
        cfg = load_config(config)

        # Apply CLI overrides
        if parallel_limit:
            cfg.parallel_tests = parallel_limit
        if timeout:
            cfg.default_timeout = timeout
        if output:
            cfg.output_directory = output

        # Collect test cases
        test_path = Path(path)
        test_cases = []

        if test_path.is_file():
            if test_path.suffix == ".md":
                test_case = parse_test_case(str(test_path))
                test_cases.append((test_case, str(test_path)))
        elif test_path.is_dir():
            md_files = list(test_path.glob("**/*.md"))
            for md_file in md_files:
                try:
                    test_case = parse_test_case(str(md_file))
                    test_cases.append((test_case, str(md_file)))
                except (YAMLValidationError, MarkdownParseError) as e:
                    console.print(f"[yellow]⚠ Skipping {md_file.name}: {str(e)}[/yellow]")

        if not test_cases:
            console.print("[yellow]No valid test cases found[/yellow]")
            return

        console.print(f"[cyan]Running {len(test_cases)} test(s)...[/cyan]\n")

        # Create client in mock mode for now
        client = MCPClient(cfg, mock_mode=True, mock_responses={
            "default": {
                "content": "This is a mock response from the agent.",
                "tool_calls": [],
                "resources": [],
                "tokens": {"prompt": 15, "completion": 25, "total": 40}
            }
        })

        # Run tests
        if parallel and cfg.parallel_tests > 1:
            runner = TestRunner(cfg, client)
            executor = ParallelExecutor(cfg, runner)
            result = asyncio.run(executor.execute_suite(test_cases))

            if output_json:
                console.print(json.dumps(result.model_dump(), indent=2, default=str))
            else:
                # Display results
                console.print(Panel(f"[bold cyan]Test Suite Results[/bold cyan]"))

                results_table = Table(show_header=True)
                results_table.add_column("Test", style="cyan")
                results_table.add_column("Status")
                results_table.add_column("Duration", justify="right")
                results_table.add_column("Cost", justify="right")

                for test_result in result.test_results:
                    status_color = "green" if test_result.status == "passed" else "red"
                    duration = f"{test_result.execution_time:.2f}s"
                    cost = f"${test_result.performance.estimated_cost_usd:.6f}" if test_result.performance else "N/A"

                    results_table.add_row(
                        test_result.test_name,
                        f"[{status_color}]{test_result.status}[/{status_color}]",
                        duration,
                        cost
                    )

                console.print(results_table)
                console.print(f"\n[bold]Summary:[/bold]")
                console.print(f"  Total: {result.total_tests}")
                console.print(f"  Passed: [green]{result.passed}[/green]")
                console.print(f"  Failed: [red]{result.failed}[/red]")
                console.print(f"  Errors: [red]{result.errors}[/red]")
                console.print(f"  Duration: {result.total_duration:.2f}s")
                if result.total_cost:
                    console.print(f"  Total Cost: ${result.total_cost:.6f}")
        else:
            # Run sequentially
            runner = TestRunner(cfg, client)
            results = []

            for test_case, test_path in test_cases:
                console.print(f"[cyan]Running: {test_case.metadata.name}[/cyan]")
                result = asyncio.run(runner.run_test_with_timeout(test_case, test_path=test_path))
                results.append(result)

                status_color = "green" if result.status == "passed" else "red"
                console.print(f"  Status: [{status_color}]{result.status}[/{status_color}]")
                if result.error_message:
                    console.print(f"  Error: [red]{result.error_message}[/red]")
                console.print()

            # Summary
            passed = sum(1 for r in results if r.status == "passed")
            failed = sum(1 for r in results if r.status == "failed")
            errors = sum(1 for r in results if r.status == "error")

            console.print(f"\n[bold]Summary:[/bold]")
            console.print(f"  Total: {len(results)}")
            console.print(f"  Passed: [green]{passed}[/green]")
            console.print(f"  Failed: [red]{failed}[/red]")
            console.print(f"  Errors: [red]{errors}[/red]")

    except (YAMLValidationError, MarkdownParseError) as e:
        console.print(f"[red]✗ Parse error:[/red] {str(e)}", style="bold")
        raise click.Abort()
    except ConfigError as e:
        console.print(f"[red]✗ Config error:[/red] {str(e)}", style="bold")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]✗ Unexpected error:[/red] {str(e)}", style="bold")
        import traceback
        console.print(traceback.format_exc())
        raise click.Abort()


@cli.command()
@click.option("--actual", required=True, help="Actual output to compare")
@click.option("--expected", required=True, help="Expected output or pattern")
@click.option("--type", "comparison_type", type=click.Choice(['exact', 'regex', 'semantic', 'custom']), default='exact', help="Comparison type")
@click.option("--threshold", type=float, help="Threshold for semantic comparison (0.0-1.0)")
@click.option("--custom-function", help="Custom Python evaluation function")
def compare(actual: str, expected: str, comparison_type: str, threshold: float, custom_function: str):
    """
    Compare actual output against expected using different strategies.

    Examples:
        mcp-eval compare --actual "Hello, World" --expected "Hello, World" --type exact
        mcp-eval compare --actual "Hello, World" --expected "Hello, \\w+" --type regex
        mcp-eval compare --actual "The cat sat" --expected "A cat was sitting" --type semantic --threshold 0.5
        mcp-eval compare --actual "Hello World" --expected "test" --type custom --custom-function "len(actual) > 5"
    """
    try:
        # Create expectation
        exp_type = ExpectationType(comparison_type)
        expectation = Expectation(
            type=exp_type,
            value=expected,
            threshold=threshold,
            custom_function=custom_function
        )

        # Perform comparison
        result = compare_result(actual, expectation)

        # Display results
        console.print(Panel(f"[bold cyan]Comparison Result: {comparison_type.upper()}[/bold cyan]"))

        status_color = "green" if result.passed else "red"
        status_symbol = "✓" if result.passed else "✗"

        console.print(f"\n[bold]Status:[/bold] [{status_color}]{status_symbol} {'PASS' if result.passed else 'FAIL'}[/{status_color}]")

        if result.score is not None:
            console.print(f"[bold]Score:[/bold] {result.score:.2%}")

        console.print(f"\n[bold]Expected:[/bold]")
        console.print(Panel(expected, border_style="yellow"))

        console.print(f"[bold]Actual:[/bold]")
        console.print(Panel(actual, border_style="cyan"))

        if result.details:
            console.print(f"\n[bold]Details:[/bold]")
            console.print(Panel(result.details, border_style="dim"))

    except Exception as e:
        console.print(f"[red]✗ Comparison error:[/red] {str(e)}", style="bold")
        import traceback
        console.print(traceback.format_exc())
        raise click.Abort()


@cli.group()
def baseline():
    """Manage baseline test results for regression detection."""
    pass


@baseline.command("save")
@click.argument("suite_id", type=int, required=False)
@click.option("--label", help="Optional label for this baseline")
@click.option("--db", default="./eval-cache.db", help="Path to SQLite database")
def baseline_save(suite_id: int, label: str, db: str):
    """
    Save a test suite result as a baseline.

    SUITE_ID: Database ID of the test suite result (uses latest if not specified)
    """
    try:
        store = SQLiteStore(db)
        manager = BaselineManager(store)

        if suite_id:
            result = store.get_suite_result(suite_id)
            if not result:
                console.print(f"[red]✗ Suite result with ID {suite_id} not found[/red]")
                raise click.Abort()
        else:
            # Get latest result
            suites = store.list_suites(limit=1)
            if not suites:
                console.print("[yellow]No test results found in database[/yellow]")
                return
            suite_id = suites[0]["id"]
            result = store.get_suite_result(suite_id)

        saved_id = manager.save_baseline(result, label=label)
        console.print(f"[green]✓ Saved baseline for {result.suite_name} (ID: {saved_id})[/green]")
        if label:
            console.print(f"  Label: {label}")
        if result.git_commit:
            console.print(f"  Commit: {result.git_commit[:8]}")

    except Exception as e:
        console.print(f"[red]✗ Error saving baseline:[/red] {str(e)}", style="bold")
        raise click.Abort()


@baseline.command("list")
@click.option("--suite", help="Filter by suite name")
@click.option("--limit", type=int, default=10, help="Maximum results to show")
@click.option("--db", default="./eval-cache.db", help="Path to SQLite database")
def baseline_list(suite: str, limit: int, db: str):
    """
    List available baseline test results.
    """
    try:
        store = SQLiteStore(db)
        manager = BaselineManager(store)

        baselines = manager.list_baselines(suite_name=suite, limit=limit)

        if not baselines:
            console.print("[yellow]No baselines found[/yellow]")
            return

        console.print(Panel(f"[bold cyan]Available Baselines[/bold cyan]", border_style="cyan"))

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("ID", justify="right")
        table.add_column("Suite")
        table.add_column("Timestamp")
        table.add_column("Tests", justify="right")
        table.add_column("Passed", justify="right")
        table.add_column("Cost", justify="right")

        for baseline in baselines:
            timestamp = baseline.get("timestamp", "N/A")
            if len(timestamp) > 19:
                timestamp = timestamp[:19]

            table.add_row(
                str(baseline.get("id", "N/A")),
                baseline.get("suite_name", "N/A"),
                timestamp,
                str(baseline.get("total_tests", 0)),
                f"[green]{baseline.get('passed', 0)}[/green]",
                f"${baseline.get('total_cost', 0):.6f}" if baseline.get('total_cost') else "N/A"
            )

        console.print(table)
        console.print(f"\nShowing {len(baselines)} baseline(s)")

    except Exception as e:
        console.print(f"[red]✗ Error listing baselines:[/red] {str(e)}", style="bold")
        raise click.Abort()


@cli.command()
@click.argument("current_id", type=int)
@click.argument("baseline_id", type=int, required=False)
@click.option("--db", default="./eval-cache.db", help="Path to SQLite database")
@click.option("--config", "-c", default="./mcp-eval.yaml", help="Path to config file")
def regression(current_id: int, baseline_id: int, db: str, config: str):
    """
    Compare test results and detect regressions.

    CURRENT_ID: Database ID of current test suite result
    BASELINE_ID: Database ID of baseline result (uses latest if not specified)
    """
    try:
        store = SQLiteStore(db)
        cfg = None
        try:
            cfg = load_config(config)
        except ConfigError:
            pass

        # Get current result
        current = store.get_suite_result(current_id)
        if not current:
            console.print(f"[red]✗ Current result with ID {current_id} not found[/red]")
            raise click.Abort()

        # Get baseline result
        if baseline_id:
            baseline = store.get_suite_result(baseline_id)
            if not baseline:
                console.print(f"[red]✗ Baseline result with ID {baseline_id} not found[/red]")
                raise click.Abort()
        else:
            manager = BaselineManager(store, config=cfg)
            baseline = manager.get_baseline(current.suite_name)
            if not baseline:
                console.print(f"[red]✗ No baseline found for suite '{current.suite_name}'[/red]")
                raise click.Abort()

        # Run regression detection
        detector = RegressionDetector(config=cfg)
        has_regression, issues = detector.detect_regressions(baseline, current)

        # Display report
        reporter = ConsoleReporter(console)
        reporter.print_regression_report(baseline, current, issues)

        # Show text report for CI logs
        text_report = detector.generate_report(baseline, current, issues)
        console.print("\n[dim]Text Report (for CI logs):[/dim]")
        console.print(Panel(text_report, border_style="dim"))

        # Exit with appropriate code
        exit_code = detector.get_exit_code(issues)
        if exit_code != 0:
            console.print(f"\n[red]Exiting with code {exit_code} due to regressions[/red]")
            sys.exit(exit_code)

    except Exception as e:
        console.print(f"[red]✗ Error during regression detection:[/red] {str(e)}", style="bold")
        import traceback
        console.print(traceback.format_exc())
        raise click.Abort()


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--config", "-c", default="./mcp-eval.yaml", help="Path to config file")
@click.option("--db", default="./eval-cache.db", help="Path to SQLite database")
@click.option("--timeout", type=int, help="Override default timeout (seconds)")
def ci_run(path: str, config: str, db: str, timeout: int):
    """
    Run tests in CI mode with regression detection.

    Runs tests, compares against baseline, and exits with code 1 if regressions detected.

    PATH: Path to test file or directory
    """
    try:
        # Load configuration
        cfg = load_config(config)

        if timeout:
            cfg.default_timeout = timeout

        # Initialize storage and manager
        store = SQLiteStore(db)
        manager = BaselineManager(store, config=cfg)
        detector = RegressionDetector(config=cfg)

        # Collect test cases
        test_path = Path(path)
        test_cases = []

        if test_path.is_file():
            if test_path.suffix == ".md":
                test_case = parse_test_case(str(test_path))
                test_cases.append((test_case, str(test_path)))
        elif test_path.is_dir():
            md_files = list(test_path.glob("**/*.md"))
            for md_file in md_files:
                try:
                    test_case = parse_test_case(str(md_file))
                    test_cases.append((test_case, str(md_file)))
                except (YAMLValidationError, MarkdownParseError) as e:
                    console.print(f"[yellow]⚠ Skipping {md_file.name}: {str(e)}[/yellow]")

        if not test_cases:
            console.print("[yellow]No valid test cases found[/yellow]")
            sys.exit(1)

        console.print(f"[cyan]Running {len(test_cases)} test(s) in CI mode...[/cyan]\n")

        # Create client in mock mode for now
        client = MCPClient(cfg, mock_mode=True, mock_responses={
            "default": {
                "content": "This is a mock response from the agent.",
                "tool_calls": [],
                "resources": [],
                "tokens": {"prompt": 15, "completion": 25, "total": 40}
            }
        })

        # Run tests
        runner = TestRunner(cfg, client)
        executor = ParallelExecutor(cfg, runner)
        result = asyncio.run(executor.execute_suite(test_cases))

        # Add git commit
        result.git_commit = detector.get_git_commit()

        # Save result
        suite_id = store.save_suite_result(result)
        console.print(f"[green]✓ Saved test results (ID: {suite_id})[/green]\n")

        # Get baseline and compare
        baseline = manager.get_baseline(result.suite_name)
        if baseline:
            console.print("[cyan]Comparing against baseline...[/cyan]\n")
            has_regression, issues = detector.detect_regressions(baseline, result)

            # Mark regression in result
            result.regression_detected = has_regression
            result.baseline_commit = baseline.git_commit

            # Display report
            reporter = ConsoleReporter(console)
            reporter.print_regression_report(baseline, result, issues)

            # Exit with appropriate code
            exit_code = detector.get_exit_code(issues)
            if exit_code != 0:
                console.print(f"\n[red]CI FAILURE: Regressions detected[/red]")
                sys.exit(1)
            else:
                console.print(f"\n[green]CI SUCCESS: No regressions detected[/green]")
                sys.exit(0)
        else:
            console.print("[yellow]No baseline found for comparison[/yellow]")
            console.print("[yellow]This result will be used as the baseline for future runs[/yellow]")

            # Display basic results
            console.print(f"\n[bold]Results:[/bold]")
            console.print(f"  Total: {result.total_tests}")
            console.print(f"  Passed: [green]{result.passed}[/green]")
            console.print(f"  Failed: [red]{result.failed}[/red]")
            console.print(f"  Errors: [red]{result.errors}[/red]")

            # Exit based on test results
            if result.failed > 0 or result.errors > 0:
                console.print("\n[red]CI FAILURE: Tests failed[/red]")
                sys.exit(1)
            else:
                console.print("\n[green]CI SUCCESS: All tests passed[/green]")
                sys.exit(0)

    except (YAMLValidationError, MarkdownParseError) as e:
        console.print(f"[red]✗ Parse error:[/red] {str(e)}", style="bold")
        sys.exit(1)
    except ConfigError as e:
        console.print(f"[red]✗ Config error:[/red] {str(e)}", style="bold")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Unexpected error:[/red] {str(e)}", style="bold")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    cli()
