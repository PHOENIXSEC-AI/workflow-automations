"""
Time utilities for measuring performance and durations.
"""
import time

def get_run_duration(start_time: float) -> float:
    """
    Calculate the duration of a process.
    
    Args:
        start_time: Timestamp when the process started
        
    Returns:
        Duration in seconds as a float
    """
    end_time = time.time()
    return end_time - start_time

def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds to a human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "2m 30s" or "150ms")
    """
    # Handle negative values
    is_negative = seconds < 0
    abs_seconds = abs(seconds)
    
    # Format the absolute value
    if abs_seconds < 0.001:
        formatted = f"{abs_seconds * 1000000:.2f}µs"
    elif abs_seconds < 1:
        formatted = f"{abs_seconds * 1000:.2f}ms"
    elif abs_seconds < 60:
        formatted = f"{abs_seconds:.2f}s"
    else:
        minutes = int(abs_seconds // 60)
        remaining_seconds = abs_seconds % 60
        formatted = f"{minutes}m {remaining_seconds:.2f}s"
    
    # Add the negative sign if needed
    if is_negative:
        return f"-{formatted}"
    else:
        return formatted 