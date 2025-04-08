import os
import importlib.resources
import threading
import time
from pathlib import Path
from typing import Optional, Self
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Module-level variables for Prefect server management
# These cannot be inside the Settings class because they can't be pickled
_prefect_server = None
_server_thread = None

# load_dotenv()
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    load_dotenv()
    # Application Config, used with OpenRouter requests
    APP_TITLE: str = os.environ.get("APP_TITLE", "Workflow Automation")
    APP_URL: str = os.environ.get("APP_URL", "https://workflow-automations.local")
    
    # Database settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", '')
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "workflows")
    MONGODB_RESULT_COL: str = os.getenv("MONGODB_RESULT_COL", "repos")
    POSTGRES_DATABASE_URL: str = os.getenv("POSTGRES_DATABASE_URL", '') # Prefect Backend DB
    
    
    #
    DB_DATA_DIR: str = os.getenv("DB_DATA_DIR", '.workflow-automation/data')
    DB_DATA_FILENAME:str = os.getenv("DB_DATA_FILENAME", 'db.json')
    
    # GitHub settings for private repository access
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN", '')
    
    # OpenRouter LLMs
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", '')
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY",'') # 
    
    # Logging settings
    DEBUG: bool = os.getenv("DEBUG", False)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_TRACE: bool = os.getenv("ENABLE_TRACE", False)
    
    # Logfire logging & tracing
    LOGFIRE_API_KEY: Optional[str] = os.getenv("LOGFIRE_API_KEY", '') # Tracing
    
    # Proxy
    LITELLM_PROXY_BASE_URL: Optional[str] = os.getenv("LITELLM_PROXY_BASE_URL", '')
    LITELLM_PROXY_API_KEY: Optional[str] = os.getenv("LITELLM_PROXY_API_KEY", '')
    
    # HTTPX Config for LLM requests
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", 10)) # Concurrency settings for LLM calls
    HTTPX_MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", 3))  # Maximum number of retries
    HTTPX_RETRY_DELAY: int = int(os.getenv("HTTPX_RETRY_DELAY", 2)) # Delay between retries in seconds
    HTTPX_TIMEOUT_SECONDS: int = int(os.getenv("HTTPX_TIMEOUT_SECONDS", 60))  # Timeout for LLM requests
    HTTPX_MAX_CONNECTIONS: int = int(os.getenv("HTTPX_MAX_CONNECTIONS", MAX_WORKERS))
    
    # Tokenization settings - exposed to end users
    DEFAULT_TOKENIZER: str = os.getenv("DEFAULT_TOKENIZER", "o200k_base")  # The tokenizer model to use for token counting
    TOKEN_LIMIT: int = int(os.getenv("TOKEN_FILE_LIMIT", "50000"))  # Default token limit per file chunk
    BYTES_PER_TOKEN: int = int(os.getenv("BYTES_PER_TOKEN", "4"))  # Approximate bytes per token for estimation
    MAX_SAFE_TOKEN_COUNT: int = 4000000  # Maximum safe tokens (~16MB document size for Mongo)

    DEFAULT_REPOMIX_CONFIG_PATH: str = "" # see model_post_init() for more info
    __PREFECT_RESULTS_PERSIST_BY_DEFAULT: str = os.getenv("PREFECT_RESULTS_PERSIST_BY_DEFAULT", 'false')
    # __PREFECT_API_URL: str = os.getenv("PREFECT_API_URL", "http://prefect:4200/api/")
    __PREFECT_API_URL: str = os.getenv("PREFECT_API_URL", "http://localhost:4200/api/")
    @property
    def PREFECT_RESULTS_PERSIST_BY_DEFAULT(self) -> bool:
        return self.__PREFECT_RESULTS_PERSIST_BY_DEFAULT in {'true', 'True', 'yes','y','1'}
    
    @property
    def PREFECT_API_URL(self) -> str:
        """Get the Prefect API URL, defaulting to the Docker-based server URL."""
        return self.__PREFECT_API_URL
    
    @PREFECT_API_URL.setter
    def PREFECT_API_URL(self, value):
        self.__PREFECT_API_URL = value
        # os.environ['PREFECT_API_URL'] = value
        # self.__PREFECT_API_URL = ''
        # os.environ['PREFECT_API_URL'] = ''
    
    def start_prefect_server(self,force_new=False) -> str:
        """Start a Prefect server if needed and return its API URL.
        
        Args:
            force_new: If True, shut down any existing server and start a new one
            
        Returns:
            str: The API URL of the Prefect server (either external or in-memory)
        """
        global _prefect_server, _server_thread
        
        api_url = self.__PREFECT_API_URL
        
        # Check existing connection first
        if not force_new and _test_prefect_connection(api_url):
            return api_url
        
        else:
            return 'http://localhost:4200/api'
            # import uvicorn
            # from prefect.server.api.server import create_app

            # app = create_app(final=True)
            # uvicorn.run(
            #     app=app,
            #     app_dir='src',
            #     host='127.0.0.1',
            #     port=4200,
            #     timeout_keep_alive=5,
            #     log_level=30 #Warnings only
            # )
            
            # print()
        # return api_url

    def is_development(self) -> bool:
        return self.DEBUG
    
    @property
    def log_level(self) -> str:
        return "DEBUG" if self.DEBUG else "INFO"

    @property
    def log_level_int(self) -> int:
        return 10 if self.DEBUG else 20 #INFO

    @classmethod
    def get_repomix_config_path(cls) -> str:
        """Get the path to the repomix config file using a prioritized approach."""
        
        # 1. Check environment variable if defined
        env_path = os.environ.get("REPOMIX_CONFIG_PATH")
        if env_path and Path(env_path).exists():
            return env_path
            
        # 2. Check package resources (works even when installed as package)
        try:
            # First try to get it from the package resources using files() instead of deprecated path()
            resource_path = importlib.resources.files("tools.repomix").joinpath("default_repomix_config.json")
            if resource_path.exists():
                return str(resource_path)
        except (ImportError, ModuleNotFoundError):
            pass
        
        # Fallback to a default path relative to this file
        return str(Path(__file__).parent.parent.parent / "tools" / "repomix" / "default_repomix_config.json")

    def get_db_path(cls) -> str:
        return os.path.join(cls.DB_DATA_DIR,cls.DB_DATA_FILENAME)
        
    def model_post_init(self, __context):
        """Set the repomix config path after initialization"""
        self.DEFAULT_REPOMIX_CONFIG_PATH = self.get_repomix_config_path()
        self.PREFECT_API_URL = self.start_prefect_server()


# Module-level helper functions for Prefect server management
def _test_prefect_connection(api_url: str) -> bool:
    """Test connection to Prefect server"""
    try:
        import requests
        from requests.exceptions import ConnectionError, Timeout
        
        # Simple connection test with timeout
        response = requests.get(
            api_url, 
            timeout=3,
            headers={"Content-Type": "application/json"}
        )
        return response.status_code < 500  # Consider any non-5xx response as success
    except (ConnectionError, Timeout):
        return False
    except Exception as e:
        print(f"Error testing Prefect connection: {str(e)}")
        return False


# Create a global settings object
app_config = Settings()

__all__ = ["app_config"]