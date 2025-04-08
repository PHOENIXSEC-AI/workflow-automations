#!/usr/bin/env python3
"""
Script to generate test fixtures for MongoDB document size limit testing.
This creates files of various sizes including one exceeding MongoDB's 16MB limit.

The fixtures can be compressed to save disk space and decompressed when needed.
"""

import os
import sys
import shutil
import platform
import json
import gzip
import time
from pathlib import Path

# ANSI colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

# Configuration
FIXTURE_DIR = "tests/fixtures"
REQUIRED_SPACE_MB = 70
MAX_OVERSIZED_FILE_SIZE_MB = 50
COMPRESS_FILES = True  # Set to True by default to compress files

def print_colored(color, message):
    """Print a message with the specified color."""
    print(f"{color}{message}{Colors.NC}")

def check_disk_space(required_mb):
    """Check if there's enough disk space for generating fixtures."""
    # Get the total, used, and free space in bytes
    if platform.system() == 'Windows':
        # Windows
        free_bytes = shutil.disk_usage('.').free
    else:
        # Unix/Linux/macOS
        free_bytes = shutil.disk_usage('.').free
    
    # Convert to MB
    free_mb = free_bytes // (1024 * 1024)
    
    print_colored(Colors.BLUE, f"Available disk space: {free_mb} MB")
    
    if free_mb < required_mb:
        print_colored(Colors.RED, f"Error: Not enough disk space. Required: {required_mb} MB, Available: {free_mb} MB")
        return False
    
    print_colored(Colors.GREEN, f"Sufficient disk space available: {free_mb} MB")
    return True

def get_confirmation(prompt):
    """Get confirmation from the user."""
    # Auto-confirm in CI environments
    if os.environ.get('CI'):
        print(f"CI environment detected, auto-confirming: {prompt}")
        return True
    
    response = input(f"{Colors.YELLOW}{prompt} (y/n): {Colors.NC}")
    return response.lower().startswith('y')

def create_small_file(fixture_dir):
    """Create a small test fixture (~1KB)."""
    print("Creating small test fixture...")
    filepath = os.path.join(fixture_dir, "small_file.txt")
    with open(filepath, 'w') as f:
        f.write("This is a small test file for MongoDB storage testing.\n")
        f.write("It contains just a few lines of text and won't need chunking.\n")
    
    file_size = os.path.getsize(filepath)
    print_colored(Colors.GREEN, f"Small file created: {format_size(file_size)}")
    return filepath

def create_medium_file(fixture_dir):
    """Create a medium test fixture (~100KB)."""
    print("Creating medium test fixture...")
    filepath = os.path.join(fixture_dir, "medium_file.txt")
    
    try:
        with open(filepath, 'w') as f:
            f.write("This is a medium-sized content for testing. " * 2000)
    except Exception as e:
        print_colored(Colors.YELLOW, f"Error in Python method: {e}")
        print_colored(Colors.YELLOW, "Using fallback method...")
        
        with open(filepath, 'w') as f:
            for _ in range(2000):
                f.write("This is a medium-sized content for testing.\n")
    
    file_size = os.path.getsize(filepath)
    print_colored(Colors.GREEN, f"Medium file created: {format_size(file_size)}")
    return filepath

def create_large_file(fixture_dir):
    """Create a large test fixture (~1MB)."""
    print("Creating large test fixture...")
    filepath = os.path.join(fixture_dir, "large_file.txt")
    
    try:
        with open(filepath, 'w') as f:
            f.write("This is a large content that should require token-based chunking. " * 20000)
    except Exception as e:
        print_colored(Colors.YELLOW, f"Error in Python method: {e}")
        print_colored(Colors.YELLOW, "Using fallback method...")
        
        with open(filepath, 'w') as f:
            for _ in range(20000):
                f.write("This is a large content that should require token-based chunking.\n")
    
    file_size = os.path.getsize(filepath)
    print_colored(Colors.GREEN, f"Large file created: {format_size(file_size)}")
    return filepath

