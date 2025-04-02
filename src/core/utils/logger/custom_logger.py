import logging
import logfire

class CustomLogger:
    """Custom logger that primarily uses logfire tracing with fallback to standard logging."""
    
    def __init__(self, logger: logging.Logger, use_trace: bool = True):
        """
        Initialize a custom logger with logfire as primary logging destination.
        
        Args:
            logger: The base logger instance for fallback logging
            use_trace: Whether this logger should output to logfire (default: True)
        """
        self.logger = logger
        self.use_trace = use_trace
    
    def info(self, msg: str, *args, **kwargs):
        """Log an info message primarily to logfire, with fallback to standard logger."""
        if self.use_trace:
            logfire.info(msg)
        self.logger.info(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """Log an error message primarily to logfire, with fallback to standard logger."""
        if self.use_trace:
            logfire.error(msg)
        self.logger.error(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """Log a warning message primarily to logfire, with fallback to standard logger."""
        if self.use_trace:
            logfire.warning(msg)
        self.logger.warning(msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        """Log a debug message primarily to logfire, with fallback to standard logger."""
        if self.use_trace:
            logfire.debug(msg)
        self.logger.debug(msg, *args, **kwargs)
    
    # Keep the trace-specific methods for backward compatibility
    def log_info_w_trace(self, msg: str):
        """
        Legacy method for compatibility - now equivalent to info().
        
        Args:
            msg: The message to log
        """
        self.info(msg)
    
    def log_error_w_trace(self, msg: str, stack_info: bool = False):
        """
        Legacy method for compatibility - now equivalent to error().
        
        Args:
            msg: The message to log
            stack_info: Whether to include stack information
        """
        if self.use_trace:
            logfire.error(msg)
        self.logger.error(msg, stack_info=stack_info)
    
    def log_warning_w_trace(self, msg: str):
        """
        Legacy method for compatibility - now equivalent to warning().
        
        Args:
            msg: The message to log
        """
        self.warning(msg) 