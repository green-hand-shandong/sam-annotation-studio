"""标注导出：COCO / YOLO-Segmentlation / labelme。

mask 统一从 PNG 解码，多边形用 cv2.findContours 提取最大轮廓。
"""
import base64
import io
import json
import os
import zipfile

import numpy as np


def mask_from_png_b64(b64: str) -> np.ndarray:
    from PIL import Image
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    return np.array(img) > 127


def mask_to_polygons(mask: np.ndarray, eps: float = 2.0) -> list[list[float]]:
    """mask -> COCO 风格多边形（最大轮廓顶点序列 [x1,y1,x2,y2,...]）。"""
    import cv2
    mask_u8 = (mask * 255).astype("uint8")
    contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
    if not contours:
        return []
    c = max(contours, key=cv2.contourArea)
    approx = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
    return [approx.reshape(-1).astype(float).tolist()]


def rle_counts(mask: np.ndarray) -> list[int]:
    """COCO 未压缩 RLE（列优先）。"""
    h, w = mask.shape
    flat = mask.flatten(order="F")
    counts, prev, run = [], 0, 0
    for v in flat:
        if v == prev:
            run += 1
        else:
            counts.append(run)
            run = 1
            prev = v
    counts.append(run)
    return counts


def build_coco(images: list[dict], annos: list[dict], categories: list[str]) -> dict:
    cats = [{"id": i + 1, "name": n} for i, n in enumerate(categories)]
    cat_name = {c["id"]: c["name"] for c in cats}
    out_images, out_annos = [], []
    img_ids = {}
    for im in images:
        img_ids[im["id"]] = len(out_images) + 1
        out_images.append({"id": img_ids[im["id"]], "file_name": im["filename"],
                           "width": im["width"], "height": im["height"]})
    aid = 1
    for a in annos:
        if not a.get("mask_png"):
            continue
        mask = mask_from_png_b64(a["mask_png"])
        poly = mask_to_polygons(mask)
        x, y, w, h = a["bbox"]
        out_annos.append({
            "id": aid, "image_id": img_ids[a["image_id"]],
            "category_id": a["category_id"] + 1,
            "bbox": [x, y, w, h], "area": float(a["area"]),
            "segmentation": poly, "iscrowd": 0,
            "score": a.get("score", 1.0),
            "attributes": {"source": a.get("source", "manual"),
                           "review": a.get("review_status", "")},
        })
        aid += 1
    return {"images": out_images, "annotations": out_annos, "categories": cats,
            "info": {"description": "SAM Annotation Studio export"}}


def build_yolo(images: list[dict], annos: list[dict], categories: list[str]) -> dict:
    """返回 {图片相对名: txt 内容} + classes.txt 内容。"""
    img_by_id = {im["id"]: im for im in images}
    per_image = {}
    for a in annos:
        if not a.get("mask_png"):
            continue
        im = img_by_id[a["image_id"]]
        mask = mask_from_png_b64(a["mask_png"])
        h, w = mask.shape
        poly = mask_to_polygons(mask)
        if not poly:
            continue
        pts = poly[0]
        norm = []
        for i in range(0, len(pts), 2):
            norm += [round(pts[i] / w, 6), round(pts[i + 1] / h, 6)]
        line = f"{a['category_id']} " + " ".join(str(v) for v in norm)
        per_image.setdefault(im["filename"], []).append(line)
    classes = "\n".join(categories)
    return {"labels": per_image, "classes": classes}


def build_labelme(images: list[dict], annos: list[dict], categories: list[str],
                  image_dir: str) -> list[dict]:
    img_by_id = {im["id"]: im for im in images}
    per_image = {}
    for a in annos:
        if not a.get("mask_png"):
            continue
        im = img_by_id[a["image_id"]]
        mask = mask_from_png_b64(a["mask_png"])
        poly = mask_to_polygons(mask)
        if not poly:
            continue
        pts = poly[0]
        shapes = per_image.setdefault(im["filename"], [])
        shapes.append({
            "label": categories[a["category_id"]],
            "points": [[pts[i], pts[i + 1]] for i in range(0, len(pts), 2)],
            "shape_type": "polygon", "score": a.get("score", 1.0),
            "source": a.get("source", "manual"),
        })
    out = []
    img_by_name = {im["filename"]: im for im in images}
    for fn, shapes in per_image.items():
        im = img_by_name[fn]
        out.append({"version": "1.0", "imagePath": fn, "imageData": None,
                    "imageHeight": im["height"], "imageWidth": im["width"],
                    "shapes": shapes})
    return out


def make_zip(path: str, files: dict[str, bytes]):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            if isinstance(data, str):
                data = data.encode()
            z.writestr(name, data)
