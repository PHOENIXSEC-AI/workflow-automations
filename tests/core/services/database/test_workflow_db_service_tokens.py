import os
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, mock_open
import tiktoken
import pymongo
import gridfs
from bson.objectid import ObjectId

# from core.services.database.workflow_db_service import WorkflowDatabaseService, DEFAULT_TOKEN_LIMIT
from core.services.database.mongodb import MongoDBConnector
from core.utils.tokenization import count_tokens, chunk_text_by_tokens
from core.config import app_config

# Use MAX_SAFE_TOKEN_COUNT from app_config
MAX_SAFE_TOKEN_COUNT = app_config.MAX_SAFE_TOKEN_COUNT

# Test data
SHORT_CONTENT = "This is a short content for testing."
MEDIUM_CONTENT = "This is a medium length content for testing. " * 50
LONG_CONTENT = "This is a very long content that should exceed token limits. " * 5000

# Generate real package content to test with large files
def generate_large_content():
    """Generate a very large text from installed packages."""
    try:
        import sys
        content = ""
        site_packages = next(p for p in sys.path if p.endswith('site-packages'))
        count = 0
        
        for root, _, files in os.walk(site_packages):
            for file in files:
                if file.endswith('.py') and count < 50:
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            content += f.read()
                            count += 1
                    except:
                        pass  # Skip files that can't be read
                        
        return content
    except:
        # Fallback if we can't read packages
        return LONG_CONTENT * 10

# Try to generate large content, or use fallback
try:
    VERY_LARGE_CONTENT = generate_large_content()
except Exception as e:
    VERY_LARGE_CONTENT = LONG_CONTENT * 10


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
        mongodb_uri = app_config.MONGODB_URI
    except (ImportError, AttributeError):
        mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        
    service = WorkflowDatabaseService(
        connection_string=mongodb_uri,
        database="test_db"
    )
    service.connector = mock_mongodb_connector
    return service


