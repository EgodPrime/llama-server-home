from lsh.controller.lib import Controller
from lsh.repo.metrics import get_metrics_last_one


def list_nodes():
    controller = Controller()
    nodes = controller.get_all_nodes()
    if not nodes:
        print("No nodes found.")
        return
    for node in nodes:
        print(node)
        metric = get_metrics_last_one(controller.db["metrics"], node.node_id)
        if metric:
            print(metric)
