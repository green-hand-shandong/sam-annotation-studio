"""应用入口：FastAPI 装配 + 静态前端 + 启动初始化。

运行: uvicorn backend.app:app --host 0.0.0.0 --port 8100
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, db
from .routers import (annotations_router, auth_router, datasets_router,
                      export_router, inference_router, review_router,
                      system_router, tasks_router)

db.init()

app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

for r in (auth_router, datasets_router, tasks_router, annotations_router,
          inference_router, review_router, export_router, system_router):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": config.APP_NAME, "version": config.APP_VERSION}


# 前端静态资源（生产一体机部署：单进程同时服务页面与接口）
_FRONTEND = os.path.join(config.BASE_DIR, "frontend-dist")  # React 构建产物
if os.path.isdir(_FRONTEND):
    app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="frontend")
