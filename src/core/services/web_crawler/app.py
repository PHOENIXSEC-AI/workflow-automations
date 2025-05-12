import asyncio
import argparse
import json
import os
from src.core.services.web_crawler.crawler import crawl_with_proxy_rotation

# Default tasks if no JSON file is provided
DEFAULT_TASKS = [{"url":"https://www.skelbiu.lt/skelbimai/kompiuterija/kompiuteriai/stacionarus-kompiuteriai/","id":"skelbiu_stacionarus_kompiuteriai"}]

def load_tasks_from_json(json_file):
    """Load tasks from a JSON file"""
    if not os.path.exists(json_file):
        print(f"Warning: JSON file {json_file} not found. Using default tasks.")
        return DEFAULT_TASKS
    
    try:
        with open(json_file, 'r') as f:
            tasks = json.load(f)
        print(f"Loaded {len(tasks)} tasks from {json_file}")
        return tasks
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {json_file}. Using default tasks.")
        return DEFAULT_TASKS

async def main(tasks_file=None):
    # Load tasks from file if provided, otherwise use default
    tasks = DEFAULT_TASKS
    if tasks_file:
        tasks = load_tasks_from_json(tasks_file)
    
    # Extract URLs from each task in the tasks list
    urls = [task["url"] for task in tasks]
    print(f"Crawling {len(urls)} URLs...")
    
    batch_result = await crawl_with_proxy_rotation(urls)
    
    # Create output directory if it doesn't exist
    output_dir = "crawler_results"
    os.makedirs(output_dir, exist_ok=True)
    
    for i, result in enumerate(batch_result):
        if i < len(tasks):  # Safety check
            task_id = tasks[i]["id"]
            output_path = os.path.join(output_dir, f"{task_id}_markdown.md")
            with open(output_path, 'w') as result_file:
                result_file.write(result.markdown)
            print(f"Saved result for {task_id} to {output_path}")
    
    print("Crawling completed successfully!")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Web crawler with proxy rotation')
    parser.add_argument('--tasks', type=str, help='Path to JSON file containing tasks')
    args = parser.parse_args()
    
    # Run the crawler with the provided tasks file
    asyncio.run(main(args.tasks))