import os
import threading
import time
from contextlib import asynccontextmanager
from typing import List

import bcrypt
import fastapi
import jwt
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from lsh.controller.lib import Controller
from lsh.repo.metrics import get_metrics_last_n
from lsh.utils.schema import Instance, InstanceGroup, InstanceTask, Log, User

controller = Controller()


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    print("[APP] 启动生命周期...")

    # 1. 启动后台线程
    th = threading.Thread(target=controller.node_discovery_and_check_loop, daemon=True)
    th.start()
    print(f"[APP] 已启动线程，ID: {th.ident}")

    # 2. 等待服务器完全就绪（可选，如果需要等待某些初始化完成）
    yield


app = fastapi.FastAPI(lifespan=lifespan)


# 列出所有节点
@app.get("/nodes/list_nodes")
async def get_nodes():
    nodes = controller.get_all_nodes()
    return [node.model_dump() for node in nodes]


# -- 节点性能指标相关接口 ---
@app.get("/nodes/{node_id}/metrics")
async def get_node_metrics(node_id: str, n: int = 20):
    col = controller.db["metrics"]
    metrics = get_metrics_last_n(col, node_id, n)
    return [metric.model_dump() for metric in metrics]


# 列出所有实例任务
@app.get("/tasks/list_instance_tasks")
async def list_instance_tasks():
    col = controller.db["instance_tasks"]
    tasks = col.find().sort("created_at", -1)
    return [InstanceTask.model_validate(task).model_dump() for task in tasks]


# 创建实例任务
@app.post("/tasks/create_instance")
async def create_instance(task: InstanceTask):
    task.status = "INIT"
    col = controller.db["instance_tasks"]
    col.insert_one(task.model_dump())
    return {"message": f"Instance task for {task.instance_name}@{task.node_id} created"}


# 删除实例任务
@app.post("/tasks/delete_instance_task/{task_id}")
async def delete_instance_task(task_id: str):
    col = controller.db["instance_tasks"]
    result = col.delete_one({"task_id": task_id})
    if result.deleted_count == 1:
        return {"message": f"Task {task_id} deleted"}
    else:
        return fastapi.HTTPException(status_code=404, detail="Task not found")


# 实例列表
@app.get("/instances/list_instances")
async def list_instances():
    col = controller.db["instances"]
    instances = col.find().sort("created_at", -1)
    return [Instance.model_validate(instance).model_dump() for instance in instances]


# 删除实例
@app.post("/instances/delete_instance/{node_id}/{instance_name}")
async def delete_instance(node_id: str, instance_name: str):
    col = controller.db["instances"]
    result = col.delete_one({"node_id": node_id, "instance_name": instance_name})
    if result.deleted_count == 1:
        return {"message": f"Instance {instance_name}@{node_id} deleted"}
    else:
        return fastapi.HTTPException(status_code=404, detail="Instance not found")


# 停止实例
@app.post("/tasks/stop_instance/{node_id}/{instance_name}")
async def stop_instance(node_id: str, instance_name: str):
    col = controller.db["instance_tasks"]
    mit = InstanceTask(type="STOP", instance_name=instance_name, node_id=node_id, status="INIT")
    col.insert_one(mit.model_dump())
    return {"message": f"Instance {instance_name}@{node_id} stop task created"}


# 恢复实例
@app.post("/tasks/resume_instance/{node_id}/{instance_name}")
async def resume_instance(node_id: str, instance_name: str):
    col = controller.db["instance_tasks"]
    mit = InstanceTask(type="RESUME", instance_name=instance_name, node_id=node_id, status="INIT")
    col.insert_one(mit.model_dump())
    return {"message": f"Instance {instance_name}@{node_id} resume task created"}


# 获取实例日志
@app.get("/instances/logs/{node_id}/{instance_name}")
async def get_instance_logs(node_id: str, instance_name: str):
    col = controller.db["logs"]
    log_doc = col.find_one({"node_id": node_id, "instance_name": instance_name})
    if not log_doc:
        return {"log": "No logs found for this instance"}
    log = Log.model_validate(log_doc)
    return log.model_dump()


# --- NFS 文件浏览相关接口 ---
def list_directory(dir_path: str):
    res = []
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        nfs_path = os.path.relpath(item_path, controller.nfs_path)
        if os.path.isdir(item_path):
            res.append({"name": item, "type": "directory", "nfs_path": nfs_path})
        else:
            res.append({"name": item, "type": "file", "nfs_path": nfs_path})
    return res