def create_oversized_file(fixture_dir, max_size_mb):
    """Create an oversized test fixture (~25MB)."""
    print("Creating oversized test fixture exceeding MongoDB's limit...")
    filepath = os.path.join(fixture_dir, "oversized_file.txt")
    
    # Target size - aim for 25MB to properly exceed MongoDB's 16MB limit
    target_size_bytes = 25 * 1024 * 1024
    
    try:
        print("Using simple method to generate oversized file...")
        with open(filepath, 'wb') as f:
            f.write(b'X' * target_size_bytes)
    except Exception as e:
        print_colored(Colors.YELLOW, f"Error in Python binary method: {e}")
        print_colored(Colors.YELLOW, "Using text fallback method...")
        
        try:
            with open(filepath, 'w') as f:
                # Each line is approximately 60 bytes
                # Writing in chunks to avoid memory issues
                chunk_size = 10000
                line = "This is oversized content to exceed MongoDB document size limits.\n"
                
                current_size = 0
                while current_size < target_size_bytes:
                    for _ in range(chunk_size):
                        f.write(line)
                    
                    f.flush()
                    current_size = os.path.getsize(filepath)
                    print_colored(Colors.YELLOW, f"Generated approximately {current_size // (1024 * 1024)}MB so far...")
                    
                    if current_size >= target_size_bytes:
                        break
        except Exception as e:
            print_colored(Colors.RED, f"Failed to create oversized file: {e}")
            return None
    
    file_size = os.path.getsize(filepath)
    print_colored(Colors.GREEN, f"Oversized file generated: {format_size(file_size)}")
    return filepath

def create_token_limits_file(fixture_dir):
    """Create a JSON file with token count limits."""
    print("Creating token count limit reference file...")
    filepath = os.path.join(fixture_dir, "token_limits.json")
    
    # Import the actual values from the app configuration
    try:
        print("Trying to import actual config values from core.config...")
        # First try to import actual values
        from core.config import app_config
        
        # Get the values from app_config
        max_safe_token_count = app_config.MAX_SAFE_TOKEN_COUNT
        token_limit = app_config.TOKEN_LIMIT
        bytes_per_token = app_config.BYTES_PER_TOKEN
        default_tokenizer = app_config.DEFAULT_TOKENIZER
        
        print(f"Successfully imported config values: MAX_SAFE_TOKEN_COUNT={max_safe_token_count}")
    except ImportError:
        print("Could not import from core.config, using hardcoded values...")
        # Fallback to hardcoded values that match what's in core.config.__init__.py
        max_safe_token_count = 4000000
        token_limit = 50000
        bytes_per_token = 4
        default_tokenizer = "o200k_base"
    
    # MongoDB's maximum document size is 16MB (16,777,216 bytes)
    mongodb_max_size = 16777216
    
    # Calculate the safe document size based on the max safe token count
    # This ensures the values are consistent with each other
    mongodb_safe_size = max_safe_token_count * bytes_per_token
    
    limits = {
        "mongodb_max_document_size": mongodb_max_size,  # 16MB in bytes
        "mongodb_safe_document_size": mongodb_safe_size,  # Based on max_safe_token_count
        "max_safe_token_count": max_safe_token_count,  # From app_config
        "default_token_limit": token_limit,  # From app_config
        "bytes_per_token": bytes_per_token,  # From app_config
        "default_tokenizer": default_tokenizer  # From app_config
    }
    
    with open(filepath, 'w') as f:
        json.dump(limits, f, indent=2)
    
    print_colored(Colors.GREEN, "Token limits reference file created")
    print_colored(Colors.BLUE, f"Max safe token count: {max_safe_token_count}")
    print_colored(Colors.BLUE, f"MongoDB safe document size: {mongodb_safe_size} bytes (~{mongodb_safe_size/1024/1024:.1f}MB)")
    
    return filepath

def format_size(size_bytes):
    """Format byte size to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024 or unit == 'GB':
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024

def compress_file(filepath):
    """Compress a file using gzip and return compressed filepath."""
    if not os.path.exists(filepath):
        print_colored(Colors.RED, f"File not found for compression: {filepath}")
        return None
    
    compressed_filepath = f"{filepath}.gz"
    
    # Don't compress JSON files, they're already small
    if filepath.endswith('.json'):
        return filepath
    
    try:
        print(f"Compressing {os.path.basename(filepath)}...")
        start_time = time.time()
        
        with open(filepath, 'rb') as f_in:
            with gzip.open(compressed_filepath, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        original_size = os.path.getsize(filepath)
        compressed_size = os.path.getsize(compressed_filepath)
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        print_colored(
            Colors.GREEN,
            f"Compressed {format_size(original_size)} → {format_size(compressed_size)} "
            f"({compression_ratio:.1f}% reduction) in {time.time() - start_time:.1f}s"
        )
        
        # Remove the original file to save space
        os.remove(filepath)
        return compressed_filepath
        
    except Exception as e:
        print_colored(Colors.RED, f"Compression failed: {e}")
        # Keep the original if compression fails
        return filepath

def create_manifest_file(fixture_dir, file_info):
    """Create a manifest file with information about the fixtures."""
    manifest_path = os.path.join(fixture_dir, "manifest.json")
    
    manifest = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "compressed": COMPRESS_FILES,
        "files": file_info
    }
    
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print_colored(Colors.GREEN, "Fixture manifest created")
    return manifest_path

def create_decompression_helper(fixture_dir):
    """Create a Python helper file for decompressing files in tests."""
    helper_path = os.path.join(fixture_dir, "fixtures_helper.py")
    
    with open(helper_path, 'w') as f:
        f.write('''"""
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
''')
    
    print_colored(Colors.GREEN, "Fixture helper module created for test decompression")
    return helper_path

def create_pytest_fixture_example(fixture_dir):
    """Create an example pytest fixture file for using the fixtures."""
    example_path = os.path.join(fixture_dir, "pytest_fixture_example.py")
    
    with open(example_path, 'w') as f:
        f.write('''"""
Example pytest fixtures for working with the test files.
Import these in your conftest.py or directly in your test files.
"""

