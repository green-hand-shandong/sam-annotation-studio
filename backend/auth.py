"""认证：口令哈希 + HMAC 签名 Token + 角色依赖。"""
import hashlib
import hmac
import json
import os
import time

from fastapi import Depends, Header, HTTPException

_SECRET = os.environ.get("APP_SECRET", "sam-annotation-studio-secret")
_EXPIRE = 7 * 24 * 3600


def hash_password(pw: str) -> str:
    return hashlib.sha256(f"samstudio:{pw}".encode()).hexdigest()


def make_token(username: str, role: str) -> str:
    payload = json.dumps({"u": username, "r": role, "t": time.time()})
    sig = hmac.new(_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return payload + "." + sig


def parse_token(token: str) -> dict:
    try:
        payload, sig = token.rsplit(".", 1)
        expect = hmac.new(_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        assert hmac.compare_digest(sig, expect)
        data = json.loads(payload)
        assert time.time() - data["t"] < _EXPIRE
        return data
    except Exception:  # noqa: BLE001
        raise HTTPException(401, "登录已失效，请重新登录")


def current_user(authorization: str = Header(default=""), token: str = "") -> dict:
    """支持 Header(Authorization: Bearer xxx) 与 ?token=xxx 两种方式。

    后者用于 <img src> / 新窗口下载等无法携带 Header 的场景。
    """
    if token and not authorization:
        return parse_token(token)
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    return parse_token(authorization[7:])


def require_role(*roles):
    def dep(user: dict = Depends(current_user)) -> dict:
        if user["r"] not in roles:
            raise HTTPException(403, f"需要角色: {'/'.join(roles)}")
        return user
    return dep
