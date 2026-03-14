import os

import fastapi

from lsh.controller.lib import Controller
from lsh.repo.metrics import get_metrics_last_n
from lsh.utils.schema import Instance, InstanceTask

app = fastapi.FastAPI()
controller = Controller()


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
