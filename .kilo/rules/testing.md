# Testing

- Test public behaviour not implementation details
- Add failure cases and edge cases alongside happy path
- All async tests use pytest-asyncio
- Do not remove or weaken existing tests
- Do not mock away the behaviour being tested
- Report any test that could not be run and explain why
