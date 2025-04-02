import os
import pytest
from unittest.mock import patch, MagicMock
import tiktoken

from core.utils import LoggerFactory
from core.utils.tokenization import (
    count_tokens, 
    chunk_text_by_tokens, 
    estimate_tokens_from_bytes,
    estimate_tokens_in_file,
    get_tokenizer,
    DEFAULT_TOKENIZER,
    DEFAULT_TOKEN_LIMIT,
    BYTES_PER_TOKEN_APPROX
)

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

# Sample texts for testing
SHORT_TEXT = "This is a short text for testing token counting."
MEDIUM_TEXT = "This is a medium length text. " * 50
LONG_TEXT = "This is a long text that should exceed the default chunk size. " * 5000

class TestTokenization:
    """Test suite for tokenization utilities."""
    
    def test_get_tokenizer(self):
        """Test that we can get a tiktoken tokenizer."""
        # Test with default tokenizer
        tokenizer = get_tokenizer()
        assert tokenizer is not None
        assert hasattr(tokenizer, 'encode')
        assert hasattr(tokenizer, 'decode')
        
        # Test with specific encoding
        tokenizer = get_tokenizer(app_config.DEFAULT_TOKENIZER)
        assert tokenizer is not None
        
        # Test with a known model name (should use encoding_for_model fallback)
        with patch('tiktoken.get_encoding', side_effect=Exception("Unknown encoding")):
            with patch('tiktoken.encoding_for_model', return_value=MagicMock()) as mock_encoding_for_model:
                tokenizer = get_tokenizer("gpt-4")
                assert tokenizer is not None
                mock_encoding_for_model.assert_called_once_with("gpt-4")
        
    def test_count_tokens(self):
        """Test token counting for different texts."""
        # Count tokens in short text
        short_count = count_tokens(SHORT_TEXT)
        assert short_count > 0
        assert isinstance(short_count, int)
        
        # Verify with tiktoken directly
        tokenizer = tiktoken.get_encoding(DEFAULT_TOKENIZER)
        expected_count = len(tokenizer.encode(SHORT_TEXT))
        assert short_count == expected_count
        
        # Count tokens in medium text
        medium_count = count_tokens(MEDIUM_TEXT)
        assert medium_count > short_count
        
        # Count tokens in long text
        long_count = count_tokens(LONG_TEXT)
        assert long_count > medium_count
        
        # Handle empty text
        assert count_tokens("") == 0
        assert count_tokens(None) == 0
    
    def test_token_count_fallback(self):
        """Test token counting fallback when tiktoken fails."""
        with patch('core.utils.tokenization.get_tokenizer', return_value=None):
            # Should use character-based approximation
            count = count_tokens(SHORT_TEXT)
            expected_approx = len(SHORT_TEXT) // BYTES_PER_TOKEN_APPROX
            assert count == expected_approx
    
    def test_chunk_text_by_tokens(self):
        """Test chunking text by token count."""
        # Test with short text (should return a single chunk)
        chunks = chunk_text_by_tokens(SHORT_TEXT, token_limit=100)
        assert len(chunks) == 1
        assert chunks[0] == SHORT_TEXT
        
        # Test with medium text and small token limit
        small_limit = 10
        chunks = chunk_text_by_tokens(MEDIUM_TEXT, token_limit=small_limit)
        assert len(chunks) > 1
        
        # Verify each chunk is smaller than the limit
        for chunk in chunks:
            chunk_tokens = count_tokens(chunk)
            # Allow slight variance because token boundaries might not align perfectly
            assert chunk_tokens <= small_limit + 5
        
        # Test with empty text
        assert chunk_text_by_tokens("") == []
        assert chunk_text_by_tokens(None) == []
    
    def test_chunking_fallback(self):
        """Test chunking fallback when tiktoken fails."""
        with patch('core.utils.tokenization.get_tokenizer', return_value=None):
            # Should use character-based approximation
            chunks = chunk_text_by_tokens(MEDIUM_TEXT, token_limit=50)
            assert len(chunks) > 1
            
            # Each chunk should be approximately 50*4=200 characters
            for chunk in chunks:
                assert len(chunk) <= 50 * BYTES_PER_TOKEN_APPROX
    
    def test_estimate_tokens_from_bytes(self):
        """Test estimating tokens from byte count."""
        assert estimate_tokens_from_bytes(100) == 100 // BYTES_PER_TOKEN_APPROX
        assert estimate_tokens_from_bytes(1000) == 1000 // BYTES_PER_TOKEN_APPROX
        assert estimate_tokens_from_bytes(0) == 0
    
    def test_estimate_tokens_in_file(self, tmp_path):
        """Test estimating tokens in a file."""
        # Create a temporary file with known content
        test_file = tmp_path / "test_file.txt"
        test_file.write_text(MEDIUM_TEXT)
        
        # Estimate tokens in the file
        token_count = estimate_tokens_in_file(str(test_file))
        assert token_count > 0
        
        # Verify count
        expected_count = count_tokens(MEDIUM_TEXT)
        assert token_count == expected_count
        
        # Test with nonexistent file - suppress expected error logs
        with patch('core.utils.tokenization.logger.error') as mock_error:
            token_count = estimate_tokens_in_file(str(tmp_path / "nonexistent.txt"))
            assert token_count == 0
            # Verify error was logged but suppressed in output
            assert mock_error.call_count >= 1
        
    def test_estimate_tokens_in_file_fallback(self, tmp_path):
        """Test token estimation fallback for file when reading fails."""
        # Create a temporary file
        test_file = tmp_path / "test_file.bin"
        with open(test_file, "wb") as f:
            f.write(b'\x00' * 1000)  # Binary content
            
        # Mock open to raise an exception and suppress expected logfire errors
        with patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'\x00', 0, 1, 'invalid start byte')):
            with patch('core.utils.tokenization.logger.error') as mock_error:
                token_count = estimate_tokens_in_file(str(test_file))
                # Should fallback to file size estimation
                assert token_count == 1000 // BYTES_PER_TOKEN_APPROX
                # Verify error was logged but suppressed in output
                assert mock_error.call_count >= 1

if __name__ == "__main__":
    # Run all tests even if some fail
    pytest.main(["-vs", "--tb=short", "--no-header", "--continue-on-collection-errors", __file__]) 