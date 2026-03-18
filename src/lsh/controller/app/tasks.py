from fastapi import APIRouter

from lsh.controller.lib import Controller
from lsh.utils.schema import InstanceTask

router = APIRouter(prefix="/tasks", tags=["tasks"])
controller = Controller()


@router.get("/list_instance_tasks")
async def list_instance_tasks():
    col = controller.db["instance_tasks"]
    tasks = col.find().sort("created_at", -1)
    return [InstanceTask.model_validate(task).model_dump() for task in tasks]


@router.post("/create_instance")
async def create_instance(task: InstanceTask):
    task.status = "INIT"
    col = controller.db["instance_tasks"]
    col.insert_one(task.model_dump())
    return {"message": f"Instance task for {task.instance_name}@{task.node_id} created"}


@router.post("/delete_instance_task/{task_id}")
async def delete_instance_task(task_id: str):
    col = controller.db["instance_tasks"]
    result = col.delete_one({"task_id": task_id})
    if result.deleted_count == 1:
        return {"message": f"Task {task_id} deleted"}
    else:
        return {"error": "Task not found"}
