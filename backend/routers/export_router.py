"""导出：COCO / YOLO-Seg / labelme 打包下载。"""
import json
import os
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from .. import config, db
from ..auth import current_user
from ..schemas import ExportReq
from ..services import exporters

router = APIRouter(prefix="/api/export", tags=["export"])


def json_loads(s):
    return json.loads(s) if s else []


@router.post("/{task_id}")
def export_task(task_id: int, req: ExportReq, user: dict = Depends(current_user)):
    con = db.connect()
    task = con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if task is None:
        con.close()
        raise HTTPException(404, "任务不存在")
    images = db.rows(con, """
        SELECT DISTINCT i.* FROM annotations a JOIN images i ON i.id=a.image_id
        WHERE a.task_id=?""", (task_id,))
    annos = db.rows(con, "SELECT * FROM annotations WHERE task_id=?", (task_id,))
    con.close()
    if not annos:
        raise HTTPException(400, "该任务暂无标注")
    categories = json_loads(task["categories"])

    for a in annos:
        a["bbox"] = eval(a["bbox"]) if isinstance(a["bbox"], str) else a["bbox"]

    stamp = time.strftime("%Y%m%d_%H%M%S")
    fname = f"task{task_id}_{req.format}_{stamp}.zip"
    path = os.path.join(config.EXPORT_DIR, fname)

    if req.format == "coco":
        coco = exporters.build_coco(images, annos, categories)
        exporters.make_zip(path, {"annotations.json": json.dumps(coco, ensure_ascii=False)})
        count = len(coco["annotations"])
    elif req.format == "yolo":
        yolo = exporters.build_yolo(images, annos, categories)
        files = {"classes.txt": yolo["classes"]}
        for fn, lines in yolo["labels"].items():
            files[f"labels/{os.path.splitext(fn)[0]}.txt"] = "\n".join(lines)
        exporters.make_zip(path, files)
        count = len(yolo["labels"])
    else:  # labelme
        items = exporters.build_labelme(images, annos, categories, "")
        exporters.make_zip(path, {f"{it['imagePath']}.json": json.dumps(it, ensure_ascii=False)
                                  for it in items})
        count = len(items)

    con = db.connect()
    con.execute("INSERT INTO exports(task_id,format,path,count,created_by,created_at)"
                " VALUES(?,?,?,?,?,?)",
                (task_id, req.format, path, count, user["u"], db.now()))
    con.commit()
    con.close()
    db.log(user["u"], "导出", f"task={task_id} {req.format} {count} 条")
    return {"file": fname, "format": req.format, "count": count,
            "download": f"/api/export/download/{fname}"}


@router.get("/download/{fname}")
def download(fname: str, user: dict = Depends(current_user)):
    if "/" in fname or "\\" in fname or ".." in fname:
        raise HTTPException(400, "非法文件名")
    path = os.path.join(config.EXPORT_DIR, fname)
    if not os.path.exists(path):
        raise HTTPException(404, "文件不存在")
    return FileResponse(path, filename=fname)


@router.get("/history")
def history(user: dict = Depends(current_user)):
    con = db.connect()
    rows = db.rows(con, "SELECT id,task_id,format,count,created_by,created_at,path FROM exports ORDER BY id DESC")
    con.close()
    for r in rows:
        r["file"] = os.path.basename(r.pop("path"))
    return rows
