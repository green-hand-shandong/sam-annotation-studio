"""系统：看板统计、模型/设备信息、操作日志。"""
from fastapi import APIRouter, Depends

from .. import config, db
from ..auth import current_user
from ..services import inference

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/dashboard")
def dashboard(user: dict = Depends(current_user)):
    con = db.connect()
    c = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    stats = {
        "datasets": c("SELECT COUNT(*) FROM datasets"),
        "images": c("SELECT COUNT(*) FROM images"),
        "tasks": c("SELECT COUNT(*) FROM tasks"),
        "annotations": c("SELECT COUNT(*) FROM annotations"),
        "pending_review": c("SELECT COUNT(*) FROM annotations WHERE review_status='待审核'"),
        "passed": c("SELECT COUNT(*) FROM annotations WHERE review_status='通过'"),
        "rejected": c("SELECT COUNT(*) FROM exports") and c(
            "SELECT COUNT(*) FROM logs WHERE action='审核驳回'"),
        "exports": c("SELECT COUNT(*) FROM exports"),
    }
    by_source = db.rows(con, """SELECT source, COUNT(*) count FROM annotations
                               GROUP BY source""")
    by_task = db.rows(con, """SELECT t.id, t.name, t.status, COUNT(a.id) annos FROM tasks t
                             LEFT JOIN annotations a ON a.task_id=t.id
                             GROUP BY t.id ORDER BY t.id DESC LIMIT 8""")
    recent_logs = db.rows(con, "SELECT user,action,detail,created_at FROM logs"
                               " ORDER BY id DESC LIMIT 15")
    con.close()
    return {"stats": stats, "by_source": by_source, "by_task": by_task,
            "recent_logs": recent_logs}


@router.get("/info")
def info(user: dict = Depends(current_user)):
    return {"app": config.APP_NAME, "version": config.APP_VERSION,
            "npu": inference.system_info()}
