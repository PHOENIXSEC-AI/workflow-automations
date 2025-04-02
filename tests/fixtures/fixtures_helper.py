"""
Helper module for working with compressed test fixtures.
"""

import os
import gzip
import tempfile
import shutil
import atexit
import json
from pathlib import Path

# Track temporary files to clean up on exit
TEMP_FILES = []

def get_fixture_path(fixture_name):
    """
    Gets the path to a fixture file, decompressing it if necessary.
    
    Args:
        fixture_name: Base name of the fixture file (e.g., "large_file.txt")
    
    Returns:
        Path to the fixture file (decompressed if needed)
    """
    fixture_dir = Path(__file__).parent
    
    # Check for uncompressed version first
    uncompressed_path = fixture_dir / fixture_name
    if uncompressed_path.exists():
        return str(uncompressed_path)
    
    # Check for compressed version
    compressed_path = fixture_dir / f"{fixture_name}.gz"
    if compressed_path.exists():
        # Create a temporary file for the decompressed content
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{fixture_name}")
        temp_file.close()
        
        # Decompress to the temporary file
        with gzip.open(str(compressed_path), 'rb') as f_in:
            with open(temp_file.name, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Track for cleanup
        TEMP_FILES.append(temp_file.name)
        return temp_file.name
    
    raise FileNotFoundError(f"Fixture {fixture_name} not found (checked both compressed and uncompressed)")

def read_fixture(fixture_name, binary=False):
    """
    Reads the content of a fixture file, decompressing if necessary.
    
    Args:
        fixture_name: Base name of the fixture file
        binary: If True, return bytes instead of string
    
    Returns:
        Content of the fixture file
    """
    mode = 'rb' if binary else 'r'
    with open(get_fixture_path(fixture_name), mode) as f:
        return f.read()

# Clean up temporary files on exit
def _cleanup_temp_files():
    for path in TEMP_FILES:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass  # Best effort cleanup

atexit.register(_cleanup_temp_files)
