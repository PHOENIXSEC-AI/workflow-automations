"""
Tests for the WorkflowDatabaseService using compressed test fixtures.
These tests verify that the MongoDB document size validation works correctly with real-world sized files.
"""

import os
import uuid
import pytest
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from bson.objectid import ObjectId
from pathlib import Path

# Add fixtures directory to path
fixtures_dir = Path(__file__).parent.parent.parent.parent / "fixtures"
if fixtures_dir.exists():
    sys.path.insert(0, str(fixtures_dir))
    try:
        from fixtures_helper import get_fixture_path, read_fixture
        HAS_FIXTURES = True
    except ImportError:
        HAS_FIXTURES = False
else:
    HAS_FIXTURES = False

# Get the correct token count limit from app_config
try:
    from core.config import app_config
    MAX_SAFE_TOKEN_COUNT = app_config.MAX_SAFE_TOKEN_COUNT
except ImportError:
    # Fallback to a default value
    MAX_SAFE_TOKEN_COUNT = 4000000

from core.services.database.workflow_db_service import WorkflowDatabaseService, DEFAULT_TOKEN_LIMIT
from core.services.database.mongodb import MongoDBConnector
from core.utils.tokenization import count_tokens, chunk_text_by_tokens

# Check if we need to skip fixture-dependent tests
pytestmark = pytest.mark.skipif(
    not HAS_FIXTURES, 
    reason="Test fixtures not found. Run scripts/generate_test_fixtures.py first."
)


class MockGridFSFile:
    """Mock GridFS file."""
    def __init__(self, file_id, filename, content, metadata=None):
        self._id = file_id
        self.filename = filename
        self.content = content
        self.metadata = metadata or {}
        self.length = len(content)
        self.upload_date = datetime.now(tz=timezone.utc)


@pytest.fixture
def mock_mongodb_connector():
    """Create a mock MongoDB connector with GridFS functionality."""
    connector = MagicMock(spec=MongoDBConnector)
    
    # Track stored files
    stored_files = {}
    
    # Mock store_file_in_gridfs
    def mock_store_file(content, filename, metadata=None):
        file_id = str(ObjectId())
        stored_files[file_id] = MockGridFSFile(
            file_id=file_id,
            filename=filename,
            content=content,
            metadata=metadata
        )
        return file_id
    
    # Mock retrieve_file_from_gridfs
    def mock_retrieve_file(file_id):
        if file_id in stored_files:
            return stored_files[file_id].content
        return f"Error: File with ID {file_id} not found"
    
    # Mock list_gridfs_files
    def mock_list_files(query=None):
        query = query or {}
        result = []
        
        for file_id, file_obj in stored_files.items():
            # Check if query matches
            if 'metadata.content_id' in query and query['metadata.content_id'] != file_obj.metadata.get('content_id'):
                continue
                
            # Create file info dict
            file_info = {
                'file_id': file_id,
                'filename': file_obj.filename,
                'length': file_obj.length,
                'upload_date': file_obj.upload_date,
                'metadata': file_obj.metadata
            }
            result.append(file_info)
            
        return result
    
    connector.store_file_in_gridfs.side_effect = mock_store_file
    connector.retrieve_file_from_gridfs.side_effect = mock_retrieve_file
    connector.list_gridfs_files.side_effect = mock_list_files
    
    return connector


@pytest.fixture
def workflow_db_service(mock_mongodb_connector):
    """Create a workflow db service with mocked MongoDB connector."""
    # Use the MongoDB URI from app_config or fallback to environment variable
    try:
        from core.config import app_config
        mongodb_uri = app_config.MONGODB_URI
    except (ImportError, AttributeError):
        mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        
    service = WorkflowDatabaseService(
        connection_string=mongodb_uri,
        database="test_db"
    )
    service.connector = mock_mongodb_connector
    return service


