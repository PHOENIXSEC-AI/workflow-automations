"""
Application initialization module.
This should be imported early in the application lifecycle to set up global configurations.
"""

from core.utils.logger.logger_factory import LoggerFactory
from core.config import app_config

def initialize_app(trace_enabled: bool = True):
    """
    Initialize the application with necessary configurations.
    
    Args:
        trace_enabled: Whether to enable Logfire tracing
    """
    # Initialize Logfire tracing if enabled
    if trace_enabled and app_config.LOGFIRE_API_KEY:
        LoggerFactory.initialize_tracing()

# Initialize by default when this module is imported
initialize_app() 