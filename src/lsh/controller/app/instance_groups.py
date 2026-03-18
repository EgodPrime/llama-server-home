from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lsh.controller.lib import Controller
from lsh.utils.schema import Instance, InstanceGroup

from .utils import get_current_user_name

router = APIRouter(prefix="/instance_groups", tags=["instance_groups"])
controller = Controller()


class CreateInstanceGroupRequest(BaseModel):
    group_name: str
    instance_names: List[str]
    instance_node_ids: List[str]


@router.post("/create")
async def create_instance_group(cigr: CreateInstanceGroupRequest, username=Depends(get_current_user_name)):
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
    group = InstanceGroup(owner_username=username, group_name=cigr.group_name, instances=instances)
    col_groups = controller.db["instance_groups"]
    col_groups.insert_one(group.model_dump())
    return {"message": f"Instance group {cigr.group_name} created successfully"}


@router.get("/list")
async def list_instance_groups(username=Depends(get_current_user_name)):
    col_groups = controller.db["instance_groups"]
    groups_cursor = col_groups.find({"owner_username": username}).sort("created_at", -1)
    groups = [InstanceGroup.model_validate(group_doc).model_dump() for group_doc in groups_cursor]
    return groups


@router.get("/detail/{group_name}")
async def get_instance_group_detail(group_name: str, username=Depends(get_current_user_name)):
    col_groups = controller.db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)
    return group.model_dump()
