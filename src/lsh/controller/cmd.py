from lsh.controller.lib import Controller

def list_nodes():
    controller = Controller()
    nodes = controller.get_all_nodes()
    for node in nodes:
        print(node)
    else:
        print("No nodes found.")