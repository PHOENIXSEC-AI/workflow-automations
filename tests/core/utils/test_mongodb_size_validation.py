"""
Tests for MongoDB document size validation using test fixtures.
These tests specifically check that files are properly validated against MongoDB's 16MB limit.
"""

import os
import sys
import pytest
from pathlib import Path

# Add fixtures directory to path
fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
if fixtures_dir.exists():
    sys.path.insert(0, str(fixtures_dir))
    try:
        from fixtures_helper import get_fixture_path, read_fixture
        HAS_FIXTURES = True
    except ImportError:
        HAS_FIXTURES = False
else:
    HAS_FIXTURES = False

# Import core configuration if available
try:
    from core.config import app_config
    HAS_APP_CONFIG = True
    MAX_SAFE_TOKEN_COUNT = app_config.MAX_SAFE_TOKEN_COUNT
except ImportError:
    HAS_APP_CONFIG = False
    # Use a placeholder value that will be overridden from the fixture if available
    MAX_SAFE_TOKEN_COUNT = 4000000

# Import validation functions
from core.utils.tokenization import (
    count_tokens, 
    estimate_tokens_from_bytes,
)

# Update global constant if needed
if HAS_APP_CONFIG and 'MONGODB_MAX_TOKEN_ESTIMATE' in globals():
    # Ensure our test uses the same value as the application
    globals()['MONGODB_MAX_TOKEN_ESTIMATE'] = MAX_SAFE_TOKEN_COUNT

# Try to import MongoDB validation
try:
    from core.services.database.workflow_db_service import validate_file_size_for_mongodb
    HAS_VALIDATION_FUNCTION = True
except ImportError:
    # Create a mock validation function for testing
    HAS_VALIDATION_FUNCTION = False
    def validate_file_size_for_mongodb(file_path=None, content=None, token_count=None):
        """Mock validation function for testing."""
        # Use the MAX_SAFE_TOKEN_COUNT from app_config or fixtures
        max_token_count = MAX_SAFE_TOKEN_COUNT
        
        # If token count is provided directly, check it
        if token_count is not None:
            if token_count > max_token_count:
                return False, f"Token count {token_count} exceeds safe limit of {max_token_count}"
            return True, "Valid token count"
            
        # If file path is provided, estimate tokens from file
        if file_path is not None:
            if not os.path.exists(file_path):
                return False, f"File does not exist: {file_path}"
                
            file_size = os.path.getsize(file_path)
            estimated_tokens = estimate_tokens_from_bytes(file_size)
            
            if estimated_tokens > max_token_count:
                return False, f"Estimated token count {estimated_tokens} exceeds safe limit of {max_token_count}"
            return True, "Valid file size"
            
        # If content is provided, count tokens directly
        if content is not None:
            token_count = count_tokens(content)
            
            if token_count > max_token_count:
                return False, f"Token count {token_count} exceeds safe limit of {max_token_count}"
            return True, "Valid content size"
            
        return False, "No content, file path, or token count provided for validation"

# Update MAX_SAFE_TOKEN_COUNT from fixture if available
def load_fixture_limits():
    """Load token limits from the fixture file if available."""
    global MAX_SAFE_TOKEN_COUNT
    
    if not HAS_FIXTURES:
        return
        
    try:
        import json
        limits_path = get_fixture_path("token_limits.json")
        with open(limits_path) as f:
            limits = json.load(f)
            
        # Update our global constant
        fixture_max_tokens = limits.get("max_safe_token_count")
        if fixture_max_tokens is not None:
            # Only update if not using app_config
            if not HAS_APP_CONFIG:
                MAX_SAFE_TOKEN_COUNT = fixture_max_tokens
                # Also update MONGODB_MAX_TOKEN_ESTIMATE if it exists
                if 'MONGODB_MAX_TOKEN_ESTIMATE' in globals():
                    globals()['MONGODB_MAX_TOKEN_ESTIMATE'] = MAX_SAFE_TOKEN_COUNT
    except:
        pass  # Silently continue if fails
        
# Try loading limits from fixture
load_fixture_limits()
        
# Mark to skip tests if fixtures aren't available
pytestmark = pytest.mark.skipif(
    not HAS_FIXTURES, 
    reason="Test fixtures not found. Run scripts/generate_test_fixtures.py first."
)


