"""
Agent configuration module for AI operations.

This module contains configuration for different AI agents, 
including model selection, system prompts, and network settings.
"""

import httpx
import os
import time
from typing import Tuple, Dict, Any

from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# from workflows.agents.models import RunAIDeps
from workflows.agents.prompts import CODE_ANALYZER_SYS_PROMPT, SECURITY_ANALYZER_SYS_PROMPT
from workflows.agents.openrouter_models import DEEPSEEK_V3_0324, GEMINI_FLASH_V2, HERMES_3
from workflows.tasks.ai_ops.tools import parse_code_analysis_response

DEFAULT_MODEL_TEMP = 0.5
DEFAULT_MODEL = GEMINI_FLASH_V2
# Agent configuration mapping
agent_mapping = {
    "env-vars-extractor": {
        "model": GEMINI_FLASH_V2,
        "system_prompt": CODE_ANALYZER_SYS_PROMPT,
        # "deps": RunAIDeps
    },
    "appsec": {
        "model": GEMINI_FLASH_V2, # Prod HERMES_3
        "system_prompt": SECURITY_ANALYZER_SYS_PROMPT,
    }
}

# Maximum concurrent connections for HTTP LLM requests
HTTPX_MAX_CONNECTIONS = os.environ.get("MAX_WORKERS", 10)
# Retry settings for LiteLLM proxy connection
MAX_RETRIES = 3  # Maximum number of retries
RETRY_DELAY = 2  # Delay between retries in seconds
TIMEOUT_SECONDS = 60  # Timeout for LLM requests

# LiteLLM Proxy Configuration
# When running in Docker, use the service name (litellm-proxy) instead of localhost
LITELLM_PROXY_BASE_URL = os.environ.get("LITELLM_PROXY_BASE_URL", "http://litellm-proxy:4000")
LITELLM_PROXY_API_KEY = os.environ.get("LITELLM_PROXY_AGENT_KEY", "")

# OpenRouter Configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", '')


APP_TITLE = os.environ.get("APP_TITLE", "Workflow Automation")
APP_URL =os.environ.get("APP_URL", "https://workflow-automations.local")

from core.config import app_config

def get_async_litellm_proxy_agent(agent_name: str) -> Tuple[Agent, str]:
    """
    Create an async-compatible Pydantic AI agent that uses LiteLLM proxy.
    
    Args:
        agent_name: Name of the agent to create from agent_mapping
        
    Returns:
        Tuple containing (Agent instance, agent name)
    """
    agent_config = agent_mapping.get(agent_name, {})
    
    agent_system_prompt = agent_config.get('system_prompt', 'You are helpful assistant')
    agent_model_name = agent_config.get('model', DEFAULT_MODEL)
    
    # Configure AsyncClient for LLM requests
    timeout = httpx.Timeout(timeout=TIMEOUT_SECONDS, connect=10)
    limits = httpx.Limits(max_connections=HTTPX_MAX_CONNECTIONS)
    transport = httpx.AsyncHTTPTransport(limits=limits)
    headers = {
        'X-Title': agent_name,
        'User-Agent': f'pydantic-ai/{agent_name}',
        # Add retry and idempotency headers for LiteLLM proxy
        'X-Retry-Count': '5',  # Increased from 3
        'X-Idempotency-Key': f'{agent_name}-{time.time()}',
        # Add safe mode for graceful error handling
        'X-Litellm-Safe-Mode': 'true'
    }
    custom_http_client = httpx.AsyncClient(
        transport=transport, 
        timeout=timeout, 
        headers=headers
    )
    
    # Initialize OpenAI model with LiteLLM proxy
    # LiteLLM proxy will route to the appropriate provider
    model = OpenAIModel(
        agent_model_name,
        provider=OpenAIProvider(
            base_url=LITELLM_PROXY_BASE_URL,
            api_key=LITELLM_PROXY_API_KEY,
            http_client=custom_http_client
        )
    )
    
    proxy_agent = Agent(
        model=model,
        name=agent_name,
        instrument=True,
        system_prompt=agent_system_prompt
    )
    
    return proxy_agent, agent_name

