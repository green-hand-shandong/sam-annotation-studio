"""后端单元测试（无需 NPU）：认证、任务流、标注存储、导出格式。"""
import base64
import io
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATA_DIR"] = "/tmp/sam_studio_test_data"

from backend import config, db  # noqa: E402
from backend.services import exporters  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _init_db():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    db.init()


def _fake_mask_b64(h=64, w=64, box=(10, 10, 40, 40)) -> str:
    """生成一个方形 mask 的 PNG base64。"""
    from PIL import Image
    m = np.zeros((h, w), dtype="uint8")
    x, y, w2, h2 = box
    m[y:y + h2, x:x + w2] = 255
    buf = io.BytesIO()
    Image.fromarray(m, mode="L").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class TestAuth:
    def test_password_hash_deterministic(self):
        from backend.auth import hash_password
        assert hash_password("a") == hash_password("a")
        assert hash_password("a") != hash_password("b")

    def test_token_roundtrip(self):
        from fastapi import HTTPException
        from backend.auth import make_token, parse_token
        t = make_token("alice", "标注员")
        assert parse_token(t)["u"] == "alice"
        with pytest.raises(HTTPException):
            parse_token(t + "x")


class TestTaskFlow:
    def test_status_flow(self):
        from backend.routers.tasks_router import STATUS_FLOW
        assert "待审核" in STATUS_FLOW["进行中"]
        assert "已完成" in STATUS_FLOW["待审核"]
        assert "进行中" in STATUS_FLOW["待审核"]
        # 已完成 不能直接跳到 待审核
        assert "待审核" not in STATUS_FLOW["已完成"]


class TestExporters:
    def _sample(self):
        images = [{"id": 1, "filename": "a.jpg", "width": 64, "height": 64}]
        annos = [{"id": 1, "image_id": 1, "category_id": 0, "bbox": [10, 10, 31, 31],
                  "area": 961, "score": 0.9, "source": "sam", "review_status": "通过",
                  "mask_png": _fake_mask_b64()}]
        return images, annos, ["object"]

    def test_coco_structure(self):
        images, annos, cats = self._sample()
        coco = exporters.build_coco(images, annos, cats)
        assert len(coco["categories"]) == 1 and coco["categories"][0]["name"] == "object"
        assert len(coco["annotations"]) == 1
        a = coco["annotations"][0]
        assert a["image_id"] == 1 and a["category_id"] == 1
        assert a["bbox"] == [10, 10, 31, 31]
        assert isinstance(a["segmentation"], list) and a["segmentation"]
        # 多边形点在图像范围内
        for v in a["segmentation"][0]:
            assert -1 <= v <= 65

    def test_rle_counts_sum(self):
        mask = exporters.mask_from_png_b64(_fake_mask_b64())
        counts = exporters.rle_counts(mask)
        assert sum(counts) == mask.size

    def test_yolo_normalized(self):
        images, annos, cats = self._sample()
        yolo = exporters.build_yolo(images, annos, cats)
        assert yolo["classes"] == "object"
        line = yolo["labels"]["a.jpg"][0]
        parts = line.split()
        assert parts[0] == "0"
        coords = [float(v) for v in parts[1:]]
        assert all(0 <= v <= 1.001 for v in coords), "YOLO 坐标应归一化"
        assert len(coords) >= 6 and len(coords) % 2 == 0

    def test_labelme_shapes(self):
        images, annos, cats = self._sample()
        items = exporters.build_labelme(images, annos, cats, "")
        assert len(items) == 1 and items[0]["imagePath"] == "a.jpg"
        assert items[0]["shapes"][0]["label"] == "object"

    def test_zip_roundtrip(self, tmp_path):
        p = str(tmp_path / "x.zip")
        exporters.make_zip(p, {"a.txt": "hello", "b.json": json.dumps({"k": 1})})
        import zipfile
        with zipfile.ZipFile(p) as z:
            assert z.read("a.txt").decode() == "hello"


class TestDb:
    def test_seed_users(self):
        con = db.connect()
        rows = db.rows(con, "SELECT username, role FROM users")
        con.close()
        roles = {r["username"]: r["role"] for r in rows}
        assert roles.get("admin") == "管理员"
        assert "标注员" in roles.values() and "审核员" in roles.values()

    def test_annotation_crud(self):
        con = db.connect()
        con.execute("INSERT INTO datasets(name,created_by,created_at) VALUES('t','u',0)")
        ds = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        con.execute("INSERT INTO images(dataset_id,filename,path,width,height)"
                    " VALUES(?,?,?,?,?)", (ds, "x.jpg", "/tmp/x.jpg", 64, 64))
        im = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        con.execute("INSERT INTO annotations(task_id,image_id,category_id,bbox,mask_png,"
                    "area,score,source,updated_at) VALUES(1,?,0,'[1,2,3,4]','x',10,0.9,'sam',0)", (im,))
        n = con.execute("SELECT COUNT(*) FROM annotations").fetchone()[0]
        con.commit()
        con.close()
        assert n >= 1
