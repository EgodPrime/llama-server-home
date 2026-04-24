from fastapi import APIRouter

from lsh.controller.lib import get_controller
from lsh.repo.metrics import get_metrics_last_n

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("/list_nodes")
async def get_nodes():
    nodes = get_controller().get_all_nodes()
    return [node.model_dump() for node in nodes]


@router.get("/{node_id}/metrics")
async def get_node_metrics(node_id: str, n: int = 20):
    col = get_controller().db["metrics"]
    metrics = get_metrics_last_n(col, node_id, n)
    return [metric.model_dump() for metric in metrics]
