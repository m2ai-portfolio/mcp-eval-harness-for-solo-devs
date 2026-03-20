---
name: Template Variable Test
description: Test with template variables
tags:
  - template
timeout: 30
---

## Prompt

What is the capital of {{country}}?

## Expected

<!-- type: regex -->
The capital of {{country}} is {{capital}}\.
