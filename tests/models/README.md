# Workflow Models Tests

This directory contains tests for the workflow models used in the application. The tests validate the behavior of data models used throughout the workflow system.

## Test Files

- `test_base_model.py`: Tests for the base `AgentAnalysisResult` model
- `test_workflow_models.py`: Tests for workflow-specific models like `RunAIDeps` and `RunAITask`
- `test_agent_result_models.py`: Tests for agent result models like `AgentTask`, `TokenUsage`, and `AgentSuccessResult`
- `test_extract_base_models.py`: Tests for extract base models like `BaseAgentAnalysisResult`, `EnvVarInfo`, etc.

## Running Tests

You can run all tests using pytest:

```bash
pytest tests/
```

Or run specific test files:

```bash
pytest tests/test_workflow_models.py
```

## Test Philosophy

These tests have been kept deliberately simple and focused on:

1. Validating that models can be correctly instantiated with default and custom values
2. Ensuring that validation rules work as expected
3. Testing utility methods and factory functions
4. Verifying model type safety and field constraints