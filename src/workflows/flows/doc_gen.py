import asyncio
from typing import List
from datetime import datetime
from pathlib import Path

from prefect import flow, task
from prefect.artifacts import create_markdown_artifact

from workflows.tasks.db_ops import db_retrieve_document_by_id
from core.utils import LoggerFactory

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

@flow(
    log_prints=True, 
    name="run_generate_docs", 
    result_storage="local-file-system/dev-result-storage",
    description="Build markdown docs from MongoDB object",
)
async def run_generate_docs(build_from_obj_id: str):
    """
    Generate markdown documentation based on a MongoDB document.
    
    Args:
        build_from_obj_id: MongoDB ObjectId of the document to use
        
    Returns:
        Path to the generated markdown file
    """
    # Retrieve MongoDB document by ID
    retrieval_result = await db_retrieve_document_by_id.fn(
        doc_id=build_from_obj_id,
        db_name="workflows",
        coll_name="repomix",
        create_artifact=False
    )
    
    if retrieval_result.is_failed():
        retrieval_result = await retrieval_result.result()
        raise ValueError(f"Failed to retrieve document: {getattr(retrieval_result,'errors',[])}")
    
    # Access the document data
    retrieval_result = await retrieval_result.result()
    
    doc = getattr(retrieval_result,'db_result', None)
    
    if not doc:
        raise ValueError(f"No document found with ID {build_from_obj_id}")
    
    # Generate markdown documentation
    markdown_content = generate_markdown_from_doc(doc)
    
    # Create artifact filename (repo name + timestamp)
    repo_name = doc.get("repository_name", "unnamed-repo")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    artifact_key = f"documentation-{repo_name}-{timestamp}"
    
    # Create markdown artifact
    artifact = await create_markdown_artifact(
        key=artifact_key,
        markdown=markdown_content,
        description=f"Documentation for {repo_name}",
    )
    
    # Also save to a file in the reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    filename = f"{repo_name.upper()}.md"
    filepath = reports_dir / filename
    
    with open(filepath, "w") as f:
        f.write(markdown_content)
    
    logger.info(f"Documentation saved to {filepath}")
    return str(filepath)

@task(name="generate_markdown_from_doc")
def generate_markdown_from_doc(doc):
    """
    Generate structured markdown from a MongoDB document.
    
    Args:
        doc: MongoDB document containing repository analysis data
        
    Returns:
        Formatted markdown content as a string
    """
    # Build the markdown content section by section
    content = []
    
    # Add metadata with document generation info
    content.append(generate_metadata_section())
    
    # Add executive summary
    content.append(generate_executive_summary(doc))
    
    # 1. Header section with main repository info
    content.append(generate_header_section(doc))
    
    # 2. Directory structure section
    content.append(generate_directory_structure_section(doc))
    
    # 3. Top files table from tool_output
    content.append(generate_top_files_section(doc))
    
    # 4. Summary section from tool_output
    content.append(generate_summary_section(doc))
    
    # 5. Files details section
    content.append(generate_files_section(doc))
    
    # Join all sections with double newlines and return
    return "\n\n".join(content)

@task(name="generate_metadata_section")
def generate_metadata_section():
    """Generate metadata about the document generation."""
    from datetime import datetime
    
    generated_time = datetime.now().strftime("%B %d, %Y at %H:%M:%S")
    
    markdown = f"""<div class="metadata">
<strong>📋 Documentation</strong> | Generated: {generated_time} | <a href="#quick-nav">Skip to Navigation</a>
</div>

---
"""
    return markdown

@task(name="generate_executive_summary")
def generate_executive_summary(doc):
    """Generate an executive summary for the repository."""
    repo_name = doc.get("repository_name", "Unknown Repository")
    file_count = len(doc.get("files", []))
    
    # Get environment variables across all files
    all_env_vars = set()
    for file in doc.get("files", []):
        for env_var in file.get("env_vars", []):
            if "name" in env_var:
                all_env_vars.add(env_var["name"])
    
    # Get all database names
    all_dbs = set()
    for file in doc.get("files", []):
        for db in file.get("db", []):
            if "db_name" in db:
                all_dbs.add(db["db_name"])
    
    # Get all API hosts
    all_apis = set()
    for file in doc.get("files", []):
        for api in file.get("api", []):
            if "host" in api:
                all_apis.add(api["host"])
    
    markdown = f"""<div class="executive-summary" id="quick-nav">

## Executive Summary

This documentation provides an automated analysis of **{repo_name}**, containing {file_count} analyzed files.

### Key Insights:

- **Environment Variables**: {len(all_env_vars)} unique variables identified
- **Database Connections**: {len(all_dbs)} database(s) referenced
- **External APIs**: {len(all_apis)} API endpoint(s) used

<details>
<summary><strong>Quick Reference - Environment Variables</strong></summary>

| Variable | Used In |
|----------|---------|
"""
    
    # Add environment variables with file references
    for var in sorted(all_env_vars):
        files_using_var = []
        for file in doc.get("files", []):
            for env_var in file.get("env_vars", []):
                if env_var.get("name") == var:
                    files_using_var.append(file.get("path", "Unknown"))
        
        # Limit to first 3 files with "+X more" if needed
        if len(files_using_var) > 3:
            file_list = f"`{files_using_var[0]}`, `{files_using_var[1]}`, `{files_using_var[2]}` +{len(files_using_var)-3} more"
        else:
            file_list = ", ".join([f"`{f}`" for f in files_using_var])
            
        markdown += f"| `{var}` | {file_list} |\n"
    
    markdown += """
</details>

</div>

---
"""
    
    return markdown

