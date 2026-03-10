from typing import Optional
from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime

class ConnectorBase(BaseModel):
    name: str
    type: str
    host: str
    port: int
    database_name: str
    username: str

class ConnectorCreate(ConnectorBase):
    password: str

class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class ConnectorResponse(ConnectorBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    initialization_status: str
    initialized_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
