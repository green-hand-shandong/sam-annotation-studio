# 基于昇腾一体机的图像分割智能标注与质量管理系统 V1.0

**SAM Annotation Studio** — 基于 Huawei Ascend 310P 一体机（Atlas 300I Duo）+ Meta SAM 的图像分割标注系统。SAM ViT-H 交互式分割（点选/框选 → mask），SAM3 文本提示批量预标注，标注 → 审核工作流 → COCO / YOLO Segmentation / LabelMe 导出。

> 模型适配层（`ascend310p_compat`）与 310P 跑通 SAM 家族的过程见姊妹仓库 [sam3-ascend-310p](https://github.com/green-hand-shandong/sam3-ascend-310p)。

## 功能模块

| 模块 | 功能 |
|---|---|
| 工作看板 | 数据集/图片/任务/标注统计、标注来源分布、最近任务、操作日志 |
| 数据集管理 | 创建、上传（zip/多图）、服务器路径批量导入、删除 |
| 标注任务 | 创建（绑定数据集+自定义类别）、状态流转（进行中→待审核→已完成→重开） |
| **标注工作台** | Canvas 点选（前景/背景）/框选 → **SAM ViT-H 生成 mask（NPU）** → 保存；SAM3 文字批量预标注；快捷键（Enter 分割 / S 保存 / Esc 清除） |
| 质量审核 | 待审核列表、通过/驳回（带原因）、驳回自动删除 |
| 数据导出 | COCO JSON / YOLO Segmentation / LabelMe JSON 打包下载、导出历史 |
| 模型与设备 | NPU 状态、显存、已加载模型、推理模型说明 |
| 用户权限 | 管理员/标注员/审核员三种角色、HMAC 签名 Token、操作日志 |

## 架构

```
浏览器 React 18 + shadcn/ui 风格组件 + Canvas 标注交互 (hash 路由, 无后端渲染依赖)
   │ REST (Bearer token)
后端 FastAPI ── 8 个路由模块 (认证/数据集/任务/标注/推理/审核/导出/系统) + SQLite WAL
   │
推理服务 (torch_npu + ascend310p_compat 兼容层)
   ├─ SAM ViT-H    交互式分割: 点/框 → 3 候选 mask + IoU 预测 (fp32 @1024, ~1.6s)
   └─ SAM3         文本预标注: 文字 → 全图实例框+mask+分数 (fp32 @1008, ~2.4s)
   │
本地存储: 图片上传目录 + SQLite + 导出 zip (数据不出域, 一体机内网部署)
```

## 快速开始

### 1) 模型准备

```bash
# 权重下载与 310P 适配见姊妹仓库, 或直接:
bash scripts/prepare_models.sh    # 检查 /data1/models/{SAM-vit-h, SAM3} 是否就位
```

### 2) 后端（容器内运行，NPU 环境）

```bash
bash scripts/deploy.sh             # 启动容器+装依赖+起服务(端口 18100)
# 或手动:
docker run -itd --name sam-studio -e ASCEND_VISIBLE_DEVICES=<空闲卡> \
  -p 18100:8100 -v /data1/models:/data1/models -v $(pwd):/workspace \
  quay.io/ascend/vllm-ascend:v0.23.0-310p sleep infinity
# 容器内:
export PYTHONPATH=/root/pylibs:/workspace && source /usr/local/Ascend/ascend-toolkit/set_env.sh
pip install --target /root/pylibs transformers==5.13.1 tokenizers==0.22.2 safetensors pillow fastapi 'uvicorn[standard]' python-multipart
python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8100
```

> ⚠️ 环境变量顺序：**先 `export PYTHONPATH=...` 再 `source set_env.sh`**（set_env 会把 CANN 路径前置；顺序反了会缺 `tbe` 模块导致 NPU 初始化失败）。

### 3) 前端（开发模式 / 生产构建）

```bash
cd web && npm install
npm run dev          # 开发: http://localhost:5173 (代理 /api → 8100)
npm run build        # 生产: 构建到 frontend-dist/, 由 FastAPI 静态服务 (单进程部署)
```

访问 `http://<一体机IP>:18100`。默认账号：`admin/admin123`（管理员）、`annotator/123456`（标注员）、`reviewer/123456`（审核员）。

## 目录

```
├── backend/                 # FastAPI 后端
│   ├── app.py               #   入口: 装配路由 + 静态前端
│   ├── config.py / db.py / auth.py / schemas.py
│   ├── routers/             #   auth/datasets/tasks/annotations/inference/review/export/system
│   └── services/            #   inference.py (NPU 推理) / exporters.py (格式转换)
├── web/                     # React 18 + TypeScript + Tailwind 前端源码
│   └── src/{pages,components/ui,lib}
├── frontend-dist/           # 前端构建产物（npm run build 生成）
├── ascend310p_compat/       # 310P 兼容层（来自姊妹仓库）
├── scripts/                 # 部署/模型准备脚本
├── tests/                   # 后端单元测试（无 NPU 可跑）
└── docs/                    # 软著材料（操作说明书、设计说明）
```

## 测试

```bash
python3 -m pytest tests/ -q        # 10 个单元测试: 认证/任务流/标注存储/导出格式
```

全链路验收（已实测通过）：登录 → 建数据集 → 上传 → 建任务 → SAM 交互分割（NPU, score 1.01, mask 面积与提示框吻合）→ 保存 → 审核通过 → COCO 导出下载（类别正确）→ YOLO 导出 → 看板统计。

## License

Apache-2.0
