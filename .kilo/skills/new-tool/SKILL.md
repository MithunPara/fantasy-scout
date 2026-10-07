---
name: new-tool
description: Use when adding a new data source tool to the Fantasy Scout agent
---

# Adding a New Tool

1. Write and test the function standalone in `test_[name].py` first
2. Verify it returns a clean typed dict with consistent keys
3. Add `@tool` decorator and move to `tools/[name].py`
4. Write a complete docstring covering the args and return format for the tool

- LLM will use this to decide when to call the tool

5. Register the tool in `agent/graph.py`
6. Add a test in `tests/tools/test_[name].py`
