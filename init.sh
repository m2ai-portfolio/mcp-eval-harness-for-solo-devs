#!/bin/bash
# MCP Eval Harness - Development Server Setup
set -e

cd "$(dirname "$0")"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install click pydantic aiohttp rich pyyaml markdown jsonschema pytest aiofiles websockets 2>/dev/null || pip install click pydantic aiohttp rich pyyaml markdown jsonschema pytest

# Create necessary directories
mkdir -p src/mcp_eval/parser src/mcp_eval/executor src/mcp_eval/comparison src/mcp_eval/reporting src/mcp_eval/storage src/mcp_eval/server
mkdir -p tests/unit tests/integration/fixtures/sample_tests tests/examples
mkdir -p eval-results screenshots docs

echo "Setup complete! Run: source venv/bin/activate && python -m mcp_eval"
