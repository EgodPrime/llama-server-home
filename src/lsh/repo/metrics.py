from typing import Optional

import pymongo

from lsh.utils.schema import Metrics


def get_metrics_last_one(col: pymongo.collection.Collection, node_id: str) -> Optional[Metrics]:
    doc = col.find_one({"node_id": node_id}, sort=[("timestamp", pymongo.DESCENDING)])
    if doc:
        return Metrics(**doc)
    return None


def get_metrics_last_n(col: pymongo.collection.Collection, node_id: str, n: int) -> Optional[list[Metrics]]:
    cursor = col.find({"node_id": node_id}).sort("timestamp", pymongo.DESCENDING).limit(n)
    return [Metrics(**doc) for doc in cursor]
