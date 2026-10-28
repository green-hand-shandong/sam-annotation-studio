"""登录与用户信息。"""
from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..auth import current_user, hash_password, make_token
from ..schemas import LoginReq

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(req: LoginReq):
    con = db.connect()
    row = con.execute("SELECT * FROM users WHERE username=?", (req.username,)).fetchone()
    con.close()
    if row is None or row["pw_hash"] != hash_password(req.password):
        raise HTTPException(401, "用户名或密码错误")
    db.log(req.username, "登录")
    return {"token": make_token(row["username"], row["role"]),
            "username": row["username"], "role": row["role"]}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user


@router.get("/users")
def list_users(user: dict = Depends(current_user)):
    con = db.connect()
    rows = db.rows(con, "SELECT id,username,role,created_at FROM users")
    con.close()
    return rows