# 列出NFS根目录下的文件和子目录
@app.get("/nfs/list_root")
async def list_nfs_root():
    return list_directory(controller.nfs_path)


# 列出指定目录下的文件和子目录
@app.get("/nfs/list_dir/{dir_path}")
async def list_nfs_dir(dir_path: str):
    target_dir = os.path.join(controller.nfs_path, dir_path)
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return {"error": "Directory not found"}

    return list_directory(target_dir)


# 列出所有模型
@app.get("/nfs/list_models")
async def list_nfs_models():
    """
    模型都放在根目录的直接子目录里，目录名就是模型名，每个模型目录里都有一个xxx.gguf(不一定与目录名一致)，视觉模型额外有一个mmproj*.gguf，需要都返回
    """
    root_items = list_directory(controller.nfs_path)
    models = []
    for item in root_items:
        if item["type"] == "directory":
            model_dir = os.path.join(controller.nfs_path, item["name"])
            model_name = item["name"]
            model_files = list_directory(model_dir)
            model_info = {"model_name": model_name, "model_file": None, "mmproj_file": None}
            for f in model_files:
                if f["type"] == "file" and f["name"].endswith(".gguf"):
                    if f["name"].startswith("mmproj"):
                        model_info["mmproj_file"] = f["nfs_path"]
                    else:
                        model_info["model_file"] = f["nfs_path"]
            models.append(model_info)
    return models


def hash_passwd(password: str) -> bytes:
    passwdb = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(passwdb, salt)
    return hashed


def verify_passwd(password: str, hashed: bytes) -> bool:
    passwdb = password.encode("utf-8")
    return bcrypt.checkpw(passwdb, hashed)


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/user/register")
async def register_user(request: LoginRequest):
    username = request.username
    password = request.password
    col = controller.db["users"]
    if col.find_one({"username": username}):
        raise HTTPException(status_code=409, detail="Username already exists")
    password_hash = hash_passwd(password)  # 注意：实际应用中应使用更安全的哈希算法，如 bcrypt
    user = User(username=username, password_hash=password_hash)
    col.insert_one(user.model_dump())
    return {"message": f"User {username} registered successfully"}


