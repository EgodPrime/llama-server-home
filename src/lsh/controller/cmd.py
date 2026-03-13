from lsh.controller.lib import Controller


def list_nodes():
    controller = Controller()
    nodes = controller.get_all_nodes()
    if not nodes:
        print("No nodes found.")
        return
    for node in nodes:
        print(node)
