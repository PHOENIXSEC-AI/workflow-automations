import os
import logging
from typing import Dict, Optional

import logfire
from rich.console import Console
from rich.logging import RichHandler

from .custom_logger import CustomLogger

from src.core.config import app_config

class LoggerFactory:
    """Singleton factory class for creating and caching loggers with rich console output and logfire tracing."""
    
    # Class variable to store logger instances
    _logger_instances: Dict[str, CustomLogger] = {}
    
    # Flag to track if logfire has been set up
    _logfire_initialized: bool = False
    
    @classmethod
    def initialize_tracing(cls):
        """
        Initialize Logfire tracing once at application startup.
        This method should be called early in the application lifecycle.
        """
        if not cls._logfire_initialized:
            cls._setup_logfire_tracing()
            cls._logfire_initialized = True
            return True
        return False
    
    @classmethod
    def get_logger(cls, name: Optional[str] = None, log_level: int = None, trace_enabled: bool = True) -> CustomLogger:
        """
        Get or create a logger configured with rich console output and logfire tracing.
        Falls back to Prefect's run logger when in a Prefect flow context.

        Args:
            name: The name of the logger (if None, automatically detects the caller's module name)
            log_level: The logging level (default: from app_config.log_level)
            trace_enabled: Whether to enable Logfire tracing (default: True)

        Returns:
            A configured CustomLogger instance
        """
        # If name is not provided, get the caller's module name
        if name is None:
            name = cls._get_caller_module_name()
        
        # If log_level is not provided, use the app_config
        if log_level is None:
            # Convert string log level to int
            log_level_str = app_config.log_level
            numeric_level = getattr(logging, log_level_str) if isinstance(log_level_str, str) else log_level_str
            log_level = numeric_level if isinstance(numeric_level, int) else logging.INFO
        
        # Create a cache key based on the logger name and trace setting
        cache_key = f"{name}_{trace_enabled}"
        
        # Return cached logger if it exists
        if cache_key in cls._logger_instances:
            return cls._logger_instances[cache_key]
        
        # Setup Logfire tracing if requested and not already initialized
        if trace_enabled:
            cls.initialize_tracing()
            
        # Create the base logger
        try:
            from prefect.logging import get_run_logger
            base_logger = get_run_logger()
        except Exception:
            # Configure rich logger
            logging.basicConfig(
                level=log_level,
                format="%(message)s",
                datefmt="[%X]",
                handlers=[RichHandler(console=Console(), rich_tracebacks=True)]
            )
            base_logger = logging.getLogger(name)
        
        # Create the custom logger wrapper and cache it
        custom_logger = CustomLogger(base_logger, use_trace=trace_enabled)
        cls._logger_instances[cache_key] = custom_logger
        
        return custom_logger
    
    @staticmethod
    def _setup_logfire_tracing():
        """Configure Logfire tracing for AI operations."""
        
        # Get logfire token and check if it's present
        logfire_token = os.getenv('LOGFIRE_API_KEY', None)
        send_to_logfire = bool(logfire_token)
        
        # Configure logfire instrumentation
        logfire.configure(
            environment="dev" if app_config.is_development() else 'prod',
            service_name='workflow-agents',
            token=logfire_token,
            send_to_logfire=send_to_logfire,  # Set to False if sending to another OpenTelemetry backend
        )
        
        
        logfire.instrument_pydantic_ai() 