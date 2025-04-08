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
async def run_generate_docs_new(build_from_obj):
    
    if hasattr(build_from_obj,'model_dump'):
        data = build_from_obj.model_dump()
    elif hasattr(build_from_obj, 'to_dict'):
        data = build_from_obj.to_dict()
    elif isinstance(build_from_obj, dict):
        data = build_from_obj
    else:
        raise ValueError(f"Error: Failed to created Markdown object from type:{type(build_from_obj)}, Supported Types: pydantic.BaseModel, to_dict() method, or dict instance itself")
    
    markdown_content = generate_markdown_from_doc(doc=data)
    
    # Create artifact filename (repo name + timestamp)
    repo_name = data.get("repository_name", "unnamed-repo")
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
    
@flow(
    log_prints=True, 
    name="run_generate_docs_old", 
    result_storage="local-file-system/dev-result-storage",
    description="Build markdown docs from MongoDB object",
)
async def run_generate_docs_old(build_from_obj_id: str):
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
    
    # Enhanced Executive Summary with more data
    # content.append(generate_enhanced_executive_summary(doc))
    # Use new GitHub compatible version
    content.append(generate_github_executive_summary(doc))
    
    # Combined overview with summary and top files
    # content.append(generate_combined_overview_section(doc))
    # Use new GitHub compatible version
    content.append(generate_github_overview_section(doc))
    
    # Directory structure section (moved before navigation)
    content.append(generate_github_directory_structure(doc))
    
    # Navigation section (toggleable, closed by default)
    # content.append(generate_navigation_section(doc))
    
    # Files details section (with all extracted fields)
    # content.append(generate_enhanced_files_section(doc))
    # Use new GitHub compatible version
    content.append(generate_github_files_section(doc))
    
    # Join all sections with double newlines and return
    return "\n\n".join(content)

# @task(name="generate_metadata_section")
def generate_metadata_section():
    """Generate metadata about the document generation."""
    from datetime import datetime
    
    generated_time = datetime.now().strftime("%B %d, %Y at %H:%M:%S")
    
    # Original HTML version
    # markdown = f"""<div class="metadata">
    # <strong>📋 Documentation</strong> | Generated: {generated_time} | <a href="#quick-nav">Skip to Navigation</a>
    # </div>
    
    # GitHub compatible version
    markdown = f"""# Repository Documentation

> Generated: {generated_time}

---
"""
    return markdown

def generate_github_executive_summary(doc):
    """Generate a simplified executive summary using GitHub markdown."""
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
    
    # Get all file types by extension
    all_file_types = set()
    for file in doc.get("files", []):
        path = file.get("path", "")
        if "." in path:
            ext = path.split(".")[-1]
            all_file_types.add(ext)
    
    # Get all tables mentioned in the codebase
    all_tables = set()
    for file in doc.get("files", []):
        for db in file.get("db", []):
            for table in db.get("tables", []):
                if "name" in table:
                    all_tables.add(table["name"])
    
    # Get all security findings
    all_malicious_elements = []
    all_sensitive_info = []
    all_vulnerabilities = []
    
    for file in doc.get("files", []):
        # Extract security data from their actual locations in the file data
        malicious = file.get("malicious_elements", [])
        sensitive = file.get("sensitive_info", [])
        vulns = file.get("vulnerabilities", [])
        
        # Filter and reclassify findings
        reclassified_malicious = []
        for element in malicious:
            # Check if this is a credential in a CI/CD file that should be reclassified
            description = element.get("description", "").lower()
            element_type = element.get("type", "").lower()
            location = element.get("location", "").lower()
            
            # Conditions to reclassify as sensitive info instead of malicious
            is_cicd_credential = (
                ("password" in description or "credential" in description or "token" in description) and
                ("jenkins" in location or "dockerfile" in location or ".yml" in location or 
                 "docker" in description or "registry" in description)
            )
            
            if is_cicd_credential:
                # Create a copy of the elemen   t with type changed to credential
                sensitive_element = element.copy()
                sensitive_element["type"] = "CI/CD Credential"
                sensitive.append(sensitive_element)
            else:
                reclassified_malicious.append(element)
        
        # Use the filtered list instead of the original
        all_malicious_elements.extend(reclassified_malicious)
        all_sensitive_info.extend(sensitive)
        all_vulnerabilities.extend(vulns)
    
    total_security_findings = len(all_malicious_elements) + len(all_sensitive_info) + len(all_vulnerabilities)
    
    markdown = f"""## Executive Summary

This documentation provides an automated analysis of **{repo_name}**, containing {file_count} analyzed files.

### Key Insights:

- **Environment Variasles**: {len(all_env_vars)} unique variables identified
- **Database Connections**: {len(all_dbs)} database(s) referenced
- **Database Tables**: {len(all_tables)} table(s) referenced
- **External APIs**: {len(all_apis)} API endpoint(s) used
- **File Types**: {len(all_file_types)} different file extensions (.{', .'.join(sorted(all_file_types))})
- **Security Findings**: {total_security_findings} issues identified ({len(all_vulnerabilities)} vulnerabilities, {len(all_sensitive_info)} sensitive info exposures, {len(all_malicious_elements)} suspicious code patterns)

### Environment Variables

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
    
    if not all_env_vars:
        markdown += "| *None found* | - |\n"
    
    markdown += """
