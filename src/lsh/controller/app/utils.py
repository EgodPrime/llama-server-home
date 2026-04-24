# Lifespan context manager
import threading
from contextlib import asynccontextmanager

import bcrypt
import jwt
from fastapi import HTTPException, Request

from lsh.controller.lib import get_controller
from lsh.utils.schema import User


def hash_passwd(password: str) -> bytes:
    passwdb = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(passwdb, salt)
    return hashed


def verify_passwd(password: str, hashed: bytes) -> bool:
    passwdb = password.encode("utf-8")
    return bcrypt.checkpw(passwdb, hashed)


async def get_current_user(request: Request) -> User:
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token is missing")
    token = token.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, get_controller().jwt_secret, algorithms=["HS256"])
        username = payload.get("username")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token: username missing")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    col = get_controller().db["users"]
    user_doc = col.find_one({"username": username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user = User.model_validate(user_doc)
    return user


async def get_current_user_name(request: Request) -> str:
    user = await get_current_user(request)
    return user.username


@asynccontextmanager
async def lifespan(app):
    print("[APP] 启动生命周期...")
    ctrl = get_controller()
    th = threading.Thread(target=ctrl.node_discovery_and_check_loop, daemon=True)
    th.start()
    print(f"[APP] 已启动线程，ID: {th.ident}")
    yield
