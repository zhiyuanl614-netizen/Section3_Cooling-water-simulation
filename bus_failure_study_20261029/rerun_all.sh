#!/usr/bin/env bash
# 用修正后的代码重跑全部 63 案（K1–K6）。
# 目的：填充新增的静态减载成因分解列
#   deenergized_shed_mw / collapse_shed_mw / vcls_shed_mw / uvls_shed_mw / grid_ufls_shed_mw
# 代码改动为纯附加记账，不改变仿真动力学，H 等指标应逐位不变（作为回归校验）。
set -euo pipefail
cd "$(dirname "$0")"
export CASE="${CASE:-IEEE30}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"

for step in "K1-all" K2 K3 K4 K5 K6; do
  echo "########## $(date +%H:%M:%S) 开始 ${step} ##########"
  bash run.sh "${step}"
  echo "########## $(date +%H:%M:%S) 完成 ${step} ##########"
done
echo "全部完成 $(date +%H:%M:%S)"