@app.post("/user/login")
async def login_user(request: LoginRequest):
    username = request.username
    password = request.password
    hash_passwd(password)
    col = controller.db["users"]
    user_doc = col.find_one({"username": username})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    user = User.model_validate(user_doc)
    if not verify_passwd(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    # 更新最后登录时间
    col.update_one({"username": username}, {"$set": {"last_login_at": time.time()}})
    # 生成JWT token

    payload = {"username": username, "exp": time.time() + 3600}  # token有效期1小时
    token = jwt.encode(payload, "kb310", algorithm="HS256")
    return {"token": token}


@app.get("/user/profile")
async def get_user_profile(request: Request):
    # 从请求头中获取JWT token
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token is missing")
    token = token.replace("Bearer ", "")  # 移除 "Bearer "前缀
    try:
        payload = jwt.decode(token, "kb310", algorithms=["HS256"])
        username = payload.get("username")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token: username missing")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    col = controller.db["users"]
    user_doc = col.find_one({"username": username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    user = User.model_validate(user_doc)
    return user.model_dump()


"""
--- 实例组相关接口 ---
"""


class CreateInstanceGroupRequest(BaseModel):
    group_name: str
    instance_names: List[str]
    instance_node_ids: List[str]


async def get_current_user(request: Request) -> User:
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token is missing")
    token = token.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, "kb310", algorithms=["HS256"])
        username = payload.get("username")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token: username missing")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    col = controller.db["users"]
    user_doc = col.find_one({"username": username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    user = User.model_validate(user_doc)
    return user


# 创建一个实例组
@app.post("/instance_groups/create")
async def create_instance_group(cigr: CreateInstanceGroupRequest, username=Depends(get_current_user)):
    # 1. 验证实例ID是否存在
    col_instances = controller.db["instances"]
    instances = []
    for i in range(len(cigr.instance_names)):
        instance_name = cigr.instance_names[i]
        node_id = cigr.instance_node_ids[i]
        instance_doc = col_instances.find_one({"instance_name": instance_name, "node_id": node_id})
        if not instance_doc:
            raise HTTPException(status_code=404, detail=f"Instance {instance_name}@{node_id} not found")
        instance = Instance.model_validate(instance_doc)
        instances.append(instance)

    # 2. 创建实例组
    group = InstanceGroup(owner_username=username, group_name=cigr.group_name, instances=instances)

    col_groups = controller.db["instance_groups"]
    col_groups.insert_one(group.model_dump())

    return {"message": f"Instance group {cigr.group_name} created successfully"}


# 获取用户的实例组列表
@app.get("/instance_groups/list")
async def list_instance_groups(username=Depends(get_current_user)):
    col_groups = controller.db["instance_groups"]
    groups_cursor = col_groups.find({"owner_username": username}).sort("created_at", -1)
    groups = [InstanceGroup.model_validate(group_doc).model_dump() for group_doc in groups_cursor]
    return groups


# 获取实例组详情
@app.get("/instance_groups/detail/{group_name}")
async def get_instance_group_detail(group_name: str, username=Depends(get_current_user)):
    col_groups = controller.db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)
    return group.model_dump()


class InstanceStatus(BaseModel):
    instance_name: str
    node_id: str
    status: str  # RUNNING | STOPPED | ERROR | NOT_FOUND | UNKNOWN


# 查询实例组中的实例状态
@app.get("/instance_groups/{group_name}/instances_status")
async def get_instance_group_instances_status(group_name: str, username=Depends(get_current_user)):
    col_groups = controller.db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)

    col_instances = controller.db["instances"]
    instances_status = []
    for instance in group.instances:
        instance_doc = col_instances.find_one({"instance_name": instance.instance_name, "node_id": instance.node_id})
        if instance_doc:
            status = instance_doc.get("status", "UNKNOWN")
            instances_status.append(
                InstanceStatus(
                    instance_name=instance.instance_name, node_id=instance.node_id, status=status
                ).model_dump()
            )
        else:
            instances_status.append(
                InstanceStatus(
                    instance_name=instance.instance_name, node_id=instance.node_id, status="NOT_FOUND"
                ).model_dump()
            )

    return instances_status


# 删除实例组
@app.post("/instance_groups/delete/{group_name}")
async def delete_instance_group(group_name: str, username=Depends(get_current_user)):
    col_groups = controller.db["instance_groups"]
    result = col_groups.delete_one({"owner_username": username, "group_name": group_name})
    if result.deleted_count == 1:
        return {"message": f"Instance group {group_name} deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Instance group not found")


# 实例组内批量停止实例
@app.post("/instance_groups/stop_instances/{group_name}")
async def stop_instance_group_instances(group_name: str, username=Depends(get_current_user)):
    col_groups = controller.db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)

    col_instance_tasks = controller.db["instance_tasks"]
    for instance in group.instances:
        mit = InstanceTask(
            type="STOP",
            instance_name=instance.instance_name,
            node_id=instance.node_id,
            status="INIT",
            owner_username=username,
        )
        col_instance_tasks.insert_one(mit.model_dump())

    return {"message": f"Stop tasks for all instances in group {group_name} created successfully"}


# 实例组内批量恢复实例
@app.post("/instance_groups/resume_instances/{group_name}")
async def resume_instance_group_instances(group_name: str, username=Depends(get_current_user)):
    col_groups = controller.db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)

    col_instance_tasks = controller.db["instance_tasks"]
    for instance in group.instances:
        mit = InstanceTask(
            type="RESUME",
            instance_name=instance.instance_name,
            node_id=instance.node_id,
            status="INIT",
            owner_username=username,
        )
        col_instance_tasks.insert_one(mit.model_dump())

    return {"message": f"Resume tasks for all instances in group {group_name} created successfully"}


# 实例组内批量部署实例
@app.post("/instance_groups/deploy_instances/{group_name}")
async def deploy_instance_group_instances(group_name: str, username=Depends(get_current_user)):
    col_groups = controller.db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)

    col_instance_tasks = controller.db["instance_tasks"]
    for instance in group.instances:
        mit = InstanceTask(
            owner_username=username,
            type="DEPLOY",
            instance_name=instance.instance_name,
            node_id=instance.node_id,
            port=instance.port,
            model_path=instance.model_path,
            mmproj_path=instance.mmproj_path,
            status="INIT",
        )
        col_instance_tasks.insert_one(mit.model_dump())

    return {"message": f"Deploy tasks for all instances in group {group_name} created successfully"}


# 实例组内批量删除实例
@app.post("/instance_groups/delete_instances/{group_name}")
async def delete_instance_group_instances(group_name: str, username=Depends(get_current_user)):
    col_groups = controller.db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)

    col_instances = controller.db["instances"]
    for instance in group.instances:
        col_instances.delete_one({"instance_name": instance.instance_name, "node_id": instance.node_id})

    return {"message": f"All instances in group {group_name} deleted successfully"}
