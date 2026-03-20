"""Command-line interface for MCP Eval Harness."""

import click
import json
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from .parser import parse_test_case, parse_test_suite
from .parser.yaml_validator import YAMLValidationError
from .parser.markdown import MarkdownParseError
from .config import load_config, ConfigError

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


if __name__ == "__main__":
    cli()
