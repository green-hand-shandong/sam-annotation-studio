"""标注任务：创建/列表/详情/状态流转/类别管理。"""
from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..auth import current_user
from ..schemas import TaskReq

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

STATUS_FLOW = {"进行中": ["待审核", "已完成"],
               "待审核": ["进行中", "已完成"],
               "已完成": ["进行中"]}


def _task_dict(row) -> dict:
    d = db.rowdict(row)
    d["categories"] = json_loads(d.get("categories", "[]"))
    return d


def json_loads(s):
    import json
    return json.loads(s) if s else []


@router.post("")
def create_task(req: TaskReq, user: dict = Depends(current_user)):
    con = db.connect()
    if con.execute("SELECT 1 FROM datasets WHERE id=?", (req.dataset_id,)).fetchone() is None:
        con.close()
        raise HTTPException(404, "数据集不存在")
    import json
    cur = con.execute(
        "INSERT INTO tasks(name,dataset_id,categories,assignee,created_by,created_at)"
        " VALUES(?,?,?,?,?,?)",
        (req.name, req.dataset_id, json.dumps(req.categories, ensure_ascii=False),
         req.assignee or user["u"], user["u"], db.now()))
    con.commit()
    tid = cur.lastrowid
    con.close()
    db.log(user["u"], "创建任务", f"{req.name} #{tid}")
    return {"id": tid, **req.dict()}


@router.get("")
def list_tasks(user: dict = Depends(current_user)):
    con = db.connect()
    rows = db.rows(con, """
        SELECT t.*, d.name dataset_name, COUNT(DISTINCT i.id) image_count,
               COUNT(a.id) anno_count,
               SUM(CASE WHEN a.review_status='通过' THEN 1 ELSE 0 END) passed_count
        FROM tasks t
        JOIN datasets d ON d.id=t.dataset_id
        LEFT JOIN images i ON i.dataset_id=t.dataset_id
        LEFT JOIN annotations a ON a.task_id=t.id
        GROUP BY t.id ORDER BY t.id DESC""")
    con.close()
    for r in rows:
        r["categories"] = json_loads(r.get("categories", "[]"))
    return rows


@router.get("/{task_id}")
def task_detail(task_id: int, user: dict = Depends(current_user)):
    con = db.connect()
    row = con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if row is None:
        con.close()
        raise HTTPException(404, "任务不存在")
    d = _task_dict(row)
    d["dataset_name"] = con.execute(
        "SELECT name FROM datasets WHERE id=?", (d["dataset_id"],)).fetchone()["name"]
    con.close()
    return d


@router.post("/{task_id}/status")
def set_status(task_id: int, status: str, user: dict = Depends(current_user)):
    con = db.connect()
    row = con.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
    if row is None:
        con.close()
        raise HTTPException(404, "任务不存在")
    if status not in STATUS_FLOW.get(row["status"], []):
        con.close()
        raise HTTPException(400, f"不允许 {row['status']} -> {status}")
    con.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    con.commit()
    con.close()
    db.log(user["u"], "任务状态", f"#{task_id} -> {status}")
    return {"id": task_id, "status": status}


@router.put("/{task_id}/categories")
def set_categories(task_id: int, categories: list[str], user: dict = Depends(current_user)):
    import json
    con = db.connect()
    con.execute("UPDATE tasks SET categories=? WHERE id=?",
                (json.dumps(categories, ensure_ascii=False), task_id))
    con.commit()
    con.close()
    return {"id": task_id, "categories": categories}


@router.get("/{task_id}/images")
def task_images(task_id: int, user: dict = Depends(current_user)):
    """任务图片列表 + 每张图的标注数（工作台左列表用）。"""
    con = db.connect()
    rows = db.rows(con, """
        SELECT i.*, COUNT(a.id) anno_count FROM tasks t
        JOIN images i ON i.dataset_id=t.dataset_id
        LEFT JOIN annotations a ON a.image_id=i.id AND a.task_id=t.id
        WHERE t.id=? GROUP BY i.id ORDER BY i.id""", (task_id,))
    con.close()
    return rows
