#!/usr/bin/env python3
"""
Script to retrieve all repository URLs from a GitHub organization using a personal access token.
Uses the GITHUB_TOKEN environment variable for authentication.
Combines the GitHub API and GitPython to ensure all repositories are retrieved.
"""

import os
import requests
import tempfile
import subprocess
import shutil
from typing import List, Dict, Any, Set
import argparse
import sys

from dotenv import load_dotenv
# from git import Repo
# from git.exc import GitCommandError

def get_organization_repos_api(org_name: str, token: str) -> List[Dict[Any, Any]]:
    """
    Fetches repositories using the GitHub API for a given organization.
    
    Args:
        org_name: The name of the GitHub organization
        token: GitHub personal access token
        
    Returns:
        List of repository data
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    repos = []
    page = 1
    
    while True:
        url = f"https://api.github.com/orgs/{org_name}/repos"
        params = {
            "per_page": 100,
            "page": page,
            "type": "all"  # Include all repositories (public, private, forks, etc.)
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Warning: API error fetching repositories: {response.status_code}")
            print(response.json().get("message", "Unknown error"))
            break
            
        page_repos = response.json()
        if not page_repos:
            break
            
        repos.extend(page_repos)
        page += 1
        
    return repos

def get_organization_repos_git(org_name: str, token: str) -> Set[str]:
    """
    Fetches repository names using git directly.
    
    Args:
        org_name: The name of the GitHub organization
        token: GitHub personal access token
        
    Returns:
        Set of repository names
    """
    temp_dir = tempfile.mkdtemp()
    try:
        # Clone the organization index repository to get a list of all repos
        org_url = f"https://{token}:x-oauth-basic@github.com/{org_name}"
        
        # Use the git command directly to get info without cloning
        command = ["git", "ls-remote", "--heads", org_url]
        
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            
            # Parse the output to extract repository names
            repo_names = set()
            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue
                    
                parts = line.split('/')
                if len(parts) >= 3:
                    repo_name = parts[-2]
                    repo_names.add(repo_name)
                    
            return repo_names
            
        except subprocess.CalledProcessError as e:
            print(f"Warning: Git command failed: {e}")
            print(f"STDERR: {e.stderr}")
            return set()
    finally:
        shutil.rmtree(temp_dir)

def get_repository_info(org_name: str, repo_name: str, token: str) -> Dict[str, Any]:
    """
    Fetches detailed information about a specific repository.
    
    Args:
        org_name: The name of the GitHub organization
        repo_name: The name of the repository
        token: GitHub personal access token
        
    Returns:
        Repository data dictionary
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"https://api.github.com/repos/{org_name}/{repo_name}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        # Return a minimal fallback data structure if API call fails
        return {
            "name": repo_name,
            "html_url": f"https://github.com/{org_name}/{repo_name}",
            "clone_url": f"https://github.com/{org_name}/{repo_name}.git",
            "ssh_url": f"git@github.com:{org_name}/{repo_name}.git",
            "private": True,  # Assume private as we're using a token
            "description": ""
        }
        
    return response.json()

def get_repository_urls(repos: List[Dict[Any, Any]]) -> Dict[str, Dict[str, str]]:
    """
    Extracts repository URLs from repository data.
    
    Args:
        repos: List of repository data
        
    Returns:
        Dictionary with repository names and URLs
    """
    repo_urls = {}
    
    for repo in repos:
        name = repo["name"]
        repo_urls[name] = {
            "html_url": repo["html_url"],
            "clone_url": repo["clone_url"],
            "ssh_url": repo["ssh_url"],
            "is_private": repo["private"],
            "description": repo["description"] or ""
        }
    
    return repo_urls

def main():
    parser = argparse.ArgumentParser(description="Get repository URLs from a GitHub organization")
    parser.add_argument("--org", "-o", required=True, help="GitHub organization name")
    parser.add_argument("--output", "-f", help="Output format: text, csv, json (default: text)")
    parser.add_argument("--private-only", action="store_true", help="Show only private repositories")
    args = parser.parse_args()
    
    load_dotenv()
    
    # Get token from environment variable
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set")
        sys.exit(1)
    
    # Get repositories using API
    print(f"Fetching repositories for organization '{args.org}' using GitHub API...")
    api_repos = get_organization_repos_api(args.org, token)
    api_repo_names = {repo["name"] for repo in api_repos}
    
    # Get repositories using Git
    print(f"Fetching additional repositories using Git...")
    git_repo_names = get_organization_repos_git(args.org, token)
    
    # Combine results from both methods
    all_repo_names = api_repo_names.union(git_repo_names)
    print(f"Found {len(all_repo_names)} total repositories.")
    
    # Get detailed info for all repositories
    all_repos = []
    for repo in api_repos:
        all_repos.append(repo)
    
    # Get details for repositories found via Git but not via API
    missing_repos = git_repo_names - api_repo_names
    if missing_repos:
        print(f"Fetching detailed information for {len(missing_repos)} additional repositories...")
        for repo_name in missing_repos:
            repo_info = get_repository_info(args.org, repo_name, token)
            all_repos.append(repo_info)
    
    # Filter private repositories if requested
    if args.private_only:
        all_repos = [repo for repo in all_repos if repo["private"]]
    
    repo_urls = get_repository_urls(all_repos)
    
    # Handle different output formats
    if args.output == "json":
        import json
        print(json.dumps(repo_urls, indent=2))
    elif args.output == "csv":
        import csv
        with open(f"{args.org}_repos.csv", "w", newline="") as csvfile:
            fieldnames = ["name", "html_url", "clone_url", "ssh_url", "is_private", "description"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for name, data in repo_urls.items():
                writer.writerow({
                    "name": name,
                    **data
                })
        print(f"CSV output written to {args.org}_repos.csv")
    elif args.output == 'text':
        http_urls = [repo[1].get('html_url') for repo in repo_urls.items()]
        with open(f'{args.org}_repos.txt', 'w') as out_f:
            out_f.write('\n'.join(http_urls))
        print(f"Text output written to {args.org}_repos.txt")
    else:
        # Default text output
        print(f"\nFound {len(repo_urls)} repositories in '{args.org}':\n")
        for name, data in sorted(repo_urls.items()):
            privacy = "[PRIVATE]" if data["is_private"] else "[PUBLIC]"
            print(f"{name} {privacy}")
            print(f"  URL:         {data['html_url']}")
            print(f"  Clone URL:   {data['clone_url']}")
            print(f"  SSH URL:     {data['ssh_url']}")
            if data["description"]:
                print(f"  Description: {data['description']}")
            print()

if __name__ == "__main__":
    main() 