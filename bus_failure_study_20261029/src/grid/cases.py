"""IEEE30 算例注册：从项目 data/grid/IEEE30 读取本地冻结的标准表。"""
from __future__ import annotations
import csv
import json
import os
from pathlib import Path
import numpy as np

CASE = os.environ.get("CASE", "IEEE30")
if CASE != "IEEE30":
    raise SystemExit(f"本主线只支持 IEEE30，收到 CASE={CASE!r}")
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "grid" / "IEEE30"
META = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))

def _table(name: str) -> np.ndarray:
    path = DATA / f"{name}.csv"
    with path.open(newline="", encoding="utf-8") as f:
        return np.asarray([[float(x) for x in row] for row in list(csv.reader(f))[1:]], dtype=float)

def loader():
    """返回全新的 PYPOWER case dict，场景之间不共享可变状态。"""
    return {"version": "2", "baseMVA": float(META["baseMVA"]),
            "bus": _table("bus"), "gen": _table("gen"),
            "branch": _table("branch"), "gencost": _table("gencost")}

def cfg(base=None):
    """以电网级联默认配置为底，应用本算例备用假设。"""
    from grid.cascade import CFG
    return dict(base or CFG, reserve_margin=0.0)
