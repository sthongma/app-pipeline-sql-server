# Test Suite

This directory contains automated tests for the SQL Server Pipeline application.

## Running Tests

### Prerequisites

Install testing dependencies:
```bash
pip install pytest pytest-cov
```

### Run All Tests

```bash
# From project root
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=. --cov-report=html
```

### Run Specific Test Files

```bash
# Security tests only
pytest tests/test_security.py -v

# Health check tests only
pytest tests/test_health_check.py -v
```

### Run Specific Test Class or Method

```bash
# Run specific test class
pytest tests/test_security.py::TestSQLIdentifierSanitization -v

# Run specific test method
pytest tests/test_security.py::TestSQLIdentifierSanitization::test_valid_identifiers -v
```

## Test Coverage

Current test coverage focuses on:

### Security Tests (`test_security.py`)
- ✅ SQL identifier sanitization
- ✅ SQL injection prevention
- ✅ Password masking in logs
- ✅ Connection string masking
- ✅ Credentials masking in config dictionaries

### Health Check Tests (`test_health_check.py`)
- ✅ Application health checks
- ✅ Database health checks
- ✅ Full system health reports
- ✅ Error handling in health checks

## Test Structure

```
tests/
├── __init__.py           # Test package initialization
├── README.md             # This file
├── test_security.py      # Security and SQL injection tests
├── test_health_check.py  # Health check tests
└── conftest.py           # Shared test fixtures (TODO)
```

## Adding New Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Example Test

```python
def test_my_feature():
    """Test description"""
    # Arrange
    input_data = "test"

    # Act
    result = my_function(input_data)

    # Assert
    assert result == expected_output
```

## Continuous Integration

Tests should be run automatically in CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install pytest pytest-cov
    pytest tests/ -v --cov=. --cov-report=xml
```

## TODO: Additional Tests Needed

- [ ] Database connection tests with real SQL Server
- [ ] File processing integration tests
- [ ] Data validation tests
- [ ] Performance/load tests
- [ ] End-to-end workflow tests
- [ ] Configuration loading tests
- [ ] Error handling edge cases

## Test Data

Test data and fixtures should be placed in `tests/fixtures/` directory (to be created as needed).

## Notes

- Tests use mocking for database connections to avoid requiring actual SQL Server
- Security tests focus on preventing common attack vectors
- Health checks validate system monitoring capabilities
- All critical security functions have test coverage
