import os
import pathlib
import subprocess
import threading
import time
from typing import Any, List

import psutil
import pymongo
import pynvml
import yaml
from loguru import logger

from lsh.utils.path_helper import NODE_CONFIG_PATH
from lsh.utils.schema import CPUInfo, CreateInstanceTask, GPUInfo, Instance, MemoryInfo, Metric, Node


def measure_cpu() -> CPUInfo:
    usage_percent = psutil.cpu_percent(interval=1)
    cores_count = psutil.cpu_count(logical=True)
    return CPUInfo(usage_percent=usage_percent, cores_count=cores_count)


def measure_memory() -> MemoryInfo:
    memory = psutil.virtual_memory()
    return MemoryInfo(
        total_mb=memory.total / (1024 * 1024),
        used_mb=memory.used / (1024 * 1024),
        free_mb=memory.free / (1024 * 1024),
        usage_percent=memory.percent,
    )


def measure_gpu() -> List[GPUInfo]:
    gpus = []
    try:
        pynvml.nvmlInit()
        gpu_count = pynvml.nvmlDeviceGetCount()

        for i in range(gpu_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            gpu_info = GPUInfo(
                id=i,
                model=pynvml.nvmlDeviceGetName(handle),
                temperature_c=pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU),
                power_draw_w=pynvml.nvmlDeviceGetPowerUsage(handle) / 1000,
                memory_total_mb=mem_info.total / (1024 * 1024),
                memory_used_mb=mem_info.used / (1024 * 1024),
                memory_free_mb=mem_info.free / (1024 * 1024),
            )
            gpus.append(gpu_info)
    except pynvml.NVMLError:
        pass
    finally:
        try:
            pynvml.nvmlShutdown()
        except pynvml.NVMLError:
            pass
    return gpus


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
                    case "RESTARTING", "ERROR", "STOPPED":
                        if works_fine:
                            cfg["status"] = "RUNNING"
                            cfg["last_error"] = None
                col.update_one({"_id": inst_doc["_id"]}, {"$set": cfg})

            elapsed = time.time() - t0
            time.sleep(max(0, self.heartbeat_interval - elapsed))
            

    def handle_create_instance_task(self):
        col = self.db["create_instance_tasks"]
        while True:
            task_doc = col.find_one(
                {"node_id": self.node.node_id, "status": "INIT"},
                sort=[("created_at", pymongo.ASCENDING)],
            )
            if task_doc:
                task = CreateInstanceTask.model_validate(task_doc)
                err_msg = None
                result = None
                pid = None
                try:
                    logger.info(f"Node {self.node.node_id} handling task: {task.task_id}")
                    col.update_one(
                        {"task_id": task.task_id}, {"$set": {"status": "PROCESSING", "started_at": time.time()}}
                    )
                    log_file = f"/tmp/{task.instance_name}.log"
                    cmd_list = [
                        str(self.node.llama_path),
                        "--model", str(self.nfs_path / task.model_path),
                        "--host", self.node.ip_address,
                        "--port", str(task.port),
                    ]
                    if task.mmproj_path:
                        cmd_list += ["--mmproj", str(self.nfs_path / task.mmproj_path)]
                    for k, v in task.config.items():
                        cmd_list += [k, str(v)]
                    process = subprocess.Popen(cmd_list, 
                                     env=task.env, 
                                     stdout=open(log_file, "w"),
                                     stderr=subprocess.STDOUT,
                                     start_new_session=True)
                 
               
                    pid = process.pid
                    logger.info(f"Node {self.node.node_id} successfully handled task: {task.task_id}")
                    result = "FINISHED"
                except Exception as e:
                    err_msg = str(e)
                    logger.warning(f"Node {self.node.node_id} failed to handle task: {task.task_id}")
                    result = "FAILED"
                    if pid:
                        try:
                            psutil.Process(pid).kill()
                        except Exception:
                            pass
                finally:
                    col.update_one(
                        {"task_id": task.task_id},
                        {"$set": {"status": result, "finished_at": time.time(), "error_msg": err_msg}},
                    )

                if result == "FINISHED":
                    # --- 任务完成后，创建一个新的实例记录 ---
                    created_time = time.time() if task.status == "FINISHED" else None
                    instance = Instance(
                        instance_name=task.instance_name,
                        node_id=task.node_id,
                        status="RUNNING",
                        pid=pid,
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
                    col_instances = self.db["instances"]
                    col_instances.insert_one(instance.model_dump())
                    logger.info(f"Node {self.node.node_id} created instance record for task: {task.task_id}")
            else:
                time.sleep(5)

    def run(self):
        self.register_self()

        # 创建线程
        th_self_maintenance = threading.Thread(target=self.self_maintenance, daemon=True)
        th_handle_create_instance_task = threading.Thread(target=self.handle_create_instance_task, daemon=True)
        th_instance_maintenance = threading.Thread(target=self.instance_maintenance, daemon=True)

        # 启动线程
        th_self_maintenance.start()
        th_handle_create_instance_task.start()
        th_instance_maintenance.start()

        th_self_maintenance.join()
