import fastapi

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
    controller.create_instance_task(task)
    return {"message": "Instance creation task created", "task_id": task.task_id}


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

    uvicorn.run(app, host="0.0.0.0", port=8000, debug=True)