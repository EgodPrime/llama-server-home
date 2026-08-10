import json
import shlex
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict

import psutil
from loguru import logger

from lsh.server.db import Database
from lsh.server.metrics import measure_cpu, measure_gpu, measure_memory
from lsh.utils.schema import Instance, InstanceTask


class Agent:
    def __init__(
        self,
        db: Database,
        llama_path: str,
        storage_dir: str,
        maintenance_interval: int = 5,
        metrics_interval: int = 5,
        max_metrics: int = 200,
        host: str = "127.0.0.1",
    ):
        self.db = db
        self.llama_path = Path(llama_path).resolve()
        self.storage_dir = Path(storage_dir).resolve()
        self.maintenance_interval = maintenance_interval
        self.metrics_interval = metrics_interval
        self.max_metrics = max_metrics
        self.host = host
        self._stop_event = threading.Event()

    def start(self):
        logger.info("Agent starting...")
        t_maintenance = threading.Thread(target=self._maintenance_loop, daemon=True)
        t_metrics = threading.Thread(target=self._metrics_loop, daemon=True)
        t_tasks = threading.Thread(target=self._task_loop, daemon=True)
        t_maintenance.start()
        t_metrics.start()
        t_tasks.start()
        logger.info("Agent started")

    def stop(self):
        self._stop_event.set()
        logger.info("Agent stopping...")

    def _maintenance_loop(self):
        while not self._stop_event.wait(timeout=self.maintenance_interval):
            try:
                self._check_instances()
            except Exception as e:
                logger.error(f"Instance maintenance error: {e}")

    def _check_instances(self):
        instances = self.db.list_instances()
        for inst_doc in instances:
            instance = Instance.model_validate(inst_doc)
            if instance.status not in ("RUNNING", "ERROR"):
                continue

            works_fine = False
            err_msg = None
            try:
                proc = psutil.Process(instance.pid)
                if proc.is_running():
                    works_fine = True
            except Exception as e:
                err_msg = str(e)
                logger.info(f"Instance {instance.instance_name} has issue: {err_msg}")

            cfg = {"last_heartbeat": time.time()}
            if instance.status == "RUNNING" and not works_fine:
                cfg["status"] = "ERROR"
                cfg["last_error"] = err_msg
            elif instance.status in ("ERROR", "STOPPED") and works_fine:
                cfg["status"] = "RUNNING"
                cfg["last_error"] = None
                logger.warning(f"Instance {instance.instance_name} seems alive. Updated to RUNNING.")
            elif not works_fine and err_msg:
                cfg["last_error"] = err_msg

            self.db.update_instance(instance.instance_name, cfg)

            if works_fine:
                self._update_instance_log(instance)

    def _update_instance_log(self, instance: Instance):
        log_dir = Path(__file__).resolve().parents[2] / "logs"
        log_file = log_dir / f"{instance.instance_name}.log"
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()[-50:]
                content = "".join(lines)
        except Exception as e:
            content = f"Failed to read log file: {e}"
        self.db.update_instance_log(instance.instance_name, content)

    def _metrics_loop(self):
        while not self._stop_event.wait(timeout=self.metrics_interval):
            try:
                self._collect_metrics()
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")

    def _collect_metrics(self):
        cpu = measure_cpu()
        mem = measure_memory()
        gpus = measure_gpu()

        self.db.insert_metric({
            "timestamp": time.time(),
            "cpu_usage": cpu.usage_percent,
            "cpu_cores": cpu.cores_count,
            "mem_total_mb": mem.total_mb,
            "mem_used_mb": mem.used_mb,
            "mem_usage_pct": mem.usage_percent,
            "gpus_info": [g.model_dump() for g in gpus],
        })

        self.db.trim_metrics(self.max_metrics)

    def _task_loop(self):
        while not self._stop_event.is_set():
            task_doc = self.db.claim_next_task()
            if not task_doc:
                time.sleep(1)
                continue

            task = InstanceTask.model_validate(task_doc)
            err_msg = None
            result = "FAILED"
            try:
                logger.info(f"Handling task {task.task_id} ({task.type})")
                match task.type:
                    case "DEPLOY":
                        self._deploy_instance(task)
                    case "STOP":
                        self._stop_instance(task)
                    case "RESUME":
                        self._resume_instance(task)
                    case _:
                        raise RuntimeError(f"Unknown task type: {task.type}")
                result = "FINISHED"
                logger.info(f"Task {task.task_id} finished")
            except Exception as e:
                err_msg = str(e)
                logger.error(f"Task {task.task_id} failed: {e}")
            finally:
                self.db.update_instance_task(task.task_id, {
                    "status": result,
                    "finished_at": time.time(),
                    "error_msg": err_msg,
                })

    def _build_cmd(self, cmd_args: str | None, instance_name: str) -> list[str]:
        log_dir = Path(__file__).resolve().parents[2] / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{instance_name}.log"

        base = [str(self.llama_path), "--log-file", str(log_file)]
        extra = shlex.split(cmd_args) if cmd_args else []
        return base + extra

    def _start_process(self, cmd: list[str], env: Dict[str, str] | None, instance_name: str) -> subprocess.Popen:
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return process

    def _deploy_instance(self, task: InstanceTask):
        if not task.cmd_args:
            raise RuntimeError("DEPLOY task requires cmd_args")

        cmd = self._build_cmd(task.cmd_args, task.instance_name)
        process = self._start_process(cmd, task.env, task.instance_name)

        created_time = time.time()
        self.db.create_instance({
            "instance_name": task.instance_name,
            "status": "RUNNING",
            "pid": process.pid,
            "host": task.host,
            "port": task.port,
            "env": task.env,
            "cmd_args": task.cmd_args,
            "last_heartbeat": created_time,
            "last_error": None,
            "created_at": created_time,
            "started_at": created_time,
        })
        logger.info(f"Deployed instance {task.instance_name} (pid={process.pid})")

    def _stop_instance(self, task: InstanceTask):
        instance = self.db.get_instance(task.instance_name)
        if not instance:
            raise RuntimeError(f"Instance {task.instance_name} not found")

        try:
            psutil.Process(instance["pid"]).kill()
        except Exception:
            pass

        self.db.update_instance(task.instance_name, {
            "status": "STOPPED",
            "last_error": None,
            "last_stopped_at": time.time(),
        })
        logger.info(f"Stopped instance {task.instance_name}")

    def _resume_instance(self, task: InstanceTask):
        instance_doc = self.db.get_instance(task.instance_name)
        if not instance_doc:
            raise RuntimeError(f"Instance {task.instance_name} not found")
        instance = Instance.model_validate(instance_doc)

        if not instance.cmd_args:
            raise RuntimeError(f"Instance {task.instance_name} missing cmd_args")

        cmd = self._build_cmd(instance.cmd_args, task.instance_name)
        process = self._start_process(cmd, instance.env, task.instance_name)

        self.db.update_instance(task.instance_name, {
            "status": "RUNNING",
            "pid": process.pid,
            "last_error": None,
            "started_at": time.time(),
        })
        logger.info(f"Resumed instance {task.instance_name} (pid={process.pid})")
