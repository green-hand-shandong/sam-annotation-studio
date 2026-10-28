"""全局配置：路径、模型、版本。"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
DATASET_DIR = os.path.join(DATA_DIR, "datasets")
EXPORT_DIR = os.path.join(DATA_DIR, "exports")
DB_PATH = os.path.join(DATA_DIR, "annotations.sqlite")

# 模型目录（一体机内路径）
MODEL_DIRS = {
    "sam": os.environ.get("SAM_DIR", "/data1/models/SAM-vit-h"),      # 原版 SAM ViT-H（点/框）
    "sam3": os.environ.get("SAM3_DIR", "/data1/models/SAM3"),         # SAM3 detector（文本预标注）
}

# 交互分割模型元信息（前端展示用）
INTERACTIVE_MODELS = {
    "sam": {"name": "SAM ViT-H", "prompt": ["point", "box"], "desc": "点选前景/背景或框选目标"},
}

DEVICE = os.environ.get("NPU_DEVICE", "npu")
APP_VERSION = "V1.0"
APP_NAME = "基于昇腾一体机的图像分割智能标注与质量管理系统"

for d in (DATA_DIR, DATASET_DIR, EXPORT_DIR):
    os.makedirs(d, exist_ok=True)
