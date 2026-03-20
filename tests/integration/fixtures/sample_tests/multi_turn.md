---
name: Multi-turn Conversation Test
description: Test with multiple conversation turns
tags:
  - conversation
  - multi-turn
timeout: 60
retries: 1
critical: true
---

## Conversation

### User
Hello, can you help me with Python?

### Assistant
Of course! I'd be happy to help you with Python. What specific topic or problem would you like assistance with?

### User
How do I read a file in Python?

### Assistant
To read a file in Python, you can use the built-in `open()` function. Here's a simple example:

```python
with open('filename.txt', 'r') as file:
    content = file.read()
    print(content)
```

This uses a context manager (the `with` statement) which automatically closes the file when done.

## Expectations

<!-- type: semantic -->
<!-- threshold: 0.85 -->
The assistant should explain how to use the open() function to read files in Python, mention the 'with' statement for proper file handling, and provide a code example.