<details>
<summary><strong>Database Information</strong></summary>

"""
    
    # Add database information
    has_db_info = False
    
    # First handle known databases
    for db_name in sorted(all_dbs):
        has_db_info = True
        db_tables = []
        files_using_db = []
        
        for file in doc.get("files", []):
            for db in file.get("db", []):
                if db.get("db_name") == db_name:
                    files_using_db.append(file.get("path", "Unknown"))
                    for table in db.get("tables", []):
                        if "name" in table:
                            db_tables.append(table["name"])
        
        # Remove duplicates and sort
        db_tables = sorted(set(db_tables))
        
        # Create a header for this database
        markdown += f"**Database: `{db_name}`**\n\n"
        
        # Limit file list for the database
        if len(files_using_db) > 3:
            file_list = f"`{files_using_db[0]}`, `{files_using_db[1]}`, `{files_using_db[2]}` +{len(files_using_db)-3} more"
        else:
            file_list = ", ".join([f"`{f}`" for f in files_using_db])
            
        markdown += f"**Used in**: {file_list}\n\n"
        
        # List tables if any
        if db_tables:
            markdown += "**Tables**:\n\n"
            for table in db_tables:
                # Find files using this table
                table_files = []
                for file in doc.get("files", []):
                    for db in file.get("db", []):
                        if db.get("db_name") == db_name:
                            for tbl in db.get("tables", []):
                                if tbl.get("name") == table:
                                    table_files.append(file.get("path", "Unknown"))
                
                # Remove duplicates
                table_files = sorted(set(table_files))
                
                # Format file list
                if len(table_files) > 3:
                    file_list = f"`{table_files[0]}`, `{table_files[1]}`, `{table_files[2]}` +{len(table_files)-3} more"
                else:
                    file_list = ", ".join([f"`{f}`" for f in table_files])
                
                markdown += f"- `{table}` - Used in: {file_list}\n"
        else:
            markdown += "**Tables**: *No tables specified*\n"
        
        markdown += "\n---\n\n"
    
    # Handle tables without a specific database
    orphan_tables = set()
    for file in doc.get("files", []):
        for db in file.get("db", []):
            if not db.get("db_name") or db.get("db_name") == "Unknown":
                for table in db.get("tables", []):
                    if "name" in table:
                        orphan_tables.add(table["name"])
    
    # Remove tables that are already associated with known databases
    for db_name in all_dbs:
        for file in doc.get("files", []):
            for db in file.get("db", []):
                if db.get("db_name") == db_name:
                    for table in db.get("tables", []):
                        if "name" in table and table["name"] in orphan_tables:
                            orphan_tables.remove(table["name"])
    
    if orphan_tables:
        has_db_info = True
        markdown += "**Database: `Unknown`**\n\n"
        
        # Find files using these orphan tables
        all_orphan_files = []
        for table_name in orphan_tables:
            for file in doc.get("files", []):
                for db in file.get("db", []):
                    for table in db.get("tables", []):
                        if table.get("name") == table_name:
                            all_orphan_files.append(file.get("path", "Unknown"))
        
        # Remove duplicates
        all_orphan_files = sorted(set(all_orphan_files))
        
        # Format file list
        if len(all_orphan_files) > 3:
            file_list = f"`{all_orphan_files[0]}`, `{all_orphan_files[1]}`, `{all_orphan_files[2]}` +{len(all_orphan_files)-3} more"
        else:
            file_list = ", ".join([f"`{f}`" for f in all_orphan_files])
            
        markdown += f"**Used in**: {file_list}\n\n"
        
        markdown += "**Tables**:\n\n"
        for table_name in sorted(orphan_tables):
            # Find files using this table
            table_files = []
            for file in doc.get("files", []):
                for db in file.get("db", []):
                    for table in db.get("tables", []):
                        if table.get("name") == table_name:
                            table_files.append(file.get("path", "Unknown"))
            
            # Remove duplicates
            table_files = sorted(set(table_files))
            
            # Format file list
            if len(table_files) > 3:
                file_list = f"`{table_files[0]}`, `{table_files[1]}`, `{table_files[2]}` +{len(table_files)-3} more"
            else:
                file_list = ", ".join([f"`{f}`" for f in table_files])
            
            markdown += f"- `{table_name}` - Used in: {file_list}\n"
    
    if not has_db_info:
        markdown += "**No database information found**\n"
    
    markdown += """
