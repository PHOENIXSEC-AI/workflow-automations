"""
Example pytest fixtures for working with the test files.
Import these in your conftest.py or directly in your test files.
"""

import pytest
from pathlib import Path

# Import the fixture helper
fixtures_dir = Path(__file__).parent
import sys
sys.path.insert(0, str(fixtures_dir))
from fixtures_helper import get_fixture_path, read_fixture

@pytest.fixture
def small_file_path():
    """Fixture providing path to the small test file."""
    return get_fixture_path("small_file.txt")

@pytest.fixture
def medium_file_path():
    """Fixture providing path to the medium test file."""
    return get_fixture_path("medium_file.txt")

@pytest.fixture
def large_file_path():
    """Fixture providing path to the large test file."""
    return get_fixture_path("large_file.txt")

@pytest.fixture
def oversized_file_path():
    """Fixture providing path to the oversized test file."""
    return get_fixture_path("oversized_file.txt")

@pytest.fixture
def small_file_content():
    """Fixture providing content of the small test file."""
    return read_fixture("small_file.txt")

@pytest.fixture
def medium_file_content():
    """Fixture providing content of the medium test file."""
    return read_fixture("medium_file.txt")

@pytest.fixture
def large_file_content():
    """Fixture providing content of the large test file."""
    return read_fixture("large_file.txt")

# Usage example:
# def test_tokenization_with_large_file(large_file_path):
#     # The large file will be automatically decompressed if needed
#     with open(large_file_path) as f:
#         text = f.read()
#     assert len(text) > 0
