

<p align="center">
  <img src="assets/infographic.png" alt="MCP Eval Harness for Solo Devs" width="800">
</p>

<h3 align="center">An open-source CLI tool and MCP server that provides drop-in regression testing for agent workflows. Define test cases as markdown prompts + expected outcomes, run them against any MCP-compatible agent, and get diffs, cost breakdowns, and failure traces. Designed for solo developers who need continuous eval without dedicated ML ops infrastructure.</h3>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#examples">Examples</a> &bull;
  <a href="#contributing">Contributing</a>
</p>

## What is this?
The MCP Eval Harness is a lightweight command‑line tool paired with an optional MCP server that lets solo developers test agent workflows without setting up heavyweight ML infrastructure. Test cases are written as simple Markdown files containing prompts and expected outcomes; the harness executes them against any MCP‑compatible agent and returns detailed diffs, latency measurements, token usage, and cost estimates. This enables continuous regression checking directly inside a developer’s existing edit‑test‑commit loop.

Example usage:
```
$ mcp-eval run --suite tests/basic-agent.md --agent http://localhost:8000/mcp
[INFO] Loaded 4 test cases
[RUN] Test: Basic greeting
[PASS] Exact match
[RUN] Test: Tool usage
[PASS] Tool calls matched
[SUMMARY] Passed: 4/4  •  Avg latency: 1.1s  •  Estimated cost: $0.003
```

## Problem
Autonomous agents break silently when prompts, tools, or models change. Solo developers lack lightweight eval frameworks that fit into their existing workflows -- existing solutions assume dedicated ML engineers, custom benchmarks, and ongoing tuning bandwidth. Developers resort to manual spot-checks or avoid shipping agent updates due to regression fear, slowing iteration velocity.

## Features
| Feature | Description |
|---------|-------------|
| Markdown Test Case Definition | Write tests in Markdown with YAML frontmatter for metadata, support multi‑turn conversations, and express expectations via exact match, regex, or semantic similarity. |
| MCP Protocol Execution | Connect to agents over WebSocket or stdio, send properly formatted MCP messages, capture full interaction traces including tool calls, resource accesses, and timestamps. |
| Intelligent Result Comparison | Compare outputs using exact match, regex patterns, semantic similarity scores, or custom Python functions; generate unified diffs and confidence scores for fuzzy matches. |
| Cost and Performance Tracking | Automatically extract token usage from MCP messages, compute estimated costs with configurable pricing, measure latency, and produce delta reports between runs. |
| Parallel Test Runner | Execute suites concurrently with a user‑configurable limit (default 5) using asyncio to reduce total test time. |
| Results Storage & History | Store runs locally in SQLite or export JSON; optionally serve results via an embedded MCP server for querying and trend analysis. |
| Custom Evaluation Functions | Inject Python callables to implement domain‑specific success criteria, enabling complex assertions beyond simple text matching. |
| CI/CD Friendly | Emit machine‑parseable JSON and exit codes suitable for GitHub Actions, GitLab CI, or any pipeline; include a `--fail‑fast` option for quick feedback. |

## Quick Start
1. Clone the repository:
   ```
   git clone https://github.com/m2ai-portfolio/mcp-eval-harness.git
   ```
2. Enter the project directory:
   ```
   cd mcp-eval-harness
   ```
3. Install the package in editable mode:
   ```
   pip install -e .
   ```
4. Create a minimal test case (Markdown with YAML frontmatter):
   ```
   mkdir -p tests
   cat > tests/hello.md <<'EOF'
   ---
   name: Hello World
   expectation_type: exact
   expected: Hello, World!
   ---
   # Prompt
   Return the exact greeting "Hello, World!".
   EOF
   ```
5. Run the test suite against a local MCP agent (replace the URL with your agent’s endpoint):
   ```
   mcp-eval run --suite tests/hello.md --agent http://127.0.0.1:8000/mcp
   ```
   Sample output:
   ```
   [INFO] Loaded 1 test case
   [RUN] Test: Hello World
   [PASS] Exact match
   [SUMMARY] Passed: 1/1  •  Avg latency: 0.7s  •  Estimated cost: $0.001
   ```

