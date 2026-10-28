#!/usr/bin/env bash
# 一键部署: 容器 + 依赖 + 服务
# 用法: bash scripts/deploy.sh [NPU设备号]
set -euo pipefail
DEV=${1:-3}
NAME=sam-studio
IMAGE=quay.io/ascend/vllm-ascend:v0.23.0-310p
ROOT=$(cd "$(dirname "$0")/.." && pwd)

docker inspect $NAME >/dev/null 2>&1 && docker start $NAME || \
docker run -itd --name $NAME -e ASCEND_VISIBLE_DEVICES=$DEV \
  -p 18100:8100 -v /data1/models:/data1/models -v "$ROOT":/workspace \
  --shm-size=16g "$IMAGE" sleep infinity

docker exec $NAME bash -c "pip install --target /root/pylibs -q transformers==5.13.1 'tokenizers==0.22.2' safetensors pillow fastapi 'uvicorn[standard]' python-multipart"
docker exec $NAME bash -c "pkill -9 -f uvicorn 2>/dev/null; sleep 1; true"
docker exec -d $NAME bash -c "export PYTHONPATH=/root/pylibs:/workspace && source /usr/local/Ascend/ascend-toolkit/set_env.sh && cd /workspace && exec python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8100 > /workspace/data/server.log 2>&1"
sleep 8
docker exec $NAME bash -c "curl -s -m 5 http://localhost:8100/api/health"
echo ""
echo "服务已启动: http://<本机IP>:18100  (默认账号 admin/admin123)"