@task(name="generate_header_section")
def generate_header_section(doc):
    """Generate the header section with main repository info."""
    repo_url = doc.get("repository_url", "Unknown")
    repo_name = doc.get("repository_name", "Unknown")
    timestamp = doc.get("analysis_timestamp", "Unknown")
    
    # Format timestamp if it's a datetime object or timestamp string
    if isinstance(timestamp, str) and timestamp not in ["Unknown", ""]:
        try:
            # Try to parse timestamp in case it's a string
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            timestamp = dt.strftime("%B %d, %Y at %H:%M:%S UTC")
        except:
            # Keep original if parsing fails
            pass
    
    markdown = f"""# Repository Documentation: {repo_name}

## Overview

| Information | Value |
|-------------|-------|
| **Repository URL** | [{repo_url}]({repo_url}) |
| **Repository Name** | {repo_name} |
| **Analysis Timestamp** | {timestamp} |

---
"""
    
    return markdown

@task(name="generate_directory_structure_section")
def generate_directory_structure_section(doc):
    """Generate the directory structure section."""
    dir_structure = doc.get("directory_structure", "No directory structure available")
    
    markdown = """## Directory Structure

<details open>
<summary><strong>Repository Layout</strong></summary>

```directory
"""
    markdown += dir_structure
    markdown += """
```

</details>

---"""
    
    return markdown

@task(name="generate_top_files_section")
def generate_top_files_section(doc):
    """Generate a table of top files from tool_output."""
    tool_output = doc.get("tool_output", {})
    top_files = tool_output.get("top_files", [])
    
    if not top_files:
        return "## Top Files\n\nNo top files information available."
    
    # Build markdown table
    markdown = """## Top Files

<div class="file-table">

| Rank | File Path | Characters | Tokens |
|:----:|-----------|------------:|--------:|
"""
    
    for file in top_files:
        rank = file.get("rank", "N/A")
        path = file.get("path", "Unknown")
        chars = file.get("chars", "N/A")
        tokens = file.get("tokens", "N/A")
        
        markdown += f"| {rank} | `{path}` | {chars:,} | {tokens:,} |\n"
    
    markdown += "\n</div>\n\n---"
    
    return markdown

@task(name="generate_summary_section")
def generate_summary_section(doc):
    """Generate summary section from tool_output."""
    tool_output = doc.get("tool_output", {})
    summary = tool_output.get("summary", {})
    
    if not summary:
        return "## Summary\n\nNo summary information available."
    
    # Remove output_file as requested
    summary_without_output = {k: v for k, v in summary.items() if k != "output_file"}
    
    markdown = "## Summary\n\n<div class=\"summary-box\">\n\n"
    
    for key, value in summary_without_output.items():
        formatted_key = key.replace("_", " ").title()
        
        # Special handling for security status
        if key == "security" and isinstance(value, str) and "✔" in value:
            markdown += f"- **{formatted_key}**: <span class=\"security-success\">{value}</span>\n"
        else:
            markdown += f"- **{formatted_key}**: {value}\n"
    
    markdown += "\n</div>\n\n---"
    
    return markdown

