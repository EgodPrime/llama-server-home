import time
from lsh.utils.schema import Node
from lsh.repo.node import find_nodes_all
from lsh.utils.path_helper import CONTROLLER_CONFIG_PATH
import yaml
import pymongo
from loguru import logger



class Controller:
    def __init__(self):
        cfg = yaml.safe_load(open(CONTROLLER_CONFIG_PATH, 'r'))
        self.mongo_client = pymongo.MongoClient(cfg['mongodb_url'])
        self.db = self.mongo_client[cfg['mongodb_name']]
        self.node_dead_threshold = int(cfg.get('node_dead_threshold', 60))



    # --- 核心功能：节点自动发现与巡检 ---
    async def node_discovery_and_check(self):
        col = self.db['nodes']
        nodes = find_nodes_all(col)
        for node in nodes:
            logger.trace(f"Discovering node: {node}")
            now = time.time()
            if (now-node.last_heartbeat) > self.node_dead_threshold:
                logger.info(f"Node {node.node_id} is considered dead. Last heartbeat was at {node.last_heartbeat}")
                col.update_one({"node_id": node.node_id}, {"$set": {"status": "OFFLINE"}})
    

    def get_all_nodes(self) -> list[Node]:
        col = self.db['nodes']
        nodes = find_nodes_all(col)
        return nodes