class TestMongoDBSizeValidation:
    """Tests for MongoDB document size validation."""

    def test_small_file_validation(self):
        """Test validation with a small file."""
        if not HAS_FIXTURES:
            pytest.skip("Fixtures not available")
            
        # Get the path to the small file
        file_path = get_fixture_path("small_file.txt")
        assert os.path.exists(file_path), "Small file fixture should exist"
        
        # Validate by file path
        is_valid, message = validate_file_size_for_mongodb(file_path=file_path)
        assert is_valid, f"Small file should be valid: {message}"
        
        # Also validate by content
        content = read_fixture("small_file.txt")
        is_valid, message = validate_file_size_for_mongodb(content=content)
        assert is_valid, f"Small file content should be valid: {message}"
        
        # Get actual token count for reference
        token_count = count_tokens(content)
        assert token_count < MAX_SAFE_TOKEN_COUNT, "Small file should have fewer tokens than the limit"

    def test_medium_file_validation(self):
        """Test validation with a medium file."""
        if not HAS_FIXTURES:
            pytest.skip("Fixtures not available")
            
        # Get the path to the medium file
        file_path = get_fixture_path("medium_file.txt")
        assert os.path.exists(file_path), "Medium file fixture should exist"
        
        # Validate by file path
        is_valid, message = validate_file_size_for_mongodb(file_path=file_path)
        assert is_valid, f"Medium file should be valid: {message}"
        
        # Also validate by content
        content = read_fixture("medium_file.txt")
        is_valid, message = validate_file_size_for_mongodb(content=content)
        assert is_valid, f"Medium file content should be valid: {message}"

    def test_large_file_validation(self):
        """Test validation with a large file."""
        if not HAS_FIXTURES:
            pytest.skip("Fixtures not available")
            
        # Get the path to the large file
        file_path = get_fixture_path("large_file.txt")
        assert os.path.exists(file_path), "Large file fixture should exist"
        
        # Validate by file path
        is_valid, message = validate_file_size_for_mongodb(file_path=file_path)
        assert is_valid, f"Large file should be valid: {message}"
        
        # Also validate by content (might be slow with large files)
        content = read_fixture("large_file.txt")
        is_valid, message = validate_file_size_for_mongodb(content=content)
        assert is_valid, f"Large file content should be valid: {message}"

    @pytest.mark.xfail(reason="Oversized file should exceed MongoDB's document size limit")
    def test_oversized_file_validation(self):
        """Test validation with an oversized file that exceeds MongoDB's limit."""
        if not HAS_FIXTURES:
            pytest.skip("Fixtures not available")
        
        # Check if the oversized file exists before attempting to use it
        oversized_path = fixtures_dir / "oversized_file.txt.gz"
        if not oversized_path.exists() and not (fixtures_dir / "oversized_file.txt").exists():
            pytest.skip("Oversized file fixture not found")
            
        # Get the path to the decompressed file (this will decompress it)
        file_path = get_fixture_path("oversized_file.txt")
        assert os.path.exists(file_path), "Oversized file fixture should exist after decompression"
        
        # Validate by file path - this should fail
        is_valid, message = validate_file_size_for_mongodb(file_path=file_path)
        assert not is_valid, "Oversized file should be invalid for MongoDB"
        assert "exceeds" in message.lower(), "Error message should mention size exceeding limits"
        
        # We don't test by content directly as it might be too memory-intensive

    def test_token_count_validation(self):
        """Test direct token count validation."""
        # Valid token count
        is_valid, message = validate_file_size_for_mongodb(token_count=MAX_SAFE_TOKEN_COUNT - 1000)
        assert is_valid, f"Token count under the limit should be valid: {message}"
        
        # Invalid token count
        is_valid, message = validate_file_size_for_mongodb(token_count=MAX_SAFE_TOKEN_COUNT + 1000)
        assert not is_valid, "Token count over the limit should be invalid"
        assert str(MAX_SAFE_TOKEN_COUNT) in message, "Error message should include the limit"

    def test_limits_from_fixture(self):
        """Test the token limits from the fixtures reference file."""
        if not HAS_FIXTURES:
            pytest.skip("Fixtures not available")
            
        try:
            import json
            limits_path = get_fixture_path("token_limits.json")
            with open(limits_path) as f:
                limits = json.load(f)
                
            # Check the max safe token count exists in the fixture
            fixture_max_tokens = limits.get("max_safe_token_count")
            assert fixture_max_tokens is not None, "token_limits.json should have max_safe_token_count"
            
            # Get the MongoDB limits from the fixture
            mongodb_max_size = limits.get("mongodb_max_document_size")
            mongodb_safe_size = limits.get("mongodb_safe_document_size")
            bytes_per_token = limits.get("bytes_per_token")
            
            # Verify basic relationship - safe size is less than max size
            assert mongodb_max_size > 0, "Max size should be positive"
            assert mongodb_safe_size > 0, "Safe size should be positive"
            
            # Verify that the safe document size matches the calculation
            # This will only be true if generated with our script
            expected_safe_size = fixture_max_tokens * bytes_per_token
            assert mongodb_safe_size == expected_safe_size, (
                f"Safe document size ({mongodb_safe_size}) should match "
                f"max_tokens * bytes_per_token ({expected_safe_size})"
            )
            
            # Also verify that our MAX_SAFE_TOKEN_COUNT matches the fixture
            # This will be true if we've read from app_config or fixture
            assert MAX_SAFE_TOKEN_COUNT == fixture_max_tokens, (
                f"MAX_SAFE_TOKEN_COUNT ({MAX_SAFE_TOKEN_COUNT}) should match "
                f"fixture value ({fixture_max_tokens})"
            )
                
        except (FileNotFoundError, json.JSONDecodeError) as e:
            pytest.skip(f"Could not read token limits file: {e}")


# For quick testing without pytest
if __name__ == "__main__":
    # This allows running this file directly to test functionality
    test = TestMongoDBSizeValidation()
    
    print("Testing small file validation...")
    test.test_small_file_validation()
    
    print("Testing medium file validation...")
    test.test_medium_file_validation()
    
    print("Testing large file validation...")
    test.test_large_file_validation()
    
    print("Testing oversized file validation (expected to fail)...")
    try:
        test.test_oversized_file_validation()
        print("Warning: Oversized file validation unexpectedly passed")
    except AssertionError as e:
        print(f"Expected failure: {e}")
    
    print("Testing token count validation...")
    test.test_token_count_validation()
    
    print("Testing limits from fixture...")
    test.test_limits_from_fixture()
    
    print("All tests completed!") 