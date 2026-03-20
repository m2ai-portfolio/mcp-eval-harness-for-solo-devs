---
name: Tool Usage Test
description: Test that expects specific tool calls
tags:
  - tools
  - mcp
  - filesystem
timeout: 45
retries: 0
critical: true
cost_threshold: 0.50
---

## Prompt

List all Python files in the current directory and read the contents of setup.py.

## Setup

```bash
echo "test" > setup.py
touch test1.py test2.py
```

## Expected

<!-- type: regex -->
.*setup\.py.*test1\.py.*test2\.py.*

<!-- type: exact -->
test

## Teardown

```bash
rm -f setup.py test1.py test2.py
```