</details>

<details>
<summary><strong>API Information</strong></summary>

"""
    
    # Add API information
    has_api_info = False
    for host in sorted(all_apis):
        has_api_info = True
        api_endpoints = []
        files_using_api = []
        
        for file in doc.get("files", []):
            for api in file.get("api", []):
                if api.get("host") == host:
                    files_using_api.append(file.get("path", "Unknown"))
                    for endpoint in api.get("endpoints", []):
                        if "name" in endpoint:
                            api_endpoints.append(endpoint["name"])
        
        # Remove duplicates and sort
        api_endpoints = sorted(set(api_endpoints))
        
        # Create header for this API
        markdown += f"**Host: `{host}`**\n\n"
        
        # Limit file list
        if len(files_using_api) > 3:
            file_list = f"`{files_using_api[0]}`, `{files_using_api[1]}`, `{files_using_api[2]}` +{len(files_using_api)-3} more"
        else:
            file_list = ", ".join([f"`{f}`" for f in files_using_api])
            
        markdown += f"**Used in**: {file_list}\n\n"
        
        # List endpoints if any
        if api_endpoints:
            markdown += "**Endpoints**:\n\n"
            for endpoint in api_endpoints:
                markdown += f"- `{endpoint}`\n"
        else:
            markdown += "**Endpoints**: *No endpoints specified*\n"
        
        markdown += "\n---\n\n"
    
    if not has_api_info:
        markdown += "**No API information found**\n"
    
    markdown += """
</details>

<details>
<summary><strong>Security Findings</strong></summary>

