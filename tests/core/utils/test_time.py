"""
Tests for time utilities.

This file tests the time utility functions used for measuring
durations and formatting time values.
"""
import time
import pytest

from core.utils.time import get_run_duration, format_duration


def test_get_run_duration():
    """Test the get_run_duration function accurately measures elapsed time."""
    # Test with a small delay
    start_time = time.time()
    time.sleep(0.1)  # Sleep for 100ms
    duration = get_run_duration(start_time)
    
    # The duration should be approximately 0.1s (with some margin for execution time)
    assert 0.09 <= duration <= 0.15, f"Expected duration around 0.1s, got {duration}s"
    
    # Test with no delay
    start_time = time.time()
    duration = get_run_duration(start_time)
    
    # The duration should be very small (near zero)
    assert duration < 0.01, f"Expected very small duration, got {duration}s"


def test_format_duration_microseconds():
    """Test formatting durations in the microsecond range."""
    # Test microseconds format (< 0.001s)
    assert format_duration(0.0000123) == "12.30µs"
    assert format_duration(0.0005) == "500.00µs"
    assert format_duration(0.000999) == "999.00µs"


def test_format_duration_milliseconds():
    """Test formatting durations in the millisecond range."""
    # Test milliseconds format (0.001s to 1s)
    assert format_duration(0.001) == "1.00ms"
    assert format_duration(0.0123) == "12.30ms"
    assert format_duration(0.5) == "500.00ms"
    assert format_duration(0.999) == "999.00ms"


def test_format_duration_seconds():
    """Test formatting durations in the seconds range."""
    # Test seconds format (1s to 60s)
    assert format_duration(1) == "1.00s"
    assert format_duration(1.5) == "1.50s"
    assert format_duration(30) == "30.00s"
    assert format_duration(59.99) == "59.99s"


def test_format_duration_minutes():
    """Test formatting durations in the minutes range."""
    # Test minutes format (60s and above)
    assert format_duration(60) == "1m 0.00s"
    assert format_duration(61.5) == "1m 1.50s"
    assert format_duration(122) == "2m 2.00s"
    assert format_duration(3600) == "60m 0.00s"  # 1 hour
    assert format_duration(3661.5) == "61m 1.50s"  # 1 hour, 1 minute, 1.5 seconds


def test_format_duration_edge_cases():
    """Test formatting with edge cases."""
    # Test with zero
    assert format_duration(0) == "0.00µs"
    
    # Test with negative values (not expected in normal use, but should still format)
    assert format_duration(-0.5) == "-500.00ms"
    
    # Test with very large value
    assert "m" in format_duration(86400), "Large values should use minutes format"


if __name__ == "__main__":
    # Run all tests even if some fail
    pytest.main(["-vs", "--tb=short", "--no-header", "--continue-on-collection-errors", __file__]) 