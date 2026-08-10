"""Pydantic models for the monolith service."""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Instance(BaseModel):
    instance_name: str
    status: Optional[str] = None  # RUNNING|STOPPED|ERROR
    pid: Optional[int] = None
    host: Optional[str] = "127.0.0.1"
    port: Optional[int] = None
    model_path: str
    mmproj_path: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None
    cmd_args: Optional[str] = None
    last_heartbeat: Optional[float] = None
    last_error: Optional[str] = None
    created_at: Optional[float] = Field(default_factory=time.time)
    started_at: Optional[float] = None
    last_stopped_at: Optional[float] = None


class InstanceTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # DEPLOY | STOP | RESUME | MODIFY
    instance_name: str
    port: Optional[int] = None
    model_path: Optional[str] = None
    mmproj_path: Optional[str] = None
    status: Optional[str] = None  # INIT | PROCESSING | FINISHED | FAILED
    error_msg: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None
    cmd_args: Optional[str] = None
    created_at: Optional[float] = Field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


class Log(BaseModel):
    instance_name: str
    content: Optional[str] = None
    last_updated_at: Optional[float] = Field(default_factory=time.time)


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
    timestamp: float
    cpu: CPUInfo
    memory: MemoryInfo
    gpus: List[GPUInfo]


__all__ = ["Instance", "InstanceTask", "Log", "Metric", "CPUInfo", "MemoryInfo", "GPUInfo"]
