# Tests Directory

- Store unit and integration tests executed with `pytest`.
- Name test files `test_*.py` and test functions `test_*`.
- Use fixtures for reusable setup; place shared fixtures in `conftest.py`.
- Avoid network calls and other flaky dependencies; use mocking where necessary.
- Run `pytest` and `pre-commit run --files <test>` before committing.
