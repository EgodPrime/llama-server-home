# Llama-server-home 加固与重构计划

> **目标：** 修复安全漏洞、提升生产可靠性、改善代码质量，分 4 个阶段渐进式推进，每个阶段可独立验证。

---

## Phase 1: 安全修复 (P0) — 预计 1-2 小时

### Task 1.1: JWT 密钥外部化

**问题:** `"kb310"` 硬编码在源码中，任何人拿到代码即可伪造任意用户 token。

**文件:**
- `src/lsh/controller/app/utils.py`
- `src/lsh/controller/app/user.py`
- `controller.yaml.tmp` → `controller.yaml` (新增配置项)

**步骤:**

1. 在 `controller.yaml` 中添加 `jwt_secret` 字段：
```yaml
mongodb_url: "mongodb://localhost:27017/"
mongodb_name: "llama_home"
nfs_path: "/mnt/nfs/models"
node_dead_threshold: 60
jwt_secret: "${JWT_SECRET}"  # 从环境变量读取，或改为随机字符串
```

2. 修改 `src/lsh/controller/lib.py` — 在 `Controller.__init__` 中加载 JWT 密钥：
```python
import os

class Controller:
    def __init__(self):
        cfg = yaml.safe_load(open(CONTROLLER_CONFIG_PATH, "r"))
        self.mongo_client = pymongo.MongoClient(cfg["mongodb_url"])
        self.db = self.mongo_client[cfg["mongodb_name"]]
        self.node_dead_threshold = int(cfg.get("node_dead_threshold", 60))
        self.nfs_path = cfg.get("nfs_path")
        # JWT secret: env var > config file > raise error
        self.jwt_secret = os.environ.get("JWT_SECRET", cfg.get("jwt_secret"))
        if not self.jwt_secret:
            raise RuntimeError("JWT_SECRET environment variable or jwt_secret config is required")
```

3. 修改 `src/lsh/controller/app/utils.py` — 使用 `self.jwt_secret`：
```python
async def get_current_user(request: Request) -> User:
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token is missing")
    token = token.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, controller.jwt_secret, algorithms=["HS256"])
        ...
```

4. 修改 `src/lsh/controller/app/user.py` — login 时同样使用：
```python
token = jwt.encode(payload, controller.jwt_secret, algorithm="HS256")
```

**验证:**
```bash
# 设置环境变量后启动，确认 JWT 正常工作
JWT_SECRET="my-random-secret-key-12345" uvicorn src.lsh.controller.app.main:app --host 0.0.0.0 --port 8000
# 前端登录 → 获取 token → 解码确认未过期、可验证签名
```

---

### Task 1.2: NFS 路径遍历防护

**问题:** `dir_path` 来自用户输入，可通过 `../../etc/passwd` 读取任意文件。

**文件:** `src/lsh/controller/app/nfs.py`

**步骤:**

修改 `list_nfs_dir` 和 `list_directory` 增加路径安全校验：
```python
def _safe_resolve(base: str, user_path: str) -> str:
    """Resolve path and ensure it stays within base directory."""
    resolved = os.path.realpath(os.path.join(base, user_path))
    base_resolved = os.path.realpath(base)
    if not resolved.startswith(base_resolved + os.sep) and resolved != base_resolved:
        raise ValueError(f"Path traversal detected: {user_path}")
    return resolved


@router.get("/list_dir/{dir_path}")
async def list_nfs_dir(dir_path: str):
    try:
        target_dir = _safe_resolve(controller.nfs_path, dir_path)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return {"error": "Directory not found"}
    return list_directory(target_dir)
```

**验证:**
```bash
# 正常路径应成功
curl http://localhost:8000/api/nfs/list_dir/models/llama3
# 路径遍历应被拒绝
curl http://localhost:8000/api/nfs/list_dir/../../etc
# 预期: 403 Path traversal detected
```

---

### Task 1.3: MongoDB 连接超时配置

**问题:** `MongoClient` 无超时参数，MongoDB 不可用时进程无限阻塞。

**文件:** `src/lsh/controller/lib.py`, `src/lsh/node/lib.py`

