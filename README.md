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

### What is this?
MCP Eval Harness is a lightweight evaluation suite that lets solo AI developers automate regression checks for their MCP-compatible agents. By writing test cases in simple markdown files, you can catch prompt, tool, or model drift early and ship updates with confidence.  
```
$ mcp-eval run tests/agent_flow.md
✔ Test Suite: agent_flow.md
  • Prompt: Summarize article → PASS (diff: none, cost: $0.0012)
  • Prompt: Extract entities → FAIL (diff: missing "Acme Corp", cost: $0.0008)
```
### Problem
Autonomous agents break silently when prompts, tools, or models change. Solo developers lack lightweight eval frameworks that fit into their existing workflows--existing solutions assume dedicated ML engineers, custom benchmarks, and ongoing tuning bandwidth. Developers resort to manual spot-checks or avoid shipping agent updates due to regression fear, slowing iteration velocity.

### Features
| Feature | Description |
|---------|-------------|
| Markdown Test Case Definition | Write tests as markdown with YAML frontmatter for metadata, supporting multi-turn prompts and varied expectation types (exact, regex, semantic). |
| MCP Protocol Execution | Connect via WebSocket or stdio to any MCP agent, execute prompts, capture tool calls, resources, and full interaction traces. |
| Intelligent Result Comparison | Compare outputs using unified diffs, regex matching, semantic similarity, or custom Python functions, with confidence scoring. |
| Cost & Performance Tracking | Track token usage, API costs, latency, and success rates; generate cost delta reports between runs. |
| Parallel Test Execution | Run tests concurrently with configurable limits to speed up large suites without overwhelming the agent. |
| Result Storage & History | Save runs to local SQLite or filesystem, view diffs over time, and export CSV/JSON for external analysis. |

### Quick Start
1. Clone the repository:  
   ```bash
   git clone https://github.com/m2ai-portfolio/mcp-eval-harness.git
   cd mcp-eval-harness
   ```
2. Install the package in editable mode:  
   ```bash
   pip install -e .
   ```
3. Create a simple test case (e.g., `tests/sample.md`):  
   ```markdown
   ---
   name: Basic Echo
   ---
   Prompt: Say hello
   Expected: Hello
   ```
4. Run the test suite against your MCP agent:  
   ```bash
   mcp-eval run --agent ws://localhost:8000/tests
   ```

### Examples
**Basic Test Run**  
Run a single markdown test file and view a concise summary.  
```
$ mcp-eval run tests/echo_test.md
✔ Test Suite: echo_test.md
  • Prompt: Echo "hello world" → PASS (diff: none, cost: $0.0004)
```
**Parallel Execution with Custom Config**  
Execute a suite with increased concurrency and a configuration file.  
```
$ mcp-eval run --parallel 8 --config mcp-eval.yaml tests/
[========================================] 12/12 00:03
✔ Test Suite: tests/
  • Passed: 10, Failed: 2
  • Total cost: $0.0452
```
**Serving Results via MCP Server**  
Start the optional MCP server to query historical test data programmatically.  
```
$ mcp-eval server --port 8080
[INFO] MCP Eval server listening on ws://0.0.0.0:8080
# In another terminal:
$ curl -X POST http://localhost:8080/query -d '{"suite":"regression"}'
{"history": [...], "trends": {"cost_delta": -0.002, "pass_rate": 0.92}}
```

### File Structure
```
MCP Eval Harness for Solo Devs/
  src/                  # Core source code
    mcp_eval/
      cli.py            # CLI entry point
      config.py         # Configuration handling
      models.py         # Data models for test cases and results
      parser/           # Markdown and YAML parsing
      executor/         # MCP client and test execution
      comparison/       # Result comparison strategies
      reporting/        # Console, JSON, CSV, regression reports
      storage/          # Filesystem and SQLite storage
      server/           # Optional MCP server for result serving
      __main__.py       # Module execution
  tests/                # Unit and integration tests
    unit/
    integration/
  pyproject.toml        # Project metadata and dependencies
  README.md
```

### Tech Stack
| Technology | Purpose |
|------------|---------|
| Python 3.10+ | Core runtime with async/await |
| Click | CLI framework and command parsing |
| asyncio | Asynchronous execution for concurrent tests |
| pydantic | Data validation and serialization |
| pytest | Test framework for unit/integration tests |
| aiohttp | HTTP/WebSocket client for MCP communication |
| rich | Terminal output formatting and progress bars |
| difflib | Text comparison and unified diff generation |
| yaml | Configuration file parsing |
| markdown | Parsing markdown test case files |
| jsonschema | Validation of MCP protocol messages |
| sqlite3 | Local storage for test history and caching |

### Contributing
Fork the repository, make your changes, run the test suite, and submit a pull request. Please follow the existing code style.

### License
MIT

### Author
```
Matthew Snow -- [M2AI](https://m2ai.co) | [@m2ai-portfolio](https://github.com/m2ai-portfolio)