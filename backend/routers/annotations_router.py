"""标注：保存(SAM/手工)、查询、修改、删除；图片文件访问。"""
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from .. import config, db
from ..auth import current_user
from ..schemas import SaveAnnotationReq

router = APIRouter(prefix="/api", tags=["annotations"])


@router.get("/images/{image_id}/file")
def image_file(image_id: int, user: dict = Depends(current_user)):
    con = db.connect()
    row = con.execute("SELECT * FROM images WHERE id=?", (image_id,)).fetchone()
    con.close()
    if row is None or not os.path.exists(row["path"]):
        raise HTTPException(404, "图片不存在")
    return FileResponse(row["path"])


@router.post("/annotations")
def save_annotation(req: SaveAnnotationReq, user: dict = Depends(current_user)):
    con = db.connect()
    cur = con.execute(
        "INSERT INTO annotations(task_id,image_id,category_id,bbox,mask_png,area,score,"
        "source,status,review_status,annotated_by,updated_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (req.task_id, req.image_id, req.category_id, str(req.bbox), req.mask_png_b64,
         req.area, req.score, req.source, req.status, "待审核", user["u"], db.now()))
    con.commit()
    aid = cur.lastrowid
    con.close()
    db.log(user["u"], "保存标注", f"#{aid} task={req.task_id} img={req.image_id}")
    return {"id": aid}


@router.get("/annotations")
def list_annotations(task_id: int, image_id: int = None,
                     user: dict = Depends(current_user)):
    con = db.connect()
    if image_id:
        rows = db.rows(con, "SELECT * FROM annotations WHERE task_id=? AND image_id=?",
                       (task_id, image_id))
    else:
        rows = db.rows(con, "SELECT * FROM annotations WHERE task_id=?", (task_id,))
    con.close()
    for r in rows:
        r["bbox"] = eval(r["bbox"]) if isinstance(r["bbox"], str) else r["bbox"]
        r["has_mask"] = bool(r.pop("mask_png", None))
    return rows


@router.get("/annotations/{anno_id}/mask")
def annotation_mask(anno_id: int, user: dict = Depends(current_user)):
    import base64
    con = db.connect()
    row = con.execute("SELECT mask_png FROM annotations WHERE id=?", (anno_id,)).fetchone()
    con.close()
    if row is None or not row["mask_png"]:
        raise HTTPException(404, "无 mask")
    import io
    from PIL import Image
    img = Image.open(io.BytesIO(base64.b64decode(row["mask_png"])))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return FileResponse(buf, media_type="image/png")


@router.delete("/annotations/{anno_id}")
def delete_annotation(anno_id: int, user: dict = Depends(current_user)):
    con = db.connect()
    con.execute("DELETE FROM annotations WHERE id=?", (anno_id,))
    con.commit()
    con.close()
    db.log(user["u"], "删除标注", f"#{anno_id}")
    return {"deleted": anno_id}
