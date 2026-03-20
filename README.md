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

2. Define test cases as markdown files with YAML frontmatter:
   ```markdown
   ---
   name: Calculator Test
   description: Test basic arithmetic
   tags: [math, calculator]
   timeout: 30
   ---

   ## Prompt
   Calculate 2 + 2

   ## Expected
   <!-- type: exact -->
   4
   ```

3. Parse and validate test cases:
   ```bash
   mcp-eval parse tests/examples/calculator.md
   mcp-eval validate tests/examples/
   ```

4. Run tests (future feature):
   ```bash
   mcp-eval run tests/examples/
   ```

5. View results in `eval-results/` directory with diffs and cost breakdowns

## Features

### Implemented (Feature 1)
- **Markdown Test Case Parsing**: Define test cases with YAML frontmatter and markdown sections
- **YAML Validation**: Comprehensive validation with helpful error messages
- **Multi-turn Conversations**: Support for both single and multi-turn conversation definitions
- **Multiple Expectation Types**: exact, regex, semantic similarity, and custom validators
- **Template Variables**: Parameterized test cases with variable expansion
- **Setup/Teardown Commands**: Pre and post-test command execution
- **CLI Tools**: Parse and validate commands with rich terminal output

### Coming Soon
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