**步骤:**

在 `Controller.__init__` 中添加超时参数：
```python
self.mongo_client = pymongo.MongoClient(
    cfg["mongodb_url"],
    serverSelectionTimeoutMS=5000,
    socketTimeoutMS=10000,
    connectTimeoutMS=5000,
)
```

在 `NodeAgent.__init__` 中同样添加：
```python
self.mongo_client = pymongo.MongoClient(
    cfg["mongodb_url"],
    serverSelectionTimeoutMS=5000,
    socketTimeoutMS=10000,
    connectTimeoutMS=5000,
)
```

**验证:**
```bash
# 启动时 MongoDB 不可用，应在 5 秒内报错而非无限等待
uvicorn src.lsh.controller.app.main:app --host 0.0.0.0 --port 8000
# 预期: RuntimeError 或 loguru ERROR within 5s
```

---

## Phase 2: 可靠性修复 (P1) — 预计 3-4 小时

### Task 2.1: 任务领取幂等性保护

**问题:** NodeAgent 重启后重复领取 `INIT` 状态的任务，导致重复部署/停止。

**文件:** `src/lsh/node/lib.py:258-266`

**步骤:**

将"查找 INIT 任务"和"标记 PROCESSING"合并为原子操作：
```python
def handle_instance_task(self):
    col = self.db["instance_tasks"]
    while True:
        # 原子性领取：只更新状态为 INIT → PROCESSING 的任务
        task_doc = col.find_one_and_update(
            {"node_id": self.node.node_id, "status": "INIT"},
            {"$set": {"status": "PROCESSING", "started_at": time.time()}},
            sort=[("created_at", pymongo.ASCENDING)],
        )
        if task_doc:
            # 只有真正领取到任务才执行
            task = InstanceTask.model_validate(task_doc)
            ...  # 后续逻辑不变
```

**关键点:** `find_one_and_update` 是原子操作，即使两个 NodeAgent 同时查询，只有一个能成功将状态从 INIT 改为 PROCESSING。

**验证:**
```python
# 模拟两个并发请求同时查找同一任务
task = col.find_one_and_update(
    {"task_id": "abc", "status": "INIT"},
    {"$set": {"status": "PROCESSING"}},
)
# task 有值 → 领取成功；task 为 None → 被其他 agent 领走了
```

---

### Task 2.2: 文件句柄泄漏修复

**问题:** `subprocess.Popen(stdout=open(log_file, "w"))` 的文件对象从未关闭。

**文件:** `src/lsh/node/lib.py:170-172`, `src/lsh/node/lib.py:226-228`

**步骤:**

修改 `deploy_instance`：
```python
def deploy_instance(self, task: InstanceTask):
    log_file = f"/tmp/{task.instance_name}.log"
    cmd_list = [str(self.node.llama_path), "--model", str(self.nfs_path / task.model_path), ...]
    
    # 使用 NamedTemporaryFile 或手动管理文件句柄
    log_fh = open(log_file, "w")
    try:
        process = subprocess.Popen(
            cmd_list, env=task.env, stdout=log_fh, stderr=subprocess.STDOUT, start_new_session=True
        )
    except Exception:
        log_fh.close()
        raise
    
    # 进程启动成功后，关闭文件句柄（让 llama-server 直接写入）
    log_fh.flush()
    # 注意：不 close，因为后续 update_instance_log 需要读取该文件
    # 改用 os.dup2 或直接让 Python 保持打开但定期 flush
```

更好的方案 — 使用 `subprocess.Popen` 的 `stdout=subprocess.PIPE` 然后后台写入：
```python
import asyncio

def deploy_instance(self, task: InstanceTask):
    log_file = f"/tmp/{task.instance_name}.log"
    cmd_list = [...]
    
    process = subprocess.Popen(
        cmd_list, env=task.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        start_new_session=True, text=True
    )
    
    # 后台线程持续读取 stdout 写入日志文件
    def pipe_to_log():
        try:
            with open(log_file, "w") as f:
                for line in process.stdout:
                    f.write(line)
                    f.flush()
        except Exception as e:
            logger.error(f"Log pipe error: {e}")
    
    threading.Thread(target=pipe_to_log, daemon=True).start()
    ...
```