def get_async_openrouter_agent(agent_name: str) -> Tuple[Agent, str]:
    """
    Create an async-compatible Pydantic AI agent with custom HTTP client.
    
    Args:
        agent_name: Name of the agent to create from agent_mapping
        
    Returns:
        Tuple containing (Agent instance, agent name)
    """
    agent_config = agent_mapping.get(agent_name, {})
    
    agent_system_prompt = agent_config.get('system_prompt', 'You are helpful assistant')
    agent_model_name = agent_config.get('model', DEFAULT_MODEL)
    
    # Configure AsyncClient for LLM requests
    timeout = httpx.Timeout(timeout=30, connect=5)
    limits = httpx.Limits(max_connections=HTTPX_MAX_CONNECTIONS)
    transport = httpx.AsyncHTTPTransport(limits=limits)
    headers = {
        'X-Title': agent_name,
        'User-Agent': f'pydantic-ai/{agent_name}'
    }
    custom_http_client = httpx.AsyncClient(
        transport=transport, 
        timeout=timeout, 
        headers=headers
    )
    
    # Initialize OpenAI model with OpenRouter
    model = OpenAIModel(
        agent_model_name,
        provider=OpenAIProvider(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
            http_client=custom_http_client
        )
    )
    
    code_analyzer_agent = Agent(
        model=model,
        name=agent_name,
        instrument=True,
        system_prompt=agent_system_prompt
    )
    
    return code_analyzer_agent, agent_name

def get_async_pydanticai_agent(agent_name:str) -> Tuple[Agent, Dict[str, Any]]:
    """
    Create an PydanticAI Agent with HTTPX client for more efficient handling of concurrent requests.
    
    This implementation uses the httpx directly,
    which provides better optimization for concurrent API calls and follows OpenRouter's
    recommended approach.
    
    Args:
        agent_name: Name of the agent to create from agent_mapping
        
    Returns:
        Tuple containing (pydantic_ai.Agent, agent_config)
    """
    agent_config = agent_mapping.get(agent_name, {})
    
    # Get system prompt and model from config
    agent_system_prompt = agent_config.get('system_prompt', 'You are helpful assistant')
    agent_model_name = agent_config.get('model', DEFAULT_MODEL)
    
    timeout = httpx.Timeout(timeout=30, connect=5)
    limits = httpx.Limits(max_connections=10)
    transport = httpx.AsyncHTTPTransport(limits=limits)
    headers = {
        "HTTP-Referer": APP_URL,
        'X-Title': "Test Agent",
        'User-Agent': f'pydantic-ai/test-agent',
    }
    
    custom_httpx_client = httpx.AsyncClient(
        transport=transport, 
        timeout=timeout, 
        headers=headers
    )
    
    model = OpenAIModel(
        agent_model_name,
        provider=OpenAIProvider(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
            http_client=custom_httpx_client
        )
    )
    
    agent = Agent(
        model=model,
        name=agent_name,
        instrument=True,
        result_type=str, # type: ignore
        result_tool_name='parse_code_analysis_response',
        system_prompt=CODE_ANALYZER_SYS_PROMPT
    )
    
    # Register result parser
    agent.result_validator(parse_code_analysis_response)
    
    # Store agent configuration for later use
    config = {
        "model": agent_model_name,
        "system_prompt": agent_system_prompt,
        "headers": {
            "HTTP-Referer": APP_URL,
            "X-Title": APP_TITLE
        }
    }
    
    return agent, config

def get_async_openai_agent(agent_name: str) -> Tuple[AsyncOpenAI, Dict[str, Any]]:
    """
    Create an AsyncOpenAI client for more efficient handling of concurrent requests.
    
    This implementation uses the official AsyncOpenAI client instead of httpx directly,
    which provides better optimization for concurrent API calls and follows OpenRouter's
    recommended approach.
    
    Args:
        agent_name: Name of the agent to create from agent_mapping
        
    Returns:
        Tuple containing (AsyncOpenAI client, agent_config)
    """
    agent_config = agent_mapping.get(agent_name, {})
    
    # Get system prompt and model from config
    agent_system_prompt = agent_config.get('system_prompt', 'You are helpful assistant')
    agent_model_name = agent_config.get('model', DEFAULT_MODEL)
    
    # Configure AsyncOpenAI client for OpenRouter
    client = AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
        timeout=httpx.Timeout(timeout=TIMEOUT_SECONDS),
        max_retries=3
    )
    
    # Store agent configuration for later use
    config = {
        "model": agent_model_name,
        "system_prompt": agent_system_prompt,
        "headers": {
            "HTTP-Referer": APP_URL,
            "X-Title": APP_TITLE
        }
    }
    
    return client, config

__all__ = [
    "agent_mapping", 
    "get_async_openrouter_agent", 
    "get_async_openai_agent",
    "get_async_litellm_proxy_agent"
]