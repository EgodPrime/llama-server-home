# Llama-Server-Home: 分布式 → 单体自包含服务重构计划

> 创建日期: 2026-08-10
> 最后更新: 2026-08-10
> 状态: Completed

## 一、目标

将当前的分布式架构（Controller + Node Agent + MongoDB + NFS）重构为单体自包含服务：

- 每个 node 独立运行完整的前后端
- SQLite 替代 MongoDB，本地数据存储
- 本地存储目录替代 NFS
- 单个 CLI 命令 `llama-server-home` 启动全部服务
- 静态 HTML + FastAPI（Jinja2 模板），无 Vue/npm 预编译流程
- 无用户系统，直接访问
- Makefile 构建流程（仅 Python 环境 + 模板编译）

### 核心功能

1. 查看服务器状态（CPU/GPU/内存指标）
2. 部署新的模型实例
3. 检查已有模型运行情况（列表、日志、状态）
4. 保存一组模型部署方案（Profile），支持一键部署

## 二、最终架构

```
[Client Browser] → [llama-server-home: FastAPI + Jinja2 + SQLite + Agent]
                                    ↓ subprocess
                                llama-server
```

## 三、配置 `config.yaml`（项目根目录）

```yaml
db_dir: "db_dir"                      # SQLite 数据存储，默认项目根目录下的 db_dir/
storage_dir: "/path/to/models"        # 模型存储路径
llama_path: "/path/to/llama-server"   # llama-server 二进制路径
maintenance_interval: 5               # 实例巡检间隔（秒）
metrics_interval: 5                   # 指标采集间隔（秒）
max_metrics: 200                      # 指标最大存储条数
host: "0.0.0.0"                       # 服务绑定地址
port: 8000                            # 服务端口
```

## 四、技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| SQLite 方案 | sqlite3 + Pydantic | 零额外依赖，轻量 |
| 前端模板 | FastAPI + Jinja2 | 无额外构建步骤，HTML/JS/CSS 内嵌 |
| CSS 框架 | Tailwind CSS | 通过 CDN 引入，快速开发 |
| JS 框架 | Alpine.js | 轻量响应式，通过 CDN 引入 |
| llama-server 配置 | 命令行参数 | 简单直接 |
| 用户认证 | 无 | 本地服务，无需认证 |
| CLI 命令 | llama-server-home | 单个入口 |
| 虚拟环境 | .venv（项目内） | 随项目一起，可复现 |

## 五、SQLite 数据模型

### 表结构

| 表 | 主键 | 关键列 | 说明 |
|---|---|---|---|
| instances | instance_name | status, pid, port, model_path, mmproj_path, env(JSON), config(JSON), timestamps | 运行实例 |
| instance_tasks | task_id | type, instance_name, port, model_path, mmproj_path, status, error_msg, env(JSON), config(JSON), timestamps | 任务队列 |
| logs | instance_name | content, last_updated_at | 实例日志（最后50行） |
| metrics | rowid AUTOINCREMENT | timestamp, cpu_usage, cpu_cores, mem_*, gpus_info(JSON) | 资源指标 |
| profiles | profile_name | instances(JSON), created_at | 部署方案 |

### SQL DDL（供 db.py 参考）

```sql
CREATE TABLE IF NOT EXISTS instances (
    instance_name TEXT PRIMARY KEY,
    status TEXT,
    pid INTEGER,
    port INTEGER,
    model_path TEXT,
    mmproj_path TEXT,
    env TEXT,
    config TEXT,
    last_heartbeat REAL,
    last_error TEXT,
    created_at REAL,
    started_at REAL,
    last_stopped_at REAL
);

CREATE TABLE IF NOT EXISTS instance_tasks (
    task_id TEXT PRIMARY KEY,
    type TEXT,
    instance_name TEXT,
    port INTEGER,
    model_path TEXT,
    mmproj_path TEXT,
    status TEXT,
    error_msg TEXT,
    env TEXT,
    config TEXT,
    created_at REAL,
    started_at REAL,
    finished_at REAL
);

CREATE TABLE IF NOT EXISTS logs (
    instance_name TEXT PRIMARY KEY,
    content TEXT,
    last_updated_at REAL
);

CREATE TABLE IF NOT EXISTS metrics (
    timestamp REAL,
    cpu_usage REAL,
    cpu_cores INTEGER,
    mem_total_mb REAL,
    mem_used_mb REAL,
    mem_usage_pct REAL,
    gpus_info TEXT
);

CREATE TABLE IF NOT EXISTS profiles (
    profile_name TEXT PRIMARY KEY,
    instances TEXT,
    created_at REAL
);
```

