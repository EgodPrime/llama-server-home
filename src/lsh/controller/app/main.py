from fastapi import FastAPI

from .instance_groups import router as instance_groups_router
from .instances import router as instances_router
from .nfs import router as nfs_router
from .nodes import router as nodes_router
from .tasks import router as tasks_router
from .user import router as user_router
from .utils import lifespan

app = FastAPI(lifespan=lifespan)

app.include_router(user_router)
app.include_router(nodes_router)
app.include_router(instances_router)
app.include_router(nfs_router)
app.include_router(instance_groups_router)
app.include_router(tasks_router)


# Optionally, add root endpoint or health check
@app.get("/")
def root():
    return {"message": "Llama Server Home API"}