"""

    # Add security findings
    if total_security_findings > 0:
        # Group vulnerabilities by severity
        vuln_by_severity = {}
        for vuln in all_vulnerabilities:
            severity = vuln.get("severity", "Unknown")
            if severity not in vuln_by_severity:
                vuln_by_severity[severity] = []
            vuln_by_severity[severity].append(vuln)
            
        # Group sensitive info by severity
        sensitive_by_severity = {}
        for info in all_sensitive_info:
            severity = info.get("severity", "Unknown")
            if severity not in sensitive_by_severity:
                sensitive_by_severity[severity] = []
            sensitive_by_severity[severity].append(info)
            
        # Group malicious elements by severity
        malicious_by_severity = {}
        for element in all_malicious_elements:
            severity = element.get("severity", "Unknown")
            if severity not in malicious_by_severity:
                malicious_by_severity[severity] = []
            malicious_by_severity[severity].append(element)
            
        # List of severities in descending order of importance
        severities = ["Critical", "High", "Medium", "Low", "Info", "Unknown"]
        
        # First show a summary
        markdown += "### Security Summary\n\n"
        markdown += "| Severity | Vulnerabilities | Sensitive Info | Malicious Code | Total |\n"
        markdown += "|----------|----------------|---------------|---------------|-------|\n"
        
        for severity in severities:
            vuln_count = len(vuln_by_severity.get(severity, []))
            sensitive_count = len(sensitive_by_severity.get(severity, []))
            malicious_count = len(malicious_by_severity.get(severity, []))
            total = vuln_count + sensitive_count + malicious_count
            
            if total > 0:
                markdown += f"| **{severity}** | {vuln_count} | {sensitive_count} | {malicious_count} | {total} |\n"
                
        # Show top findings across all types
        markdown += "\n### Top Security Findings\n\n"
        
        # Function to get the display severity
        def get_severity_emoji(severity):
            emoji_map = {
                "Critical": "🔴",
                "High": "🟠",
                "Medium": "🟡",
                "Low": "🟢",
                "Info": "🔵",
                "Unknown": "⚪"
            }
            return emoji_map.get(severity, "⚪")
        
        # Combine all findings and sort by severity
        all_findings = []
        for vuln in all_vulnerabilities:
            vuln['finding_type'] = 'Vulnerability'
            all_findings.append(vuln)
            
        for info in all_sensitive_info:
            info['finding_type'] = 'Sensitive Info'
            all_findings.append(info)
            
        for element in all_malicious_elements:
            element['finding_type'] = 'Malicious Code'
            all_findings.append(element)
            
        # Sort findings by severity, with Critical first
        severity_order = {severity: i for i, severity in enumerate(severities)}
        sorted_findings = sorted(all_findings, 
                                key=lambda x: (severity_order.get(x.get('severity'), 999),
                                              x.get('finding_type', ''),
                                              x.get('description', '')))
        
        # Show top 10 findings
        for i, finding in enumerate(sorted_findings[:10]):
            severity = finding.get('severity', 'Unknown')
            finding_type = finding.get('finding_type', 'Unknown')
            desc = finding.get('description', 'No description')
            location = finding.get('location', 'Unknown location')
            
            emoji = get_severity_emoji(severity)
            markdown += f"{emoji} **{severity} {finding_type}**: {desc} - *Location: {location}*\n\n"
            
        # If there are more than 10 findings, indicate there are more
        if len(sorted_findings) > 10:
            markdown += f"... and {len(sorted_findings) - 10} more findings\n"
    else:
        markdown += "No security findings detected in the codebase.\n"
    
    markdown += """
</details>
---
"""
    
    return markdown

def generate_github_overview_section(doc):
    """Generate a simple overview section using GitHub markdown."""
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
    
    # Get summary data from tool_output
    tool_output = doc.get("tool_output", {})
    summary = tool_output.get("summary", {})
    
    # Basic statistics from summary
    total_files = summary.get("total_files", "N/A")
    total_chars = summary.get("total_chars", "N/A")
    total_tokens = summary.get("total_tokens", "N/A")
    security_status = summary.get("security", "N/A")
    
    markdown = f"""## Repository Information

- **Repository URL**: [{repo_url}]({repo_url})
- **Repository Name**: {repo_name}
- **Analysis Timestamp**: {timestamp}

### Repository Statistics

- **Total Files**: {total_files}
- **Total Characters**: {total_chars:,}
- **Total Tokens**: {total_tokens:,}
- **Security Status**: {security_status}

### Top Files by Size

