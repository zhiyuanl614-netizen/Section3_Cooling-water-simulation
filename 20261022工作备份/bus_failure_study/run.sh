#!/usr/bin/env bash
# IEEE30 冷端—电网主线入口；脚本位于 src/，结果写入 results/。
#
#   ./run.sh coldend       生成六机组冷端固定出力基准（P5）
#   ./run.sh coupled       重跑 G13 既有单机对照
#   ./run.sh coupled-five  运行 G1/G2/G22/G23/G27 五个独立情景并汇总 G13 对照
set -euo pipefail
cd "$(dirname "$0")"
export CASE="${CASE:-IEEE30}"
export PYTHONPATH="src:${PYTHONPATH:-}"

case "${1:-}" in
  coldend)
    python3 src/coldend/fleet.py
    python3 src/coldend/plot.py
    ;;
  coupled)
    python3 src/coldend/coupled.py
    ;;
  coupled-five)
    python3 src/coldend/coupled.py --units G1,G2,G22,G23,G27
    ;;
  *)
    echo "用法: ./run.sh [coldend|coupled|coupled-five]" >&2
    exit 1
    ;;
esac
