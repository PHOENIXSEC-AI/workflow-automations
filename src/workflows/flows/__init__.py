"""
Workflow flow definitions.
"""
from .repo_analysis import run_repo_analysis
from .doc_gen import run_generate_docs_old
from .private_repo_analysis import run_private_repo_analysis
from .analyze_and_document_repos import run_analyze_and_document_repos
from .concurrent_agents import run_concurrent_agents
from .extraction_strategies import add_base

__all__ = [
    # Repository analysis flows
    "run_repo_analysis",
    "run_private_repo_analysis",
    
    # AI enrichment flows
    "run_analyze_and_document_repos",
    
    # Strategies for data extraction using LLMs
    "add_base",
    
    # Performance testing flows
    "run_concurrent_agents",
    
    # Documentation creation from repo analysis flow
    "run_generate_docs_old",
]