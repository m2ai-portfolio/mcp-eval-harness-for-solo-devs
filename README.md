# MCP Eval Harness for Solo Devs

A lightweight Python CLI tool and MCP server providing regression testing for agent workflows. Allows solo developers to define test cases as markdown files, run them against any MCP-compatible agent, and get diffs, cost breakdowns, and failure traces.

## Tech Stack

- **Python 3.10+**
- **CLI Framework**: Click
- **Async Runtime**: asyncio
- **Data Validation**: pydantic
- **Testing**: pytest
- **HTTP Client**: aiohttp
- **Terminal UI**: rich
- **Database**: sqlite3

## Quick Start

1. Run the setup script to initialize your development environment:
   ```bash
   ./init.sh
   source venv/bin/activate
   ```

2. Define test cases as markdown files in the `tests/examples/` directory:
   ```markdown
   # Test Case: Calculator Agent

   ## Input
   Calculate 2 + 2

   ## Expected Output
   4
   ```

3. Run the eval harness:
   ```bash
   python -m mcp_eval run tests/examples/
   ```

4. View results in `eval-results/` directory with diffs and cost breakdowns

## Features

- **Markdown Test Cases**: Define test cases in simple markdown format with inputs and expected outputs
- **MCP Protocol Execution**: Execute tests against any MCP-compatible agent with full protocol support
- **Intelligent Comparison**: Compare agent outputs against expected results with detailed diffs
- **Cost Tracking**: Automatic cost calculation and tracking for API calls and token usage
- **Regression Detection**: Track test results over time and identify performance regressions

## Project Structure

```
src/mcp_eval/
├── parser/          # Markdown test case parser
├── executor/        # MCP agent execution engine
├── comparison/      # Output comparison and diffing
├── reporting/       # Results and cost reporting
├── storage/         # Result persistence
└── server/          # MCP server implementation

tests/
├── unit/            # Unit tests
├── integration/     # Integration tests with fixtures
└── examples/        # Sample test cases

eval-results/       # Test execution results (git-ignored)
docs/              # Documentation
```

## Development

See `init.sh` for automatic setup of the development environment, including virtual environment creation and dependency installation.
