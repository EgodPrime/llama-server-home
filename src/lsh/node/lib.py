import time
from typing import Any, List

import pymongo
import yaml

from lsh.utils.path_helper import NODE_CONFIG_PATH
from lsh.utils.schema import CPUInfo, GPUInfo, MemoryInfo, Metric, Node


def measure_cpu() -> CPUInfo:
    pass


def measure_memory() -> MemoryInfo:
    pass


def measure_gpu() -> List[GPUInfo]:
    pass


class NodeAgent:
    def __init__(self):
        cfg: dict[str, Any] = yaml.safe_load(open(NODE_CONFIG_PATH, "r"))
        self.mongo_client = pymongo.MongoClient(cfg["mongodb_url"])
        self.db = self.mongo_client[cfg["mongodb_name"]]
        self.heartbeat_interval = int(cfg.get("heartbeat_interval", 5))
        self.node = Node(
            name=cfg["name"],
            ip_address=cfg["ip_address"],
            llama_path=cfg["llama_path"],
            status="ONLINE",
            last_heartbeat=time.time(),
            registered_at=time.time(),
        )

    def register_self(self):
        col = self.db["nodes"]
        existing_node = col.find_one({"node_id": self.node.node_id})
        if existing_node:
            col.update_one({"node_id": self.node.node_id}, {"$set": self.node.model_dump()})
        else:
            col.insert_one(self.node.model_dump())

    def heartbeat(self):
        col = self.db["nodes"]
        col.update_one({"node_id": self.node.node_id}, {"$set": {"last_heartbeat": time.time(), "status": "ONLINE"}})

    def updaate_metric(self):
        metric = Metric(
            node_id=self.node.node_id,
            timestamp=time.time(),
            cpu=measure_cpu(),
            memory=measure_memory(),
            gpus=measure_gpu(),
        )
        col = self.db["metrics"]
        col.insert_one(metric.model_dump())

    def run(self):
        self.register_self()
        while True:
            t0 = time.time()
            self.heartbeat()
            self.updaate_metric()
            elapsed = time.time() - t0
            time.sleep(max(0, self.heartbeat_interval - elapsed))
