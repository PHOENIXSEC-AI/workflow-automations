"""
Simple utility for generating markdown from data objects.
"""
import json
from typing import Any, Optional


def custom_json_serializer(obj):
    """
    Custom JSON serializer to handle objects that aren't directly JSON serializable.
    
    Args:
        obj: The object to serialize
        
    Returns:
        A JSON serializable representation of the object
    """
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    elif hasattr(obj, 'to_dict'):
        return obj.to_dict()
    elif hasattr(obj, 'to_json'):
        return obj.to_json()
    else:
        return str(obj)


def convert_to_serializable(data):
    """
    Convert complex data structures into JSON-serializable form.
    
    Args:
        data: The data to convert
        
    Returns:
        JSON-serializable version of the data
    """
    if isinstance(data, dict):
        return {k: convert_to_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_serializable(item) for item in data]
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    else:
        # Handle custom objects
        if hasattr(data, 'to_dict'):
            return convert_to_serializable(data.to_dict())
        elif hasattr(data, '__dict__'):
            return convert_to_serializable(data.__dict__)
        else:
            return str(data)


def json_to_markdown(data: Any, title: Optional[str] = None, target_repo_url: Optional[str] = None) -> str:
    """
    Convert a JSON-serializable object to a markdown string with formatted sections.
    
    Args:
        data: The data dictionary to convert to markdown
        title: Optional title for the markdown document
        target_repo_url: Optional repository URL if not included in data
        
    Returns:
        A formatted markdown string
    """
    markdown = ""
    repo_name = ""
    repo_url = None
    
    # Add title if provided
    if title:
        markdown += f"# {title}\n\n"
    
    # Extract repository info if available
    try:
        repo_url = data.get('repo_url', target_repo_url)
        # Extract repository name from URL if available
        if repo_url and '/' in repo_url:
            repo_name = repo_url.split('/')[-1]
    except (AttributeError, TypeError):
        # Handle case where data is not a dict
        if target_repo_url:
            repo_url = target_repo_url
            if '/' in repo_url:
                repo_name = repo_url.split('/')[-1]
    
    if repo_url:
        markdown += f"## Repository\n\n"
        if repo_name:
            markdown += f"**Name**: {repo_name}\n\n"
        markdown += f"**URL**: [{repo_url}]({repo_url})\n\n"
    
    # Convert data to serializable format
    serializable_data = convert_to_serializable(data)
    
    # markdown += "## Complete Analysis Data\n\n"
    markdown += "```json\n"
    try:
        markdown += json.dumps(serializable_data, indent=2, sort_keys=False)
    except TypeError as e:
        markdown += f"Error serializing data: {str(e)}\n"
        markdown += f"Data type: {type(data)}\n"
        # Fallback to string representation
        markdown += str(data)
    markdown += "\n```\n"
    
    return markdown


def repomix_results_to_markdown(data: Any, repo_url: Optional[str] = None, repo_path: Optional[str] = None) -> str:
    """
    Convert repository analysis results to markdown format.
    
    This function handles RepomixResultData objects by properly converting them
    to serializable data before generating the markdown.
    
    Args:
        data: Repository analysis data (could be RepomixResultData object)
        repo_url: Optional repository URL for remote repositories
        repo_path: Optional repository path for local repositories
        
    Returns:
        Formatted markdown string
    """
    # Extract repo name if URL is provided
    repo_name = ""
    if repo_url and '/' in repo_url:
        repo_name = repo_url.split('/')[-1]
    elif repo_path and '/' in repo_path:
        # For local repositories, extract the directory name
        repo_name = repo_path.rstrip('/').split('/')[-1]
    
    # Generate title
    if repo_name:
        title = f"Repository Analysis: {repo_name}"
    else:
        title = "Repository Analysis"
    
    # Add repository path info to data if provided
    if repo_path and isinstance(data, dict):
        data = {**data, "repo_path": repo_path}
    
    # Generate markdown with proper serialization
    return json_to_markdown(
        data=data,
        title=title,
        target_repo_url=repo_url
    )

def generic_results_to_markdown(data: Any) -> str:
    return json_to_markdown(data)

__all__ = ["repomix_results_to_markdown", "generic_results_to_markdown"] 