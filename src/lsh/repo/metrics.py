from typing import Optional

import pymongo

from lsh.utils.schema import Metric


def get_metrics_last_one(col: pymongo.collection.Collection, node_id: str) -> Optional[Metric]:
    doc = col.find_one({"node_id": node_id}, sort=[("timestamp", pymongo.DESCENDING)])
    if doc:
        return Metric.model_validate(doc)
    return None


def get_metrics_last_n(col: pymongo.collection.Collection, node_id: str, n: int) -> list[Metric]:
    cursor = col.find({"node_id": node_id}).sort("timestamp", pymongo.DESCENDING).limit(n)
    return [Metric.model_validate(doc) for doc in cursor]
