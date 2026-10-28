#!/usr/bin/env bash
# 检查/准备模型权重
set -uo pipefail
for d in SAM-vit-h SAM3; do
  if [ -d "/data1/models/$d" ]; then
    echo "OK /data1/models/$d"
  else
    echo "MISSING /data1/models/$d — 见姊妹仓库 sam3-ascend-310p 的 scripts/01_download_model.sh"
  fi
done