**验证:**
```bash
# 部署多个实例后检查文件句柄数
lsof -p <controller_pid> | wc -l
# 不应持续增长
```

---

### Task 2.3: Controller 单例 + 依赖注入

**问题:** 每个 router 模块各自创建 `Controller()`，导致多个 MongoDB 连接池。

**文件:** `src/lsh/controller/app/main.py`, 所有 `app/*.py` 中的 `controller = Controller()`

**步骤:**

1. 在 `main.py` 的 lifespan 中初始化全局单例：
```python
# src/lsh/controller/lib.py — 添加模块级变量
_controller_instance = None

def get_controller() -> Controller:
    """Get or create the singleton Controller instance."""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = Controller()
    return _controller_instance
```

2. 所有 router 文件改为导入 `get_controller`：
```python
# src/lsh/controller/app/instances.py
from lsh.controller.lib import get_controller
router = APIRouter(prefix="/instances", tags=["instances"])

@router.get("/list_instances")
async def list_instances(username=Depends(get_current_user_name)):
    controller = get_controller()
    col = controller.db["instances"]
    ...
```

3. 在 `main.py` lifespan 中启动心跳线程：
```python
@asynccontextmanager
async def lifespan(app):
    controller = get_controller()
    th = threading.Thread(target=controller.node_discovery_and_check_loop, daemon=True)
    th.start()
    yield
```

**验证:**
```bash
# 启动后检查 MongoDB 连接数
uvicorn src.lsh.controller.app.main:app --host 0.0.0.0 --port 8000
# mongo shell: db.serverStatus().connections → current 应 ≈ 1-2 (而非每个 router 一个)
```

---

## Phase 3: 代码质量修复 (P2) — 预计 1-2 小时

### Task 3.1: 拼写错误 + 注释更新

**文件:** `src/lsh/node/lib.py:54`, `src/lsh/utils/schema.py:138`

**步骤:**
```bash
# 1. 修复拼写
sed -i 's/updaate_metric/update_metric/g' src/lsh/node/lib.py

# 2. 更新注释
# schema.py:138 → "存储密码的 bcrypt 哈希值"
```

---

### Task 3.2: HTTP 方法规范化

**文件:** `src/lsh/controller/app/instances.py`, `src/lsh/controller/app/tasks.py`

**步骤:**

将 DELETE 操作改为正确的 HTTP 方法：
```python
# src/lsh/controller/app/instances.py:19
@router.delete("/delete_instance/{node_id}/{instance_name}")  # 而非 @router.post
async def delete_instance(node_id: str, instance_name: str):
    ...

# src/lsh/controller/app/tasks.py:25
@router.delete("/delete_instance_task/{task_id}")  # 而非 @router.post
async def delete_instance_task(task_id: str):
    ...
```

前端同步修改：`frontend/src/api/index.ts`
```typescript
// 将 axios.post 改为 axios.delete
export async function deleteInstanceTask(taskId: string) {
  const res = await axios.delete(`/api/tasks/delete_instance_task/${taskId}`);
  return res.data;
}
```

---

### Task 3.3: 实例删除级联清理

**文件:** `src/lsh/controller/app/instances.py`

**步骤:**

修改 `delete_instance` 增加级联删除：
```python
@router.delete("/delete_instance/{node_id}/{instance_name}")
async def delete_instance(node_id: str, instance_name: str):
    controller = get_controller()
    col_instances = controller.db["instances"]
    result = col_instances.delete_one({"node_id": node_id, "instance_name": instance_name})
    if result.deleted_count == 1:
        # 级联清理关联数据
        controller.db["logs"].delete_many({"node_id": node_id, "instance_name": instance_name})
        controller.db["metrics"].delete_many({"node_id": node_id})  # 可选：只删该实例相关
        return {"message": f"Instance {instance_name}@{node_id} and associated data deleted"}
    else:
        raise HTTPException(status_code=404, detail="Instance not found")
```

