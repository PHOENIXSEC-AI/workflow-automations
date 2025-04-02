"""
Utilities for working with tokens in text, using tiktoken library.
"""
import os
import tiktoken
from typing import List, Optional, Union

from core.utils import LoggerFactory

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

# Constants - sourced from application config
# These should be exposed to end users via the configuration settings
DEFAULT_TOKENIZER = app_config.DEFAULT_TOKENIZER  # Default tokenizer to use (o200k_base is recommended)
DEFAULT_TOKEN_LIMIT = app_config.TOKEN_LIMIT  # Maximum tokens per file chunk
BYTES_PER_TOKEN_APPROX = app_config.BYTES_PER_TOKEN  # Approximate bytes per token for estimation
MONGODB_MAX_TOKEN_ESTIMATE = app_config.MAX_SAFE_TOKEN_COUNT  # Maximum tokens that can safely fit in a MongoDB document

# from core.utils.logger_factory import LoggerFactory

# Default token limit per file chunk - can be overridden
DEFAULT_TOKEN_LIMIT = int(os.getenv('TOKEN_FILE_LIMIT', '50000'))

# Average bytes per token for approximation (useful for quick checks)
# This is an approximation based on research - typically 1 token is around 4 chars in English
BYTES_PER_TOKEN_APPROX = 4

def get_tokenizer(encoding_name: str = DEFAULT_TOKENIZER):
    """
    Get a tokenizer for counting tokens in text.
    
    Args:
        encoding_name: The name of the encoding to use (default from app_config)
        
    Returns:
        A tiktoken encoding object
    """
    try:
        # First try to use get_encoding with the name
        return tiktoken.get_encoding(encoding_name)
    except Exception as e:
        try:
            # If that fails, try to use encoding_for_model
            logger.info(f"Falling back to encoding_for_model for {encoding_name}")
            return tiktoken.encoding_for_model(encoding_name)
        except Exception as e2:
            logger.warning(f"Error getting tokenizer {encoding_name}: {e}. Using approximation method instead.")
            return None

def count_tokens(text: str, encoding_name: str = DEFAULT_TOKENIZER) -> int:
    """
    Count the number of tokens in a text string.
    
    Args:
        text: The text to count tokens in
        encoding_name: The name of the encoding to use
        
    Returns:
        Number of tokens
    """
    if not text:
        return 0
        
    try:
        # Try to use tiktoken for accurate token counting
        tokenizer = get_tokenizer(encoding_name)
        if tokenizer:
            return len(tokenizer.encode(text))
    except Exception as e:
        logger.warning(f"Error counting tokens with tiktoken: {e}. Using approximation instead.")
    
    # Fallback to approximation if tiktoken fails
    # Approximate based on character count (1 token ~= 4 chars in English)
    return len(text) // BYTES_PER_TOKEN_APPROX

def chunk_text_by_tokens(text: str, token_limit: int = DEFAULT_TOKEN_LIMIT, encoding_name: str = DEFAULT_TOKENIZER) -> List[str]:
    """
    Split text into chunks based on token count.
    
    Args:
        text: The text to split
        token_limit: Maximum tokens per chunk
        encoding_name: The name of the encoding to use
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
        
    # Try to use tiktoken for accurate chunking
    try:
        tokenizer = get_tokenizer(encoding_name)
        if tokenizer:
            tokens = tokenizer.encode(text)
            
            if len(tokens) <= token_limit:
                return [text]
                
            # Split into chunks based on token limit
            chunks = []
            for i in range(0, len(tokens), token_limit):
                chunk_tokens = tokens[i:i + token_limit]
                chunk_text = tokenizer.decode(chunk_tokens)
                chunks.append(chunk_text)
                
            return chunks
    except Exception as e:
        logger.warning(f"Error chunking by tokens with tiktoken: {e}. Using approximation method instead.")
    
    # Fallback to approximation if tiktoken fails
    # Approximate based on character count (token_limit tokens ~= token_limit*4 chars)
    char_limit = token_limit * BYTES_PER_TOKEN_APPROX
    
    if len(text) <= char_limit:
        return [text]
        
    chunks = []
    for i in range(0, len(text), char_limit):
        chunks.append(text[i:i + char_limit])
        
    return chunks

def estimate_tokens_from_bytes(byte_size: int) -> int:
    """
    Estimate the number of tokens from a byte count.
    
    This is a rough approximation and should only be used for quick checks.
    
    Args:
        byte_size: Size in bytes
        
    Returns:
        Estimated number of tokens
    """
    return byte_size // BYTES_PER_TOKEN_APPROX

def estimate_tokens_in_file(file_path: str, encoding_name: str = DEFAULT_TOKENIZER) -> int:
    """
    Estimate the number of tokens in a file.
    
    Args:
        file_path: Path to the file
        encoding_name: The name of the encoding to use
        
    Returns:
        Estimated number of tokens
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return count_tokens(content, encoding_name)
    except Exception as e:
        logger.error(f"Error estimating tokens in file {file_path}: {e}")
        # Fallback to file size approximation
        try:
            byte_size = os.path.getsize(file_path)
            return estimate_tokens_from_bytes(byte_size)
        except Exception as size_err:
            logger.error(f"Error getting file size for {file_path}: {size_err}")
            return 0 