import pytest
from pathlib import Path

# Import the fixture helper
fixtures_dir = Path(__file__).parent
import sys
sys.path.insert(0, str(fixtures_dir))
from fixtures_helper import get_fixture_path, read_fixture

@pytest.fixture
def small_file_path():
    """Fixture providing path to the small test file."""
    return get_fixture_path("small_file.txt")

@pytest.fixture
def medium_file_path():
    """Fixture providing path to the medium test file."""
    return get_fixture_path("medium_file.txt")

@pytest.fixture
def large_file_path():
    """Fixture providing path to the large test file."""
    return get_fixture_path("large_file.txt")

@pytest.fixture
def oversized_file_path():
    """Fixture providing path to the oversized test file."""
    return get_fixture_path("oversized_file.txt")

@pytest.fixture
def small_file_content():
    """Fixture providing content of the small test file."""
    return read_fixture("small_file.txt")

@pytest.fixture
def medium_file_content():
    """Fixture providing content of the medium test file."""
    return read_fixture("medium_file.txt")

@pytest.fixture
def large_file_content():
    """Fixture providing content of the large test file."""
    return read_fixture("large_file.txt")

# Usage example:
# def test_tokenization_with_large_file(large_file_path):
#     # The large file will be automatically decompressed if needed
#     with open(large_file_path) as f:
#         text = f.read()
#     assert len(text) > 0
''')
    
    print_colored(Colors.GREEN, "Pytest fixture example created")
    return example_path

def main():
    """Main execution function."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Generate test fixtures for MongoDB document size limit testing")
    parser.add_argument("--no-compress", action="store_true", help="Don't compress the generated files")
    parser.add_argument("--yes", "-y", action="store_true", help="Automatically answer yes to all prompts")
    args = parser.parse_args()
    
    global COMPRESS_FILES
    if args.no_compress:
        COMPRESS_FILES = False
    
    # Display warning and information
    print_colored(Colors.YELLOW, "===========================================================")
    print_colored(Colors.YELLOW, "WARNING: This script will generate test fixture files for")
    print_colored(Colors.YELLOW, "MongoDB document size limit testing, including an oversized")
    print_colored(Colors.YELLOW, "file that exceeds MongoDB's 16MB document size limit.")
    print_colored(Colors.YELLOW, "===========================================================")
    print("")
    print_colored(Colors.BLUE, f"The following files will be generated in {FIXTURE_DIR}:")
    print("- small_file.txt (~1KB)")
    print("- medium_file.txt (~100KB)")
    print("- large_file.txt (~1MB)")
    print("- oversized_file.txt (~25MB, exceeds MongoDB's 16MB limit)")
    print("- token_limits.json (reference information)")
    print("- fixtures_helper.py (for decompressing in tests)")
    print("- pytest_fixture_example.py")
    print(f"- manifest.json (fixture information)")
    if COMPRESS_FILES:
        print_colored(Colors.BLUE, "Files will be compressed with gzip to save disk space")
    print("")
    
    # Check disk space
    if not check_disk_space(REQUIRED_SPACE_MB):
        print_colored(Colors.RED, "Aborting due to insufficient disk space.")
        return 1
    
    # Get user confirmation (skip if --yes flag is provided)
    if not args.yes and not get_confirmation("Do you want to proceed with generating these test fixtures?"):
        print_colored(Colors.YELLOW, "Test fixture generation cancelled.")
        return 0
    
    # Create fixture directory if it doesn't exist
    os.makedirs(FIXTURE_DIR, exist_ok=True)
    
    print_colored(Colors.GREEN, "Generating test fixtures for MongoDB document size testing...")
    
    # Create the test fixtures
    generated_files = {}
    
    small_file = create_small_file(FIXTURE_DIR)
    if small_file:
        generated_files["small_file.txt"] = {"original_size": os.path.getsize(small_file)}
    
    medium_file = create_medium_file(FIXTURE_DIR)
    if medium_file:
        generated_files["medium_file.txt"] = {"original_size": os.path.getsize(medium_file)}
    
    large_file = create_large_file(FIXTURE_DIR)
    if large_file:
        generated_files["large_file.txt"] = {"original_size": os.path.getsize(large_file)}
    
    # The oversized file is optional
    if args.yes or get_confirmation("About to generate a large file (~25MB). Do you want to continue?"):
        oversized_file = create_oversized_file(FIXTURE_DIR, MAX_OVERSIZED_FILE_SIZE_MB)
        if oversized_file:
            generated_files["oversized_file.txt"] = {"original_size": os.path.getsize(oversized_file)}
    else:
        print_colored(Colors.YELLOW, "Oversized file generation skipped. Other fixtures are still available.")
    
    # Create token limits reference file
    token_limits_file = create_token_limits_file(FIXTURE_DIR)
    if token_limits_file:
        generated_files["token_limits.json"] = {"original_size": os.path.getsize(token_limits_file)}
    
    # Create helper files
    helper_file = create_decompression_helper(FIXTURE_DIR)
    if helper_file:
        generated_files["fixtures_helper.py"] = {"original_size": os.path.getsize(helper_file)}
    
    example_file = create_pytest_fixture_example(FIXTURE_DIR)
    if example_file:
        generated_files["pytest_fixture_example.py"] = {"original_size": os.path.getsize(example_file)}
    
    # Compress files if requested
    if COMPRESS_FILES:
        print_colored(Colors.BLUE, "Compressing files to save disk space...")
        for filename in list(generated_files.keys()):
            filepath = os.path.join(FIXTURE_DIR, filename)
            
            # Skip Python and JSON files from compression
            if filename.endswith(('.py', '.json')):
                continue
                
            if os.path.exists(filepath):
                compressed_path = compress_file(filepath)
                if compressed_path and compressed_path.endswith('.gz'):
                    generated_files[filename]["compressed"] = True
                    generated_files[filename]["compressed_size"] = os.path.getsize(compressed_path)
                    generated_files[filename]["compression_ratio"] = (
                        1 - generated_files[filename]["compressed_size"] / generated_files[filename]["original_size"]
                    ) * 100
                else:
                    generated_files[filename]["compressed"] = False
    
    # Create manifest file
    create_manifest_file(FIXTURE_DIR, generated_files)
    
    # Report file sizes
    print_colored(Colors.GREEN, "Test fixtures generated successfully:")
    total_original = 0
    total_final = 0
    
    for filename, info in generated_files.items():
        original_size = info.get("original_size", 0)
        total_original += original_size
        
        if COMPRESS_FILES and info.get("compressed", False):
            compressed_size = info.get("compressed_size", 0)
            ratio = info.get("compression_ratio", 0)
            print(f"- {filename}: {format_size(original_size)} → {format_size(compressed_size)} ({ratio:.1f}% reduction)")
            total_final += compressed_size
        else:
            print(f"- {filename}: {format_size(original_size)}")
            total_final += original_size
    
    if COMPRESS_FILES:
        overall_ratio = (1 - total_final / total_original) * 100 if total_original > 0 else 0
        print_colored(
            Colors.GREEN, 
            f"Total space: {format_size(total_original)} → {format_size(total_final)} ({overall_ratio:.1f}% reduction)"
        )
    else:
        print_colored(Colors.GREEN, f"Total space used: {format_size(total_original)}")
    
    print_colored(Colors.BLUE, "To use these fixtures in tests, import them from the fixtures directory.")
    print_colored(Colors.BLUE, "Example usage in your tests:")
    print("")
    print('''    from tests.fixtures.fixtures_helper import get_fixture_path
    
    def test_something():
        # This will decompress the file automatically if needed
        with open(get_fixture_path("large_file.txt")) as f:
            content = f.read()
        # Your test code here...
    ''')
    print("")
    print_colored(Colors.YELLOW, "WARNING: The oversized file is intended only for testing MongoDB's document size limits.")
    print_colored(Colors.YELLOW, "Delete it after testing if disk space is a concern.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 