"""唯一主算例注册：IEEE30（冷端—网侧耦合主线）。"""
from __future__ import annotations

import os

from pypower.api import case30

CASE = os.environ.get("CASE", "IEEE30")
if CASE != "IEEE30":
    raise SystemExit(f"本主线只支持 IEEE30，收到 CASE={CASE!r}")

META = {
    "gens": [1, 2, 22, 27, 23, 13],
    "n_bus": 30,
    "reserve_margin": 0.0,
}


def loader():
    """返回新的 IEEE30 算例实例，避免场景间状态污染。"""
    return case30()


def cfg(base=None):
    """以 cascade 默认配置为底，应用本算例备用假设。"""
    from cascade import CFG
    return dict(base or CFG, reserve_margin=META["reserve_margin"])
