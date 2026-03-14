# Llama-server-home

> 这个项目的目的是提供一个轻量级的基于llama.cpp中llama-server程序的模型部署和管理平台，支持多节点分布式部署、模型版本管理、自动化部署任务和实时监控等功能。

### 启动后端

```bash
uv run uvicorn src.lsh.controller.app:app --host 0.0.0.0 --port 8000
```