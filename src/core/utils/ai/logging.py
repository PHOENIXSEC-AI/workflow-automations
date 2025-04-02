"""
Utility functions for AI operation logging.
"""
from core.utils import LoggerFactory

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

def create_llm_request_error(error, context=None):
    """
    Log LiteLLM proxy errors with detailed information for troubleshooting.
    
    Args:
        error: The exception object 
        context: Optional dictionary with additional context information
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    error_details = {
        "error_type": error_type,
        "error_message": error_msg,
        "context": context or {},
    }
    
    # Add status code if it exists
    if hasattr(error, 'status_code'):
        error_details["status_code"] = error.status_code
    
    # Add request and response details if they exist
    if hasattr(error, 'request'):
        error_details["request_url"] = getattr(getattr(error, 'request', None), 'url', 'unknown')
        error_details["request_method"] = getattr(getattr(error, 'request', None), 'method', 'unknown')
    
    # Log as warning for retryable errors, error for others
    is_retryable = any([
        error_type in ('APIConnectionError', 'APITimeoutError', 'RateLimitError'),
        hasattr(error, 'status_code') and error.status_code in (429, 500, 502, 503, 504)
    ])
    
    log_level = "warning" if is_retryable else "error"
    log_message = f"LMM Request Error: {error_type} - {error_msg}"
    
    if log_level == "warning":
        logger.warning(log_message)
    else:
        logger.error(log_message)
    
    return error_details