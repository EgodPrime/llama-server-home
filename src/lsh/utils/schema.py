from __future__ import annotations

import uuid
import time
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
    node_id: str
    port: int

    model_path: str
    mmproj_path: Optional[str] = None

    """
    INIT:     任务已创建，等待 Agent 领取
    PROCESSING: Agent 已领取任务，正在执行部署或取消操作
    FINISHED: 模型已就绪，Agent 已启动服务 (或停止操作完成)
    FAILED:   任务执行失败 (网络错误等)
    """
    status: Optional[str] = None

    created_at: Optional[float] = Field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    error_msg: Optional[str] = None

    env: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None


class Instance(BaseModel):
    instance_name: str
    node_id: str

    status: Optional[str] = None  # RUNNING|STOPPED|ERROR|RESTARTING

    pid: Optional[int] = None
    host: Optional[str] = None
    port: Optional[int] = None

    model_path: str
    mmproj_path: Optional[str] = None
    local_model_path: Optional[str] = None
    local_mmproj_path: Optional[str] = None
    model_size_b: Optional[float] = None

    env: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None

    last_heartbeat: Optional[float] = None
    last_error: Optional[str] = None

    created_at: Optional[float] = Field(default_factory=time.time)
    started_at: Optional[float] = None
    last_stopped_at: Optional[float] = None


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

    created_at: Optional[float] = Field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


class Log(BaseModel):
    node_id: str
    instance_name: str
    content: Optional[str] = None  # latest ~50 lines joined by \n
    created_at: Optional[float] = Field(default_factory=time.time)
    last_updated_at: Optional[float] = None


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

    def __repr__(self):
        res = f"CPU({self.cpu.cores_count} logic cores): {self.cpu.usage_percent:.1f}%\n"
        res += f"Memory: {self.memory.used_mb:.1f}MB/{self.memory.total_mb:.1f}MB ({self.memory.usage_percent:.1f}%)\n"
        if self.gpus:
            res += "GPUs:\n"
            for gpu in self.gpus:
                res += f"  GPU {gpu.id} ({gpu.model}): {gpu.memory_used_mb:.1f}MB/{gpu.memory_total_mb:.1f}MB\n"
        else:
            res += "No GPU detected.\n"
        return res

    def __str__(self):
        return self.__repr__()


__all__ = [
    "Node",
    "CreateInstanceTask",
    "Instance",
    "ManageInstanceTask",
    "Log",
    "Metric",
]
