from typing import Union, Type
from prefect import flow
from prefect.states import Completed,Failed
from workflows.agents.prompts import CODE_ANALYZER_BASE_INSTR, SECURITY_ANALYZER_BASE_INSTR
from workflows.flows.concurrent_agents import run_concurrent_agents
from workflows.agents.models import (
    RunAIDeps, 
    RunAgentDeps, 
    BaseAgentAnalysisResult, 
    AgentBatchResult, 
    AgentAnalysisResult,
    SecurityAnalysisResult)
from core.config import app_config
from core.utils import LoggerFactory
from core.models import RepoAnalysisResult

logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)


@flow(
    log_prints=True, 
    name="add_base", 
    description="Analyze Repomix results and extract base information",
)
async def add_base(repomix_result_obj_id:str):
    
    task_ctx = RunAIDeps(
        db_name="workflows",
        db_col_name="repomix",
        target_obj_id=repomix_result_obj_id,
    )
    
    agent_to_call = 'env-vars-extractor'
    
    return await run_concurrent_agents(
        ctx=task_ctx,
        agent_name=agent_to_call, 
        instructions=CODE_ANALYZER_BASE_INSTR)

async def add_basev2(repomix_result:RepoAnalysisResult) -> Union[Completed,Failed]:
    return await _run_agents(
        repomix_result,
        agent_name='env-vars-extractor',
        instr=CODE_ANALYZER_BASE_INSTR,
        expected_result_type=BaseAgentAnalysisResult)

@flow(
    log_prints=True, 
    name="security_review", 
    description="Analyze Repomix results and perform Security Review",
)
async def security_review(repomix_result:RepoAnalysisResult):
    return await _run_agents(
        repomix_result, 
        agent_name='appsec',
        instr=SECURITY_ANALYZER_BASE_INSTR,
        expected_result_type=SecurityAnalysisResult)
    
async def _run_agents(
    repomix_result: RepoAnalysisResult, 
    agent_name:str, 
    instr: str, 
    expected_result_type: Type[AgentAnalysisResult]):
    
    if not repomix_result:
        return {}
    
    task_ctx = RunAgentDeps(
        repomix_data=repomix_result,
        result_type=expected_result_type
    )
    
    return await run_concurrent_agents(
        ctx=task_ctx,
        agent_name=agent_name,
        instructions=instr
    )

def clean_result_artifacts(strategy_result_item):
    """
    Remove artifact fields from results before merging. This is usually called before merging into single result object. 
    It helps to clean keys that we dont need
    
    Args:
        strategy_result_item: Results dictionary to clean
        
    Returns:
        Cleaned results dictionary
    """
    if hasattr(strategy_result_item,'model_dump'):
        cleaned_results = strategy_result_item.model_dump()
    elif hasattr(strategy_result_item,'to_dict'):
        cleaned_results = strategy_result_item.to_dict()
    elif isinstance(strategy_result_item, dict):
        cleaned_results = dict(strategy_result_item)
        assert cleaned_results is not strategy_result_item, 'Error: `clean_result_artifacts` failed to copy dict'
    else:
        raise ValueError(f"Error: can't clean artifacts for type: {type(strategy_result_item).__name__}. Expected either pydantic.BaseModel or to_dict() method")
    
    # Cleanup artifact fields
    result_artifacts = ["file_path", "instructions", "repo_name"]
    for key_to_remove in result_artifacts:
        if key_to_remove in cleaned_results:
            cleaned_results.pop(key_to_remove)
            
    return cleaned_results

def merge_strategy_results(org_files, results_to_be_merged):
    """
    Merge strategy results into original files.
    
    Args:
        org_files: List of original files to update
        results_to_be_merged: List of strategy results to merge
    """
    for strategy_result in results_to_be_merged:
        if isinstance(strategy_result, AgentBatchResult):
            file_mapping = strategy_result.get_file_map()
            
            for idx, file in enumerate(org_files):
                lookup_f_path = getattr(file, 'path', 'default')
                s_item_results = file_mapping.get(lookup_f_path, {})
                
                if s_item_results:
                    # Create a clean copy without artifacts
                    s_item_results = clean_result_artifacts(s_item_results)
                    # Merge file and cleaned results
                    org_files[idx] = file.model_copy(update=s_item_results)
        else:
            logger.warning(f"Warning: Strategy result of type {type(strategy_result)} can't be merged")


__all__ = ["add_base", "security_review","clean_result_artifacts", "merge_strategy_results"]