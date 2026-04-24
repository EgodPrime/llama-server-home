import time

import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from lsh.controller.lib import get_controller
from lsh.utils.schema import User

from .utils import hash_passwd, verify_passwd

router = APIRouter(prefix="/user", tags=["user"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register_user(request: LoginRequest):
    username = request.username
    password = request.password
    col = get_controller().db["users"]
    if col.find_one({"username": username}):
        raise HTTPException(status_code=409, detail="Username already exists")
    password_hash = hash_passwd(password)
    user = User(username=username, password_hash=password_hash)
    col.insert_one(user.model_dump())
    return {"message": f"User {username} registered successfully"}


@router.post("/login")
async def login_user(request: LoginRequest):
    username = request.username
    password = request.password
    col = get_controller().db["users"]
    user_doc = col.find_one({"username": username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="Invalid username or password")
    user = User.model_validate(user_doc)
    if not verify_passwd(password, user.password_hash):
        raise HTTPException(status_code=404, detail="Invalid username or password")
    col.update_one({"username": username}, {"$set": {"last_login_at": time.time()}})
    payload = {"username": username, "exp": time.time() + 3600}
    token = jwt.encode(payload, get_controller().jwt_secret, algorithm="HS256")
    return {"token": token}


@router.get("/profile")
async def get_user_profile(request: Request):
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
    return user.model_dump()
