from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    payload: dict[str, Any]


class RecordOut(BaseModel):
    id: int
    key: str
    payload: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