@task(name="generate_files_section")
def generate_files_section(doc):
    """Generate detailed file information tables from the files field."""
    files = doc.get("files", [])
    
    if not files:
        return "## File Details\n\nNo file details available."
    
    markdown = "## File Details\n\n"
    
    # Add table of contents for quick navigation
    markdown += "<div class='navigation-section'>\n\n"
    markdown += "### Quick Navigation\n\n"
    
    # First group files by type
    file_groups = {}
    for idx, file in enumerate(files):
        path = file.get("path", "Unknown")
        ext = path.split('.')[-1] if '.' in path else "other"
        
        if ext not in file_groups:
            file_groups[ext] = []
        
        file_groups[ext].append((idx, file))
    
    # Create navigation with file type grouping
    for ext, file_group in sorted(file_groups.items()):
        icon = get_file_icon_for_group(ext)
        markdown += f"**{icon} {ext.upper() if ext != 'other' else 'Other'} Files**\n\n"
        
        for idx, file in file_group:
            path = file.get("path", "Unknown")
            # Create anchor links with sanitized IDs
            file_id = f"file-{idx+1}-{path.replace('.', '-').replace('/', '-').lower()}"
            markdown += f"- [**{path}**](#{file_id})\n"
        
        markdown += "\n"
    
    markdown += "</div>\n\n---\n\n"
    
    for idx, file in enumerate(files):
        path = file.get("path", "Unknown")
        file_id = f"file-{idx+1}-{path.replace('.', '-').replace('/', '-').lower()}"
        
        # File heading with icon based on file type
        file_icon = get_file_icon(path)
        markdown += f"<h3 id='{file_id}' class='file-heading'>{idx+1}. {file_icon} {path}</h3>\n\n"
        
        # Skip content as requested
        file_data = {k: v for k, v in file.items() if k != "content"}
        
        # Handle environment variables
        env_vars = file.get("env_vars", [])
        if env_vars:
            markdown += "<details open>\n<summary><strong>Environment Variables</strong></summary>\n\n"
            markdown += "| Name | Description | Context |\n"
            markdown += "|------|-------------|--------|\n"
            
            for env_var in env_vars:
                name = env_var.get("name", "Unknown")
                description = env_var.get("description", "")
                context = env_var.get("context", "")
                markdown += f"| `{name}` | {description} | {context} |\n"
            
            markdown += "\n</details>\n\n"
        
        # Handle database information
        db_info = file.get("db", [])
        if db_info:
            markdown += "<details open>\n<summary><strong>Database Information</strong></summary>\n\n"
            
            for db in db_info:
                db_name = db.get("db_name", "Unknown")
                db_context = db.get("context", "")
                
                markdown += f"**Database**: {db_name}\n\n"
                markdown += f"**Context**: {db_context}\n\n"
                
                tables = db.get("tables", [])
                if tables:
                    markdown += "| Table | Description | Context |\n"
                    markdown += "|-------|-------------|--------|\n"
                    
                    for table in tables:
                        table_name = table.get("name", "Unknown")
                        table_desc = table.get("description", "")
                        table_context = table.get("context", "")
                        markdown += f"| `{table_name}` | {table_desc} | {table_context} |\n"
                else:
                    markdown += "No tables specified.\n"
                
                markdown += "\n"
            
            markdown += "</details>\n\n"
        
        # Handle API information
        api_info = file.get("api", [])
        if api_info:
            markdown += "<details open>\n<summary><strong>API Information</strong></summary>\n\n"
            
            for api in api_info:
                host = api.get("host", "Unknown")
                api_context = api.get("context", "")
                
                markdown += f"**Host**: {host}\n\n"
                markdown += f"**Context**: {api_context}\n\n"
                
                endpoints = api.get("endpoints", [])
                if endpoints:
                    markdown += "| Endpoint | Description | Context |\n"
                    markdown += "|----------|-------------|--------|\n"
                    
                    for endpoint in endpoints:
                        endpoint_name = endpoint.get("name", "Unknown")
                        endpoint_desc = endpoint.get("description", "")
                        endpoint_context = endpoint.get("context", "")
                        markdown += f"| `{endpoint_name}` | {endpoint_desc} | {endpoint_context} |\n"
                else:
                    markdown += "No endpoints specified.\n"
                
                markdown += "\n"
            
            markdown += "</details>\n\n"
        
        # Handle any other key-value pairs dynamically
        other_keys = [k for k in file_data.keys() if k not in ["path", "env_vars", "db", "api"]]
        if other_keys:
            markdown += "<details>\n<summary><strong>Additional Information</strong></summary>\n\n"
            
            for key in other_keys:
                value = file_data.get(key)
                
                # Format the key for display
                display_key = key.replace("_", " ").title()
                
                # Handle different types of values
                if isinstance(value, list):
                    if value:
                        markdown += f"**{display_key}**:\n\n"
                        for item in value:
                            if isinstance(item, dict):
                                for item_key, item_value in item.items():
                                    item_display_key = item_key.replace("_", " ").title()
                                    markdown += f"- {item_display_key}: {item_value}\n"
                            else:
                                markdown += f"- {item}\n"
                    else:
                        markdown += f"**{display_key}**: None\n"
                elif isinstance(value, dict):
                    if value:
                        markdown += f"**{display_key}**:\n\n"
                        for sub_key, sub_value in value.items():
                            sub_display_key = sub_key.replace("_", " ").title()
                            markdown += f"- {sub_display_key}: {sub_value}\n"
                    else:
                        markdown += f"**{display_key}**: Empty\n"
                else:
                    markdown += f"**{display_key}**: {value}\n"
                
                markdown += "\n"
            
            markdown += "</details>\n\n"
        
        # Add back to top link
        markdown += "<div class='back-to-top'><a href='#quick-nav'>↑ Back to Navigation</a></div>\n\n"
        
        # Add separator between files
        if idx < len(files) - 1:
            markdown += "<hr class='file-separator'>\n\n"
    
    # Add CSS styles at the end of the document
    markdown += """
<style>
/* Overall document styling */
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.5;
    color: #24292e;
}

/* Metadata bar */
.metadata {
    background-color: #f1f8ff;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 14px;
    margin-bottom: 20px;
}

/* Executive summary */
.executive-summary {
    background-color: #fffbdd;
    border-left: 4px solid #ffd33d;
    padding: 16px;
    border-radius: 4px;
    margin-bottom: 24px;
}

/* Summary box */
.summary-box {
    background-color: #f6f8fa;
    border-left: 4px solid #0366d6;
    padding: 16px;
    border-radius: 4px;
}

/* Navigation section */
.navigation-section {
    background-color: #f6f8fa;
    padding: 16px;
    border-radius: 6px;
    margin-bottom: 20px;
}

/* Security success indicator */
.security-success {
    color: #22863a;
    font-weight: bold;
}

/* Separator between files */
.file-separator {
    border: 0;
    height: 1px;
    background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(0, 0, 0, 0.2), rgba(0, 0, 0, 0));
    margin: 30px 0;
}

/* File table with scrolling */
.file-table {
    max-height: 400px;
    overflow-y: auto;
    display: block;
}

/* Collapsible sections */
details > summary {
    cursor: pointer;
    padding: 8px;
    background-color: #f1f8ff;
    border-radius: 4px;
    margin-bottom: 8px;
}

details {
    margin-bottom: 16px;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    padding: 0 16px 16px;
}

/* File headings */
.file-heading {
    background-color: #f1f8ff;
    padding: 8px 16px;
    border-radius: 4px;
    border-left: 4px solid #0366d6;
}

/* Back to top links */
.back-to-top {
    font-size: 14px;
    text-align: right;
    margin-top: 16px;
}

/* Code blocks */
pre {
    background-color: #f6f8fa;
    border-radius: 6px;
    padding: 16px;
    overflow: auto;
}

code {
    font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
    background-color: rgba(27, 31, 35, 0.05);
    border-radius: 3px;
    padding: 0.2em 0.4em;
    font-size: 85%;
}

/* Improve table readability */
table {
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 16px;
}

th, td {
    border: 1px solid #e1e4e8;
    padding: 8px 12px;
}

th {
    background-color: #f6f8fa;
    font-weight: 600;
}

tr:nth-child(even) {
    background-color: #f6f8fa;
}
</style>
"""
    
    return markdown

