from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field


class Node(BaseModel):
    name: str
    ip_address: str
    llama_path: str
    status: str  # "ONLINE|OFFLINE"
    last_heartbeat: float
    registered_at: float

    @computed_field
    @property
    def node_id(self) -> str:
        return f"{self.name}@{self.ip_address}"

    def __repr__(self):
        return f"Node(name={self.name}, ip_address={self.ip_address}, status={self.status})"

    def __str__(self):
        return self.__repr__()


class CreateInstanceTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # DEPLOY | CANCEL
    instance_name: str
    instance_labels: Optional[List[str]] = None
    node_id: str

    model_path: str
    model_hash: Optional[str] = None
    mmproj_path: Optional[str] = None
    mmproj_hash: Optional[str] = None

    status: Optional[str] = None

    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    error_msg: Optional[str] = None

    env: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None


class Instance(BaseModel):
    instance_name: str
    instance_labels: Optional[List[str]] = None
    node_id: str

    status: Optional[str] = None  # RUNNING|STOPPED|ERROR|RESTARTING

    pid: Optional[int] = None
    port: Optional[int] = None
    host: Optional[str] = None

    model_path: str
    local_path: Optional[str] = None
    model_size_b: Optional[float] = None

    env: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None

    last_heartbeat: Optional[datetime] = None
    last_error: Optional[str] = None

    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    last_stopped_at: Optional[datetime] = None


class ManageInstanceTask(BaseModel):
    task_id: str
    type: str  # RESTART | STOP | START | DESTROY | MODIFY
    instance_name: str
    node_id: str
    triggered_by: Optional[str] = None  # USER | SYSTEM
    status: Optional[str] = None
    error_msg: Optional[str] = None

    env_override: Optional[Dict[str, str]] = None
    config_override: Optional[Dict[str, Any]] = None

    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class Log(BaseModel):
    node_id: str
    instance_name: str
    content: Optional[str] = None  # latest ~50 lines joined by \n
    created_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None


class CPUInfo(BaseModel):
    usage_percent: float
    cores_count: int


class MemoryInfo(BaseModel):
    total_mb: float
    used_mb: float
    free_mb: float
    usage_percent: float


class GPUInfo(BaseModel):
    id: int
    model: str
    temperature_c: float
    power_draw_w: float
    memory_total_mb: float
    memory_used_mb: float
    memory_free_mb: float


class Metric(BaseModel):
    node_id: str
    timestamp: float
    cpu: CPUInfo
    memory: MemoryInfo
    gpus: List[GPUInfo]


__all__ = [
    "Node",
    "CreateInstanceTask",
    "Instance",
    "ManageInstanceTask",
    "Log",
    "Metric",
]
