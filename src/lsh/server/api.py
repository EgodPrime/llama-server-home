import json
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from lsh.server.db import Database, get_db, load_config


api_router = APIRouter()


def parse_json_field(value: str | None) -> Dict[str, Any] | List[Any] | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def format_instance(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = doc.copy()
    doc["env"] = parse_json_field(doc.get("env"))
    doc["config"] = parse_json_field(doc.get("config"))
    doc["cmd_args"] = doc.get("cmd_args")
    return doc


def format_task(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = doc.copy()
    doc["env"] = parse_json_field(doc.get("env"))
    doc["config"] = parse_json_field(doc.get("config"))
    doc["cmd_args"] = doc.get("cmd_args")
    return doc


def format_profile(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc = doc.copy()
    doc["instances"] = parse_json_field(doc.get("instances")) or []
    return doc


def parse_gpus(gpus_info: str | None) -> List[Dict[str, Any]]:
    if not gpus_info:
        return []
    try:
        return json.loads(gpus_info)
    except (json.JSONDecodeError, TypeError):
        return []


# --- Instances ---


@api_router.get("/api/instances")
async def list_instances(db: Database = Depends(get_db)):
    return [format_instance(i) for i in db.list_instances()]


@api_router.get("/api/instances/{name}")
async def get_instance(name: str, db: Database = Depends(get_db)):
    inst = db.get_instance(name)
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    return format_instance(inst)


@api_router.get("/api/instances/{name}/logs")
async def get_instance_logs(name: str, db: Database = Depends(get_db)):
    log = db.get_instance_log(name)
    if not log:
        return {"instance_name": name, "content": ""}
    return log


@api_router.get("/api/instances/{name}/cmd")
async def get_instance_cmd(name: str, request: Request, db: Database = Depends(get_db)):
    from pathlib import Path
    import shlex

    inst = db.get_instance(name)
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")

    agent = request.app.state.agent
    cfg = load_config()

    model_path = inst.get("model_path")
    mmproj_path = inst.get("mmproj_path")
    port = inst.get("port")
    config = parse_json_field(inst.get("config")) or {}
    cmd_args_raw = inst.get("cmd_args")

    if not model_path or not port:
        raise HTTPException(status_code=400, detail="Instance missing model_path or port")

    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_file = log_dir / f"{name}.log"
    host = cfg.get("host", "127.0.0.1")

    cmd = [
        str(agent.llama_path),
        "--model", str(agent.storage_dir / model_path),
        "--host", host,
        "--port", str(port),
        "--log-file", str(log_file),
    ]
    if mmproj_path:
        cmd += ["--mmproj", str(agent.storage_dir / mmproj_path)]
    for k, v in config.items():
        cmd += [k, str(v)]
    if cmd_args_raw:
        cmd += shlex.split(cmd_args_raw)

    return {"cmd": cmd}


@api_router.delete("/api/instances/{name}")
async def delete_instance(name: str, db: Database = Depends(get_db)):
    if not db.get_instance(name):
        raise HTTPException(status_code=404, detail="Instance not found")
    db.delete_instance(name)
    return {"message": f"Instance {name} deleted"}


# --- Tasks ---


@api_router.get("/api/tasks")
async def list_tasks(db: Database = Depends(get_db)):
    return [format_task(t) for t in db.list_instance_tasks()]


class CreateTaskRequest(BaseModel):
    instance_name: str
    type: str = "DEPLOY"
    port: Optional[int] = None
    model_path: Optional[str] = None
    mmproj_path: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None
    cmd_args: Optional[str] = None


@api_router.post("/api/tasks/create")
async def create_task(request: CreateTaskRequest, db: Database = Depends(get_db)):
    task_id = str(uuid.uuid4())
    db.create_instance_task({
        "task_id": task_id,
        "type": request.type,
        "instance_name": request.instance_name,
        "port": request.port,
        "model_path": request.model_path,
        "mmproj_path": request.mmproj_path,
        "status": "INIT",
        "env": request.env,
        "config": request.config,
        "cmd_args": request.cmd_args,
    })
    return {"task_id": task_id, "message": "Task created"}


@api_router.post("/api/tasks/stop/{name}")
async def stop_instance(name: str, db: Database = Depends(get_db)):
    if not db.get_instance(name):
        raise HTTPException(status_code=404, detail="Instance not found")
    task_id = str(uuid.uuid4())
    db.create_instance_task({
        "task_id": task_id,
        "type": "STOP",
        "instance_name": name,
    })
    return {"task_id": task_id, "message": f"Stop task created for {name}"}


@api_router.post("/api/tasks/resume/{name}")
async def resume_instance(name: str, db: Database = Depends(get_db)):
    if not db.get_instance(name):
        raise HTTPException(status_code=404, detail="Instance not found")
    task_id = str(uuid.uuid4())
    db.create_instance_task({
        "task_id": task_id,
        "type": "RESUME",
        "instance_name": name,
    })
    return {"task_id": task_id, "message": f"Resume task created for {name}"}


@api_router.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, db: Database = Depends(get_db)):
    if not db.get_instance_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete_instance_task(task_id)
    return {"message": f"Task {task_id} deleted"}


# --- Storage ---


def _safe_resolve(base: str, user_path: str) -> str:
    resolved = os.path.realpath(os.path.join(base, user_path))
    base_resolved = os.path.realpath(base)
    if not resolved.startswith(base_resolved + os.sep) and resolved != base_resolved:
        raise HTTPException(status_code=403, detail="Access denied: path traversal detected")
    return resolved


def _list_directory(dir_path: str, base_path: str, hidden_ok: bool = False) -> List[Dict[str, Any]]:
    result = []
    for item in os.listdir(dir_path):
        if not hidden_ok and item.startswith("."):
            continue
        item_path = os.path.join(dir_path, item)
        rel_path = os.path.relpath(item_path, base_path)
        if os.path.isdir(item_path):
            result.append({"name": item, "type": "directory", "path": rel_path})
        else:
            result.append({"name": item, "type": "file", "path": rel_path})
    return result


@api_router.get("/api/storage/list_root")
async def list_storage_root(db: Database = Depends(get_db)):
    storage_dir = load_config()["storage_dir"]
    if not os.path.exists(storage_dir):
        return []
    return _list_directory(storage_dir, storage_dir, hidden_ok=False)


@api_router.get("/api/storage/list_dir/{dir_path:path}")
async def list_storage_dir(dir_path: str, db: Database = Depends(get_db)):
    storage_dir = load_config()["storage_dir"]
    target_dir = _safe_resolve(storage_dir, dir_path)
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        raise HTTPException(status_code=404, detail="Directory not found")
    return _list_directory(target_dir, storage_dir)


@api_router.get("/api/storage/list_models")
async def list_models(db: Database = Depends(get_db)):
    storage_dir = load_config()["storage_dir"]
    if not os.path.exists(storage_dir):
        return []
    models = []
    for item in os.listdir(storage_dir):
        model_dir = os.path.join(storage_dir, item)
        if not os.path.isdir(model_dir):
            continue
        model_files = _list_directory(model_dir, storage_dir)
        model_info = {"model_name": item, "model_file": None, "mmproj_file": None}
        for f in model_files:
            if f["type"] == "file" and f["name"].endswith(".gguf"):
                if f["name"].startswith("mmproj"):
                    model_info["mmproj_file"] = f["path"]
                elif not model_info["model_file"]:
                    model_info["model_file"] = f["path"]
        if model_info["model_file"]:
            models.append(model_info)
    return models


# --- Metrics ---


@api_router.get("/api/metrics")
async def list_metrics(n: int = Query(default=20, ge=1, le=500), db: Database = Depends(get_db)):
    metrics = db.list_metrics(n)
    for m in metrics:
        m["gpus"] = parse_gpus(m.get("gpus_info"))
        m.pop("gpus_info", None)
    return metrics


# --- Profiles ---


class CreateProfileRequest(BaseModel):
    profile_name: str
    instances: List[Dict[str, Any]]


@api_router.get("/api/profiles/list")
async def list_profiles(db: Database = Depends(get_db)):
    return [format_profile(g) for g in db.list_profiles()]


@api_router.get("/api/profiles/{name}")
async def get_profile(name: str, db: Database = Depends(get_db)):
    prof = db.get_profile(name)
    if not prof:
        raise HTTPException(status_code=404, detail="Profile not found")
    return format_profile(prof)


@api_router.post("/api/profiles/create")
async def create_profile(request: CreateProfileRequest, db: Database = Depends(get_db)):
    if db.get_profile(request.profile_name):
        raise HTTPException(status_code=409, detail="Profile already exists")
    db.create_profile(request.profile_name, request.instances)
    return {"message": f"Profile {request.profile_name} created"}


@api_router.delete("/api/profiles/{name}")
async def delete_profile(name: str, db: Database = Depends(get_db)):
    if not db.get_profile(name):
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete_profile(name)
    return {"message": f"Profile {name} deleted"}


@api_router.post("/api/profiles/{name}/deploy")
async def deploy_profile(name: str, db: Database = Depends(get_db)):
    prof = db.get_profile(name)
    if not prof:
        raise HTTPException(status_code=404, detail="Profile not found")
    instances = prof["instances"] if isinstance(prof["instances"], list) else json.loads(prof["instances"])
    task_ids = []
    for inst in instances:
        task_id = str(uuid.uuid4())
        db.create_instance_task({
            "task_id": task_id,
            "type": "DEPLOY",
            "instance_name": inst.get("instance_name"),
            "port": inst.get("port"),
            "model_path": inst.get("model_path"),
            "mmproj_path": inst.get("mmproj_path"),
            "status": "INIT",
            "env": inst.get("env"),
            "config": inst.get("config"),
        })
        task_ids.append(task_id)
    return {"message": f"Deploy tasks created for profile {name}", "task_ids": task_ids}
