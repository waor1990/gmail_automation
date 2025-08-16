# Testing and Development Guide

This document explains how to run tests, linting, and code formatting for the Gmail Automation project.

## Quick Start

### Install Development Dependencies

```bash
# Install all dependencies including test and linting tools
pip install -r requirements.txt
```

### Run All Checks

```bash
# On Windows (Command Prompt)
dev.bat all

# On Windows (PowerShell)
.\dev.ps1 all

# Manual commands
python -m pytest                    # Run tests
python -m flake8 src/ tests/        # Run linting
python -m black --check src/ tests/ # Check formatting
python -m mypy src/                 # Type checking
```

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=src/gmail_automation --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_config.py

# Run tests with verbose output
python -m pytest -v

# Run only unit tests (exclude integration tests)
python -m pytest -m "not integration"
```

### Test Structure

- `tests/test_config.py` - Tests for configuration handling
- `tests/test_cli.py` - Tests for CLI functionality
- `tests/test_gmail_service.py` - Tests for Gmail API service
- `tests/test_integration.py` - Integration tests (marked with `@pytest.mark.integration`)

### Coverage Reports

Test coverage reports are generated in multiple formats:

- Terminal output (with `--cov-report=term-missing`)
- HTML report in `htmlcov/` directory
- XML report as `coverage.xml`

## Code Quality

### Linting with Flake8

```bash
# Run linting on all code
python -m flake8 src/ tests/ main.py

# Configuration is in .flake8 file
```

### Code Formatting with Black

```bash
# Check if code needs formatting
python -m black --check --diff src/ tests/ main.py

# Format code automatically
python -m black src/ tests/ main.py
```

### Type Checking with MyPy

```bash
# Run type checking
python -m mypy src/ main.py

# Configuration is in pyproject.toml under [tool.mypy]
```

## Pre-commit Hooks

Install pre-commit hooks to automatically run checks before commits:

```bash
# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Continuous Integration

The project uses GitHub Actions for CI. The workflow:

1. Runs on Python 3.9, 3.10, and 3.11
2. Installs dependencies
3. Runs linting (flake8)
4. Checks code formatting (black)
5. Runs type checking (mypy)
6. Runs tests with coverage
7. Uploads coverage to Codecov

## Development Scripts

### Windows Batch Script (dev.bat)

```batch
dev.bat help         # Show all available commands
dev.bat test         # Run tests
dev.bat test-cov     # Run tests with coverage
dev.bat lint         # Run linting
dev.bat format       # Format code
dev.bat format-check # Check formatting
dev.bat mypy         # Type checking
dev.bat all          # Run all checks
dev.bat clean        # Clean cache files
dev.bat install      # Install dependencies
```

### PowerShell Script (dev.ps1)

Same commands as batch script but run with PowerShell:

```powershell
.\dev.ps1 help
.\dev.ps1 test
# etc.
```

## Writing Tests

### Unit Tests

- Test individual functions and classes
- Use mocking for external dependencies
- Place in appropriate `test_*.py` file

Example:

```python
import unittest
from unittest.mock import patch, Mock
from gmail_automation.config import load_configuration

class TestConfig(unittest.TestCase):
    @patch('gmail_automation.config.os.path.exists')
    def test_load_configuration_file_not_exists(self, mock_exists):
        mock_exists.return_value = False
        result = load_configuration()
        self.assertEqual(result, {})
```

### Integration Tests

- Test interaction between components
- Mock external APIs (Gmail API)
- Mark with `@pytest.mark.integration`

### Best Practices

1. **Test Coverage**: Aim for high test coverage but focus on meaningful tests
2. **Mocking**: Mock external dependencies (Gmail API, file system when appropriate)
3. **Assertions**: Use specific assertions with clear error messages
4. **Setup/Teardown**: Clean up test state properly
5. **Naming**: Use descriptive test names that explain what is being tested

## Configuration Files

- `.flake8` - Flake8 linting configuration
- `pyproject.toml` - Black formatting and MyPy configuration
- `pytest.ini` - Pytest configuration
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `.github/workflows/ci.yml` - GitHub Actions CI workflow

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running tests from the project root directory
2. **Missing Dependencies**: Run `pip install -r requirements.txt`
3. **Cache Issues**: Use `dev.bat clean` or manually delete cache directories
4. **Path Issues**: Tests use `conftest.py` to add `src/` to Python path

### Test Failures

- Run tests with `-v` flag for verbose output
- Use `--tb=short` or `--tb=long` to control traceback detail
- Run specific test files to isolate issues: `pytest tests/test_config.py`

## Contributing

Before submitting pull requests:

1. Run all tests: `dev.bat all`
2. Ensure code coverage doesn't decrease significantly
3. Add tests for new functionality
4. Update this documentation if needed
