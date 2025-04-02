from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional

class TimestampedModel(BaseModel):
    """Base model with created_at and updated_at timestamps."""
    created_at: datetime = datetime.now(tz=timezone.utc)
    updated_at: Optional[datetime] = None 