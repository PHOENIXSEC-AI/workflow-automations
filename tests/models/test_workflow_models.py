import pytest
from workflows.agents.models import RunAIDeps, RunAITask

class TestRunAIDeps:
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        deps = RunAIDeps(target_obj_id="test_id")
        assert deps.db_name == 'workflows'
        assert deps.db_col_name == 'repomix'
        assert deps.target_obj_id == 'test_id'
        assert deps.shared_agent is None
    
    def test_to_dict(self):
        """Test the to_dict method correctly converts to dictionary."""
        deps = RunAIDeps(
            db_name="test_db",
            db_col_name="test_col",
            target_obj_id="test_id",
            shared_agent="some_agent"
        )
        result = deps.to_dict()
        
        # Verify dictionary contents
        assert result == {
            "db_name": "test_db",
            "db_col_name": "test_col",
            "target_obj_id": "test_id"
        }
        
        # Verify shared_agent is excluded
        assert "shared_agent" not in result
    
    def test_dict_methods(self):
        """Test that all dict-related methods return the same result."""
        deps = RunAIDeps(target_obj_id="test_id")
        
        # All these methods should return the same dictionary
        expected = {"db_name": "workflows", "db_col_name": "repomix", "target_obj_id": "test_id"}
        assert deps.to_dict() == expected
        assert deps.__dict__() == expected
        assert deps.__json__() == expected
        assert deps.toJSON() == expected

class TestRunAITask:
    def test_model_creation(self):
        """Test that the model can be created with required fields."""
        task = RunAITask(
            db_name="test_db",
            db_col_name="test_col",
            target_obj_id="test_id",
            flow_id="flow1",
            flow_name="test_flow",
            flow_run_name="run1",
            flow_run_count=1,
            task_run_id="task1",
            task_run_name="test_task"
        )
        
        # Verify all fields are set correctly
        assert task.db_name == "test_db"
        assert task.db_col_name == "test_col"
        assert task.target_obj_id == "test_id"
        assert task.flow_id == "flow1"
        assert task.flow_name == "test_flow"
        assert task.flow_run_name == "run1"
        assert task.flow_run_count == 1
        assert task.task_run_id == "task1"
        assert task.task_run_name == "test_task"
    
    def test_model_validation(self):
        """Test that the model validates required fields."""
        # Should raise validation error when missing required fields
        with pytest.raises(ValueError):
            RunAITask()
        
        # Should raise validation error on incorrect type
        with pytest.raises(ValueError):
            RunAITask(
                db_name="test_db",
                db_col_name="test_col",
                target_obj_id="test_id",
                flow_id="flow1",
                flow_name="test_flow",
                flow_run_name="run1",
                flow_run_count="not_an_integer",  # This should be an integer
                task_run_id="task1",
                task_run_name="test_task"
            )

if __name__ == "__main__":
    pytest.main(["-xvs", "--pdb", __file__]) 