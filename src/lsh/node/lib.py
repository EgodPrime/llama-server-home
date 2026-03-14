import pathlib
import subprocess
import threading
import time
from typing import Any

import psutil
import pymongo
import yaml
from loguru import logger

from lsh.node.metrics import measure_cpu, measure_gpu, measure_memory
from lsh.utils.path_helper import NODE_CONFIG_PATH
from lsh.utils.schema import Instance, InstanceTask, Metric, Node


class NodeAgent:
    def __init__(self):
        cfg: dict[str, Any] = yaml.safe_load(open(NODE_CONFIG_PATH, "r"))
        self.mongo_client = pymongo.MongoClient(cfg["mongodb_url"])
        self.db = self.mongo_client[cfg["mongodb_name"]]
        self.heartbeat_interval = int(cfg.get("heartbeat_interval", 5))
        self.nfs_path = pathlib.Path(cfg.get("nfs_path")).resolve()
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
            logger.info(f"Node {self.node.node_id} already exists. Updated info")
        else:
            col.insert_one(self.node.model_dump())
            logger.info(f"Registered new node: {self.node.node_id}")

    def heartbeat(self):
        col = self.db["nodes"]
        col.update_one({"node_id": self.node.node_id}, {"$set": {"last_heartbeat": time.time(), "status": "ONLINE"}})
        logger.trace(f"Node {self.node.node_id} sent heartbeat.")

    def updaate_metric(self):
        metric = Metric(
            node_id=self.node.node_id,
            timestamp=time.time(),
            cpu=measure_cpu(),
            memory=measure_memory(),
            gpus=measure_gpu(),
        )
        col = self.db["metrics"]
        # 如果当前记录数超过20条，则删除最旧的一条
        if col.count_documents({"node_id": self.node.node_id}) >= 20:
            oldest_one = col.find_one({"node_id": self.node.node_id}, sort=[("timestamp", pymongo.ASCENDING)])
            col.delete_one({"_id": oldest_one["_id"]})
        col.insert_one(metric.model_dump())
        logger.trace(f"Node {self.node.node_id} updated metrics")

    def self_maintenance(self):
        while True:
            t0 = time.time()
            self.heartbeat()
            self.updaate_metric()
            elapsed = time.time() - t0
            time.sleep(max(0, self.heartbeat_interval - elapsed))

    def instance_maintenance(self):
        """
        检查数据库中所有node_id为自己的实例，验证它们的状态是否正常（对应的进程还在吗？端口还在监听吗？），如果发现异常则更新状态为FAILED，并记录错误信息
        """
        col = self.db["instances"]
        while True:
            t0 = time.time()
            instances = col.find({"node_id": self.node.node_id})
            for inst_doc in instances:
                instance = Instance.model_validate(inst_doc)
                err_msg = None
                works_fine = False
                try:
                    proc = psutil.Process(instance.pid)
                    if proc.is_running():
                        # 还可以进一步检查端口是否在监听
                        if not proc.net_connections():
                            raise RuntimeError("Process is running but not listening on any port")
                        works_fine = True
                except Exception as e:
                    err_msg = str(e)
                cfg = {"last_heartbeat": time.time()}
                match instance.status:
                    case "RUNNING":
                        if not works_fine:
                            cfg["status"] = "ERROR"
                            cfg["last_error"] = err_msg
                    case "ERROR", "STOPPED":
                        if works_fine:
                            cfg["status"] = "RUNNING"
                            cfg["last_error"] = None
                col.update_one({"_id": inst_doc["_id"]}, {"$set": cfg})

            elapsed = time.time() - t0
            time.sleep(max(0, self.heartbeat_interval - elapsed))

    def deploy_instance(self, task: InstanceTask):
        log_file = f"/tmp/{task.instance_name}.log"
        cmd_list = [
            str(self.node.llama_path),
            "--model",
            str(self.nfs_path / task.model_path),
            "--host",
            self.node.ip_address,
            "--port",
            str(task.port),
        ]
        if task.mmproj_path:
            cmd_list += ["--mmproj", str(self.nfs_path / task.mmproj_path)]
        for k, v in task.config.items():
            cmd_list += [k, str(v)]
        process = subprocess.Popen(
            cmd_list, env=task.env, stdout=open(log_file, "w"), stderr=subprocess.STDOUT, start_new_session=True
        )
        col = self.db["instances"]
        created_time = time.time()
        instance = Instance(
            instance_name=task.instance_name,
            node_id=task.node_id,
            status="RUNNING",
            pid=process.pid,
            host=self.node.ip_address,
            port=task.port,
            model_path=str(task.model_path),
            local_model_path=str(self.nfs_path / task.model_path),
            mmproj_path=str(task.mmproj_path) if task.mmproj_path else None,
            local_mmproj_path=str(self.nfs_path / task.mmproj_path) if task.mmproj_path else None,
            env=task.env,
            config=task.config,
            last_heartbeat=created_time,
            last_error=None,
            created_at=created_time,
            started_at=created_time,
        )
        col.insert_one(instance.model_dump())
        logger.info(f"Node {self.node.node_id} deployed instance for task: {task.task_id}")

    def stop_instance(self, instance: Instance):
        try:
            psutil.Process(instance.pid).kill()
        except Exception:
            pass
        col = self.db["instances"]
        col.update_one(
            {"node_id": instance.node_id, "instance_name": instance.instance_name},
            {
                "$set": {
                    "status": "STOPPED",
                    "last_error": None,
                    "last_stopped_at": time.time(),
                }
            },
        )

    def resume_instance(self, instance: Instance):
        log_file = f"/tmp/{instance.instance_name}.log"
        cmd_list = [
            str(self.node.llama_path),
            "--model",
            str(self.nfs_path / instance.model_path),
            "--host",
            self.node.ip_address,
            "--port",
            str(instance.port),
        ]
        if instance.mmproj_path:
            cmd_list += ["--mmproj", str(self.nfs_path / instance.mmproj_path)]
        for k, v in instance.config.items():
            cmd_list += [k, str(v)]
        process = subprocess.Popen(
            cmd_list, env=instance.env, stdout=open(log_file, "w"), stderr=subprocess.STDOUT, start_new_session=True
        )
        new_pid = process.pid
        col = self.db["instances"]
        col.update_one(
            {"node_id": instance.node_id, "instance_name": instance.instance_name},
            {
                "$set": {
                    "status": "RUNNING",
                    "pid": new_pid,
                    "last_error": None,
                    "started_at": time.time(),
                }
            },
        )

    def handle_instance_task(self):
        col = self.db["instance_tasks"]
        while True:
            task_doc = col.find_one(
                {"node_id": self.node.node_id, "status": "INIT"},
                sort=[("created_at", pymongo.ASCENDING)],
            )
            if task_doc:
                task = InstanceTask.model_validate(task_doc)
                err_msg = None
                result = None
                try:
                    logger.info(f"Node {self.node.node_id} handling manage instance task: {task.task_id}")
                    col.update_one(
                        {"task_id": task.task_id}, {"$set": {"status": "PROCESSING", "started_at": time.time()}}
                    )
                    instance_doc = self.db["instances"].find_one(
                        {"node_id": task.node_id, "instance_name": task.instance_name}
                    )
                    if not instance_doc:
                        raise RuntimeError(f"Instance {task.instance_name} not found on node {task.node_id}")
                    instance = Instance.model_validate(instance_doc)
                    # 根据任务类型执行相应操作
                    match task.type:
                        case "DEPLOY":
                            self.deploy_instance(task)
                        case "STOP":
                            self.stop_instance(instance)
                        case "RESUME":
                            # 恢复实例：重新启动一个新的进程，更新实例状态为RUNNING
                            self.resume_instance(instance)
                        case _:
                            raise RuntimeError(f"Unknown manage instance task type: {task.type}")
                    logger.info(f"Node {self.node.node_id} successfully handled manage instance task: {task.task_id}")
                    result = "FINISHED"
                except Exception as e:
                    err_msg = str(e)
                    logger.warning(f"Node {self.node.node_id} failed to handle manage instance task: {task.task_id}")
                    result = "FAILED"
                finally:
                    col.update_one(
                        {"task_id": task.task_id},
                        {"$set": {"status": result, "finished_at": time.time(), "error_msg": err_msg}},
                    )
            else:
                time.sleep(1)

    def run(self):
        self.register_self()

        # 创建线程
        th_self_maintenance = threading.Thread(target=self.self_maintenance, daemon=True)
        th_instance_maintenance = threading.Thread(target=self.instance_maintenance, daemon=True)
        th_handle_instance_task = threading.Thread(target=self.handle_instance_task, daemon=True)

        # 启动线程
        th_self_maintenance.start()
        th_instance_maintenance.start()
        th_handle_instance_task.start()

        th_self_maintenance.join()
