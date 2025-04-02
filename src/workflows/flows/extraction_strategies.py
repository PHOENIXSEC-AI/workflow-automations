from typing import Union
from prefect import flow
from prefect.states import Completed,Failed
from workflows.agents.prompts import CODE_ANALYZER_BASE_INSTR
from workflows.flows.concurrent_agents import run_concurrent_agents
from workflows.agents.models import RunAIDeps, RunAgentRepomixDeps

from core.models import RepoAnalysisResult

@flow(
    log_prints=True, 
    name="add_base", 
    result_storage="local-file-system/dev-result-storage",
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
    if not repomix_result:
        return {}

    task_ctx = RunAgentRepomixDeps(
        repomix_data=repomix_result,
    )
    
    agent_to_call = 'env-vars-extractor'
    
    return await run_concurrent_agents(
        ctx=task_ctx,
        agent_name=agent_to_call,
        instructions=CODE_ANALYZER_BASE_INSTR)

__all__ = ["add_base"]