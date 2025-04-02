"""
Configuration file for pytest.

This file is automatically loaded by pytest and can be used to add
fixtures, modify the Python path, and configure pytest behavior.
"""
import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 