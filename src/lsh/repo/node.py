from typing import List, Optional
import pymongo

from lsh.utils.schema import Node


def find_nodes_all(col: pymongo.collection.Collection) -> List[Node]:
    nodes = list(col.find())
    res = []
    for node in nodes:
        res.append(Node.model_validate(node))
    return res