## 六、目录结构

```
llama-server-home/
├── Makefile
├── config.yaml
├── pyproject.toml
├── db_dir/                      # SQLite 数据存储
├── .venv/                       # Python 虚拟环境
├── src/lsh/
│   ├── server/
│   │   ├── main.py              # FastAPI app + CLI entry + Jinja2 templates 挂载
│   │   ├── agent.py             # Agent线程：实例巡检、指标采集、任务处理
│   │   ├── db.py                # SQLite 连接 + schema init + CRUD
│   │   ├── metrics.py           # CPU/GPU/memory 采集
│   │   └── api.py               # 所有 API routes（instances/tasks/storage/metrics/profiles）
│   └── utils/
│       ├── schema.py            # Pydantic models
│       └── path_helper.py       # 路径辅助
└── templates/                   # Jinja2 HTML 模板
    ├── base.html                # 基础布局（Tailwind CDN + Alpine CDN）
    ├── home.html                # 首页：概览 + 最新指标
    ├── instances.html           # 实例列表 + 操作
    ├── deploy.html              # 部署新实例表单
    ├── tasks.html               # 任务历史
    ├── storage.html             # 本地存储浏览
    ├── profiles.html            # 部署方案管理
    ├── metrics.html             # 系统指标
    └── modals/                  # 模态框模板片段
        ├── deploy_modal.html
        └── profile_modal.html
```

## 七、API 端点（无认证）

| 方法 | 路径 | 描述 |
|---|---|---|
| GET | /api/instances | 列出实例 |
| GET | /api/instances/{name} | 实例详情 |
| GET | /api/instances/{name}/logs | 实例日志 |
| DELETE | /api/instances/{name} | 删除实例 |
| POST | /api/tasks/create | 创建部署任务 |
| GET | /api/tasks | 列出任务 |
| POST | /api/tasks/stop/{name} | 停止实例任务 |
| POST | /api/tasks/resume/{name} | 恢复实例任务 |
| DELETE | /api/tasks/{task_id} | 删除任务 |
| GET | /api/storage/list_root | 存储根目录 |
| GET | /api/storage/list_dir/{path} | 浏览存储目录 |
| GET | /api/storage/list_models | 列出可用模型 |
| GET | /api/metrics?n=20 | 获取最近N条指标 |
| POST | /api/profiles/create | 创建部署方案 |
| GET | /api/profiles/list | 列出部署方案 |
| GET | /api/profiles/{name} | 方案详情 |
| POST | /api/profiles/{name}/deploy | 一键部署方案 |
| DELETE | /api/profiles/{name} | 删除方案 |

## 八、页面（HTML + Alpine.js）

| 路径 | 模板 | 功能 |
|---|---|---|
| / | home.html | 首页：实例数量、运行状态、最新 CPU/GPU/内存指标 |
| /instances | instances.html | 实例列表，停止/恢复/删除操作，查看日志 |
| /deploy | deploy.html | 部署表单：选模型、端口、env、llama.cpp 参数 |
| /tasks | tasks.html | 任务历史，删除 INIT 状态任务 |
| /storage | storage.html | 浏览存储目录，查看模型列表 |
| /profiles | profiles.html | 创建/查看/删除部署方案，一键部署 |
| /metrics | metrics.html | CPU/GPU/内存图表（Alpine + 原生 Canvas 或轻量库） |

## 九、Makefile 设计

```makefile
.PHONY: env serve clean

# 创建 Python 环境
env:
	@if [ ! -d ".venv" ]; then uv venv .venv; fi
	uv pip install -e .

# 启动服务
serve:
	uv run llama-server-home

# 清理
clean:
	rm -rf .venv
```