def get_file_icon(filename):
    """Return an appropriate emoji icon based on file extension."""
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    
    icons = {
        'py': '🐍',  # Python
        'js': '📜',  # JavaScript
        'ts': '📜',  # TypeScript
        'html': '🌐',  # HTML
        'css': '🎨',  # CSS
        'md': '📝',  # Markdown
        'json': '📊',  # JSON
        'yml': '⚙️',  # YAML
        'yaml': '⚙️',  # YAML
        'sql': '💾',  # SQL
        'sh': '🔧',  # Shell
        'dockerfile': '🐳',  # Dockerfile
        'txt': '📄',  # Text
        'makefile': '🛠️',  # Makefile
        'jenkinsfile': '🔄',  # Jenkinsfile
    }
    
    # Special case for Dockerfile, Jenkinsfile, etc.
    for special in ['dockerfile', 'jenkinsfile', 'makefile']:
        if filename.lower() == special:
            return icons.get(special, '📄')
    
    return icons.get(ext, '📄')  # Default to generic file icon

def get_file_icon_for_group(ext):
    """Return appropriate icon for file group heading."""
    group_icons = {
        'py': '🐍',      # Python
        'js': '📜',      # JavaScript
        'ts': '📜',      # TypeScript
        'html': '🌐',    # HTML
        'css': '🎨',     # CSS
        'md': '📝',      # Markdown
        'json': '📊',    # JSON
        'yml': '⚙️',     # YAML/Config
        'yaml': '⚙️',    # YAML/Config
        'sql': '💾',     # Database
        'sh': '🔧',      # Scripts
        'dockerfile': '🐳', # Docker
        'txt': '📄',     # Text
        'other': '📁',   # Other
    }
    
    return group_icons.get(ext.lower(), '📁')

__all__ = ["run_generate_docs"]