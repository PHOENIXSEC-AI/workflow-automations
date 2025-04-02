#!/usr/bin/env python3
"""
Example demonstrating asynchronous database operations with AIOTinyDB.
"""

import os
import asyncio
from tinydb import Query

from core.services.database import (
    AsyncWorkflowStorage,
    AsyncRepository
)

from core.models import RepomixResultData, FileRank, Summary, ToolOutput, RepoFile


async def main():
    # Create a temporary database for this example
    example_dir = os.path.join(os.path.expanduser("~"), ".workflow_automation", "examples")
    os.makedirs(example_dir, exist_ok=True)
    db_path = os.path.join(example_dir, "async_example.json")
    print(f"Using database file: {db_path}")
    
    # Initialize async storage
    storage = AsyncWorkflowStorage(db_path)
    
    # Use async context manager
    # Create repository
    workflow_repo = AsyncRepository(RepomixResultData, storage)
    
    # Initialize test models
    file_rank = FileRank(
        rank=1,
        path="src/main.py",
        chars=1500,
        tokens=500
    )

    summary = Summary(
        total_files=10,
        total_chars=15000,
        total_tokens=5000,
        output_file="/tmp/repo_analysis.xml",
        security="✓ No security issues found"
    )

    tool_output = ToolOutput(
        top_files=[file_rank],
        summary=summary
    )

    repo_file = RepoFile(
        path="src/main.py",
        content="def main():\n    print('Hello, world!')\n\nif __name__ == '__main__':\n    main()"
    )

    data = RepomixResultData(
        directory_structure=".\n└── src\n    └── main.py",
        instruction="Analyze the repository structure",
        tool_output=tool_output,
        files=[repo_file]
)
    
    # Clear any existing data
    doc_id, err_msg = await workflow_repo.create(data)
    print("Cleared existing data")
    
        


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 