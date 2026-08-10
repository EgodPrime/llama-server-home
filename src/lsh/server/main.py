from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from lsh.server.agent import Agent
from lsh.server.db import Database, get_db, load_config
from lsh.server import api as api_routes
from lsh.utils.path_helper import PROJECT_ROOT, WEB_FILES_DIR


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    cfg = load_config()
    db_dir = cfg.get("db_dir", "db_dir")
    db = Database(db_dir)
    get_db.__globals__["_db_instance"] = db  # set singleton

    agent = Agent(
        db=db,
        llama_path=cfg["llama_path"],
        storage_dir=cfg["storage_dir"],
        maintenance_interval=int(cfg.get("maintenance_interval", 5)),
        metrics_interval=int(cfg.get("metrics_interval", 5)),
        max_metrics=int(cfg.get("max_metrics", 200)),
        host=cfg.get("host", "127.0.0.1"),
    )
    agent.start()
    db.migrate_instance_names()
    db.migrate_log_file_column()
    app.state.db = db
    app.state.agent = agent
    logger.info(f"llama-server-home started (config: {cfg['host']}:{cfg['port']})")

    yield

    logger.info("Shutting down...")
    agent.stop()
    db.close()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(title="llama-server-home", lifespan=lifespan)

    # Include API routes
    app.include_router(api_routes.api_router)

    # Jinja2 templates
    templates_dir = PROJECT_ROOT / "templates"
    if templates_dir.exists():
        templates = Jinja2Templates(directory=str(templates_dir))

        @app.get("/", response_class=HTMLResponse)
        async def home(request: Request, db: Database = Depends(get_db)):
            instances = db.list_instances()
            metrics = db.list_metrics(1)
            return templates.TemplateResponse("home.html", {
                "request": request,
                "instances": instances,
                "running_count": len([i for i in instances if i.get("status") == "RUNNING"]),
                "cpu_usage": metrics[0]["cpu_usage"] if metrics else 0,
                "mem_usage": metrics[0]["mem_usage_pct"] if metrics else 0,
            })

        @app.get("/instances", response_class=HTMLResponse)
        async def instances(request: Request):
            return templates.TemplateResponse("instances.html", {"request": request})

        @app.get("/deploy", response_class=HTMLResponse)
        async def deploy(request: Request):
            return templates.TemplateResponse("deploy.html", {"request": request})

        @app.get("/tasks", response_class=HTMLResponse)
        async def tasks(request: Request):
            return templates.TemplateResponse("tasks.html", {"request": request})

        @app.get("/storage", response_class=HTMLResponse)
        async def storage(request: Request):
            return templates.TemplateResponse("storage.html", {"request": request})


        @app.get("/metrics", response_class=HTMLResponse)
        async def metrics(request: Request):
            return templates.TemplateResponse("metrics.html", {"request": request})
    else:
        logger.warning(f"templates directory not found at {templates_dir}.")

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()


def cli_main():
    cfg = load_config()
    host = cfg.get("host", "0.0.0.0")
    port = int(cfg.get("port", 8000))
    logger.info(f"Starting llama-server-home on {host}:{port}")
    uvicorn.run("lsh.server.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    cli_main()
