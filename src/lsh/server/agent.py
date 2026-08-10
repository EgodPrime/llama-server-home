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
from lsh.utils.path_helper import LOG_DIR


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
        self._discover_instances()
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
        log_file = instance.log_file
        if not log_file:
            log_dir = LOG_DIR
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

    def _build_cmd(self, cmd_args: str | None, instance_name: str, log_file: str | None = None) -> list[str]:
        base = [str(self.llama_path)]
        if log_file:
            base.append("--log-file")
            base.append(log_file)
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

        log_dir = LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(log_dir / f"{task.instance_name}.log")

        cmd = self._build_cmd(task.cmd_args, task.instance_name, log_file)
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
            "log_file": log_file,
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

    def _discover_instances(self):
        db_pids = {i["pid"] for i in self.db.list_instances()}

        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'environ']):
            try:
                cmdline = proc.info['cmdline'] or []
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

            if not cmdline:
                continue
            if any('llama-server-home' in c for c in cmdline):
                continue
            if not any('llama-server' in c for c in cmdline):
                continue

            port = None
            i = 1
            while i < len(cmdline):
                if cmdline[i] in ('--port', '-P') and i + 1 < len(cmdline):
                    try:
                        port = int(cmdline[i + 1])
                    except ValueError:
                        pass
                    break
                i += 1

            if port is None:
                continue

            try:
                env_raw = proc.info.get('environ') or {}
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

            gpu_id = env_raw.get('CUDA_VISIBLE_DEVICES', 'unknown').replace(' ', '_')

            model_basename = None
            i = 1
            while i < len(cmdline):
                if cmdline[i] in ('-m', '--model') and i + 1 < len(cmdline):
                    model_basename = cmdline[i + 1]
                    break
                i += 1

            if model_basename:
                model_basename = Path(model_basename).name
                for ext in ('.gguf', '.GGUF'):
                    if model_basename.endswith(ext):
                        model_basename = model_basename[:-len(ext)]
                        break

            if not model_basename:
                continue

            instance_name = f"{model_basename}_{gpu_id}_{port}"

            existing = self.db.get_instance(instance_name)
            if existing and existing["pid"] == proc.pid:
                continue

            relevant = {}
            for k in ('CUDA_VISIBLE_DEVICES', 'CUDA_VISIBLE_DEV', 'CUDA_DEVICE_ORDER',
                      'NCCL_SOCKET_IFNAME', 'HF_HOME', 'TRANSFORMERS_CACHE'):
                if k in env_raw:
                    relevant[k] = env_raw[k]

            try:
                proc_cwd = proc.cwd()
            except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
                proc_cwd = None

            host = None
            i = 1
            while i < len(cmdline):
                if cmdline[i] == '--host' and i + 1 < len(cmdline):
                    host = cmdline[i + 1]
                    break
                i += 1

            log_file_arg = None
            log_file_arg_idx = None
            stripped_cmdline = []
            i = 1
            while i < len(cmdline):
                if cmdline[i] == '--log-file' and i + 1 < len(cmdline):
                    log_file_arg = cmdline[i + 1]
                    log_file_arg_idx = i + 1
                    i += 2
                    continue
                stripped_cmdline.append(cmdline[i])
                i += 1

            resolved_cmdline = []
            for j, token in enumerate(stripped_cmdline):
                if j > 0 and stripped_cmdline[j - 1] in ('-m', '--model'):
                    p = Path(token)
                    if not p.is_absolute():
                        if proc_cwd:
                            resolved = (Path(proc_cwd) / p).resolve()
                            if resolved.exists():
                                token = str(resolved)
                resolved_cmdline.append(token)

            if log_file_arg:
                p = Path(log_file_arg)
                if not p.is_absolute():
                    if proc_cwd:
                        resolved = (Path(proc_cwd) / p).resolve()
                        if resolved.exists():
                            log_file_arg = str(resolved)
            else:
                log_dir = LOG_DIR
                log_dir.mkdir(parents=True, exist_ok=True)
                log_file_arg = str(log_dir / f"{instance_name}.log")

            final_cmd_args = ' '.join(resolved_cmdline)

            try:
                started_at = proc.create_time()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                started_at = None

            now = time.time()
            if not existing:
                self.db.create_instance({
                    "instance_name": instance_name,
                    "status": "RUNNING",
                    "pid": proc.pid,
                    "host": host or "0.0.0.0",
                    "port": port,
                    "env": relevant,
                    "cmd_args": final_cmd_args,
                    "log_file": log_file_arg,
                    "last_heartbeat": now,
                    "last_error": None,
                    "created_at": now,
                    "started_at": started_at,
                })
                logger.info(f"Discovered instance {instance_name} (pid={proc.pid})")
            elif existing["pid"] != proc.pid:
                self.db.update_instance(instance_name, {
                    "pid": proc.pid,
                    "status": "RUNNING",
                    "last_heartbeat": now,
                    "env": relevant,
                    "cmd_args": final_cmd_args,
                    "log_file": log_file_arg,
                    "last_error": None,
                })
                logger.warning(f"Instance {instance_name} PID changed: {existing['pid']} -> {proc.pid}")

        logger.info(f"Discovery complete: {len(db_pids)} existing instance(s)")

    def _resume_instance(self, task: InstanceTask):
        instance_doc = self.db.get_instance(task.instance_name)
        if not instance_doc:
            raise RuntimeError(f"Instance {task.instance_name} not found")
        instance = Instance.model_validate(instance_doc)

        if not instance.cmd_args:
            raise RuntimeError(f"Instance {task.instance_name} missing cmd_args")

        log_dir = LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = instance.log_file
        if not log_file:
            log_file = str(log_dir / f"{task.instance_name}.log")

        cmd = self._build_cmd(instance.cmd_args, task.instance_name, log_file)
        process = self._start_process(cmd, instance.env, task.instance_name)

        self.db.update_instance(task.instance_name, {
            "status": "RUNNING",
            "pid": process.pid,
            "log_file": log_file,
            "last_error": None,
            "started_at": time.time(),
        })
        logger.info(f"Resumed instance {task.instance_name} (pid={process.pid})")
