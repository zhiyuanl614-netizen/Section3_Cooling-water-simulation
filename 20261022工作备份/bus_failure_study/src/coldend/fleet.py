"""
fleet.py — 六台机组各自独立的冷端故障 → 退出序列
==================================================
场景定义（本文件只做这一件事）：
    每台机组的外来补水在同一时刻 t=0 中断，各机组按**自己的**冷却水系统参数
    演化（运行期间排污不隔离、保持故障前出力；池位→泵流量→塔/凝汽器→背压→低水位跳机），
    得到跳机时刻并按时间排序。

输出（results/IEEE30/P5_coldend/）：
    trip_sequence.csv         每台机组一行：跳机时刻、机制、跳机前功率、电量缺口
    fleet_power_profile.csv   1 min 网格的机组功率轨迹（跳机前保持 P0）
    grid_events.csv           离散事件流：trip（电网模型消费的最小接口）
    unit_series/<unit>.csv    每台机组完整的冷端时间序列（池位、流量、背压、耗水）

用法
----
    python3 src/coldend/fleet.py            # 主结果
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coldend import model
from coldend.units import Unit, load_fleet

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "results", "IEEE30", "P5_coldend")


def unit_table(fleet: dict[str, Unit]) -> pd.DataFrame:
    """每台机组一套系统的"铭牌"：设计水量、池容、耗水、初始工况、保护定值。"""
    rows = []
    for u in fleet.values():
        m = u.params
        st = model.steady_state(m, p_setpoint_mw=u.pg0_mw)
        rows.append(dict(
            unit=u.name, bus=u.bus, pmax_mw=m.p_rated_mw, pg0_mw=u.pg0_mw,
            load_frac=round(u.load_frac, 4), cw_config=u.row["cw_config"],
            qcw_design_m3s=round(m.qcw_design_m3s, 3),
            basin_area_m2=round(m.basin_area_m2, 1),
            level_normal_m=m.basin_level_normal_m, level_trip_m=m.basin_level_trip_m,
            v0_m3=round(model.basin_v0_m3(m)), vmin_m3=round(model.basin_vmin_m3(m)),
            usable_m3=round(model.basin_v0_m3(m) - model.basin_vmin_m3(m)),
            heat_reject_mw_th=round(st["heat_reject_mw_th"], 1),
            evap_m3h=round(st["evaporation_m3s"] * 3600, 1),
            blowdown_m3h=round(st["blowdown_m3s"] * 3600, 1),
            makeup_m3h=round(st["makeup_m3s"] * 3600, 1),
            coc=m.cycles_of_concentration, twb_c=m.twb_ref_c,
            approach_c=m.approach_design_c, ttd_c=round(st["ttd_c"], 2),
            pb_kpa=round(st["backpressure_kpa"], 2), pb_trip_kpa=m.pb_trip_kpa,
            blowdown_isolated=m.blowdown_isolated_on_detection,
            tower_tau_s=m.tower_tau_s, condenser_tau_s=m.condenser_tau_s,
            analytic_trip_h=round(model.analytic_trip_h(m), 3),
        ))
    return pd.DataFrame(rows)


def _trip_row(u: Unit, r: model.Run, horizon_h: float) -> dict:
    """把一次 Run 压成一行序列信息。"""
    p0 = r.initial_p_mw
    e = model.delivered_energy_mwh(r, horizon_h)
    t_trip = r.t_trip_h
    return dict(
        unit=u.name, bus=u.bus, pmax_mw=u.pmax_mw, pg0_mw=u.pg0_mw,
        load_frac=round(u.load_frac, 4),
        basin_area_m2=round(u.params.basin_area_m2, 1),
        basin_usable_m3=round(u.params.basin_area_m2 *
                              (u.params.basin_level_normal_m - u.params.basin_level_trip_m), 1),
        t_trip_h=None if t_trip is None else round(t_trip, 4),
        mechanism=r.mechanism,
        p_before_trip_mw=None if r.p_before_trip_mw is None else round(r.p_before_trip_mw, 3),
        e_delivered_mwh=round(e, 2),
        e_shortfall_mwh=round(p0 * horizon_h - e, 2),
        analytic_trip_h=round(r.notes["analytic_trip_h"], 3),
    )


def run_fleet(horizon_h: float = 24.0, dt_s: float = 1.0,
              fleet: dict[str, Unit] | None = None, quiet: bool = False):
    fleet = fleet or load_fleet()
    rows, runs = [], {}
    for name, u in fleet.items():
        r = u.simulate(t_max_h=horizon_h, dt_s=dt_s)
        runs[name] = r
        rows.append(_trip_row(u, r, horizon_h))
        if not quiet:
            print(f"  {u.label():<28s} 跳机 @{str(rows[-1]['t_trip_h']):>7s} h  "
                  f"{r.mechanism:<14s} 缺口 {rows[-1]['e_shortfall_mwh']:7.1f} MWh")
    df = pd.DataFrame(rows).sort_values("t_trip_h").reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    return df, runs


def power_profile(runs: dict[str, model.Run], horizon_h: float, step_min: float = 1.0) -> pd.DataFrame:
    """1 min 网格的 P_i(t)；跳机后恒为 0（保护动作按零时长处理）。"""
    n = int(round(horizon_h * 60 / step_min)) + 1
    t_h = [i * step_min / 60.0 for i in range(n)]
    data = {"t_h": [round(t, 4) for t in t_h]}
    for name, r in runs.items():
        data[name] = [round(model.p_avail_at(r, t), 4) for t in t_h]
    return pd.DataFrame(data)


def grid_events(df: pd.DataFrame) -> pd.DataFrame:
    """离散事件流：每台机组只在低水位保护时跳机。"""
    ev = []
    for row in df.itertuples():
        ev.append(dict(t_h=row.t_trip_h, unit=row.unit, bus=row.bus,
                       event="trip", p_mw=0.0,
                       note=f"低水位保护跳机，跳机前 {row.p_before_trip_mw} MW"))
    return pd.DataFrame(ev).sort_values(["t_h", "unit"]).reset_index(drop=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="六台机组独立冷端故障 → 退出序列")
    ap.add_argument("--horizon-h", type=float, default=24.0)
    ap.add_argument("--dt-s", type=float, default=1.0)
    a = ap.parse_args(argv)

    os.makedirs(os.path.join(OUT, "unit_series"), exist_ok=True)
    print("六台机组：各自独立补水中断，同一 t=0 起算")
    df, runs = run_fleet(horizon_h=a.horizon_h, dt_s=a.dt_s)
    unit_table(load_fleet()).to_csv(os.path.join(OUT, "unit_parameters.csv"), index=False)
    df.to_csv(os.path.join(OUT, "trip_sequence.csv"), index=False)
    power_profile(runs, a.horizon_h).to_csv(os.path.join(OUT, "fleet_power_profile.csv"), index=False)
    grid_events(df).to_csv(os.path.join(OUT, "grid_events.csv"), index=False)
    for name, r in runs.items():
        model.write_csv(os.path.join(OUT, "unit_series", f"{name}.csv"), r)

    print("\n退出顺序（先跳机者在前）")
    for row in df.itertuples():
        print(f"  {row.rank}. {row.unit:<4s} bus{row.bus:<3d} {row.pmax_mw:5.0f} MW  "
              f"负荷 {row.load_frac*100:4.1f}%  可用库容 {row.basin_usable_m3:6.1f} m³  "
              f"跳机 {row.t_trip_h:6.3f} h  {row.mechanism}")
    span = df.t_trip_h.max() - df.t_trip_h.min()
    print(f"\n首末跳机间隔 {span:.2f} h；全部机组在 {df.t_trip_h.max():.2f} h 内退出")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
