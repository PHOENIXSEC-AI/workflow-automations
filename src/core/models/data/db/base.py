from typing import Any, Dict, List, Optional, Union
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class BaseDocument(BaseModel):
    """Base document model with ID and timestamps"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return self.model_dump() 