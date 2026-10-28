"""Pydantic 请求模型。"""
from typing import Literal, Optional

from pydantic import BaseModel


class LoginReq(BaseModel):
    username: str
    password: str


class DatasetReq(BaseModel):
    name: str
    description: str = ""


class ImportPathReq(BaseModel):
    path: str  # 一体机本地目录（数据不出域导入）


class TaskReq(BaseModel):
    name: str
    dataset_id: int
    categories: list[str] = []
    assignee: str = ""


class SegmentReq(BaseModel):
    image_id: int
    model: Literal["sam"] = "sam"
    points: list[list[float]] = []        # [[x,y],...] 原图像素坐标
    point_labels: list[int] = []          # 1=前景 0=背景
    boxes: list[list[float]] = []         # [[x1,y1,x2,y2],...] 原图像素坐标


class SaveAnnotationReq(BaseModel):
    task_id: int
    image_id: int
    category_id: int
    bbox: list[float]           # [x,y,w,h] 原图像素坐标
    mask_png_b64: str           # 单通道 PNG base64（原图尺寸）
    area: int
    score: float = 1.0
    source: str = "manual"
    status: str = "已完成"


class ReviewReq(BaseModel):
    annotation_id: int
    result: Literal["通过", "驳回"]
    comment: str = ""


class PreannotateReq(BaseModel):
    text: str
    limit: int = 10
    score_threshold: float = 0.5


class ExportReq(BaseModel):
    format: Literal["coco", "yolo", "labelme"] = "coco"
