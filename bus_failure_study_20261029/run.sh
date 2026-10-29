#!/usr/bin/env bash
# 项目统一入口。K2–K6 按规定的全组合矩阵运行 t=0 同时断水情景。
set -euo pipefail
cd "$(dirname "$0")"
export CASE="${CASE:-IEEE30}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
case "${1:-}" in
  baseline)       python3 src/grid/baseline.py ;;
  coldend-ref)    python3 src/coldend/fleet.py && python3 src/coldend/plot.py ;;
  K1-G13)         python3 src/coupling/coupled.py --units G13 ;;
  K1-five)        python3 src/coupling/coupled.py --units G1,G2,G22,G23,G27 ;;
  K1-all)         python3 src/coupling/coupled.py --units G13,G1,G2,G22,G23,G27 --output-root results/K1 ;;
  K2)             python3 src/coupling/k2.py ;;
  K3)             python3 src/coupling/k3.py ;;
  K4)             python3 src/coupling/k4.py ;;
  K5)             python3 src/coupling/k5.py ;;
  K6)             python3 src/coupling/k6.py ;;
  K6-full)        python3 src/coupling/k6.py --continue-after-hard-loss ;;
  *)
    echo "用法：./run.sh {baseline|coldend-ref|K1-G13|K1-five|K1-all|K2|K3|K4|K5|K6|K6-full}" >&2
    exit 1
    ;;
esac
