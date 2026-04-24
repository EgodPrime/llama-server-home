from fastapi import APIRouter, HTTPException

from lsh.controller.lib import get_controller
from lsh.utils.schema import InstanceTask

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/list_instance_tasks")
async def list_instance_tasks():
    col = get_controller().db["instance_tasks"]
    tasks = col.find().sort("created_at", -1)
    return [InstanceTask.model_validate(task).model_dump() for task in tasks]


@router.post("/create_instance")
async def create_instance(task: InstanceTask):
    task.status = "INIT"
    col = get_controller().db["instance_tasks"]
    col.insert_one(task.model_dump())
    return {"message": f"Instance task for {task.instance_name}@{task.node_id} created"}


@router.delete("/delete_instance_task/{task_id}")
async def delete_instance_task(task_id: str):
    col = get_controller().db["instance_tasks"]
    result = col.delete_one({"task_id": task_id})
    if result.deleted_count == 1:
        return {"message": f"Task {task_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/stop_instance/{node_id}/{instance_name}")
async def stop_instance(node_id: str, instance_name: str):
    col = get_controller().db["instance_tasks"]
    mit = InstanceTask(type="STOP", instance_name=instance_name, node_id=node_id, status="INIT")
    col.insert_one(mit.model_dump())
    return {"message": f"Instance {instance_name}@{node_id} stop task created"}


# 恢复实例
@router.post("/resume_instance/{node_id}/{instance_name}")
async def resume_instance(node_id: str, instance_name: str):
    col = get_controller().db["instance_tasks"]
    mit = InstanceTask(type="RESUME", instance_name=instance_name, node_id=node_id, status="INIT")
    col.insert_one(mit.model_dump())
    return {"message": f"Instance {instance_name}@{node_id} resume task created"}
