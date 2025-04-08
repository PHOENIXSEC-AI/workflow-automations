import pytest
from typing import List
from workflows.agents.models import (
    BaseAgentAnalysisResult,
    EnvVarInfo,
    DbTable,
    DbInfo,
    ApiEndpoint,
    ApiInfo
)

class TestEnvVarInfo:
    def test_creation(self):
        """Test that EnvVarInfo can be created with required fields."""
        env_var = EnvVarInfo(
            name="DATABASE_URL",
            description="Connection string for the database",
            context="Used in config.py for database initialization"
        )
        
        assert env_var.name == "DATABASE_URL"
        assert env_var.description == "Connection string for the database"
        assert env_var.context == "Used in config.py for database initialization"

class TestDbTable:
    def test_creation(self):
        """Test that DbTable can be created with required fields."""
        table = DbTable(
            name="users",
            operations=["read", "write", "update"],
            context="Stores user information for authentication"
        )
        
        assert table.name == "users"
        assert table.operations == ["read", "write", "update"]
        assert table.context == "Stores user information for authentication"

class TestDbInfo:
    def test_creation(self):
        """Test that DbInfo can be created with required fields."""
        table = DbTable(
            name="users",
            operations=["read", "write"],
            context="Stores user account data"
        )
        
        db_info = DbInfo(
            name="application_db",
            tables=[table],
            context="Main application database"
        )
        
        assert db_info.name == "application_db"
        assert db_info.context == "Main application database"
        assert len(db_info.tables) == 1
        assert db_info.tables[0].name == "users"
        assert db_info.tables[0].operations == ["read", "write"]

class TestApiEndpoint:
    def test_creation(self):
        """Test that ApiEndpoint can be created with required fields."""
        endpoint = ApiEndpoint(
            name="Get Users",
            description="Fetches a list of users",
            context="Requires authentication token, returns paginated results"
        )
        
        assert endpoint.name == "Get Users"
        assert endpoint.description == "Fetches a list of users"
        assert endpoint.context == "Requires authentication token, returns paginated results"

class TestApiInfo:
    def test_creation(self):
        """Test that ApiInfo can be created with required fields."""
        endpoint = ApiEndpoint(
            name="Get Users",
            description="Fetches a list of users",
            context="Requires authentication token"
        )
        
        api_info = ApiInfo(
            host="https://api.example.com",
            context="RESTful API for user management",
            endpoints=[endpoint]
        )
        
        assert api_info.host == "https://api.example.com"
        assert api_info.context == "RESTful API for user management"
        assert len(api_info.endpoints) == 1
        assert api_info.endpoints[0].name == "Get Users"

class TestBaseAgentAnalysisResult:
    def test_creation(self):
        """Test that BaseAgentAnalysisResult can be created with all fields."""
        env_var = EnvVarInfo(
            name="DATABASE_URL",
            description="Connection string for the database",
            context="Used in config.py"
        )
        
        table = DbTable(
            name="users",
            operations=["read", "write"],
            context="Stores user information"
        )
        
        db_info = DbInfo(
            name="app_db",
            context="Main application database",
            tables=[table]
        )
        
        endpoint = ApiEndpoint(
            name="Get Users",
            description="Fetches a list of users",
            context="Implementation details"
        )
        
        api_info = ApiInfo(
            host="https://api.example.com",
            context="User management API",
            endpoints=[endpoint]
        )
        
        result = BaseAgentAnalysisResult(
            file_path="app/config.py",
            env_vars=[env_var],
            db=[db_info],
            api=[api_info]
        )
        
        assert result.file_path == "app/config.py"
        assert len(result.env_vars) == 1
        assert len(result.db) == 1
        assert len(result.api) == 1
        assert result.env_vars[0].name == "DATABASE_URL"
        assert result.db[0].name == "app_db"
        assert result.api[0].host == "https://api.example.com"
    
    def test_default_factory(self):
        """Test the default factory method."""
        result = BaseAgentAnalysisResult.default()
        
        assert result.file_path == "default"
        assert len(result.env_vars) == 0
        assert len(result.db) == 0
        assert len(result.api) == 0
    
    def test_empty_lists(self):
        """Test that empty lists are handled correctly."""
        result = BaseAgentAnalysisResult(file_path="test.py")
        
        assert result.file_path == "test.py"
        assert len(result.env_vars) == 0
        assert len(result.db) == 0
        assert len(result.api) == 0

if __name__ == "__main__":
    pytest.main(["-xvs", "--pdb", __file__]) 