#!/usr/bin/env python
"""
A module to run the repomix tool programmatically.
"""

import os
import subprocess
import json
import re

from core.config import app_config
from core.utils import LoggerFactory

logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level,trace_enabled=True)

def clean_terminal_output(text: str) -> str:
    """
    Clean terminal output by removing ANSI escape codes and progress indicators.
    
    Args:
        text: Raw terminal output
        
    Returns:
        Cleaned text
    """
    # Remove ANSI escape sequences (like color codes and cursor movements)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    
    # Remove terminal control sequences
    text = re.sub(r'\[2K|\[1A|\[G', '', text)
    
    # Convert spinner characters to simple status indicators
    spinner_chars = ['⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏', '⠋']
    for char in spinner_chars:
        text = text.replace(char, '•')
    
    # Clean up multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text


def run_repomix(
    remote_url: str,
    config_path: str,
    result_path: str
) -> tuple[int, str, str]:
    """
    Run the repomix tool with the given parameters.
    
    Args:
        remote_url: Remote repository URL
        config_path: Path to the configuration file
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    # Build the command
    
    assert config_path is not None, "Repomix requires config_path, please specify path"
    assert result_path is not None, "Repomix requires output_path, please specify path"
    
    # Ensure config_path and result_path are absolute paths
    abs_config_path = os.path.abspath(config_path)
    abs_output_file = os.path.abspath(result_path)
    
    cmd = ['repomix', '--remote', remote_url, '--config', abs_config_path, '--output', abs_output_file]
    
    try:
        # Run the repomix command
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        
        # If output file is specified, append the tool output with markers
        if abs_output_file and result.stdout:
            try:
                # Clean up the terminal output
                cleaned_output = clean_terminal_output(result.stdout)
                
                # First, check if the file exists and read its content
                content = ""
                if os.path.exists(abs_output_file):
                    with open(abs_output_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                
                # Append the tool output with markers
                with open(abs_output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                    # Add tool output section with markers
                    f.write("\n<tool_output>\n")
                    f.write(cleaned_output)
                    f.write("\n</tool_output>\n")
            except Exception as e:
                logger.error(f"Error: Failed to write tool output to file: {e}")
        
        # return 1, result.stdout, result.stderr
        return 1, abs_output_file, result.stderr
    except subprocess.CalledProcessError as e:
        # return e.returncode, e.stdout, e.stderr
        return e.returncode, "", e.stderr
    except Exception as e:
        # return 0, "", str(e)
        return 0,"",str(e)

def run_repomix_local(
    local_repo_path: str,
    config_path: str,
    result_path: str
) -> tuple[int, str, str]:
    """
    Run the repomix tool on a local repository path.
    
    This function changes the current working directory to the local repository path
    and runs repomix without --local or --remote flags. This approach allows repomix
    to analyze the current directory as the repository, which provides more accurate
    results than using the --local flag. The function ensures to change back to the
    original directory after the analysis is complete, even if an error occurs.
    
    Args:
        local_repo_path: Path to the local repository
        config_path: Path to the configuration file
        result_path: Path where the result will be saved
        
    Returns:
        Tuple of (return_code, absolute_output_file_path, stderr)
    """
    # Build the command
    
    assert os.path.exists(local_repo_path), f"Local repository path {local_repo_path} does not exist"
    assert config_path is not None, "Repomix requires config_path, please specify path"
    assert result_path is not None, "Repomix requires output_path, please specify path"
    
    # Ensure config_path and result_path are absolute paths
    abs_config_path = os.path.abspath(config_path)
    abs_output_file = os.path.abspath(result_path)
    
    # Save current directory to return to it later
    original_dir = os.getcwd()
    
    logger.info(f"Analyzing local repository at: {local_repo_path}")
    logger.info(f"Using config file: {abs_config_path}")
    logger.info(f"Output will be saved to: {abs_output_file}")
    
    try:
        # Change to the local repository directory
        logger.debug(f"Changing directory to: {local_repo_path}")
        os.chdir(local_repo_path)
        
        # Run repomix without --local or --remote flags to analyze current directory
        cmd = ['repomix', '--config', abs_config_path, '--output', abs_output_file]
        logger.debug(f"Running command: {' '.join(cmd)}")
        
        # Run the repomix command
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        
        # If output file is specified, append the tool output with markers
        if abs_output_file and result.stdout:
            try:
                # Clean up the terminal output
                cleaned_output = clean_terminal_output(result.stdout)
                
                # First, check if the file exists and read its content
                content = ""
                if os.path.exists(abs_output_file):
                    with open(abs_output_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                
                # Append the tool output with markers
                with open(abs_output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                    # Add tool output section with markers
                    f.write("\n<tool_output>\n")
                    f.write(cleaned_output)
                    f.write("\n</tool_output>\n")
            except Exception as e:
                logger.error(f"Error: Failed to write tool output to file: {e}")
        
        logger.info(f"Analysis completed successfully. Output saved to: {abs_output_file}")
        return 1, abs_output_file, result.stderr
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running repomix: {e}")
        return e.returncode, "", e.stderr
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 0, "", str(e)
    finally:
        # Always return to the original directory
        logger.debug(f"Changing back to original directory: {original_dir}")
        os.chdir(original_dir)

__all__ = ["run_repomix", "run_repomix_local"]