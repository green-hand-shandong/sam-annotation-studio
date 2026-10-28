"""NPU 推理服务：SAM / MedSAM 交互分割 + SAM3 文本预标注。

复用 ascend310p_compat 兼容层（310P 上 SDPA/interpolate/activations 的补丁），
模型按需懒加载并常驻显存。
"""
import base64
import io
import os
import sys
import threading

import numpy as np
import torch

from .. import config

_models = {}
_lock = threading.Lock()


_COMPAT_DIRS = [
    "/workspace",                                   # 容器内
    "/data2/gxw/sam31-310p-adapt",                  # 宿主机直接部署
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
]


def _patch():
    """导入兼容层并打齐补丁（幂等）。"""
    for p in _COMPAT_DIRS:
        if p not in sys.path and os.path.isdir(os.path.join(p, "ascend310p_compat")):
            sys.path.insert(0, p)
    import ascend310p_compat
    ascend310p_compat.patch_all(verbose=False)
    return ascend310p_compat


class ModelManager:
    @staticmethod
    def npu_ready() -> bool:
        try:
            import torch_npu  # noqa: F401
            return torch.npu.device_count() > 0
        except Exception:  # noqa: BLE001
            return False

    @classmethod
    def get_interactive(cls, kind: str):
        """加载 SAM / MedSAM 交互分割模型。"""
        assert kind in config.INTERACTIVE_MODELS, f"未知模型 {kind}"
        with _lock:
            if kind not in _models:
                _patch()
                from transformers import SamModel
                m = SamModel.from_pretrained(
                    config.MODEL_DIRS[kind], attn_implementation="eager").eval().to(config.DEVICE)
                _models[kind] = m
            return _models[kind]

    @classmethod
    def get_sam3(cls):
        with _lock:
            if "sam3" not in _models:
                _patch()
                from transformers.models.sam3_video.modeling_sam3_video import Sam3VideoModel
                vm = Sam3VideoModel.from_pretrained(
                    config.MODEL_DIRS["sam3"], attn_implementation="eager").eval()
                _models["sam3"] = vm.detector_model
            return _models["sam3"]


def _mask_to_png_b64(mask: np.ndarray) -> str:
    """bool mask -> 单通道 PNG base64。"""
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray((mask * 255).astype("uint8"), mode="L").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _bbox_area(mask: np.ndarray):
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return [0, 0, 0, 0], 0
    x1, x2, y1, y2 = xs.min(), xs.max(), ys.min(), ys.max()
    return [float(x1), float(y1), float(x2 - x1 + 1), float(y2 - y1 + 1)], int(mask.sum())


def segment(image: np.ndarray, req) -> dict:
    """交互分割：点/框提示 -> 最优 mask（原图分辨率 PNG b64）+ bbox + 分数。"""
    from transformers import SamProcessor

    kind = req.model
    model = ModelManager.get_interactive(kind)
    processor = SamProcessor.from_pretrained(config.MODEL_DIRS[kind])

    kwargs = {"images": image, "return_tensors": "pt"}
    if req.points:
        kwargs["input_points"] = [[req.points]]
        kwargs["input_labels"] = [[req.point_labels]]
    if req.boxes:
        kwargs["input_boxes"] = [[[b for b in box] for box in req.boxes]]
    inputs = processor(**kwargs)
    # processor 输出的 input_boxes/points 可能是 float64, 310P 无 fp64 kernel(AsStrided), 统一转 fp32
    inputs = {k: (v.to(config.DEVICE, dtype=torch.float32)
                  if hasattr(v, "to") and v.is_floating_point() else
                  (v.to(config.DEVICE) if hasattr(v, "to") else v))
              for k, v in inputs.items()}

    with torch.no_grad():
        out = model(**inputs)
    torch.npu.synchronize()

    iou = out.iou_scores[0, 0].squeeze(-1)          # (3,)
    best = int(iou.argmax())
    mask_best = out.pred_masks[0, 0, best]          # (256,256)
    # 上采样回原图分辨率: (1,1,256,256) -> (1,1,h,w)
    h, w = image.shape[:2]
    m = torch.nn.functional.interpolate(
        mask_best[None, None].float(), size=(h, w), mode="bilinear",
        align_corners=False)[0, 0]
    mask_np = (torch.sigmoid(m).cpu().numpy() > 0.5)

    bbox, area = _bbox_area(mask_np)
    return {
        "mask_png_b64": _mask_to_png_b64(mask_np),
        "bbox": bbox, "area": area,
        "score": round(float(iou[best]), 4),
        "iou_scores": [round(float(s), 4) for s in iou],
        "model": kind,
    }


def preannotate(image: np.ndarray, text: str, score_threshold: float) -> list[dict]:
    """SAM3 文本预标注：一次前向返回图内所有匹配实例。"""
    from transformers import AutoTokenizer

    model = ModelManager.get_sam3()
    tok = AutoTokenizer.from_pretrained(config.MODEL_DIRS["sam3"])
    t = tok([text], return_tensors="pt", padding="max_length", max_length=32)

    from transformers import AutoImageProcessor
    proc = AutoImageProcessor.from_pretrained(config.MODEL_DIRS["sam3"])
    pv = proc(images=image, return_tensors="pt")["pixel_values"]

    with torch.no_grad():
        out = model(pixel_values=pv.to(config.DEVICE),
                    input_ids=t["input_ids"].to(config.DEVICE),
                    attention_mask=t["attention_mask"].to(config.DEVICE))
    torch.npu.synchronize()

    h, w = image.shape[:2]
    scores = out["pred_logits"][0].sigmoid()
    boxes = out["pred_boxes"][0]                    # cxcywh 归一化
    masks = out["pred_masks"][0]                    # (200,288,288)
    keep = scores > score_threshold
    results = []
    for i in torch.nonzero(keep).flatten()[:50]:
        cx, cy, bw, bh = boxes[i].tolist()
        x1, y1 = (cx - bw / 2) * w, (cy - bh / 2) * h
        m = torch.nn.functional.interpolate(
            masks[i:i + 1].float().unsqueeze(0), size=(h, w), mode="bilinear",
            align_corners=False)[0, 0]
        mask_np = (torch.sigmoid(m).cpu().numpy() > 0.5)
        bbox, area = _bbox_area(mask_np)
        results.append({
            "mask_png_b64": _mask_to_png_b64(mask_np), "bbox": bbox, "area": area,
            "score": round(float(scores[i]), 4), "source": "sam3",
        })
    return results


def system_info() -> dict:
    info = {"device": config.DEVICE, "ready": ModelManager.npu_ready(),
            "loaded_models": list(_models.keys())}
    try:
        import torch_npu  # noqa: F401
        info["device_name"] = torch.npu.get_device_name(0)
        info["device_count"] = torch.npu.device_count()
        info["mem_reserved_GB"] = round(torch.npu.memory_reserved() / 2**30, 2)
    except Exception:  # noqa: BLE001
        pass
    return info
