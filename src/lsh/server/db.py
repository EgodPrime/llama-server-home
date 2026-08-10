import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from lsh.utils.path_helper import CONFIG_PATH, LOG_DIR


def load_config() -> Dict[str, Any]:
    import os
    import yaml

    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)

    for key, value in cfg.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_name = value[2:-1]
            resolved = os.environ.get(env_name)
            if resolved:
                cfg[key] = resolved

    return cfg


class Database:
    def __init__(self, db_dir: str):
        import os

        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, "lsh.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=5.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._init_schema()
        logger.info(f"Database initialized at {self.db_path}")

    def _init_schema(self):
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS instances (
                instance_name TEXT PRIMARY KEY,
                status TEXT,
                pid INTEGER,
                host TEXT,
                port INTEGER,
                env TEXT,
                cmd_args TEXT,
                log_file TEXT,
                last_heartbeat REAL,
                last_error TEXT,
                created_at REAL,
                started_at REAL,
                last_stopped_at REAL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS instance_tasks (
                task_id TEXT PRIMARY KEY,
                type TEXT,
                instance_name TEXT,
                host TEXT,
                port INTEGER,
                status TEXT,
                error_msg TEXT,
                env TEXT,
                cmd_args TEXT,
                created_at REAL,
                started_at REAL,
                finished_at REAL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                instance_name TEXT PRIMARY KEY,
                content TEXT,
                last_updated_at REAL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                timestamp REAL,
                cpu_usage REAL,
                cpu_cores INTEGER,
                mem_total_mb REAL,
                mem_used_mb REAL,
                mem_usage_pct REAL,
                gpus_info TEXT
            )
        """)

        self.conn.commit()
        logger.info("Database schema initialized")

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return dict(row)

    def _exec(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self.conn.cursor()
        cur.execute(query, params)
        return cur

    def _exec_commit(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self._exec(query, params)
        self.conn.commit()
        return cur

    # --- Instances ---

    def list_instances(self) -> List[Dict[str, Any]]:
        rows = self._exec("SELECT * FROM instances ORDER BY created_at DESC").fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_instance(self, instance_name: str) -> Optional[Dict[str, Any]]:
        row = self._exec("SELECT * FROM instances WHERE instance_name = ?", (instance_name,)).fetchone()
        return self._row_to_dict(row) if row else None

    def create_instance(self, instance: Dict[str, Any]):
        self._exec_commit(
            """INSERT INTO instances
            (instance_name, status, pid, host, port, env, cmd_args, log_file, last_heartbeat, last_error, created_at, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                instance["instance_name"],
                instance.get("status"),
                instance.get("pid"),
                instance.get("host"),
                instance.get("port"),
                json.dumps(instance.get("env")) if instance.get("env") else None,
                instance.get("cmd_args"),
                instance.get("log_file"),
                instance.get("last_heartbeat"),
                instance.get("last_error"),
                instance.get("created_at", time.time()),
                instance.get("started_at"),
            ),
        )

    def update_instance(self, instance_name: str, updates: Dict[str, Any]):
        set_parts = []
        params = []
        for key, value in updates.items():
            if key == "env" and isinstance(value, dict):
                value = json.dumps(value)
            set_parts.append(f"{key} = ?")
            params.append(value)
        params.append(instance_name)
        self._exec_commit(f"UPDATE instances SET {', '.join(set_parts)} WHERE instance_name = ?", tuple(params))

    def delete_instance(self, instance_name: str):
        self._exec_commit("DELETE FROM logs WHERE instance_name = ?", (instance_name,))
        self._exec_commit(
            "DELETE FROM instance_tasks WHERE instance_name = ?", (instance_name,)
        )
        self._exec_commit("DELETE FROM instances WHERE instance_name = ?", (instance_name,))

    def rename_instance(self, old_name: str, new_name: str):
        self._exec_commit(
            "UPDATE instances SET instance_name = ? WHERE instance_name = ?",
            (new_name, old_name),
        )
        self._exec_commit(
            "UPDATE instance_tasks SET instance_name = ? WHERE instance_name = ?",
            (new_name, old_name),
        )
        self._exec_commit(
            "UPDATE logs SET instance_name = ? WHERE instance_name = ?",
            (new_name, old_name),
        )

    def migrate_instance_names(self):
        instances = self.list_instances()
        migrated = 0
        for inst in instances:
            old_name = inst["instance_name"]
            if not old_name.startswith("port-"):
                continue
            port = inst["port"]
            if not port:
                continue
            cmd_args = inst.get("cmd_args") or ""
            model_basename = None
            env = {}
            if isinstance(inst.get("env"), str):
                try:
                    import json
                    env = json.loads(inst["env"])
                except Exception:
                    pass
            elif isinstance(inst.get("env"), dict):
                env = inst["env"]

            i = 0
            tokens = cmd_args.split()
            while i < len(tokens):
                if tokens[i] in ('-m', '--model') and i + 1 < len(tokens):
                    from pathlib import Path
                    model_basename = tokens[i + 1]
                    model_basename = Path(model_basename).name
                    for ext in ('.gguf', '.GGUF'):
                        if model_basename.endswith(ext):
                            model_basename = model_basename[:-len(ext)]
                            break
                    break
                i += 1

            if not model_basename:
                continue

            gpu_id = env.get('CUDA_VISIBLE_DEVICES', 'unknown').replace(' ', '_')
            new_name = f"{model_basename}_{gpu_id}_{port}"

            if new_name != old_name:
                self.rename_instance(old_name, new_name)
                logger.info(f"Migrated instance {old_name} -> {new_name}")
                migrated += 1

        if migrated > 0:
            logger.info(f"Instance migration complete: {migrated} renamed")

    def migrate_log_file_column(self):
        log_dir = LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        instances = self.list_instances()
        migrated = 0
        for inst in instances:
            old_name = inst["instance_name"]
            log_file = inst.get("log_file")

            cmd_args = inst.get("cmd_args") or ""
            # Extract log file from cmd_args
            new_log_file = None
            new_cmd_args_tokens = []
            tokens = cmd_args.split()
            i = 0
            while i < len(tokens):
                if tokens[i] == "--log-file" and i + 1 < len(tokens):
                    lf = tokens[i + 1]
                    p = Path(lf)
                    if not p.is_absolute():
                        resolved = (log_dir / p).resolve()
                        if resolved.exists():
                            lf = str(resolved)
                        else:
                            # Try from cwd (unknown, just use as-is)
                            pass
                    new_log_file = lf
                    i += 2
                else:
                    new_cmd_args_tokens.append(tokens[i])
                    i += 1

            if log_file is None or log_file != new_log_file:
                default_log_file = str(log_dir / f"{old_name}.log")
                final_log_file = new_log_file or default_log_file
                self._exec_commit(
                    "UPDATE instances SET log_file = ? WHERE instance_name = ?",
                    (final_log_file, old_name),
                )
                new_cmd_args = " ".join(new_cmd_args_tokens)
                if new_cmd_args != cmd_args:
                    self._exec_commit(
                        "UPDATE instances SET cmd_args = ? WHERE instance_name = ?",
                        (new_cmd_args, old_name),
                    )
                logger.info(f"Migrated log_file for {old_name}: {final_log_file}")
                migrated += 1

        if migrated > 0:
            logger.info(f"Log file migration complete: {migrated} instance(s)")

    # --- Instance Tasks ---

    def list_instance_tasks(self) -> List[Dict[str, Any]]:
        rows = self._exec("SELECT * FROM instance_tasks ORDER BY created_at DESC").fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_instance_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        row = self._exec("SELECT * FROM instance_tasks WHERE task_id = ?", (task_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def create_instance_task(self, task: Dict[str, Any]):
        self._exec_commit(
            """INSERT INTO instance_tasks
            (task_id, type, instance_name, host, port, status, env, cmd_args, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.get("task_id", str(__import__("uuid").uuid4())),
                task.get("type"),
                task.get("instance_name"),
                task.get("host", "0.0.0.0"),
                task.get("port"),
                task.get("status", "INIT"),
                json.dumps(task.get("env")) if task.get("env") else None,
                task.get("cmd_args"),
                task.get("created_at", time.time()),
            ),
        )

    def claim_next_task(self) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM instance_tasks WHERE status = 'INIT' ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
            if not row:
                conn.commit()
                conn.close()
                return None
            task_id = row["task_id"]
            conn.execute(
                "UPDATE instance_tasks SET status = 'PROCESSING', started_at = ? WHERE task_id = ?",
                (time.time(), task_id),
            )
            conn.commit()
            result = self._row_to_dict(row)
            result["status"] = "PROCESSING"
            result["started_at"] = time.time()
            conn.close()
            return result
        except Exception:
            conn.rollback()
            conn.close()
            raise

    def update_instance_task(self, task_id: str, updates: Dict[str, Any]):
        set_parts = []
        params = []
        for key, value in updates.items():
            set_parts.append(f"{key} = ?")
            params.append(value)
        params.append(task_id)
        self._exec_commit(f"UPDATE instance_tasks SET {', '.join(set_parts)} WHERE task_id = ?", tuple(params))

    def delete_instance_task(self, task_id: str):
        self._exec_commit("DELETE FROM instance_tasks WHERE task_id = ?", (task_id,))

    # --- Logs ---

    def get_instance_log(self, instance_name: str) -> Optional[Dict[str, Any]]:
        row = self._exec("SELECT * FROM logs WHERE instance_name = ?", (instance_name,)).fetchone()
        return self._row_to_dict(row) if row else None

    def update_instance_log(self, instance_name: str, content: str):
        self._exec_commit(
            """INSERT INTO logs (instance_name, content, last_updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(instance_name) DO UPDATE SET content = ?, last_updated_at = ?""",
            (instance_name, content, time.time(), content, time.time()),
        )

    # --- Metrics ---

    def list_metrics(self, n: int = 20) -> List[Dict[str, Any]]:
        rows = self._exec(
            "SELECT * FROM metrics ORDER BY timestamp DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def insert_metric(self, metric: Dict[str, Any]):
        self._exec_commit(
            """INSERT INTO metrics
            (timestamp, cpu_usage, cpu_cores, mem_total_mb, mem_used_mb, mem_usage_pct, gpus_info)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                metric.get("timestamp", time.time()),
                metric.get("cpu_usage"),
                metric.get("cpu_cores"),
                metric.get("mem_total_mb"),
                metric.get("mem_used_mb"),
                metric.get("mem_usage_pct"),
                json.dumps(metric.get("gpus_info")) if metric.get("gpus_info") is not None else None,
            ),
        )

    def trim_metrics(self, max_rows: int):
        self._exec_commit(
            """DELETE FROM metrics WHERE rowid NOT IN (
                SELECT rowid FROM metrics ORDER BY timestamp DESC LIMIT ?
            )""",
            (max_rows,),
        )

    def close(self):
        self.conn.close()


_db_instance: Optional[Database] = None


def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        cfg = load_config()
        db_dir = cfg.get("db_dir", "db_dir")
        _db_instance = Database(db_dir)
    return _db_instance
