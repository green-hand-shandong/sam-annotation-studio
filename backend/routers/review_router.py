"""审核：待审核列表、通过/驳回。"""
from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..auth import require_role
from ..schemas import ReviewReq

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/pending")
def pending(task_id: int = None, user: dict = Depends(require_role("审核员", "管理员"))):
    con = db.connect()
    if task_id:
        rows = db.rows(con, """SELECT id,task_id,image_id,category_id,bbox,area,score,source,
                              review_status,annotated_by FROM annotations
                              WHERE review_status='待审核' AND task_id=? ORDER BY id""", (task_id,))
    else:
        rows = db.rows(con, """SELECT id,task_id,image_id,category_id,bbox,area,score,source,
                              review_status,annotated_by FROM annotations
                              WHERE review_status='待审核' ORDER BY id""")
    con.close()
    for r in rows:
        r["bbox"] = eval(r["bbox"]) if isinstance(r["bbox"], str) else r["bbox"]
    return rows


@router.post("/decide")
def decide(req: ReviewReq, user: dict = Depends(require_role("审核员", "管理员"))):
    status = "通过" if req.result == "通过" else "已驳回"
    con = db.connect()
    if con.execute("SELECT 1 FROM annotations WHERE id=?", (req.annotation_id,)).fetchone() is None:
        con.close()
        raise HTTPException(404, "标注不存在")
    if req.result == "驳回":
        con.execute("DELETE FROM annotations WHERE id=?", (req.annotation_id,))
    else:
        con.execute("UPDATE annotations SET review_status=?, reviewed_by=?, review_comment=? WHERE id=?",
                    (status, user["u"], req.comment, req.annotation_id))
    con.commit()
    con.close()
    db.log(user["u"], f"审核{req.result}", f"#{req.annotation_id} {req.comment}")
    return {"annotation_id": req.annotation_id, "result": req.result}
