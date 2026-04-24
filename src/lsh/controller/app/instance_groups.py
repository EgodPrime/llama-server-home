from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lsh.controller.lib import get_controller
from lsh.utils.schema import Instance, InstanceGroup, InstanceTask

from .utils import get_current_user_name

router = APIRouter(prefix="/instance_groups", tags=["instance_groups"])


class CreateInstanceGroupRequest(BaseModel):
    group_name: str
    instance_names: List[str]
    instance_node_ids: List[str]


class InstanceStatus(BaseModel):
    instance_name: str
    node_id: str
    status: str  # RUNNING | STOPPED | ERROR | NOT_FOUND | UNKNOWN


@router.post("/create")
async def create_instance_group(cigr: CreateInstanceGroupRequest, username=Depends(get_current_user_name)):
    col_instances = get_controller().db["instances"]
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
    col_groups = get_controller().db["instance_groups"]
    col_groups.insert_one(group.model_dump())
    return {"message": f"Instance group {cigr.group_name} created successfully"}


@router.get("/list")
async def list_instance_groups(username=Depends(get_current_user_name)):
    col_groups = get_controller().db["instance_groups"]
    groups_cursor = col_groups.find({"owner_username": username}).sort("created_at", -1)
    groups = [InstanceGroup.model_validate(group_doc).model_dump() for group_doc in groups_cursor]
    return groups


@router.get("/detail/{group_name}")
async def get_instance_group_detail(group_name: str, username=Depends(get_current_user_name)):
    col_groups = get_controller().db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)
    return group.model_dump()


# 查询实例组中的实例状态
@router.get("/{group_name}/instances_status")
async def get_instance_group_instances_status(group_name: str, username=Depends(get_current_user_name)):
    col_groups = get_controller().db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)

    col_instances = get_controller().db["instances"]
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
@router.post("/delete/{group_name}")
async def delete_instance_group(group_name: str, username=Depends(get_current_user_name)):
    col_groups = get_controller().db["instance_groups"]
    result = col_groups.delete_one({"owner_username": username, "group_name": group_name})
    if result.deleted_count == 1:
        return {"message": f"Instance group {group_name} deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Instance group not found")


# 实例组内批量停止实例
@router.post("/stop_instances/{group_name}")
async def stop_instance_group_instances(group_name: str, username=Depends(get_current_user_name)):
    col_groups = get_controller().db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)

    col_instance_tasks = get_controller().db["instance_tasks"]
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
@router.post("/resume_instances/{group_name}")
async def resume_instance_group_instances(group_name: str, username=Depends(get_current_user_name)):
    col_groups = get_controller().db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)

    col_instance_tasks = get_controller().db["instance_tasks"]
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
@router.post("/deploy_instances/{group_name}")
async def deploy_instance_group_instances(group_name: str, username=Depends(get_current_user_name)):
    col_groups = get_controller().db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)

    col_instance_tasks = get_controller().db["instance_tasks"]
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
@router.post("/delete_instances/{group_name}")
async def delete_instance_group_instances(group_name: str, username=Depends(get_current_user_name)):
    col_groups = get_controller().db["instance_groups"]
    group_doc = col_groups.find_one({"owner_username": username, "group_name": group_name})
    if not group_doc:
        raise HTTPException(status_code=404, detail="Instance group not found")
    group = InstanceGroup.model_validate(group_doc)

    col_instances = get_controller().db["instances"]
    for instance in group.instances:
        col_instances.delete_one({"instance_name": instance.instance_name, "node_id": instance.node_id})

    return {"message": f"All instances in group {group_name} deleted successfully"}
