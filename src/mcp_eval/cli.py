"""Command-line interface for MCP Eval Harness."""

import click
import json
import asyncio
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


if __name__ == "__main__":
    cli()