| Rank | File Path | Characters | Tokens |
|:----:|-----------|------------:|--------:|
"""
    
    # Add top files from tool_output
    top_files = tool_output.get("top_files", [])
    if top_files:
        for file in top_files[:10]:  # Limit to top 10 files
            rank = file.get("rank", "N/A")
            path = file.get("path", "Unknown")
            chars = file.get("chars", "N/A")
            tokens = file.get("tokens", "N/A")
            
            markdown += f"| {rank} | `{path}` | {chars:,} | {tokens:,} |\n"
    else:
        markdown += "| - | *No files data available* | - | - |\n"
    
    markdown += "\n---\n"
    
    return markdown

def generate_github_files_section(doc):
    """Generate file details section using GitHub markdown."""
    files = doc.get("files", [])
    
    if not files:
        return "## File Details\n\nNo file details available."
    
    # Create navigation first
    markdown = "## File Details\n\n"
    markdown += "<details open>\n<summary><strong>File Navigation</strong></summary>\n\n"
    
    # Group files by type for navigation
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
            file_id = f"file-{idx+1}"
            markdown += f"- [{path}](#{file_id})\n"
        
        markdown += "\n"
    
    markdown += "</details>\n\n"
    
    # Now add individual file details
    for idx, file in enumerate(files):
        path = file.get("path", "Unknown")
        file_id = f"file-{idx+1}"
        
        # File heading with icon based on file type
        file_icon = get_file_icon(path)
        markdown += f"### {file_icon} {path} <a id='{file_id}'></a>\n\n"
        
        # Skip content as requested but keep all other fields
        file_data = {k: v for k, v in file.items() if k != "content"}
        
        # Handle environment variables
        env_vars = file.get("env_vars", [])
        
        markdown += "<details open>\n<summary><strong>Environment Variables</strong></summary>\n\n"
        
        if env_vars:
            markdown += "| Name | Description | Context |\n"
            markdown += "|------|-------------|--------|\n"
            
            for env_var in env_vars:
                name = env_var.get("name", "Unknown")
                description = env_var.get("description", "")
                context = env_var.get("context", "")
                markdown += f"| `{name}` | {description} | {context} |\n"
        else:
            markdown += "**Environment Variables**: None\n"
        
        markdown += "\n</details>\n\n"
        
        # Handle database information
        db_info = file.get("db", [])
        
        markdown += "<details open>\n<summary><strong>Database Information</strong></summary>\n\n"
        
        if db_info:
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
        else:
            markdown += "**Database Information**: None\n"
        
        markdown += "</details>\n\n"
        
        # Handle API information
        api_info = file.get("api", [])
        
        markdown += "<details open>\n<summary><strong>API Information</strong></summary>\n\n"
        
        if api_info:
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
        else:
            markdown += "**API Information**: None\n"
        
        markdown += "</details>\n\n"
        
        # Handle security information - NEW SECTION
        # Extract security findings directly from the file data
        vulnerabilities = file.get("vulnerabilities", [])
        sensitive_info = file.get("sensitive_info", [])
        malicious_elements = file.get("malicious_elements", [])
        recommendations = file.get("recommendations", [])
        
        # Reclassify CI/CD credentials from malicious to sensitive
        reclassified_malicious = []
        for element in malicious_elements:
            # Check if this is a credential in a CI/CD file that should be reclassified
            description = element.get("description", "").lower()
            element_type = element.get("type", "").lower()
            location = element.get("location", "").lower()
            
            # Conditions to reclassify as sensitive info instead of malicious
            is_cicd_credential = (
                ("password" in description or "credential" in description or "token" in description) and
                ("jenkins" in location or "dockerfile" in location or ".yml" in location or 
                 "docker" in description or "registry" in description)
            )
            
            if is_cicd_credential:
                # Create a copy of the element with type changed to credential
                sensitive_element = element.copy()
                sensitive_element["type"] = "CI/CD Credential"
                sensitive_info.append(sensitive_element)
            else:
                reclassified_malicious.append(element)
        
        # Use the reclassified list
        malicious_elements = reclassified_malicious
        
        markdown += "<details open>\n<summary><strong>Security Findings</strong></summary>\n\n"
        
        # Function to get the display severity
        def get_severity_emoji(severity):
            emoji_map = {
                "Critical": "🔴",
                "High": "🟠",
                "Medium": "🟡",
                "Low": "🟢",
                "Info": "🔵",
                "Unknown": "⚪"
            }
            return emoji_map.get(severity, "⚪")
        
        # Check if there are any security findings
        total_issues = len(vulnerabilities) + len(sensitive_info) + len(malicious_elements)
        
        if total_issues > 0:
            # Show overall risk score if available
            risk_score = file.get("overall_risk_score", None)
            score_justification = file.get("score_justification", "")
            
            if risk_score is not None:
                # Determine color based on score
                if risk_score >= 75:
                    risk_color = "🔴"
                elif risk_score >= 50:
                    risk_color = "🟠"
                elif risk_score >= 25:
                    risk_color = "🟡"
                else:
                    risk_color = "🟢"
                    
                markdown += f"**Risk Score**: {risk_color} {risk_score}/100 - {score_justification}\n\n"
            
            # Handle vulnerabilities
            if vulnerabilities:
                markdown += "#### Vulnerabilities\n\n"
                markdown += "| Severity | Type | Description | Location | False Positive? |\n"
                markdown += "|----------|------|-------------|----------|----------------|\n"
                
                for vuln in vulnerabilities:
                    severity = vuln.get("severity", "Unknown")
                    vuln_type = vuln.get("vulnerability_type", "Unknown")
                    description = vuln.get("description", "")
                    location = vuln.get("location", "")
                    fp_likelihood = vuln.get("false_positive_likelihood", "Unknown")
                    
                    emoji = get_severity_emoji(severity)
                    markdown += f"| {emoji} {severity} | {vuln_type} | {description} | {location} | {fp_likelihood} |\n"
                
                markdown += "\n"
            
            # Handle sensitive info
            if sensitive_info:
                markdown += "#### Sensitive Information Exposure\n\n"
                markdown += "| Severity | Type | Description | Location | False Positive? |\n"
                markdown += "|----------|------|-------------|----------|----------------|\n"
                
                for info in sensitive_info:
                    severity = info.get("severity", "Unknown")
                    info_type = info.get("type", "Unknown")
                    description = info.get("description", "")
                    location = info.get("location", "")
                    fp_likelihood = info.get("false_positive_likelihood", "Unknown")
                    
                    emoji = get_severity_emoji(severity)
                    markdown += f"| {emoji} {severity} | {info_type} | {description} | {location} | {fp_likelihood} |\n"
                
                markdown += "\n"
            
            # Handle malicious code elements
            if malicious_elements:
                markdown += "#### Malicious Code Elements\n\n"
                markdown += "| Severity | Type | Description | Location | False Positive? |\n"
                markdown += "|----------|------|-------------|----------|----------------|\n"
                
                for element in malicious_elements:
                    severity = element.get("severity", "Unknown")
                    element_type = element.get("type", "Unknown")
                    description = element.get("description", "")
                    location = element.get("location", "")
                    fp_likelihood = element.get("false_positive_likelihood", "Unknown")
                    
                    emoji = get_severity_emoji(severity)
                    markdown += f"| {emoji} {severity} | {element_type} | {description} | {location} | {fp_likelihood} |\n"
                
                markdown += "\n"
            
            # Handle recommendations
            if recommendations:
                markdown += "#### Security Recommendations\n\n"
                markdown += "| Priority | Issue Reference | Recommendation |\n"
                markdown += "|----------|----------------|----------------|\n"
                
                for rec in recommendations:
                    priority = rec.get("priority", "Unknown")
                    issue_ref = rec.get("issue_reference", "")
                    recommendation = rec.get("recommendation", "")
                    
                    # Determine emoji based on priority
                    if priority == "High":
                        priority_emoji = "🔴"
                    elif priority == "Medium":
                        priority_emoji = "🟠"
                    elif priority == "Low":
                        priority_emoji = "🟢"
                    else:
                        priority_emoji = "⚪"
                    
                    markdown += f"| {priority_emoji} {priority} | {issue_ref} | {recommendation} |\n"
                
                markdown += "\n"
        else:
            markdown += "No security issues detected in this file.\n"
        
        markdown += "</details>\n\n"
        
        # Handle any other key-value pairs dynamically
        other_keys = [k for k in file_data.keys() if k not in ["path", "env_vars", "db", "api", "malicious_elements", "sensitive_info", "vulnerabilities", "recommendations", "overall_risk_score", "score_justification"]]
        
        markdown += "<details open>\n<summary><strong>Additional Information</strong></summary>\n\n"
        
        if other_keys:
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
                    markdown += f"**{display_key}**: {value or 'None'}\n"
                
                markdown += "\n"
        else:
            markdown += "**Additional Information**: None\n"
        
        markdown += "</details>\n\n"
        
        # Add back to top link using GitHub compatible anchor
        markdown += "[↑ Back to top](#repository-documentation)\n\n"
        
        # Add separator between files
        if idx < len(files) - 1:
            markdown += "---\n\n"
    
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

def generate_github_directory_structure(doc):
    """Generate the directory structure section using GitHub markdown."""
    dir_structure = doc.get("directory_structure", "No directory structure available")
    
    markdown = """## Directory Structure

<details>
<summary><strong>Repository Layout</strong></summary>

```
"""
    markdown += dir_structure
    markdown += """
```

</details>

---
"""
    
    return markdown

__all__ = ["run_generate_docs_old", "run_generate_docs_new"]