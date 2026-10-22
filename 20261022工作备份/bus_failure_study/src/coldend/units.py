"""
units.py — 每台机组一套自己的冷却水系统
==========================================
把 ``model.py``（与上传的 ``coldend_makeup_interrupt.py`` 逐位等价，物理未改）
实例化成 IEEE 30 六台机组各自的冷端系统。

参数来源分三层，顺序与上传文件一致：
    1) 500 MW 原型模板            model.Params() 的默认值 [P]
    2) 容量缩放 s = Pmax/500      流量、池面积按 s 线性缩放
    3) 机组锚点覆盖                data/coldend/unit_anchors.csv（唯一事实来源）

``unit_anchors.csv`` 里每一项都写了 ``basis``，标注它为什么这么取。
除 ``pg0_mw``（来自 case30 的 Pg）外，全部是**工程假设/参考模板值**，
不是现场实测；替换该 CSV 即可完成换机组或换场站，不需要改代码。
机组群主情景采用“不隔离排污 + 保持故障前出力直至保护跳机”；不配置 SOP 降负荷参数，因为当前电网级联接口不消费连续降负荷轨迹。

用法
----
    from coldend.units import load_fleet
    fleet = load_fleet()            # dict[str, Unit]
    u = fleet["G13"]
    r = u.simulate(t_max_h=24.0)    # coldend.model.Run
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, replace

from . import model

ANCHOR_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "coldend", "unit_anchors.csv")

# 锚点 CSV 的数值列 → (model.Params 字段, 变换函数)
_DIRECT = {
    "level_normal_m": "basin_level_normal_m",
    "level_trip_m": "basin_level_trip_m",
    "coc": "cycles_of_concentration",
    "tower_tau_s": "tower_tau_s",
    "condenser_tau_s": "condenser_tau_s",
    "tower_approach_c": "approach_design_c",
    "ttd_design_c": "ttd_design_c",
    "condenser_cleanliness": "condenser_cleanliness",
    "twb_c": "twb_ref_c",
    "pump_npshr_m": "pump_npshr_design_m",
    "pb_trip_kpa": "pb_trip_kpa",
    "atm_kpa": "site_atm_pressure_kpa",
}


@dataclass(frozen=True)
class Unit:
    """一台机组的冷端系统：身份 + 参数 + 来源行。"""
    name: str
    bus: int
    pmax_mw: float
    pg0_mw: float
    params: model.Params
    row: dict

    @property
    def load_frac(self) -> float:
        return self.pg0_mw / self.pmax_mw

    def simulate(self, *, t_max_h: float = 24.0, dt_s: float = 1.0,
                 sample_s: float = 60.0):
        """不隔离排污、保持故障前出力，模拟补水中断至保护跳机。"""
        return model.simulate(self.params, dt_s=dt_s, sample_every_s=sample_s,
                              t_max_h=t_max_h, initial_load_frac=self.load_frac)

    def label(self) -> str:
        return f"{self.name}(bus{self.bus}, {self.pmax_mw:.0f}MW, {self.load_frac*100:.1f}%)"


def _f(row: dict, key: str) -> float:
    return float(row[key])


def build_unit(row: dict) -> Unit:
    pmax = _f(row, "pmax_mw")
    over: dict[str, float] = {}
    for col, field in _DIRECT.items():
        over[field] = _f(row, col)
    # 池面积：build_model 已按 s 线性缩放（1600·s），再乘机组自己的场地/土建系数
    params = model.build_model(pmax, **over)
    # 机组群主情景：运行期间正常排污；不加入水位触发的 SOP 降负荷。
    # 本版既有电网级联只接收发电机跳机集合，不消费 P(t) 降负荷轨迹。
    params = replace(params,
                     basin_area_m2=params.basin_area_m2 * _f(row, "basin_area_factor"),
                     blowdown_isolated_on_detection=False,
                     ride_down=False)
    u = Unit(name=row["unit"], bus=int(float(row["bus"])), pmax_mw=pmax,
             pg0_mw=_f(row, "pg0_mw"), params=params, row=row)
    if not (0.0 < u.load_frac <= 1.0):
        raise ValueError(f"{u.name}: 初始负荷分数 {u.load_frac:.3f} 越界")
    if u.params.basin_level_trip_m >= u.params.basin_level_normal_m:
        raise ValueError(f"{u.name}: 跳机水位不低于正常水位")
    return u


def read_anchors(path: str = ANCHOR_CSV) -> list[dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_fleet(path: str = ANCHOR_CSV) -> dict[str, Unit]:
    units = [build_unit(r) for r in read_anchors(path)]
    seen = set()
    for u in units:
        if u.name in seen:
            raise ValueError(f"重复机组名 {u.name}")
        seen.add(u.name)
    return {u.name: u for u in units}


if __name__ == "__main__":
    for name, u in load_fleet().items():
        p = u.params
        print(f"{name:4s} bus{u.bus:>2d} Pmax {u.pmax_mw:5.0f} MW  P0 {u.pg0_mw:5.2f} "
              f"({u.load_frac*100:5.1f}%)  池 {p.basin_area_m2:5.0f} m²  "
              f"水位 {p.basin_level_normal_m:.2f}/{p.basin_level_trip_m:.2f} m  "
              f"CoC {p.cycles_of_concentration:.1f}  排污隔离 {p.blowdown_isolated_on_detection}  "
              f"保持初始出力至跳机 解析排空 {model.analytic_trip_h(p):5.2f} h")