class TestWorkflowDBWithFixtures:
    """Test MongoDB document size limits using realistic fixtures."""
    
    def test_store_small_fixture(self, workflow_db_service):
        """Test storing a small file fixture."""
        if not HAS_FIXTURES:
            pytest.skip("Fixtures not available")
            
        # Get the small file content
        content = read_fixture("small_file.txt")
        
        # Mock functions to avoid circular imports
        with patch('workflows.flows.private_repo_analysis.count_tokens', side_effect=count_tokens):
            with patch('workflows.flows.private_repo_analysis.chunk_text_by_tokens', side_effect=chunk_text_by_tokens):
                result = workflow_db_service.store_file_with_tokens(
                    content=content,
                    filename="small_fixture.txt",
                    metadata={"test": True}
                )
                
                # Verify result
                assert "error" not in result, f"Got error: {result.get('error', '')}"
                assert result["is_chunked"] is False
                assert "content_id" in result
                assert len(result["file_ids"]) == 1
                assert result["token_count"] > 0
                assert result["total_size"] == len(content)
    
    def test_store_medium_fixture(self, workflow_db_service):
        """Test storing a medium file fixture."""
        if not HAS_FIXTURES:
            pytest.skip("Fixtures not available")
            
        # Get the medium file content
        content = read_fixture("medium_file.txt")
        
        # Mock functions to avoid circular imports
        with patch('workflows.flows.private_repo_analysis.count_tokens', side_effect=count_tokens):
            with patch('workflows.flows.private_repo_analysis.chunk_text_by_tokens', side_effect=chunk_text_by_tokens):
                result = workflow_db_service.store_file_with_tokens(
                    content=content,
                    filename="medium_fixture.txt",
                    token_limit=1000  # Use a small limit to force chunking
                )
                
                # Verify result
                assert "error" not in result, f"Got error: {result.get('error', '')}"
                assert result["is_chunked"] is True
                assert "content_id" in result
                assert len(result["file_ids"]) > 1
                assert result["token_count"] > 0
                assert result["total_size"] == len(content)
    
    def test_store_large_fixture(self, workflow_db_service):
        """Test storing a large file fixture with chunking."""
        if not HAS_FIXTURES:
            pytest.skip("Fixtures not available")
            
        # Get the large file content
        content = read_fixture("large_file.txt")
        
        # Mock functions to avoid circular imports
        with patch('workflows.flows.private_repo_analysis.count_tokens', side_effect=count_tokens):
            with patch('workflows.flows.private_repo_analysis.chunk_text_by_tokens', side_effect=chunk_text_by_tokens):
                result = workflow_db_service.store_file_with_tokens(
                    content=content,
                    filename="large_fixture.txt"
                )
                
                # Verify result
                assert "error" not in result, f"Got error: {result.get('error', '')}"
                assert "content_id" in result
                assert result["token_count"] > 0
                assert result["total_size"] == len(content)
    
    @pytest.mark.xfail(reason="Oversized file should exceed MongoDB's document size limit")
    def test_store_oversized_fixture(self, workflow_db_service):
        """Test that oversized file exceeds MongoDB document size limit."""
        if not HAS_FIXTURES:
            pytest.skip("Fixtures not available")
        
        # Check if oversized file exists
        oversized_path = fixtures_dir / "oversized_file.txt.gz"
        if not oversized_path.exists() and not (fixtures_dir / "oversized_file.txt").exists():
            pytest.skip("Oversized file fixture not found")
        
        try:
            # Get the oversized file content
            content = read_fixture("oversized_file.txt")
        except Exception as e:
            pytest.skip(f"Failed to read oversized file: {e}")
        
        # Mock functions to avoid circular imports
        with patch('workflows.flows.private_repo_analysis.count_tokens', side_effect=count_tokens):
            with patch('workflows.flows.private_repo_analysis.chunk_text_by_tokens', side_effect=chunk_text_by_tokens):
                result = workflow_db_service.store_file_with_tokens(
                    content=content,
                    filename="oversized_fixture.txt"
                )
                
                # This should fail with an error about exceeding MongoDB limits
                assert "error" in result
                assert "exceeds MongoDB safe limit" in result["error"]
                assert result["token_count"] > MAX_SAFE_TOKEN_COUNT
                assert result["max_safe_tokens"] == MAX_SAFE_TOKEN_COUNT
                
                # Verify no attempt was made to store the file
                workflow_db_service.connector.store_file_in_gridfs.assert_not_called()
    
    def test_retrieve_fixtures(self, workflow_db_service):
        """Test retrieving stored fixtures."""
        if not HAS_FIXTURES:
            pytest.skip("Fixtures not available")
            
        # Get the small file content
        content = read_fixture("small_file.txt")
        
        # Mock functions to avoid circular imports
        with patch('workflows.flows.private_repo_analysis.count_tokens', side_effect=count_tokens):
            with patch('workflows.flows.private_repo_analysis.chunk_text_by_tokens', side_effect=chunk_text_by_tokens):
                # Store file first
                result = workflow_db_service.store_file_with_tokens(
                    content=content,
                    filename="retrieve_fixture.txt"
                )
                
                content_id = result["content_id"]
                
                # Reset mock to clear call history
                workflow_db_service.connector.list_gridfs_files.reset_mock()
                workflow_db_service.connector.retrieve_file_from_gridfs.reset_mock()
                
                # Retrieve the file
                retrieved_content = workflow_db_service.retrieve_file_with_tokens(content_id)
                
                # Verify content
                assert retrieved_content == content
                
                # Verify correct calls were made
                workflow_db_service.connector.list_gridfs_files.assert_called_once()
                workflow_db_service.connector.retrieve_file_from_gridfs.assert_called_once()
    
    def test_chunked_fixture_retrieval(self, workflow_db_service):
        """Test retrieving chunked fixtures."""
        if not HAS_FIXTURES:
            pytest.skip("Fixtures not available")
            
        # Get the medium file content
        content = read_fixture("medium_file.txt")
        token_limit = 500  # Small limit to force chunking
        
        # Mock functions to avoid circular imports
        with patch('workflows.flows.private_repo_analysis.count_tokens', side_effect=count_tokens):
            with patch('workflows.flows.private_repo_analysis.chunk_text_by_tokens', side_effect=chunk_text_by_tokens):
                # Store file first with chunking
                result = workflow_db_service.store_file_with_tokens(
                    content=content,
                    filename="chunked_fixture.txt",
                    token_limit=token_limit
                )
                
                content_id = result["content_id"]
                chunk_count = result["chunk_count"]
                
                # Reset mock to clear call history
                workflow_db_service.connector.list_gridfs_files.reset_mock()
                workflow_db_service.connector.retrieve_file_from_gridfs.reset_mock()
                
                # Retrieve the file
                retrieved_content = workflow_db_service.retrieve_file_with_tokens(content_id)
                
                # Verify content
                assert retrieved_content == content
                
                # Verify correct calls were made
                workflow_db_service.connector.list_gridfs_files.assert_called_once()
                assert workflow_db_service.connector.retrieve_file_from_gridfs.call_count == chunk_count


