from typing import Union

from core.utils.logger import LoggerFactory
from core.utils.format import repomix_results_to_markdown

from tools.repomix import run_repomix, run_repomix_local, RepoMixParser

from prefect import task
from prefect.states import Completed, Failed
from prefect.artifacts import create_markdown_artifact

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

@task(name="analyze_remote_repo")
def analyze_remote_repo(remote_url: str,
    config_path: str,
    result_path: str) -> Union[Completed,Failed]:
    
    logger.debug(f"Running a analyze_remote_repo task with: remote_url={remote_url},config_path={config_path},result_path={result_path}")
    
    return_code, abs_output_path, stderr  = run_repomix(remote_url, config_path, result_path)
    
    task_result = {
        "repo_url": remote_url,
        "return_code":return_code,
        "output_path":abs_output_path,
        "stderr":stderr
    }
    if stderr:
        return Failed(data=task_result,message="❌ "+str(stderr))
    
    _debug_task_result_str = repomix_results_to_markdown(data=task_result,repo_url=remote_url)
    
    create_markdown_artifact(markdown=_debug_task_result_str,key="debug-analyze-remote-repo")
    
    return Completed(data=task_result,message="✅ Task Run Success")

@task(name="analyze_local_repo")
def analyze_local_repo(local_repo_path: str,
    config_path: str,
    result_path: str) -> Union[Completed,Failed]:
    
    logger.debug(f"Running analyze_local_repo task with: local_repo_path={local_repo_path},config_path={config_path},result_path={result_path}")
    
    return_code, abs_output_path, stderr = run_repomix_local(local_repo_path, config_path, result_path)
    
    task_result = {
        "repo_path": local_repo_path,
        "return_code": return_code,
        "output_path": abs_output_path,
        "stderr": stderr
    }
    if stderr:
        return Failed(data=task_result, message="❌ "+str(stderr))
    
    _debug_task_result_str = repomix_results_to_markdown(data=task_result)
    
    create_markdown_artifact(markdown=_debug_task_result_str, key="debug-analyze-local-repo")
    
    return Completed(data=task_result, message="✅ Task Run Success")

@task(name="parse_tool_results")
def parse_tool_results(result_path:str) -> Union[Completed,Failed]:
    
    parsed_result_data = RepoMixParser.parse(file_path=result_path)
    
    task_result = parsed_result_data if parsed_result_data else None
    
    if not task_result:
        return Failed(message="❌ Failed to parse Repomix tool result file")
    
    if app_config.is_development():
        _debug_task_result_str = repomix_results_to_markdown(data=task_result)
        create_markdown_artifact(markdown=_debug_task_result_str,key="debug-parse-tool-results")
    
    return Completed(data=task_result, message="✅ Task Run Success")


__all__ = ["analyze_remote_repo", "analyze_local_repo", "parse_tool_results"]
