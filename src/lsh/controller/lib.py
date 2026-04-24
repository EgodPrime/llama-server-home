import os
import time

import pymongo
import yaml
from loguru import logger

from lsh.repo.node import find_nodes_all
from lsh.utils.path_helper import CONTROLLER_CONFIG_PATH
from lsh.utils.schema import Node


class Controller:
    def __init__(self):
        cfg = yaml.safe_load(open(CONTROLLER_CONFIG_PATH, "r"))
        self.mongo_client = pymongo.MongoClient(
            cfg["mongodb_url"],
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=10000,
            connectTimeoutMS=5000,
        )
        self.db = self.mongo_client[cfg["mongodb_name"]]
        self.node_dead_threshold = int(cfg.get("node_dead_threshold", 60))
        self.nfs_path = cfg.get("nfs_path")
        # JWT secret: env var > config file > raise error
        self.jwt_secret = os.environ.get("JWT_SECRET", cfg.get("jwt_secret"))
        if not self.jwt_secret:
            raise RuntimeError("JWT_SECRET environment variable or jwt_secret config is required")

    # --- 核心功能：节点自动发现与巡检 ---
    def node_discovery_and_check(self):
        col = self.db["nodes"]
        nodes = col.find({"status": "ONLINE"})
        for node_doc in nodes:
            node = Node.model_validate(node_doc)
            logger.trace(f"Discovering node: {node}")
            now = time.time()
            if (now - node.last_heartbeat) > self.node_dead_threshold:
                logger.info(f"Node {node.node_id} is considered dead. Last heartbeat was at {node.last_heartbeat}")
                col.update_one({"node_id": node.node_id}, {"$set": {"status": "OFFLINE"}})

    def node_discovery_and_check_loop(self):
        while True:
            t0 = time.time()
            try:
                self.node_discovery_and_check()
            except Exception as e:
                logger.error(f"Error in node discovery and check: {e}")
            t1 = time.time()
            elapsed = t1 - t0
            sleep_time = max(5, self.node_dead_threshold - elapsed)
            time.sleep(sleep_time)

    def get_all_nodes(self) -> list[Node]:
        col = self.db["nodes"]
        nodes = find_nodes_all(col)
        return nodes


# Module-level singleton for Controller instances
_controller_instance = None


def get_controller() -> "Controller":
    """Get or create the singleton Controller instance.

    Ensures all router modules share a single MongoDB connection pool
    and JWT secret configuration.
    """
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = Controller()
    return _controller_instance
