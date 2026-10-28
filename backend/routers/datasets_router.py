"""数据集管理：创建、上传(zip/多文件)、服务器路径导入、列表、图片查询。"""
import os
import shutil
import zipfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image

from .. import config, db
from ..auth import current_user
from ..schemas import DatasetReq, ImportPathReq

router = APIRouter(prefix="/api/datasets", tags=["datasets"])
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def _read_size(path):
    try:
        with Image.open(path) as im:
            return im.size  # (w, h)
    except Exception:  # noqa: BLE001
        return None


def _register_image(con, dataset_id: int, fname: str, path: str):
    size = _read_size(path)
    if size is None:
        return False
    con.execute(
        "INSERT INTO images(dataset_id,filename,path,width,height) VALUES(?,?,?,?,?)",
        (dataset_id, fname, path, size[0], size[1]))
    return True


@router.post("")
def create_dataset(req: DatasetReq, user: dict = Depends(current_user)):
    con = db.connect()
    cur = con.execute("INSERT INTO datasets(name,description,created_by,created_at) VALUES(?,?,?,?)",
                      (req.name, req.description, user["u"], db.now()))
    con.commit()
    ds_id = cur.lastrowid
    out = {"id": ds_id, **req.dict()}
    con.close()
    db.log(user["u"], "创建数据集", f"{req.name} #{ds_id}")
    return out


@router.get("")
def list_datasets(user: dict = Depends(current_user)):
    con = db.connect()
    rows = db.rows(con, """
        SELECT d.*, COUNT(i.id) image_count FROM datasets d
        LEFT JOIN images i ON i.dataset_id=d.id GROUP BY d.id ORDER BY d.id DESC""")
    con.close()
    return rows


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: int, user: dict = Depends(current_user)):
    con = db.connect()
    n = con.execute("SELECT COUNT(*) c FROM images WHERE dataset_id=?", (dataset_id,)).fetchone()["c"]
    con.execute("DELETE FROM datasets WHERE id=?", (dataset_id,))
    con.execute("DELETE FROM images WHERE dataset_id=?", (dataset_id,))
    con.commit()
    con.close()
    db.log(user["u"], "删除数据集", f"#{dataset_id} ({n} 张图)")
    return {"deleted": dataset_id, "images_removed": n}


@router.post("/{dataset_id}/upload")
async def upload_files(dataset_id: int, files: list[UploadFile],
                       user: dict = Depends(current_user)):
    """上传 zip 包或多张图片。"""
    dest = os.path.join(config.DATASET_DIR, str(dataset_id))
    os.makedirs(dest, exist_ok=True)
    added = skipped = 0

    def _handle():
        nonlocal added, skipped
        con = db.connect()
        for f in files:
            suffix = os.path.splitext(f.filename or "")[1].lower()
            if suffix == ".zip":
                tmp = os.path.join(dest, "_tmp.zip")
                with open(tmp, "wb") as fh:
                    shutil.copyfileobj(f.file, fh)
                with zipfile.ZipFile(tmp) as z:
                    for info in z.infolist():
                        if info.is_dir():
                            continue
                        ext = os.path.splitext(info.filename)[1].lower()
                        if ext not in IMG_EXTS:
                            continue
                        out = os.path.join(dest, os.path.basename(info.filename))
                        with open(out, "wb") as fh:
                            fh.write(z.read(info))
                        added += _register_image(con, dataset_id,
                                                 os.path.basename(info.filename), out)
            elif suffix in IMG_EXTS:
                out = os.path.join(dest, os.path.basename(f.filename))
                with open(out, "wb") as fh:
                    shutil.copyfileobj(f.file, fh)
                added += _register_image(con, dataset_id, os.path.basename(f.filename), out)
            else:
                skipped += 1
        con.commit()
        con.close()

    await run_in_threadpool(_handle)
    return {"added": added, "skipped": skipped}


@router.post("/{dataset_id}/import_path")
def import_from_path(dataset_id: int, req: ImportPathReq,
                     user: dict = Depends(current_user)):
    """从一体机本地目录导入（大数据集免上传，数据不出域）。"""
    root = req.path
    if not os.path.isdir(root):
        raise HTTPException(404, f"目录不存在: {root}")
    dest = os.path.join(config.DATASET_DIR, str(dataset_id))
    os.makedirs(dest, exist_ok=True)
    added = 0
    con = db.connect()
    for base, _, names in os.walk(root):
        for n in names:
            if os.path.splitext(n)[1].lower() not in IMG_EXTS:
                continue
            src = os.path.join(base, n)
            out = os.path.join(dest, n)
            if not os.path.exists(out):
                shutil.copy2(src, out)
            added += _register_image(con, dataset_id, n, out)
    con.commit()
    con.close()
    db.log(user["u"], "路径导入", f"{root} -> #{dataset_id} ({added} 张)")
    return {"added": added}


@router.get("/{dataset_id}/images")
def list_images(dataset_id: int, user: dict = Depends(current_user)):
    con = db.connect()
    rows = db.rows(con, "SELECT * FROM images WHERE dataset_id=? ORDER BY id", (dataset_id,))
    con.close()
    return rows