---

### Task 3.4: 指标存储优化 — Capped Collection

**问题:** `count_documents` + `find_one` + `delete_one` = 3 次网络往返，且有竞态条件。

**文件:** `src/lsh/node/lib.py:65-70`, `src/lsh/controller/lib.py` (启动时创建 capped collection)

**步骤:**

1. 在 Controller 初始化时创建 capped collection：
```python
# src/lsh/controller/lib.py — __init__ 中增加
try:
    self.db.command({"create": "metrics", "capped": True, "size": 1048576, "max": 200})
except pymongo.errors.OperationFailure:
    pass  # collection 已存在
```

2. NodeAgent 改为直接 insert（MongoDB capped collection 自动淘汰最旧文档）：
```python
def updaate_metric(self):  # 同时修复拼写
    metric = Metric(...)
    col = self.db["metrics"]
    col.insert_one(metric.model_dump())  # 不再需要手动删除
```

**注意:** Capped collection 不支持按 `node_id` 过滤（所有节点共享一个 capped collection）。如果每个节点需要独立 20 条限制，改用 TTL index + 定期清理脚本。

---

## Phase 4: 前端改进 (P2) — 预计 30 min

### Task 4.1: 轮询竞态保护

**文件:** `frontend/src/composables/usePolling.ts`

**步骤:**

```typescript
export function usePolling(
  callback: () => void | Promise<void>,
  interval: number,
  options: { immediate?: boolean } = {}
) {
  const { immediate = false } = options;
  let timer: ReturnType<typeof setInterval> | null = null;
  let isRunning = false;

  const start = () => {
    if (isRunning) return;  // 防止重叠
    if (immediate) {
      callback();
    }
    timer = setInterval(async () => {
      if (!isRunning) {
        isRunning = true;
        try {
          await callback();
        } finally {
          isRunning = false;
        }
      }
    }, interval);
  };

  const stop = () => {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    isRunning = false;
  };

  onUnmounted(() => {
    stop();
  });

  return { start, stop };
}
```

---

## 执行顺序与依赖关系

```
Phase 1 (安全) ──────────────────────────────▶ Phase 2 (可靠性) ──▶ Phase 3 (质量) ──▶ Phase 4 (前端)
   ├─ Task 1.1 JWT 密钥外部化                     ├─ Task 2.1 任务幂等性         ├─ Task 3.1 拼写/注释    └─ Task 4.1 轮询竞态
   ├─ Task 1.2 NFS 路径遍历                       ├─ Task 2.2 文件句柄泄漏       ├─ Task 3.2 HTTP 方法    
   └─ Task 1.3 MongoDB 超时                       └─ Task 2.3 Controller DI        └─ Task 3.3 级联删除
                                                   └─ Task 3.4 Capped Collection
```

**Phase 1 之间相互独立，可并行。**  
**Phase 2 依赖 Phase 1（Controller DI 需要统一的 jwt_secret）。**  
**Phase 3 大部分独立，Task 3.4 与 Phase 2 Task 2.3 有轻微耦合。**  
**Phase 4 完全独立，可与 Phase 2/3 并行。**

---

## 验证清单

每个 Phase 完成后执行：

| Phase | 命令 | 预期结果 |
|-------|------|----------|
| 1 | `JWT_SECRET=test uvicorn ...` | 服务正常启动，JWT 可验证 |
| 1 | `curl /api/nfs/list_dir/../../etc` | 返回 403 |
| 1 | `mongosh --eval "db.serverStatus().connections"` | current ≈ 1-2 |
| 2 | 模拟 NodeAgent 重启 + 重复领取任务 | 只执行一次 |
| 3 | `curl -X DELETE /api/instances/...` | HTTP 200 + 级联删除 logs |
| 4 | 快速切换页面 | 无重叠请求，控制台无警告 |

---

## 回滚策略

每个 Phase 独立提交，可单独 revert：
```bash
# 如果某个 Phase 引入问题，直接 revert 该阶段的所有 commit
git revert HEAD~N..HEAD  # N = 该阶段的 commit 数
```
