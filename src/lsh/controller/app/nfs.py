import os

from fastapi import APIRouter, HTTPException

from lsh.controller.lib import get_controller

router = APIRouter(prefix="/nfs", tags=["nfs"])


def _safe_resolve(base: str, user_path: str) -> str:
    """Resolve a user-provided path and ensure it stays within the base directory."""
    resolved = os.path.realpath(os.path.join(base, user_path))
    base_resolved = os.path.realpath(base)
    if not resolved.startswith(base_resolved + os.sep) and resolved != base_resolved:
        raise HTTPException(status_code=403, detail="Access denied: path traversal detected")
    return resolved


def list_directory(dir_path: str, base_path: str):
    res = []
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        nfs_path = os.path.relpath(item_path, base_path)
        if os.path.isdir(item_path):
            res.append({"name": item, "type": "directory", "nfs_path": nfs_path})
        else:
            res.append({"name": item, "type": "file", "nfs_path": nfs_path})
    return res


@router.get("/list_root")
async def list_nfs_root():
    base = get_controller().nfs_path
    return list_directory(base, base)


@router.get("/list_dir/{dir_path}")
async def list_nfs_dir(dir_path: str):
    base = get_controller().nfs_path
    target_dir = _safe_resolve(base, dir_path)
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return {"error": "Directory not found"}
    return list_directory(target_dir, base)


@router.get("/list_models")
async def list_nfs_models():
    base = get_controller().nfs_path
    root_items = list_directory(base, base)
    models = []
    for item in root_items:
        if item["type"] == "directory":
            model_dir = os.path.join(base, item["name"])
            model_name = item["name"]
            model_files = list_directory(model_dir, base)
            model_info = {"model_name": model_name, "model_file": None, "mmproj_file": None}
            for f in model_files:
                if f["type"] == "file" and f["name"].endswith(".gguf"):
                    if f["name"].startswith("mmproj"):
                        model_info["mmproj_file"] = f["nfs_path"]
                    else:
                        model_info["model_file"] = f["nfs_path"]
            models.append(model_info)
    return models
