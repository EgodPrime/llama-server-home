from fastapi import APIRouter, Depends

from lsh.controller.lib import get_controller
from lsh.utils.schema import Instance, Log

from .utils import get_current_user_name

router = APIRouter(prefix="/instances", tags=["instances"])


@router.get("/list_instances")
async def list_instances(username=Depends(get_current_user_name)):
    col = get_controller().db["instances"]
    instances = col.find().sort("created_at", -1)
    return [Instance.model_validate(instance).model_dump() for instance in instances]


@router.post("/delete_instance/{node_id}/{instance_name}")
async def delete_instance(node_id: str, instance_name: str):
    col = get_controller().db["instances"]
    result = col.delete_one({"node_id": node_id, "instance_name": instance_name})
    if result.deleted_count == 1:
        return {"message": f"Instance {instance_name}@{node_id} deleted"}
    else:
        return {"error": "Instance not found"}


@router.get("/logs/{node_id}/{instance_name}")
async def get_instance_logs(node_id: str, instance_name: str):
    col = get_controller().db["logs"]
    log_doc = col.find_one({"node_id": node_id, "instance_name": instance_name})
    if not log_doc:
        return {"log": "No logs found for this instance"}
    log = Log.model_validate(log_doc)
    return log.model_dump()
