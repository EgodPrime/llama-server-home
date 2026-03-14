import fastapi
import os
from lsh.controller.lib import Controller, CreateInstanceTask
from lsh.repo.metrics import get_metrics_last_n

app = fastapi.FastAPI()
controller = Controller()


@app.get("/nodes/list_nodes")
async def get_nodes():
    nodes = controller.get_all_nodes()
    return [node.model_dump() for node in nodes]


@app.get("/nodes/{node_id}/metrics")
async def get_node_metrics(node_id: str, n: int = 20):
    col = controller.db["metrics"]
    metrics = get_metrics_last_n(col, node_id, n)
    return [metric.model_dump() for metric in metrics]


@app.post("/tasks/create_instance_task")
async def create_instance(task: CreateInstanceTask):
    task.status = "INIT"
    controller.create_instance_task(task)
    return {"message": "Instance creation task created", "task_id": task.task_id}

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

@app.get("/nfs/list_root")
async def list_nfs_root():
    return list_directory(controller.nfs_path)

@app.get("/nfs/list_dir/{dir_path}")
async def list_nfs_dir(dir_path: str):
    target_dir = os.path.join(controller.nfs_path, dir_path)
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return {"error": "Directory not found"}
    
    return list_directory(target_dir)

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



@app.post("/tasks/cancel_create_instance_task")
async def cancel_instance(task: CreateInstanceTask):
    task.type = "CANCEL"
    controller.create_instance_task(task)
    return {"message": "Instance cancellation task created", "task_id": task.task_id}


@app.get("/tasks/list_create_instance_tasks")
async def list_create_instance_tasks():
    col = controller.db["instance_tasks"]
    tasks = col.find().sort("created_at", -1)
    return [CreateInstanceTask.model_validate(task).model_dump() for task in tasks]


@app.get("/instances/list_instances")
async def list_instances():
    col = controller.db["instances"]
    instances = col.find().sort("created_at", -1)
    return [instance for instance in instances]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)