# Workflow Task Testing

This directory contains tests for the workflow task modules. The tests are implemented following Prefect's best practices for testing tasks and flows.

## Test Structure

The tests mirror the structure of the source code:

- `tests/workflows/tasks/` - Tests for workflow tasks in `src/workflows/tasks/`
- `tests/models/` - Tests for models

## Testing Approach

### Task Testing

For testing Prefect tasks, we follow these best practices:

1. **Testing with `prefect_test_harness`**:
   - We use the Prefect test harness as a session-scoped fixture to provide a testing environment for tasks

2. **Testing tasks within flows**:
   - Tasks are typically tested within the context of a flow to properly simulate the Prefect runtime environment
   - This allows testing of the task's integration with Prefect's state handling

3. **Direct function testing**:
   - We can also test the underlying task function directly using `.fn` attribute
   - This is useful for testing the raw functionality without Prefect's overhead

4. **Mocking dependencies**:
   - External dependencies are mocked to isolate task behavior
   - This includes database operations, API calls, and file system interactions

5. **Testing state handling**:
   - We verify that tasks properly return `Completed` or `Failed` states
   - We validate that task results are correctly stored in state data

## Running Tests

To run the tests:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/workflows/tasks/test_tool_repomix.py

# Run specific test
pytest tests/workflows/tasks/test_tool_repomix.py::test_analyze_remote_repo_success

# Run with increased verbosity
pytest -v
```

## Test Fixtures

Common test fixtures are defined in relevant test files or in `conftest.py` files. Key fixtures include:

- `prefect_test_fixture`: Sets up the Prefect test harness
- Mock objects for external dependencies

## Adding New Tests

When adding new tasks to the workflow system, corresponding tests should be added following the same patterns demonstrated in existing test files. 