class TestWorkflowDBTokenStorage:
    """Test suite for token-based file storage in WorkflowDatabaseService."""
    
    def test_store_small_file(self, workflow_db_service):
        """Test storing a small file that doesn't need chunking."""
        # Import count_tokens and chunk_text_by_tokens here to avoid circular import in the actual code
        with patch('workflows.flows.private_repo_analysis.count_tokens', side_effect=count_tokens):
            with patch('workflows.flows.private_repo_analysis.chunk_text_by_tokens', side_effect=chunk_text_by_tokens):
                result = workflow_db_service.store_file_with_tokens(
                    content=SHORT_CONTENT,
                    filename="test_small.txt",
                    metadata={"test": True}
                )
                
                # Verify result
                assert result["is_chunked"] is False
                assert "content_id" in result
                assert len(result["file_ids"]) == 1
                assert result["token_count"] > 0
                assert result["total_size"] == len(SHORT_CONTENT)
                
                # Verify MongoDB connector was called correctly
                workflow_db_service.connector.store_file_in_gridfs.assert_called_once()
                call_args = workflow_db_service.connector.store_file_in_gridfs.call_args[1]
                assert call_args["content"] == SHORT_CONTENT
                assert call_args["filename"] == "test_small.txt"
                assert call_args["metadata"]["test"] is True
                assert call_args["metadata"]["chunk_index"] == 0
                assert call_args["metadata"]["total_chunks"] == 1
    
    def test_store_large_file_with_chunking(self, workflow_db_service):
        """Test storing a large file that requires chunking."""
        token_limit = 100  # Use a small limit to force chunking
        
        # First, count tokens to know expected chunks
        tokenizer = tiktoken.get_encoding("cl100k_base")
        total_tokens = len(tokenizer.encode(LONG_CONTENT))
        expected_chunks = (total_tokens + token_limit - 1) // token_limit  # Ceiling division
        
        # Mock functions to avoid circular imports
        with patch('workflows.flows.private_repo_analysis.count_tokens', side_effect=count_tokens):
            with patch('workflows.flows.private_repo_analysis.chunk_text_by_tokens', side_effect=chunk_text_by_tokens):
                result = workflow_db_service.store_file_with_tokens(
                    content=LONG_CONTENT,
                    filename="test_large.txt",
                    metadata={"test": True},
                    token_limit=token_limit
                )
                
                # Verify result
                assert result["is_chunked"] is True
                assert "content_id" in result
                assert len(result["file_ids"]) > 1
                assert result["token_count"] > 0
                assert result["total_size"] == len(LONG_CONTENT)
                assert result["chunk_count"] >= expected_chunks
                
                # Verify MongoDB connector was called multiple times
                assert workflow_db_service.connector.store_file_in_gridfs.call_count == result["chunk_count"]
                
                # Check first chunk
                first_call = workflow_db_service.connector.store_file_in_gridfs.call_args_list[0][1]
                assert first_call["metadata"]["chunk_index"] == 0
                assert first_call["metadata"]["total_chunks"] == result["chunk_count"]
                
                # Check last chunk
                last_call = workflow_db_service.connector.store_file_in_gridfs.call_args_list[-1][1]
                assert last_call["metadata"]["chunk_index"] == result["chunk_count"] - 1
                assert last_call["metadata"]["total_chunks"] == result["chunk_count"]
    
    def test_store_very_large_file(self, workflow_db_service):
        """Test storing a very large file to ensure it doesn't cause memory issues."""
        # Mock functions to avoid circular imports
        with patch('workflows.flows.private_repo_analysis.count_tokens', side_effect=count_tokens):
            with patch('workflows.flows.private_repo_analysis.chunk_text_by_tokens', side_effect=chunk_text_by_tokens):
                result = workflow_db_service.store_file_with_tokens(
                    content=VERY_LARGE_CONTENT,
                    filename="test_very_large.txt",
                    token_limit=1000  # Use moderate limit to avoid too many chunks
                )
                
                # Verify result
                assert result["is_chunked"] is True
                assert len(result["file_ids"]) > 1
                assert result["token_count"] > 0
                assert result["total_size"] == len(VERY_LARGE_CONTENT)
    
    def test_retrieve_single_chunk_file(self, workflow_db_service):
        """Test retrieving a file stored as a single chunk."""
        # Mock functions to avoid circular imports
        with patch('workflows.flows.private_repo_analysis.count_tokens', side_effect=count_tokens):
            with patch('workflows.flows.private_repo_analysis.chunk_text_by_tokens', side_effect=chunk_text_by_tokens):
                # Store file first
                result = workflow_db_service.store_file_with_tokens(
                    content=SHORT_CONTENT,
                    filename="test_retrieve_small.txt"
                )
                
                content_id = result["content_id"]
                
                # Retrieve the file
                retrieved_content = workflow_db_service.retrieve_file_with_tokens(content_id)
                
                # Verify content
                assert retrieved_content == SHORT_CONTENT
                
                # Verify correct calls were made
                workflow_db_service.connector.list_gridfs_files.assert_called_once()
                workflow_db_service.connector.retrieve_file_from_gridfs.assert_called_once()
    
    def test_retrieve_chunked_file(self, workflow_db_service):
        """Test retrieving a file stored as multiple chunks."""
        token_limit = 100  # Small limit to force chunking
        
        # Mock functions to avoid circular imports
        with patch('workflows.flows.private_repo_analysis.count_tokens', side_effect=count_tokens):
            with patch('workflows.flows.private_repo_analysis.chunk_text_by_tokens', side_effect=chunk_text_by_tokens):
                # Store file first
                result = workflow_db_service.store_file_with_tokens(
                    content=MEDIUM_CONTENT,
                    filename="test_retrieve_chunked.txt",
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
                assert retrieved_content == MEDIUM_CONTENT
                
                # Verify correct calls were made
                workflow_db_service.connector.list_gridfs_files.assert_called_once()
                assert workflow_db_service.connector.retrieve_file_from_gridfs.call_count == chunk_count
    
    def test_retrieve_nonexistent_file(self, workflow_db_service):
        """Test retrieving a file that doesn't exist."""
        # Use a random UUID as content_id
        content_id = str(uuid.uuid4())
        
        # Reset the mocks to ensure we're starting fresh
        workflow_db_service.connector.list_gridfs_files.reset_mock()
        workflow_db_service.connector.retrieve_file_from_gridfs.reset_mock()
        
        # Mock list_gridfs_files to return empty list
        workflow_db_service.connector.list_gridfs_files.return_value = []
        
        # Retrieve the file
        result = workflow_db_service.retrieve_file_with_tokens(content_id)
        
        # Verify error message
        assert "Error" in result
        assert content_id in result
        
        # Verify correct calls were made
        workflow_db_service.connector.list_gridfs_files.assert_called_once_with(
            {"metadata.content_id": content_id}
        )
        workflow_db_service.connector.retrieve_file_from_gridfs.assert_not_called()
    
    def test_get_file_token_count(self, workflow_db_service):
        """Test getting token count for a file."""
        token_count = 1234
        content_id = str(uuid.uuid4())
        
        # Mock list_gridfs_files to return file with token count
        file_info = {
            'file_id': 'test_file_id',
            'filename': 'test.txt',
            'length': 100,
            'upload_date': datetime.now(tz=timezone.utc),
            'metadata': {
                'token_count': token_count,
                'content_id': content_id
            }
        }
        
        # Reset the mock to ensure we're starting fresh
        workflow_db_service.connector.list_gridfs_files.reset_mock()
        
        # Configure the mock to return our file info when called with the specific content_id
        workflow_db_service.connector.list_gridfs_files.return_value = [file_info]
        
        # Explicitly bypass the side_effect function if it exists
        if hasattr(workflow_db_service.connector.list_gridfs_files, "_mock_side_effect"):
            workflow_db_service.connector.list_gridfs_files._mock_side_effect = None
        
        # Get token count
        result = workflow_db_service.get_file_token_count(content_id)
        
        # Verify result
        assert result == token_count
        
        # Verify the correct query was used
        workflow_db_service.connector.list_gridfs_files.assert_called_once_with(
            {"metadata.content_id": content_id}
        )
    
    def test_get_file_token_count_nonexistent(self, workflow_db_service):
        """Test getting token count for nonexistent file."""
        # Use a random UUID as content_id
        content_id = str(uuid.uuid4())
        
        # Reset the mock to ensure we're starting fresh
        workflow_db_service.connector.list_gridfs_files.reset_mock()
        
        # Mock list_gridfs_files to return empty list
        workflow_db_service.connector.list_gridfs_files.return_value = []
        
        # Get token count
        result = workflow_db_service.get_file_token_count(content_id)
        
        # Verify result
        assert result == 0
        
        # Verify the correct query was used
        workflow_db_service.connector.list_gridfs_files.assert_called_once_with(
            {"metadata.content_id": content_id}
        )
    
    def test_error_handling(self, workflow_db_service, mock_mongodb_connector):
        """Test error handling in store_file_with_tokens."""
        # Mock an exception during storing
        mock_mongodb_connector.store_file_in_gridfs.side_effect = Exception("Test exception")
        
        # Attempt to store
        result = workflow_db_service.store_file_with_tokens(
            content=SHORT_CONTENT,
            filename="test.txt"
        )
        
        # Verify error is returned
        assert "error" in result
        assert "Failed to store file" in result["error"]
    
    def test_token_count_exceeds_mongodb_limit(self, workflow_db_service, mock_mongodb_connector, monkeypatch):
        """Test token count validation against MongoDB document size limits."""
        # Mock the count_tokens function to return a value exceeding the limit
        def mock_count_tokens(text, encoding_name=None):
            return MAX_SAFE_TOKEN_COUNT + 1000
            
        monkeypatch.setattr("workflows.flows.private_repo_analysis.count_tokens", mock_count_tokens)
        
        # Attempt to store content with excessive tokens
        result = workflow_db_service.store_file_with_tokens(
            content="Test content",
            filename="large_file.txt"
        )
        
        # Verify error is returned with appropriate information
        assert "error" in result
        assert "exceeds MongoDB safe limit" in result["error"]
        assert result["token_count"] > MAX_SAFE_TOKEN_COUNT
        assert result["max_safe_tokens"] == MAX_SAFE_TOKEN_COUNT
        
        # Verify no attempt was made to store the file
        mock_mongodb_connector.store_file_in_gridfs.assert_not_called() 

    def test_store_file_with_tokens_oversized(self, workflow_db_service, monkeypatch):
        """Test storing an oversized file that exceeds MongoDB's limit."""
        # Instead of creating a massive string that causes stack overflow,
        # we'll use a smaller string and mock the count_tokens function
        content = "This is a test content"
        
        # Create a mock function that returns an oversized token count
        def mock_count_tokens(text, encoding_name=None):
            return MAX_SAFE_TOKEN_COUNT + 1000
            
        # Apply the mock to both the imported function and the one in private_repo_analysis
        with patch('workflows.flows.private_repo_analysis.count_tokens', side_effect=mock_count_tokens):
            with patch('core.utils.tokenization.count_tokens', side_effect=mock_count_tokens):
                result = workflow_db_service.store_file_with_tokens(
                    content=content,
                    filename="oversized.txt"
                )
                
                # This should fail with an error about exceeding MongoDB limits
                assert "error" in result
                assert "exceeds MongoDB safe limit" in result["error"]
                assert result["token_count"] > MAX_SAFE_TOKEN_COUNT
                assert result["max_safe_tokens"] == MAX_SAFE_TOKEN_COUNT
                
                # Verify no attempt was made to store the file
                workflow_db_service.connector.store_file_in_gridfs.assert_not_called()

if __name__ == "__main__":
    # Run all tests even if some fail
    pytest.main(["-vs", "--tb=short", "--no-header", "--continue-on-collection-errors", __file__]) 