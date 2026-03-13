from typing import List

import pymongo

from lsh.utils.schema import Node


def find_nodes_all(col: pymongo.collection.Collection) -> List[Node]:
    nodes = list(col.find())
    res = []
    for node in nodes:
        res.append(Node.model_validate(node))
    return res


def insert_node(col: pymongo.collection.Collection, node: Node) -> str:
    res = col.insert_one(node.model_dump())
    return str(res.inserted_id)
