from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ResourceCreate(BaseModel):
    resource_name: str = Field(..., min_length=2, max_length=80)
    quantity_available: int = Field(..., ge=0, le=1000)


class ResourceUpdate(BaseModel):
    quantity_available: Optional[int] = Field(None, ge=0, le=1000)


class ResourceOut(BaseModel):
    id: int
    resource_name: str
    quantity_available: int
    quantity_in_use: int
    quantity_free: int
    updated_at: datetime
