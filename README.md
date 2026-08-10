# llama-server-home

Monolith llama-server management platform. Deploy, monitor, and manage [llama.cpp llama-server](https://github.com/ggml-org/llama.cpp) instances on a single machine.

**One binary, one config, everything in one process.**

## Architecture

```
[Browser] → [llama-server-home: FastAPI + Jinja2 + SQLite + Agent]
                           ↓ subprocess
                      llama-server
```

Single-process design — no MongoDB, no NFS, no separate frontend build step. SQLite stores state, Agent manages subprocesses in the background.

## Features

- **Instances** — List, stop, resume, delete instances with status polling
- **Deploy** — Interactive form: select model from storage, pick GPU, set ports, preview full command
- **Metrics** — Real-time CPU / memory / GPU charts (CPU cores, RAM, GPU memory, GPU power, temperature)
- **Storage browser** — Navigate local GGUF model directory with breadcrumb navigation
- **Auto-discovery** — Detects running llama-server processes on startup and restores them to the database

## Quick Start

### Prerequisites

- Python 3.13+
- NVIDIA GPU + drivers (optional, for GPU metrics)
- [llama.cpp](https://github.com/ggml-org/llama.cpp) built (llama-server binary)

### Setup

```bash
# 1. Clone and create environment
git clone https://github.com/EgodPrime/llama-server-home.git
cd llama-server-home
make env

# 2. Configure
cp config.yaml.tmp config.yaml
# Edit config.yaml — set storage_dir, llama_path, etc.

# 3. Run
make serve
```

Open `http://localhost:8000` in your browser.

## Configuration

Edit `config.yaml` in the project root:

```yaml
db_dir: "db_dir"                        # SQLite data directory
storage_dir: "/path/to/ggufs"           # Directory containing GGUF models
llama_path: "/path/to/llama-server"     # llama-server binary path
maintenance_interval: 5                 # Instance health check interval (seconds)
metrics_interval: 5                     # System metrics collection interval (seconds)
max_metrics: 200                        # Keep last N metric records
host: "0.0.0.0"                         # Bind address
port: 8000                              # Web UI port
```

Values can reference environment variables using `${ENV_VAR}` syntax:

```yaml
db_dir: "${LSH_DB_DIR}"
storage_dir: "${LSH_STORAGE_DIR}"
llama_path: "${LSH_LLAMA_PATH}"
```

## API Endpoints

No authentication. All endpoints return JSON.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/instances` | List all instances |
| `GET` | `/api/instances/{name}` | Instance details |
| `GET` | `/api/instances/{name}/logs` | Instance logs (last 50 lines) |
| `GET` | `/api/instances/{name}/cmd` | Deploy command for this instance |
| `DELETE` | `/api/instances/{name}` | Delete instance (cascades to logs & tasks) |
| `POST` | `/api/tasks/create` | Create deploy/stop/resume task |
| `GET` | `/api/tasks` | List task history |
| `POST` | `/api/tasks/stop/{name}` | Queue stop task |
| `POST` | `/api/tasks/resume/{name}` | Queue resume task |
| `DELETE` | `/api/tasks/{task_id}` | Delete a task |
| `GET` | `/api/storage/list_root` | List GGUF files in storage root |
| `GET` | `/api/storage/list_dir/{path}` | List files in a subdirectory |
| `GET` | `/api/storage/list_models` | List detected model groups |
| `GET` | `/api/metrics?n=20` | System metrics (last N records) |
| `GET` | `/api/config` | Server configuration (storage_dir, llama_path) |

## Pages

| URL | Description |
|-----|-------------|
| `/` | Dashboard: instance counts, CPU/memory usage, recent instances |
| `/instances` | Full instance list with stop/resume/delete actions and logs |
| `/deploy` | Deploy a new model instance |
| `/tasks` | Task history (deploy/stop/resume) |
| `/storage` | Browse local model storage directory |
| `/metrics` | CPU / memory / GPU charts |

## Page Walkthrough

### Deploy

1. Select a model from storage (populated from `storage_dir`)
2. Choose a GPU (or CPU) from detected GPUs
3. Set host and port
4. Optionally add a multimodal projector (mmproj)
5. Add extra llama-server args (e.g. `-ngl -1 --ctx-size 4096`)
6. Preview the full command, then create the task

The Agent process queue, starts `llama-server` as a background subprocess, and tracks it by PID.

### Metrics

Live charts for:
- **CPU usage** — auto-scaled percentage
- **Memory** — percentage + absolute (used / total in GB)
- **GPU** — per-GPU memory usage and power draw (via NVML)
- **GPU temperature** — displayed in the latest snapshot card

### Storage

Breadcrumbs navigate `storage_dir`. `.gguf` files and directories are shown. Hidden files (starting with `.`) are filtered out. Click a directory to drill in; click "Root" to return.

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | FastAPI + uvicorn | Async, automatic OpenAPI docs, simple |
| Frontend | Jinja2 + Alpine.js + Tailwind (CDN) | No build step, minimal JS, responsive UI |
| Database | SQLite (WAL mode) | Zero config, single file, thread-safe with WAL |
| Process Mgmt | subprocess + psutil | Lightweight subprocess control + PID tracking |
| GPU Metrics | pynvml (NVML) | Official NVIDIA bindings |
| Logging | loguru | Structured, colored logs |

## Directory Structure

```
llama-server-home/
├── Makefile
├── config.yaml.tmp           # Template config (copy to config.yaml)
├── pyproject.toml
├── src/
│   ├── lsh/
│   │   ├── server/
│   │   │   ├── main.py       # FastAPI app, CLI entry, route mounting
│   │   │   ├── agent.py      # Background agent (health checks, metrics, tasks)
│   │   │   ├── api.py        # All API routes
│   │   │   ├── db.py         # SQLite connection, schema, CRUD
│   │   │   └── metrics.py    # CPU/GPU/memory measurement
│   │   └── utils/
│   │       ├── schema.py     # Pydantic models
│   │       └── path_helper.py
├── logs/                     # Instance logs (auto-created)
├── templates/                # Jinja2 HTML templates
│   ├── base.html
│   ├── home.html
│   ├── instances.html
│   ├── deploy.html
│   ├── tasks.html
│   ├── storage.html
│   └── metrics.html
└── .opencode/                # Project planning docs
```

## Development

```bash
# Install dev tools
uv pip install -e ".[dev]"

# Lint
ruff check src/ templates/
```

The `config.yaml` file is gitignored. Start with `cp config.yaml.tmp config.yaml` and edit.

## Database

SQLite is stored in `db_dir/` (defaults to project root). Schema is created automatically on first run. To reset:

```bash
rm -rf db_dir/lsh.db
```

The Agent auto-discovers running llama-server processes on startup and restores them in the database.

## License

MIT