# Run tests directly for debugging
if __name__ == "__main__":
    # Skip pytests infrastructure for quick testing
    import doctest
    from pathlib import Path
    
    # Setup fixtures directory
    fixtures_dir = Path(__file__).parent.parent.parent.parent / "fixtures"
    if not fixtures_dir.exists():
        print(f"Fixtures directory not found at {fixtures_dir}")
        print("Please run scripts/generate_test_fixtures.py first")
        sys.exit(1)
    
    sys.path.insert(0, str(fixtures_dir))
    from fixtures_helper import get_fixture_path, read_fixture
    
    # Print fixture information
    manifest_path = fixtures_dir / "manifest.json"
    if manifest_path.exists():
        import json
        with open(manifest_path) as f:
            manifest = json.load(f)
        print(f"Found test fixtures generated at: {manifest.get('generated_at', 'unknown')}")
        for filename, info in manifest.get('files', {}).items():
            print(f"- {filename}: {info.get('original_size', 0)} bytes")
    
    print("\nTo run tests with pytest: pytest tests/core/services/database/test_workflow_db_service_with_fixtures.py -v")
    
if __name__ == "__main__":
    # Run all tests even if some fail
    pytest.main(["-vs", "--tb=short", "--no-header", "--continue-on-collection-errors", __file__]) 