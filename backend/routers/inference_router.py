"""推理接口：交互分割（SAM）与批量预标注（SAM3）。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from PIL import Image

from .. import config, db
from ..auth import current_user
from ..schemas import PreannotateReq, SegmentReq
from ..services import inference

router = APIRouter(prefix="/api/inference", tags=["inference"])


def _load_image(image_id: int) -> tuple:
    con = db.connect()
    row = con.execute("SELECT * FROM images WHERE id=?", (image_id,)).fetchone()
    con.close()
    if row is None or not os.path.exists(row["path"]):
        raise HTTPException(404, "图片不存在")
    img = Image.open(row["path"]).convert("RGB")
    return img, row


import os  # noqa: E402


@router.get("/models")
def list_models(user: dict = Depends(current_user)):
    return {"interactive": config.INTERACTIVE_MODELS,
            "preannotate": {"name": "SAM3", "prompt": ["text"]}}


@router.post("/segment")
async def segment(req: SegmentReq, user: dict = Depends(current_user)):
    if not req.points and not req.boxes:
        raise HTTPException(400, "至少提供一个点或一个框")
    if not inference.ModelManager.npu_ready():
        raise HTTPException(503, "NPU 不可用，请检查一体机设备")
    img, _ = await run_in_threadpool(_load_image, req.image_id)

    def _run():
        import numpy as np
        return inference.segment(np.array(img), req)

    result = await run_in_threadpool(_run)
    db.log(user["u"], "交互分割", f"img={req.image_id} model={req.model} score={result['score']}")
    return result


@router.post("/preannotate/{task_id}")
async def preannotate(task_id: int, req: PreannotateReq,
                      user: dict = Depends(current_user)):
    """SAM3 文本预标注：对任务内前 limit 张未标注图自动生成标注（source=sam3）。"""
    if not inference.ModelManager.npu_ready():
        raise HTTPException(503, "NPU 不可用")
    con = db.connect()
    task = con.execute("SELECT categories FROM tasks WHERE id=?", (task_id,)).fetchone()
    if task is None:
        con.close()
        raise HTTPException(404, "任务不存在")
    rows = db.rows(con, """
        SELECT i.* FROM tasks t JOIN images i ON i.dataset_id=t.dataset_id
        LEFT JOIN annotations a ON a.image_id=i.id AND a.task_id=t.id
        WHERE t.id=? GROUP BY i.id HAVING COUNT(a.id)=0 LIMIT ?""", (task_id, req.limit))
    con.close()

    done = 0

    def _run():
        nonlocal done
        import numpy as np
        con = db.connect()
        for r in rows:
            if not os.path.exists(r["path"]):
                continue
            img = np.array(Image.open(r["path"]).convert("RGB"))
            for det in inference.preannotate(img, req.text, req.score_threshold):
                con.execute(
                    "INSERT INTO annotations(task_id,image_id,category_id,bbox,mask_png,"
                    "area,score,source,status,review_status,annotated_by,updated_at)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (task_id, r["id"], 0, str(det["bbox"]), det["mask_png_b64"],
                     det["area"], det["score"], "sam3", "已完成", "待复核",
                     user["u"], db.now()))
                done += 1
        con.commit()
        con.close()

    await run_in_threadpool(_run)
    db.log(user["u"], "批量预标注", f"task={task_id} text={req.text} 生成 {done} 条")
    return {"task_id": task_id, "text": req.text, "generated": done, "images": len(rows)}
