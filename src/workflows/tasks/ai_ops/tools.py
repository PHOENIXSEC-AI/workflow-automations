from pydantic_ai.agent import AgentRunResult

from workflows.agents.models import BaseAgentAnalysisResult, AgentAnalysisResult
from workflows.tasks.ai_ops.utils import sanitize_and_parse_agent_response

from core.utils import LoggerFactory

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

async def parse_code_analysis_response(result: AgentRunResult) -> AgentAnalysisResult:
        """
        Parse and validate the agent's response, ensuring it matches the expected structure.
        
        This validator ensures:
        1. The 'file_path' field is present in the result
        2. The given result(raw str) can be parsed into valid JSON object
        
        Parameters:
            result: The raw response from the agent containing extracted fields as defined in instructions
            
        Returns:
            A validated AgentAnalysisResult object with properly structured fields
        """
        # Create default result in case all parsing attempts fail
        parsed_content = AgentAnalysisResult.default()
        
        try:
            # Try to parse response directly using our sanitize function
            content = sanitize_and_parse_agent_response(result)
            
            # If we got a valid AgentAnalysisResult, convert it to BaseAgentAnalysisResult
            if isinstance(content, AgentAnalysisResult):
                # Validate the content has no errors before proceeding
                if hasattr(content, 'errors') and getattr(content, 'errors'):
                    raise ValueError(f"Validation errors in parsed content: {getattr(content, 'errors')}")
                    
                # return AgentAnalysisResult.model_validate(content.model_dump())
                return content
                
            # If we get here, the content is of an unexpected type
            raise ValueError(f"Unexpected content type: {type(content).__name__}")
            
        except Exception as ex:
            # Log the error but return a default object instead of failing
            logger.error(f"Error parsing agent response: {str(ex)}")
            return parsed_content


__all__ = ["parse_code_analysis_response"]