## 十、Check Points

### CP-1: SQLite 基础 + Schema ✅

**任务:**
- 创建 `src/lsh/server/db.py`
- 精简 `src/lsh/utils/schema.py`（移除 Node、User）
- 实现 SQLite 连接、schema 初始化、基础 CRUD（instances/tasks/logs/metrics/profiles）

**验证:**
- [x] db.py 能正确创建所有表
- [x] 能插入/查询记录

### CP-2: Agent 核心逻辑 ✅

**任务:**
- 创建 `src/lsh/server/agent.py`
- 实现实例巡检、指标采集、任务处理线程
- 复用 `node/metrics.py` 到 `server/metrics.py`

**验证:**
- [x] Agent 能定期采集 CPU/GPU/memory 指标
- [x] Agent 能检测实例进程状态
- [x] Agent 能处理 DEPLOY/STOP/RESUME 任务

### CP-3: API Routes ✅

**任务:**
- 实现所有 API routes（instances/tasks/storage/metrics/profiles）
- 移除 auth/users 相关

**验证:**
- [x] 所有 endpoint 可访问，无需认证
- [x] Storage API 能浏览本地目录和识别模型文件

### CP-4: main.py + CLI ✅

**任务:**
- 更新 `src/lsh/server/main.py`，使用 Jinja2 模板
- CLI entry `llama-server-home`
- 更新 `pyproject.toml`（移除 JWT、bcrypt、pymongo）

**验证:**
- [x] `uv run llama-server-home` 能启动服务
- [x] Agent 线程在后台运行
- [x] API 端点可访问

### CP-5: Makefile ✅

**任务:**
- 简化 Makefile（仅 env/serve/clean）

**验证:**
- [x] `make env` 创建 .venv 并安装依赖
- [x] `make serve` 能一键启动服务

### CP-6: HTML 模板 + Alpine.js（In Progress）

**任务:**
- 创建 templates/ 目录和所有 HTML 模板
- base.html 引入 Tailwind CSS CDN + Alpine.js CDN
- 实现各页面，使用 Alpine.js 做响应式交互
- API 调用使用原生 fetch

**验证:**
- [x] 所有页面可访问
- [x] 能创建实例并看到运行状态
- [x] 指标页面正常显示
- [x] Storage 页面能浏览本地目录
- [x] Profiles 能保存方案并一键部署

### CP-7: 清理旧代码

**任务:**
- 删除 controller/ node/ repo/ 目录
- 删除 frontend/ 目录
- 删除 controller.yaml.tmp、node.yaml.tmp
- 更新 pyproject.toml（移除旧依赖）
- 更新 .gitignore

**验证:**
- [x] `make serve` 仍然正常工作
- [x] 无残留的 MongoDB/pymongo 引用
- [x] 无残留的 Node/User 模型引用
- [x] 代码库干净

### CP-8: 最终验证 + README

**任务:**
- 端到端测试整个流程
- 更新 README.md

**验证:**
- [x] 全新克隆项目后，`make env && make serve` 能跑起来
- [x] README.md 准确描述新架构和使用方法

## 十一、删除内容清单

- [x] src/lsh/controller/ 整个目录
- [x] src/lsh/node/ 整个目录（metrics.py → server/metrics.py）
- [x] src/lsh/repo/ 整个目录
- [x] frontend/ 整个目录
- [x] controller.yaml.tmp
- [x] node.yaml.tmp
- [x] pyproject.toml 中的 `list-nodes` 命令
- [x] pyproject.toml 中的 `run-node` 命令
- [x] pyproject.toml 中的 pymongo、bcrypt、pyjwt 依赖
- [x] schema.py 中的 Node、User、InstanceGroup

## 十二、风险与注意事项

1. **并发**: SQLite 写入并发性能不如 MongoDB，但当前负载场景（单节点）足够
2. **Metrics 清理**: 定期执行 DELETE 语句控制 metrics 表大小
3. **任务原子性**: SQLite 使用 `BEGIN IMMEDIATE` 事务保证
4. **路径安全**: Storage API 防止 path traversal
5. **日志路径**: `/tmp/{instance_name}.log`