## Examples
**Basic regression test**
```
$ mcp-eval run --suite tests/working-agent.md
[INFO] Loaded 3 test cases
[RUN] Test: Echo
[PASS] Exact match
[RUN] Test: Add two numbers
[PASS] Exact match
[RUN] Test: List files
[PASS] Exact match
[SUMMARY] Passed: 3/3  •  Avg latency: 0.9s  •  Estimated cost: $0.002
```

**Parallel execution with baseline comparison**
```
$ mcp-eval run --suite tests/advanced/ --parallel 8 --compare-baseline runs/baseline-20260315.json
[INFO] Running 15 tests in parallel (limit 8)
[PASS] 13/15 passed, 2 failed
[COST] Baseline: $0.007, Current: $0.006, Delta: -$0.001
[FAILURES]
  - Test: TimeoutTool
    Reason: Agent did not respond within 5s
  - Test: SemanticSimilarity
    Reason: Similarity 0.58 < threshold 0.75
```

**Serve results via the built‑in MCP server**
```
$ mcp-eval server --port 9000 --results-dir eval-results
[INFO] MCP Eval server listening on ws://localhost:9000/mcp
[INFO] Serving results from ./eval-results
[INFO] Press Ctrl+C to stop
```
Then query from another terminal:
```
$ curl -X POST http://localhost:9000/query -d '{"suite":"advanced","limit":5}'
[
  {"run_id":"20260320_153054","passed":12,"failed":1,"cost":0.006},
  {"run_id":"20260320_153105","passed":13,"failed":0,"cost":0.005}
]
```

## File Structure
```
MCP Eval Harness for Solo Devs/
  assets/               # Project graphics (infographic.png)
  src/
    mcp_eval/           # Core Python package
      __init__.py
      __main__.py       # Entry point for `mcp-eval` command
      cli.py            # Click‑based command line interface
      config.py         # YAML configuration handling
      models.py         # Pydantic schemas for tests, runs, and metrics
      parser/           # Markdown and YAML parsing utilities
        __init__.py
        markdown.py
        yaml_validator.py
      executor/         # Test execution logic and MCP client
        __init__.py
        mcp_client.py   # Low‑level MCP protocol handling
        parallel.py     # Asyncio‑based concurrent runner
        test_runner.py  # Orchestrates parsing, execution, comparison
      comparison/       # Output comparison strategies
        __init__.py
        exact.py
        regex.py
        semantic.py
        custom.py
      reporting/        # Console, file, and regression report generation
        __init__.py
        console.py      # Rich‑based terminal output
        csv_export.py   # Export to CSV
        json.py         # JSON report writer
        regression.py   # Diff and trend analysis
      storage/          # Persistence layers
        __init__.py
        filesystem.py   # JSON file storage
        sqlite.py       # SQLite cache for history and metrics
      server/           # Optional MCP server for exposing results
        __init__.py
        main.py         # Server bootstrap
        handlers.py     # WebSocket message handlers
  tests/                # Test suite
    unit/               # Unit tests for internal modules
    integration/        # End‑to‑end tests with mock MCP agents
      fixtures/         # Sample test cases and expected outputs
  eval-results/         # Generated JSON test run outputs (ignored by git)
  screenshots/          # Demo images and terminal captures
  pyproject.toml        # Project metadata, dependencies, and entry points
  README.md
```

## Tech Stack
| Technology | Purpose |
|------------|---------|
| Python 3.10+ | Core runtime with async/await support |
| Click | Building the CLI interface |
| asyncio | Concurrent test execution |
| pydantic | Data validation and settings management |
| pytest | Testing framework for unit and integration tests |
| aiohttp | HTTP/WebSocket client for MCP communication |
| rich | Pretty terminal output, tables, and progress bars |
| difflib | Generating unified text diffs |
| PyYAML | Parsing configuration and frontmatter |
| markdown | Converting Markdown to internal representation |
| jsonschema | Validating MCP protocol messages |
| sqlite3 | Lightweight local storage for runs and metrics |

## Contributing
- Fork the repository and create a feature branch.
- Make your changes, adding tests when appropriate.
- Run `pytest` to ensure everything passes.
- Submit a pull request with a clear description of the work.

## License
MIT

## Author
Matthew Snow -- [M2AI](https://m2ai.co) | [@m2ai-portfolio](https://github.com/m2ai-portfolio)