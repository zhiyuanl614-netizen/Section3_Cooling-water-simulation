#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单台机组补水中断 → 机组爬坡再调度 → 冷端需水/库存动态 → 电网终态级联。默认运行 G13，--units 可单独指定其他机组或批量情景。

本主线固定 IEEE30 原始负荷，不扫描负荷倍率。现场参数缺失时，读取
 data/coldend/coupling_reference_assumptions.csv 中明确标注的参考假设。
冷端物理内核 model.py 不修改；本文件负责时域耦合与事件编排。
"""
from __future__ import annotations

import argparse
import copy
import csv
import math
import os
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grid import cases
from grid.cascade import (CascadeSim, GEN_BUS, GEN_PG, GEN_QG, GEN_STATUS,
                          solve_island)
from coldend import model
from coldend.units import Unit, load_fleet

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "K1" / "scenarios" / "G13"
BATCH_OUT = ROOT / "results" / "K1"
ASSUMPTIONS = ROOT / "data" / "coldend" / "coupling_reference_assumptions.csv"


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def load_assumptions() -> dict[str, float]:
    with ASSUMPTIONS.open(newline="", encoding="utf-8") as f:
        return {r["parameter"]: float(r["value"]) for r in csv.DictReader(f)}


def solve_base_operating_point() -> tuple[dict, dict[int, float], dict[int, float]]:
    """求 IEEE30 原始负荷基态潮流，并把 slack 调整后的 Pg/Qg 写回机组表。"""
    case = cases.loader()
    cfg = cases.cfg()
    res, _, _, ok = solve_island(copy.deepcopy(case), cfg)
    if not ok or res is None:
        raise RuntimeError("IEEE30 原始基准潮流不收敛")
    pg = {int(g[GEN_BUS]): float(g[GEN_PG]) for g in res["gen"]}
    qg = {int(g[GEN_BUS]): float(g[GEN_QG]) for g in res["gen"]}
    for i, g in enumerate(case["gen"]):
        bus = int(g[GEN_BUS])
        if g[GEN_STATUS] > 0:
            case["gen"][i, GEN_PG] = pg[bus]
            case["gen"][i, GEN_QG] = qg[bus]
            if pg[bus] > g[8] + 1e-6:
                raise RuntimeError(f"基态机组 bus{bus} Pg={pg[bus]:.3f} 超过 Pmax={g[8]:.3f}")
    return case, pg, qg


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def simulate_frequency_ramp(base_pg: dict[int, float], target_pg: dict[int, float],
                            fleet: dict[str, Unit], *, lost_mw: float,
                            base_load_mw: float, base_gen_mw: float,
                            cfg: dict, assumptions: dict[str, float],
                            trip_buses: tuple[int, ...] = (13,),
                            initial_frequency_hz: float | None = None
                            ) -> tuple[list[dict], dict[int, dict[int, float]], dict]:
    """降阶 SFR + 参考 AGC 爬坡；返回频率轨迹、逐秒机组 Pg 轨迹与汇总。"""
    pmax = {u.bus: u.pmax_mw for u in fleet.values()}
    target_delta: dict[int, float] = {}
    trip_set = {int(b) for b in trip_buses}
    for bus, p0 in base_pg.items():
        if bus in trip_set or target_pg.get(bus, 0.0) <= 1e-9:
            continue
        delta = max(0.0, target_pg.get(bus, p0) - p0)
        if delta > 1e-9:
            target_delta[bus] = delta
    delta_sum = sum(target_delta.values())
    if lost_mw <= 0:
        raise RuntimeError("动态频率事件缺少正的跳机损失")
    shares = ({b: d / delta_sum for b, d in target_delta.items()}
              if delta_sum > 1e-9 else {})

    ramp_frac = assumptions["ramp_frac_pmax_per_min"]
    delay_s = assumptions["redispatch_delay_s"]
    dt = assumptions["frequency_time_step_s"]
    relay_delay = assumptions["ufls_relay_delay_s"]
    ramp_end_s = (max(delay_s + target_delta[b] /
                       max(ramp_frac * pmax[b] / 60.0, 1e-9) for b in target_delta)
                  if target_delta else delay_s)
    t_end = max(300.0, ramp_end_s + 180.0)
    n_step = int(math.ceil(t_end / dt))

    # 一次调频下垂按仍在线机组的事故前可用上调裕度分摊。
    gov_units = [b for b, pg in base_pg.items()
                 if b not in trip_set and target_pg.get(b, 0.0) > 1e-9 and b in pmax]
    gov_head = {b: max(pmax[b] - base_pg[b], 0.0) for b in gov_units}
    head_sum = sum(gov_head.values())
    gov_share = ({b: x / head_sum for b, x in gov_head.items()} if head_sum > 0
                 else {b: shares.get(b, 0.0) for b in gov_units})
    gov_up_limit = head_sum
    gov_down_limit = sum(base_pg[b] for b in gov_units)

    agc = {b: 0.0 for b in target_delta}
    initial_frequency_hz = cfg["f0"] if initial_frequency_hz is None else initial_frequency_hz
    w = initial_frequency_hz / cfg["f0"] - 1.0
    pm = 0.0
    shed_mw = 0.0
    remaining_load = base_load_mw
    stage = 0
    under_threshold_s = 0.0
    fmin = min(cfg["f0"], initial_frequency_hz)
    t_fmin = 0.0 if initial_frequency_hz < cfg["f0"] else 0.0
    rocof = -lost_mw / max(base_gen_mw, 1e-9) * cfg["f0"] / (2.0 * cfg["H_default"])
    ufls_events: list[str] = []
    freq_rows: list[dict] = []
    pg_profile: dict[int, dict[int, float]] = {0: {b: (0.0 if b in trip_set else p)
                                                   for b, p in base_pg.items()}}
    sample_every = 1.0
    next_sample = 1.0
    t = 0.0
    initial_row = dict(elapsed_s=0, frequency_hz=round(initial_frequency_hz, 5), agc_increment_mw=0.0,
                       governor_increment_mw=0.0,
                       total_generation_mw=round(base_gen_mw - lost_mw, 4),
                       shed_mw=0.0, ufls_stage=0)
    for bus, pg in sorted(pg_profile[0].items()):
        initial_row[f"pg_bus{bus}_mw"] = round(pg, 4)
    freq_rows.append(initial_row)

    def governor_mw(pm_pu: float) -> float:
        return _clip(pm_pu * base_gen_mw, -gov_down_limit, gov_up_limit)

    for k in range(n_step):
        t = k * dt
        gov0 = governor_mw(pm)
        agc_target_total = max(0.0, delta_sum - shed_mw - gov0)
        for bus in target_delta:
            target_i = shares[bus] * agc_target_total
            if t >= delay_s:
                max_move = ramp_frac * pmax[bus] * dt / 60.0
                agc[bus] += _clip(target_i - agc[bus], -max_move, max_move)
        agc_total = sum(agc.values())
        gov0 = governor_mw(pm)
        net_pu = (-lost_mw + shed_mw + agc_total + gov0) / max(base_gen_mw, 1e-9)

        def deriv(w_: float, pm_: float) -> tuple[float, float]:
            dw = (pm_ + net_pu - cfg["damping"] * w_) / (2.0 * cfg["H_default"])
            dpm = (-w_ / cfg["droop"] - pm_) / cfg["Tg"]
            return dw, dpm

        k1w, k1p = deriv(w, pm)
        k2w, k2p = deriv(w + 0.5 * dt * k1w, pm + 0.5 * dt * k1p)
        w += dt * k2w
        pm += dt * k2p
        freq = cfg["f0"] * (1.0 + w)
        if freq < fmin:
            fmin, t_fmin = freq, t + dt

        if stage < len(cfg["f_uf"]) and freq < cfg["f_uf"][stage]:
            under_threshold_s += dt
        else:
            under_threshold_s = 0.0
        if stage < len(cfg["f_uf"]) and under_threshold_s >= relay_delay:
            fraction = cfg["ufls_frac"][stage]
            cut = remaining_load * fraction
            shed_mw += cut
            remaining_load -= cut
            stage += 1
            ufls_events.append(f"round{stage}@{t + dt:.2f}s f={freq:.4f}Hz shed={cut:.3f}MW")
            under_threshold_s = 0.0

        if (t + dt >= next_sample - 1e-8) or (k == n_step - 1):
            gov = governor_mw(pm)
            pg_now = {b: (0.0 if b in trip_set else p)
                      for b, p in base_pg.items()}
            for bus in gov_units:
                pg_now[bus] = _clip(base_pg[bus] + agc.get(bus, 0.0) +
                                    gov * gov_share.get(bus, 0.0), 0.0, pmax[bus])
            sec = int(round(t + dt))
            pg_profile[sec] = pg_now.copy()
            row = dict(elapsed_s=sec, frequency_hz=round(freq, 5),
                       agc_increment_mw=round(agc_total, 4),
                       governor_increment_mw=round(gov, 4),
                       total_generation_mw=round(sum(pg_now.values()), 4),
                       shed_mw=round(shed_mw, 4), ufls_stage=stage)
            for bus in sorted(pg_now):
                row[f"pg_bus{bus}_mw"] = round(pg_now[bus], 4)
            freq_rows.append(row)
            next_sample += sample_every

    final_pg = pg_profile[max(pg_profile)].copy()
    summary = dict(f_nadir_hz=round(fmin, 5), t_f_nadir_s=round(t_fmin, 3),
                   rocof_hz_s=round(rocof, 5), ufls_shed_mw=round(shed_mw, 4),
                   ufls_events=";".join(ufls_events), final_frequency_hz=round(freq, 5),
                   ramp_completion_s=round(ramp_end_s, 3), frequency_horizon_s=round(t_end, 3))
    return freq_rows, pg_profile, summary


def positive_ramp_gap_mwh(freq_rows: list[dict], target_generation_mw: float,
                           ramp_window_s: float) -> float:
    """爬坡命令窗口内，相对稳态目标的正向发电缺额面积（不是用户未供电量/EENS）。"""
    by_time: dict[float, float] = {}
    for row in freq_rows:
        t = float(row["elapsed_s"])
        if t <= ramp_window_s + 1e-9:
            by_time[t] = float(row["total_generation_mw"])
    if not by_time:
        return 0.0
    times = sorted(by_time)
    if ramp_window_s not in by_time:
        lo = max((t for t in times if t < ramp_window_s), default=times[0])
        hi = min((t for t in [float(r["elapsed_s"]) for r in freq_rows]
                  if t > ramp_window_s), default=None)
        if hi is None:
            pg_end = by_time[lo]
        else:
            pg_hi = next(float(r["total_generation_mw"]) for r in freq_rows
                         if float(r["elapsed_s"]) == hi)
            pg_end = by_time[lo] + (pg_hi - by_time[lo]) * (ramp_window_s - lo) / (hi - lo)
        by_time[ramp_window_s] = pg_end
        times = sorted(by_time)

    energy_mwh = 0.0
    for t0, t1 in zip(times, times[1:]):
        if t1 <= t0:
            continue
        gap0 = target_generation_mw - by_time[t0]
        gap1 = target_generation_mw - by_time[t1]
        dt_h = (t1 - t0) / 3600.0
        if gap0 >= 0 and gap1 >= 0:
            energy_mwh += 0.5 * (gap0 + gap1) * dt_h
        elif gap0 > 0 > gap1:
            positive_fraction = gap0 / (gap0 - gap1)
            energy_mwh += 0.5 * gap0 * dt_h * positive_fraction
        elif gap1 > 0 > gap0:
            positive_fraction = gap1 / (gap1 - gap0)
            energy_mwh += 0.5 * gap1 * dt_h * positive_fraction
    return energy_mwh


def pg_settling_time_s(freq_rows: list[dict], target_pg: dict[int, float],
                       tolerance_mw: float = 0.01) -> float | None:
    """首个此后每台机组均保持在终态 Pg ± tolerance 内的采样时刻。"""
    def is_settled(row: dict) -> bool:
        for bus, target in target_pg.items():
            key = f"pg_bus{bus}_mw"
            if key in row and abs(float(row[key]) - float(target)) > tolerance_mw:
                return False
        return True

    for i, row in enumerate(freq_rows):
        if is_settled(row) and all(is_settled(later) for later in freq_rows[i:]):
            return float(row["elapsed_s"])
    return None


def initial_cooling_state(u: Unit, p_mw: float) -> dict:
    """建立耦合起点的冷端热/水力状态；物理状态量来自现有 model.py 稳态函数。"""
    m = u.params
    ss = model.steady_state(m, p_setpoint_mw=p_mw)
    return dict(
        tin_c=ss["tin_c"], tsat_c=ss["t_sat_c"],
        level_m=m.basin_level_normal_m,
        volume_m3=m.basin_area_m2 * m.basin_level_normal_m,
        x_state=1.0, supply_flow_m3s=ss["makeup_m3s"],
        backpressure_kpa=ss["backpressure_kpa"], pb_high_since_s=None,
        min_basin_level_m=m.basin_level_normal_m,
        maximum_thermal_shortfall_mw=0.0,
    )


def simulate_cooling_segment(u: Unit, *, state: dict, p_final_mw: float,
                             pg_profile: dict[int, dict[int, float]], trip_h: float,
                             start_elapsed_s: float, duration_s: float,
                             assumptions: dict[str, float], dt_s: float = 1.0,
                             sample_s: float = 60.0, record_start: bool = False,
                             makeup_interrupted: bool = False
                             ) -> tuple[list[dict], dict, dict | None]:
    """推进一个网侧响应片段；返回冷端状态和首个低水位保护事件。"""
    m = u.params
    state = copy.deepcopy(state)
    # A failed external makeup source is a discontinuous outage at t=0; the response
    # time constant applies to normal supply following changing demand, not to water
    # continuing to arrive after the source has been interrupted.
    if makeup_interrupted:
        state["supply_flow_m3s"] = 0.0
    qcw_design = m.qcw_design_m3s
    area = m.basin_area_m2
    supply_cap = (0.0 if makeup_interrupted else
                  model.design_makeup_m3s(m) * assumptions["makeup_capacity_factor"])
    makeup_tau = assumptions["makeup_response_tau_s"]
    tau_pump, tau_tower, tau_cond = m.pump_tau_s, m.tower_tau_s, m.condenser_tau_s
    capacity = tau_cond * model.condenser_exchange(m, qcw_design, clean_design=True)[1]
    rows: list[dict] = []
    event = None
    local_t = 0.0
    next_sample = (math.floor((start_elapsed_s + 1e-8) / sample_s) + 1) * sample_s

    def p_at(local_sec: int) -> float:
        if local_sec in pg_profile:
            return float(pg_profile[local_sec].get(u.bus, p_final_mw))
        return p_final_mw

    def record(global_elapsed: float, pg: float, qcw: float, heat: float,
               evap: float, blow: float, makeup: float, pb: float,
               pcap: float, status: str = "online") -> None:
        rows.append(dict(unit=u.name, bus=u.bus,
                         elapsed_min=round(global_elapsed / 60.0, 3),
                         system_t_h=round(trip_h + global_elapsed / 3600.0, 4),
                         pg_command_mw=round(pg, 4),
                         basin_level_m=round(state["level_m"], 4),
                         qcw_m3s=round(qcw, 5), heat_reject_mw_th=round(heat, 4),
                         evaporation_m3h=round(evap * 3600, 4),
                         blowdown_m3h=round(blow * 3600, 4),
                         makeup_required_m3h=round(makeup * 3600, 4),
                         makeup_supply_m3h=round(state["supply_flow_m3s"] * 3600, 4),
                         backpressure_kpa=round(pb, 4), thermal_cap_mw=round(pcap, 4),
                         status=status))

    if record_start and duration_s > 0:
        p0 = p_at(0)
        p0_actual = min(p0, model.thermal_power_mw(m, state["backpressure_kpa"]))
        heat0 = model.heat_reject_mw_th(m, p0_actual)
        q0 = qcw_design * state["x_state"]
        evap0, blow0, _, makeup0 = model.water_balance_m3s(
            m, heat0, q0, state["tin_c"])
        record(start_elapsed_s, p0_actual, q0, heat0, evap0, blow0, makeup0,
               state["backpressure_kpa"],
               model.thermal_power_mw(m, state["backpressure_kpa"]))

    while local_t < duration_s - 1e-9:
        global_t = start_elapsed_s + local_t
        h = min(dt_s, duration_s - local_t, next_sample - global_t)
        if h <= 1e-9:
            next_sample += sample_s
            continue
        p_command = p_at(int(round(local_t)))
        p_actual = min(p_command, model.thermal_power_mw(m, state["backpressure_kpa"]))
        state["maximum_thermal_shortfall_mw"] = max(
            state["maximum_thermal_shortfall_mw"], p_command - p_actual)
        steam0 = model.heat_reject_mw_th(m, p_actual)
        qcw_old = qcw_design * state["x_state"]
        old_demand = model.water_balance_m3s(
            m, max(0.0, model.condenser_exchange(m, qcw_old)[1] *
                  (state["tsat_c"] - state["tin_c"])),
            qcw_old, state["tin_c"])[3]
        old_supply = state["supply_flow_m3s"]

        x_hyd = model.pump_flow_fraction(m, state["level_m"], state["tin_c"])
        a_p_half = 1.0 if tau_pump <= 0 else 1.0 - math.exp(-h / (2.0 * tau_pump))
        a_p_full = 1.0 if tau_pump <= 0 else 1.0 - math.exp(-h / tau_pump)
        x_mid = _clip(state["x_state"] + (x_hyd - state["x_state"]) * a_p_half, 0.0, 1.0)
        x_new = _clip(state["x_state"] + (x_hyd - state["x_state"]) * a_p_full, 0.0, 1.0)
        qcw_mid = qcw_design * x_mid
        _, g_mid = model.condenser_exchange(m, qcw_mid)
        water_target = max(0.0, g_mid * (state["tsat_c"] - state["tin_c"]))
        tin_target = (model.tower_outlet_c(m, m.twb_ref_c, water_target, qcw_mid)
                      if qcw_mid > 0 else state["tin_c"])
        a_t_half = 1.0 if tau_tower <= 0 else 1.0 - math.exp(-h / (2.0 * tau_tower))
        a_t_full = 1.0 if tau_tower <= 0 else 1.0 - math.exp(-h / tau_tower)
        tin_mid = state["tin_c"] + (tin_target - state["tin_c"]) * a_t_half
        tin_new = state["tin_c"] + (tin_target - state["tin_c"]) * a_t_full
        tsat_new, _, _ = model.advance_condenser(
            state["tsat_c"], tin_mid, steam0, g_mid, capacity, h)
        qcw_new = qcw_design * x_new
        _, g_new = model.condenser_exchange(m, qcw_new)
        water_new = max(0.0, g_new * (tsat_new - tin_new))
        evap, blow, _, makeup = model.water_balance_m3s(m, water_new, qcw_new, tin_new)
        pb_new = model.sat_pressure_kpa(tsat_new) + m.condenser_air_partial_pressure_kpa
        pcap_new = model.thermal_power_mw(m, pb_new)

        supply_target = min(makeup, supply_cap)
        a_makeup = 1.0 if makeup_tau <= 0 else 1.0 - math.exp(-h / makeup_tau)
        supply_new = old_supply + (supply_target - old_supply) * a_makeup
        avg_demand = 0.5 * (old_demand + makeup)
        state["volume_m3"] = max(
            0.0, state["volume_m3"] +
            (0.5 * (old_supply + supply_new) - avg_demand) * h)
        state["level_m"] = state["volume_m3"] / max(area, 1e-9)
        local_t += h
        global_t = start_elapsed_s + local_t
        state.update(tin_c=tin_new, tsat_c=tsat_new, x_state=x_new,
                     supply_flow_m3s=supply_new, backpressure_kpa=pb_new)
        state["min_basin_level_m"] = min(state["min_basin_level_m"], state["level_m"])

        status = "online"
        trip_cause = None
        if state["level_m"] <= m.basin_level_trip_m + 1e-10:
            trip_cause = "low_basin_level"
        elif x_new <= 0.02:  # matches model.simulate() default qcw_frac_floor
            trip_cause = "pump_cavitation"
        elif pb_new >= m.pb_trip_kpa:
            if state["pb_high_since_s"] is None:
                state["pb_high_since_s"] = global_t
            if global_t - state["pb_high_since_s"] >= m.pb_trip_delay_s - 1e-10:
                trip_cause = "backpressure_protection"
        else:
            state["pb_high_since_s"] = None
        if trip_cause:
            status = "coldend_trip"
            event = dict(unit=u.name, bus=u.bus,
                         elapsed_s=round(global_t, 3),
                         system_t_h=round(trip_h + global_t / 3600.0, 5),
                         level_m=round(state["level_m"], 4), cause=trip_cause)
        if global_t >= next_sample - 1e-8 or local_t >= duration_s - 1e-8 or event:
            record(global_t, p_actual, qcw_new, steam0, evap, blow, makeup,
                   pb_new, pcap_new, status)
            if global_t >= next_sample - 1e-8:
                next_sample += sample_s
        if event:
            break
    return rows, state, event


def simulate_single_unit_dynamic(initial_unit_name: str = "G13", *,
                                 makeup_interrupted_units: tuple[str, ...] | None = None,
                                 stop_at_hard_service_loss: bool = True,
                                 stop_on_solver_failure: bool = False
                                 ) -> tuple[list[dict], list[dict], list[dict], list[dict], dict]:
    """模拟一个或多个同时开始断水的机组；可选在首次硬失供时停止。"""
    assumptions = load_assumptions()
    fleet_anchor = load_fleet()
    faulted_units = tuple(makeup_interrupted_units or (initial_unit_name,))
    if not faulted_units or len(set(faulted_units)) != len(faulted_units):
        raise ValueError("补水中断机组列表不能为空且不得重复")
    unknown = sorted(set(faulted_units) - set(fleet_anchor))
    if unknown:
        raise ValueError(f"未知机组 {unknown}; available={sorted(fleet_anchor)}")
    base_case, base_pg, base_qg = solve_base_operating_point()
    fleet = {name: replace(u, pg0_mw=base_pg.get(u.bus, u.pg0_mw))
             for name, u in fleet_anchor.items()}
    cooling_horizon_s = assumptions["post_trip_cooling_horizon_h"] * 3600.0

    # K1 retains its archived trip-time convention. For multi-unit K2, both makeup
    # interruptions start at t=0; the coupled supply-response model determines each
    # initial cold-end trip time before the first grid disturbance.
    pre_event_rows: list[dict] = []
    pre_event_states: dict[int, dict] = {}
    pre_event_trip_events: list[dict] = []
    if len(faulted_units) == 1:
        initial_unit_name = faulted_units[0]
        initiating_unit = fleet[initial_unit_name]
        cold = initiating_unit.simulate(t_max_h=24.0, dt_s=1.0, sample_s=60.0)
        if cold.t_trip_h is None:
            raise RuntimeError(f"{initial_unit_name} did not trip within the 24 h horizon")
        trip_h = float(cold.t_trip_h)
        initially_tripped_units = (initial_unit_name,)
    else:
        fault_trials: dict[str, tuple[list[dict], dict, dict | None]] = {}
        for name in faulted_units:
            u = fleet[name]
            initial_state = initial_cooling_state(u, u.pg0_mw)
            fault_trials[name] = simulate_cooling_segment(
                u, state=initial_state, p_final_mw=u.pg0_mw,
                pg_profile={0: {u.bus: u.pg0_mw}}, trip_h=0.0,
                start_elapsed_s=0.0, duration_s=cooling_horizon_s,
                assumptions=assumptions, dt_s=assumptions["power_time_step_s"],
                sample_s=60.0, record_start=True, makeup_interrupted=True)
        event_candidates = [(name, trial[2]) for name, trial in fault_trials.items()
                            if trial[2] is not None]
        if not event_candidates:
            raise RuntimeError(f"No faulted unit trips within {cooling_horizon_s/3600:g} h")
        first_trip_s = min(float(event["elapsed_s"]) for _, event in event_candidates)
        simultaneous_names = tuple(sorted(name for name, event in event_candidates
                                          if float(event["elapsed_s"]) <= first_trip_s + 1e-3))
        initial_unit_name = simultaneous_names[0]
        initiating_unit = fleet[initial_unit_name]
        trip_h = first_trip_s / 3600.0
        initially_tripped_units = simultaneous_names
        for name in faulted_units:
            u = fleet[name]
            rows, state, event = simulate_cooling_segment(
                u, state=initial_cooling_state(u, u.pg0_mw), p_final_mw=u.pg0_mw,
                pg_profile={0: {u.bus: u.pg0_mw}}, trip_h=0.0,
                start_elapsed_s=0.0, duration_s=first_trip_s,
                assumptions=assumptions, dt_s=assumptions["power_time_step_s"],
                sample_s=60.0, record_start=True, makeup_interrupted=True)
            pre_event_rows.extend(rows)
            pre_event_states[u.bus] = state
            if event is not None and float(event["elapsed_s"]) <= first_trip_s + 1e-3:
                event["initial_makeup_pair"] = True
                pre_event_trip_events.append(event)
        if {e["unit"] for e in pre_event_trip_events} != set(initially_tripped_units):
            raise RuntimeError("初始双机跳闸集合与补水中断预演不一致")

    initiating_bus = initiating_unit.bus
    initial_unit_names_label = "+".join(faulted_units)
    initial_trip_names_label = ";".join(initially_tripped_units)
    initial_makeup_buses = {fleet[name].bus for name in faulted_units}
    initial_event_buses = {fleet[name].bus for name in initially_tripped_units}
    cold = cold if len(faulted_units) == 1 else None
    base_load_mw = float(base_case["bus"][:, 2].sum())
    base_gen_mw = sum(base_pg.values())

    cfg_grid = cases.cfg()
    cfg_grid.update(f_uf=[0.0, 0.0, 0.0], f_gen_trip=-1e6, f_of=1e6)
    cfg_freq = cases.cfg()  # 保留 59.30/58.90/58.50 Hz 的时域 UFLS 定值

    def gen_map(result: dict) -> dict[int, dict]:
        return {int(g["bus"]): g for g in result["gen_final"]}

    def add_dispatch_rows(rows: list[dict], offset_s: float, stage: int) -> None:
        for r in rows:
            row = dict(r)
            row["event_stage"] = stage
            row["elapsed_s"] = round(offset_s + float(r["elapsed_s"]), 3)
            row["system_t_h"] = round(trip_h + row["elapsed_s"] / 3600.0, 5)
            dispatch_rows.append(row)

    dispatch_rows: list[dict] = []
    cooling_rows: list[dict] = list(pre_event_rows)
    cold_trip_events: list[dict] = []
    pre_event_recorded_buses = {int(r["bus"]) for r in pre_event_rows}
    grid_trip_buses: set[int] = set()
    all_failed_buses: set[int] = set()  # legacy composite indicator; retained for compatibility
    all_hard_failure_buses: set[int] = set()
    f1_new_buses_seen: set[int] = set()
    f2a_buses_seen: set[int] = set()
    f2b_buses_seen: set[int] = set()
    f3_buses_seen: set[int] = set()
    emergency_actions = {"uvls", "ufls", "line_overload_trip", "gen_trip_voltage",
                         "gen_trip_underfreq", "gen_trip_overfreq", "load_shed_vcls"}
    emergency_actions_seen: set[str] = set()

    def record_grid_result(result: dict) -> None:
        for bus, d in result["bus"].items():
            bus = int(bus)
            if d["I"]:
                all_failed_buses.add(bus)
            if d["F1_new"]:
                f1_new_buses_seen.add(bus)
            if d["F2a"]:
                f2a_buses_seen.add(bus)
            if d["F2b"]:
                f2b_buses_seen.add(bus)
            if d["F3"]:
                f3_buses_seen.add(bus)
            if d["F3"] or d["F2b"]:
                all_hard_failure_buses.add(bus)
        emergency_actions_seen.update(
            action for stage_id, action, _ in result["log"]
            if stage_id > 0 and action in emergency_actions)

    static_shed_total = 0.0
    ramp_energy_gap_command_mwh = 0.0
    ramp_energy_gap_settle_mwh = 0.0
    pg_settling_s = 0.0
    pg_settling_tolerance_mw = 0.01
    ufls_shed_total = 0.0
    ufls_event_log: list[str] = []
    ramp_completion_s = 0.0
    f_nadir_hz = cfg_grid["f0"]
    t_f_nadir_s = 0.0
    rocof_hz_s = 0.0
    final_frequency_hz = cfg_grid["f0"]

    # Stage 1: the selected initiating unit trips and the network computes a redispatch target.
    target_sim = CascadeSim(case=copy.deepcopy(base_case), cfg=cfg_grid,
                            sync_dispatch=True)
    target_result = target_sim.run_scenario(gen_trip=sorted(initial_event_buses))
    target_gen = gen_map(target_result)
    initial_trip_buses = set(initial_event_buses)
    initial_trip_buses.update(b for b, g in target_gen.items()
                              if b not in initial_event_buses and not g["online"] and base_pg.get(b, 0.0) > 0)
    grid_trip_buses.update(initial_trip_buses - initial_event_buses)
    target_pg = {b: (float(g["pg_mw"]) if g["online"] else 0.0)
                 for b, g in target_gen.items()}
    initial_lost_mw = sum(base_pg.get(b, 0.0) for b in initial_trip_buses)
    freq_rows, pg_profile, freq_summary = simulate_frequency_ramp(
        base_pg, target_pg, fleet, lost_mw=initial_lost_mw,
        base_load_mw=base_load_mw, base_gen_mw=base_gen_mw,
        cfg=cfg_freq, assumptions=assumptions,
        trip_buses=tuple(sorted(initial_trip_buses)))
    add_dispatch_rows(freq_rows, 0.0, 1)
    initial_profile_end = pg_profile[max(pg_profile)].copy()
    for b in initial_trip_buses:
        initial_profile_end[b] = 0.0

    # Apply UFLS from the time-domain frequency result, then run the post-ramp AC cascade.
    final_case = copy.deepcopy(base_case)
    if freq_summary["ufls_shed_mw"] > 0:
        factor = max(0.0, (base_load_mw - freq_summary["ufls_shed_mw"]) / base_load_mw)
        final_case["bus"][:, 2] *= factor
        final_case["bus"][:, 3] *= factor
    final_sim = CascadeSim(case=final_case, cfg=cfg_grid, sync_dispatch=True)
    final_result = final_sim.run_scenario(
        gen_trip=sorted(initial_trip_buses), dispatch_override=initial_profile_end)
    current_grid_case = final_result["case_final"]
    current_grid = gen_map(final_result)
    current_pg_final = {b: (float(g["pg_mw"]) if g["online"] else 0.0)
                        for b, g in current_grid.items()}
    stage_target_generation_mw = sum(current_pg_final.values())
    ramp_energy_gap_command_mwh += positive_ramp_gap_mwh(
        freq_rows, stage_target_generation_mw, float(freq_summary["ramp_completion_s"]))
    stage_settle_s = pg_settling_time_s(freq_rows, current_pg_final, pg_settling_tolerance_mw)
    if stage_settle_s is None:
        stage_settle_s = float(freq_summary["ramp_completion_s"])
    pg_settling_s = max(pg_settling_s, stage_settle_s)
    ramp_energy_gap_settle_mwh += positive_ramp_gap_mwh(
        freq_rows, stage_target_generation_mw, stage_settle_s)
    grid_trip_buses.update(b for b, g in current_grid.items()
                           if not g["online"] and b not in initial_trip_buses)
    record_grid_result(final_result)
    solver_failure_detected = stop_on_solver_failure and bool(f2b_buses_seen)
    static_shed_total += float(final_result["total_shed"])
    ufls_shed_total += float(freq_summary["ufls_shed_mw"])
    if freq_summary["ufls_events"]:
        ufls_event_log.append(f"stage1:{freq_summary['ufls_events']}")
    ramp_completion_s = float(freq_summary["ramp_completion_s"])
    f_nadir_hz = float(freq_summary["f_nadir_hz"])
    t_f_nadir_s = float(freq_summary["t_f_nadir_s"])
    rocof_hz_s = float(freq_summary["rocof_hz_s"])
    final_frequency_hz = float(freq_summary["final_frequency_hz"])

    cooling_states = {u.bus: initial_cooling_state(u, u.pg0_mw)
                      for u in fleet.values()}
    cooling_states.update(pre_event_states)
    if cold is not None and cold.level_m:
        cooling_states[initiating_bus]["min_basin_level_m"] = min(cold.level_m)
    current_profile = pg_profile
    current_elapsed_s = 0.0
    stage = 1
    online_buses = {b for b, g in current_grid.items()
                    if g["online"] and b in cooling_states}
    # Ordinary F1/F2a states do not end the study. Stop cooling feedback only after
    # modelled hard service loss (F3/F2b); otherwise continue to the configured horizon.
    cooling_tracking_end_s = cooling_horizon_s
    if all_hard_failure_buses and stop_at_hard_service_loss:
        cooling_tracking_end_s = min(cooling_horizon_s, float(max(pg_profile)))

    def offline_row(u: Unit, elapsed_s: float, status: str) -> dict:
        return dict(unit=u.name, bus=u.bus, elapsed_min=round(elapsed_s / 60.0, 3),
                    system_t_h=round(trip_h + elapsed_s / 3600.0, 4),
                    pg_command_mw=0.0, basin_level_m="", qcw_m3s=0.0,
                    heat_reject_mw_th=0.0, evaporation_m3h=0.0,
                    blowdown_m3h=0.0, makeup_required_m3h=0.0,
                    makeup_supply_m3h=0.0, backpressure_kpa="",
                    thermal_cap_mw=0.0, status=status)

    for u in fleet.values():
        if u.bus not in online_buses and u.bus not in pre_event_recorded_buses:
            cooling_rows.append(offline_row(u, 0.0,
                                            "tripped" if u.bus in initial_event_buses else "grid_trip"))

    # Each later cold-end trip starts a new grid dispatch/frequency stage. Cooling states
    # are carried across stages; the first trip time is found by advancing all live units.
    while (current_elapsed_s < cooling_tracking_end_s - 1e-9 and online_buses
           and not solver_failure_detected):
        segment_start_s = current_elapsed_s
        segment_clock_s = (trip_h * 3600.0 + segment_start_s
                           if len(faulted_units) > 1 else segment_start_s)
        segment_duration_s = cooling_tracking_end_s - segment_start_s
        candidate_events: list[dict] = []
        segment_trials: dict[int, tuple[list[dict], dict, dict | None]] = {}
        for bus in sorted(online_buses):
            u = next(x for x in fleet.values() if x.bus == bus)
            trial = simulate_cooling_segment(
                u, state=cooling_states[bus], p_final_mw=current_pg_final.get(bus, 0.0),
                pg_profile=current_profile,
                trip_h=(0.0 if len(faulted_units) > 1 else trip_h),
                start_elapsed_s=segment_clock_s, duration_s=segment_duration_s,
                assumptions=assumptions, dt_s=assumptions["power_time_step_s"],
                sample_s=60.0,
                record_start=(segment_start_s == 0.0 and not pre_event_rows),
                makeup_interrupted=(bus in initial_makeup_buses))
            segment_trials[bus] = trial
            if trial[2]:
                candidate_events.append(trial[2])

        if not candidate_events:
            for bus, (rows, state, _) in segment_trials.items():
                cooling_rows.extend(rows)
                cooling_states[bus] = state
            current_elapsed_s = cooling_tracking_end_s
            break

        earliest_s = min(float(e["elapsed_s"]) for e in candidate_events)
        segment_to_trip_s = max(0.0, earliest_s - segment_clock_s)
        trip_now: list[dict] = []
        for bus in sorted(online_buses):
            u = next(x for x in fleet.values() if x.bus == bus)
            rows, state, event = simulate_cooling_segment(
                u, state=cooling_states[bus], p_final_mw=current_pg_final.get(bus, 0.0),
                pg_profile=current_profile,
                trip_h=(0.0 if len(faulted_units) > 1 else trip_h),
                start_elapsed_s=segment_clock_s, duration_s=segment_to_trip_s,
                assumptions=assumptions, dt_s=assumptions["power_time_step_s"],
                sample_s=60.0,
                record_start=(segment_start_s == 0.0 and not pre_event_rows),
                makeup_interrupted=(bus in initial_makeup_buses))
            cooling_rows.extend(rows)
            cooling_states[bus] = state
            if event and float(event["elapsed_s"]) <= earliest_s + assumptions["power_time_step_s"]:
                trip_now.append(event)
        if not trip_now:
            raise RuntimeError("冷端跳机候选未能在事件时刻重现")
        cold_trip_events.extend(trip_now)
        cold_trip_buses = {int(e["bus"]) for e in trip_now}
        current_elapsed_s += segment_to_trip_s

        # Reconstruct the pre-trip electrical dispatch at the event time.
        local_event_s = int(round(earliest_s - segment_clock_s))
        p_event = current_profile.get(local_event_s, current_pg_final).copy()
        event_case = copy.deepcopy(current_grid_case)
        for i, g in enumerate(event_case["gen"]):
            bus = int(g[GEN_BUS])
            if g[GEN_STATUS] > 0:
                event_case["gen"][i, GEN_PG] = max(0.0, float(p_event.get(bus, g[GEN_PG])))

        event_load_mw = float(event_case["bus"][:, 2].sum())
        event_gen_mw = float(event_case["gen"][event_case["gen"][:, GEN_STATUS] > 0,
                                                 GEN_PG].sum())
        event_sim = CascadeSim(case=event_case, cfg=cfg_grid, sync_dispatch=True)
        event_target = event_sim.run_scenario(gen_trip=sorted(cold_trip_buses))
        event_target_f2b = {int(b) for b,d in event_target["bus"].items() if d["F2b"]}
        if stop_on_solver_failure and event_target_f2b:
            record_grid_result(event_target)
            solver_failure_detected = True
            final_result = event_target
            static_shed_total += float(event_target["total_shed"])
            current_grid_case = event_target["case_final"]
            current_grid = gen_map(event_target)
            current_pg_final = {b:(float(g["pg_mw"]) if g["online"] else 0.0)
                                for b,g in current_grid.items()}
            grid_trip_buses.update(b for b,g in current_grid.items() if not g["online"])
            online_buses = {b for b,g in current_grid.items()
                            if g["online"] and b in cooling_states}
            break
        event_target_gen = gen_map(event_target)
        newly_off = {b for b, g in event_target_gen.items()
                     if not g["online"] and event_case["gen"][event_sim.gen_bus[b], GEN_STATUS] > 0}
        newly_off.update(cold_trip_buses)
        lost_event_mw = sum(float(p_event.get(b, 0.0)) for b in newly_off)
        if lost_event_mw <= 1e-9:
            raise RuntimeError(f"二次保护事件没有可计的发电损失: {sorted(newly_off)}")
        target_event_pg = {b: (float(g["pg_mw"]) if g["online"] else 0.0)
                           for b, g in event_target_gen.items()}
        freq_lookup = {int(r["elapsed_s"]): float(r["frequency_hz"])
                       for r in freq_rows}
        initial_f = freq_lookup.get(local_event_s, final_frequency_hz)
        # Use the nearest current-stage frequency sample if the event follows an earlier ramp.
        if stage > 1:
            freq_lookup = {int(r["elapsed_s"]): float(r["frequency_hz"])
                           for r in current_freq_rows}
            initial_f = freq_lookup.get(local_event_s, final_frequency_hz)
        next_rows, next_profile, next_summary = simulate_frequency_ramp(
            p_event, target_event_pg, fleet, lost_mw=lost_event_mw,
            base_load_mw=event_load_mw, base_gen_mw=event_gen_mw,
            cfg=cfg_freq, assumptions=assumptions,
            trip_buses=tuple(sorted(newly_off)), initial_frequency_hz=initial_f)
        stage += 1
        add_dispatch_rows(next_rows, current_elapsed_s, stage)
        current_freq_rows = next_rows
        current_profile = next_profile
        next_profile_end = next_profile[max(next_profile)].copy()
        for b in newly_off:
            next_profile_end[b] = 0.0

        # Apply the UFLS amount for this event stage, then continue the network cascade.
        stage_case = copy.deepcopy(event_case)
        if next_summary["ufls_shed_mw"] > 0 and event_load_mw > 0:
            factor = max(0.0, (event_load_mw - next_summary["ufls_shed_mw"]) / event_load_mw)
            stage_case["bus"][:, 2] *= factor
            stage_case["bus"][:, 3] *= factor
        stage_sim = CascadeSim(case=stage_case, cfg=cfg_grid, sync_dispatch=True)
        final_result = stage_sim.run_scenario(
            gen_trip=sorted(newly_off), dispatch_override=next_profile_end)
        current_grid_case = final_result["case_final"]
        current_grid = gen_map(final_result)
        current_pg_final = {b: (float(g["pg_mw"]) if g["online"] else 0.0)
                            for b, g in current_grid.items()}
        stage_target_generation_mw = sum(current_pg_final.values())
        ramp_energy_gap_command_mwh += positive_ramp_gap_mwh(
            next_rows, stage_target_generation_mw, float(next_summary["ramp_completion_s"]))
        stage_settle_s = pg_settling_time_s(next_rows, current_pg_final,
                                             pg_settling_tolerance_mw)
        if stage_settle_s is None:
            stage_settle_s = float(next_summary["ramp_completion_s"])
        pg_settling_s = max(pg_settling_s, current_elapsed_s + stage_settle_s)
        ramp_energy_gap_settle_mwh += positive_ramp_gap_mwh(
            next_rows, stage_target_generation_mw, stage_settle_s)
        grid_trip_buses.update(b for b, g in current_grid.items()
                               if not g["online"] and b not in cold_trip_buses
                               and b != initiating_bus)
        record_grid_result(final_result)
        if stop_on_solver_failure and any(d["F2b"] for d in final_result["bus"].values()):
            solver_failure_detected = True
        static_shed_total += float(final_result["total_shed"])
        ufls_shed_total += float(next_summary["ufls_shed_mw"])
        if next_summary["ufls_events"]:
            ufls_event_log.append(f"stage{stage}:{next_summary['ufls_events']}")
        if next_summary["f_nadir_hz"] < f_nadir_hz:
            f_nadir_hz = float(next_summary["f_nadir_hz"])
            t_f_nadir_s = current_elapsed_s + float(next_summary["t_f_nadir_s"])
        rocof_hz_s = min(rocof_hz_s, float(next_summary["rocof_hz_s"]))
        ramp_completion_s = max(ramp_completion_s,
                                current_elapsed_s + float(next_summary["ramp_completion_s"]))
        final_frequency_hz = float(next_summary["final_frequency_hz"])
        online_buses = {b for b, g in current_grid.items()
                        if g["online"] and b in cooling_states}
        if solver_failure_detected:
            break
        if all_hard_failure_buses and stop_at_hard_service_loss:
            break

    final_grid = gen_map(final_result)
    demand_rows: list[dict] = []
    for u in fleet.values():
        before = model.steady_state(u.params, p_setpoint_mw=u.pg0_mw)
        g = final_grid.get(u.bus, {"online": False, "pg_mw": 0.0})
        online_after = bool(g["online"])
        p_after = float(g["pg_mw"]) if online_after else 0.0
        after = model.steady_state(u.params, p_setpoint_mw=p_after) if p_after > 1e-9 else None
        state = cooling_states.get(u.bus)
        demand_rows.append(dict(
            unit=u.name, bus=u.bus, online_after_grid=online_after,
            pg_before_mw=round(u.pg0_mw, 4), pg_after_mw=round(p_after, 4),
            delta_pg_mw=round(p_after - u.pg0_mw, 4),
            qg_before_mvar=round(base_qg.get(u.bus, 0.0), 4),
            qg_after_mvar=round(float(g.get("qg_mvar", 0.0)), 4) if online_after else 0.0,
            makeup_before_m3h=round(before["makeup_m3s"] * 3600, 3),
            makeup_after_steady_m3h=round(after["makeup_m3s"] * 3600, 3) if after else 0.0,
            delta_makeup_m3h=round((after["makeup_m3s"] - before["makeup_m3s"]) * 3600, 3)
                              if after else round(-before["makeup_m3s"] * 3600, 3),
            heat_before_mw_th=round(before["heat_reject_mw_th"], 3),
            heat_after_steady_mw_th=round(after["heat_reject_mw_th"], 3) if after else 0.0,
            makeup_capacity_m3h=round(model.design_makeup_m3s(u.params) *
                                       assumptions["makeup_capacity_factor"] * 3600, 3),
            minimum_basin_level_m=round(state["min_basin_level_m"], 4) if state else "",
            maximum_thermal_shortfall_mw=round(state["maximum_thermal_shortfall_mw"], 4)
                                         if state else ""))

    survivor_demands = [x for x in demand_rows if x["online_after_grid"]]
    makeup_before_survivors = sum(x["makeup_before_m3h"] for x in survivor_demands)
    makeup_after_survivors = sum(x["makeup_after_steady_m3h"] for x in survivor_demands)
    observed_faulted_trips = set(initially_tripped_units)
    observed_faulted_trips.update(e["unit"] for e in cold_trip_events)
    if solver_failure_detected:
        simulation_stop_reason = "solver_failure_F2b"
    elif set(faulted_units).issubset(observed_faulted_trips):
        simulation_stop_reason = "all_faulted_units_tripped"
    elif not online_buses and all_hard_failure_buses:
        simulation_stop_reason = "all_generators_offline_after_hard_service_loss"
    elif not online_buses:
        simulation_stop_reason = "all_cooling_units_offline"
    elif all_hard_failure_buses and stop_at_hard_service_loss:
        simulation_stop_reason = "hard_service_loss_F3_or_F2b"
    elif current_elapsed_s >= cooling_horizon_s - 1e-6:
        simulation_stop_reason = "configured_24h_cooling_horizon"
    else:
        simulation_stop_reason = "simulation_ended_before_horizon"
    for b, d in final_result["bus"].items():
        if d["I"]:
            all_failed_buses.add(int(b))
    terminal_voltage = final_result["trace"][-1]["volt"] if final_result["trace"] else {}
    terminal_f1_buses = sorted(
        b for b, v in terminal_voltage.items()
        if (v < final_sim.vlim.get(b, (cfg_grid["v_lo"], cfg_grid["v_hi"]))[0] - 1e-8 or
            v > final_sim.vlim.get(b, (cfg_grid["v_lo"], cfg_grid["v_hi"]))[1] + 1e-8))
    has_emergency_action = bool(emergency_actions_seen)
    n_f2a, n_f2b, n_f3 = len(f2a_buses_seen), len(f2b_buses_seen), len(f3_buses_seen)
    hard_failure_buses = sorted(all_hard_failure_buses)
    if n_f2a or n_f2b or n_f3 or final_result["n_bus_dead"]:
        impact_class = "N3_collapse_or_deenergization"
    elif has_emergency_action or static_shed_total > 1e-6 or ufls_shed_total > 1e-6:
        impact_class = "N2_emergency_control_or_shedding"
    elif f1_new_buses_seen:
        impact_class = "N1_voltage_violation_no_emergency_action"
    else:
        impact_class = "N0_no_recorded_violation_or_action"
    summary = [dict(
        operating_point="IEEE30_base_load", total_load_mw=round(base_load_mw, 3),
        base_generation_after_pf_mw=round(base_gen_mw, 4),
        base_pg_bus1_mw=round(base_pg.get(1, 0.0), 4),
        initial_unit=initial_unit_names_label,
        initial_unit_bus=(";".join(str(fleet[n].bus) for n in faulted_units)
                          if len(faulted_units) > 1 else initiating_bus),
        initial_event=(f"{initial_unit_name}_makeup_interruption" if len(faulted_units) == 1
                       else f"simultaneous_makeup_interruption:{initial_unit_names_label}"),
        initial_makeup_interruption_start_h=0.0,
        initial_makeup_failure_units=";".join(faulted_units),
        initial_trip_units=initial_trip_names_label,
        initial_trip_buses=";".join(str(b) for b in sorted(initial_event_buses)),
        initial_trip_events=";".join(
            f"{e['unit']}@{float(e['elapsed_s'])/3600.0:.5f}h" for e in pre_event_trip_events),
        initial_trip_h=round(trip_h, 4),
        initial_trip_pg_mw=round(sum(base_pg[b] for b in initial_event_buses), 4),
        g13_trip_h=round(trip_h, 4) if initial_unit_name == "G13" else "",
        g13_trip_pg_mw=round(base_pg[initiating_bus], 4) if initial_unit_name == "G13" else "",
        dispatch_ramp_frac_pmax_per_min=assumptions["ramp_frac_pmax_per_min"],
        dispatch_delay_s=assumptions["redispatch_delay_s"],
        makeup_capacity_factor=assumptions["makeup_capacity_factor"],
        makeup_response_tau_s=assumptions["makeup_response_tau_s"],
        post_trip_cooling_horizon_h=assumptions["post_trip_cooling_horizon_h"],
        cooling_tracking_elapsed_h=round(current_elapsed_s / 3600.0, 4),
        simulation_stop_reason=simulation_stop_reason,
        f_nadir_hz=round(f_nadir_hz, 5), t_f_nadir_s=round(t_f_nadir_s, 3),
        rocof_hz_s=round(rocof_hz_s, 5), ufls_shed_mw=round(ufls_shed_total, 4),
        ufls_events=";".join(ufls_event_log),
        frequency_final_hz=round(final_frequency_hz, 5),
        ramp_completion_s=round(ramp_completion_s, 3),
        pg_settling_s=round(pg_settling_s, 3),
        pg_settling_tolerance_mw=pg_settling_tolerance_mw,
        dispatch_ramp_energy_gap_to_command_end_mwh=round(ramp_energy_gap_command_mwh, 6),
        dispatch_ramp_energy_gap_to_pg_settle_mwh=round(ramp_energy_gap_settle_mwh, 6),
        energy_gap_definition="positive integral of terminal-Pg minus actual total Pg; not EENS", 
        static_grid_shed_mw=round(static_shed_total, 4),
        total_shed_mw=round(ufls_shed_total + static_shed_total, 4),
        n_bus_failed=len(all_failed_buses),
        n_f1_new=len(f1_new_buses_seen),
        n_f2_voltage_collapse=n_f2a,
        n_f2_pf_divergence=n_f2b,
        n_f3_deenergized=n_f3,
        n_bus_dead=final_result["n_bus_dead"],
        n_bus_hard_failure=len(hard_failure_buses),
        hard_failure_buses=";".join(str(b) for b in hard_failure_buses),
        hard_failure_definition=("modelled_hard_service_loss:F3_deenergized_or_F2b_unresolved_AC_collapse; "
                                 "excludes_F1/F2a_alone; not_physical_damage"),
        n_f1_terminal=len(terminal_f1_buses),
        f1_terminal_buses=";".join(str(b) for b in terminal_f1_buses),
        impact_class=impact_class,
        impact_class_definition=("operational state class, not scalar severity rank; "
                                 "N0=no violation/action; N1=F1 only; "
                                 "N2=emergency control/load shed; N3=F2/F3/deenergization"),
        emergency_actions=";".join(sorted(emergency_actions_seen)),
        bus_failure_definition=("LEGACY_composite_metric:F1_new_or_F2a_or_F2b_or_F3; "
                                "includes_voltage-limit_violation; not_primary_hard_failure_endpoint"), 
        bfi=round(len(all_failed_buses) / len(final_sim.bus_ids), 4),
        failed_buses=";".join(str(b) for b in sorted(all_failed_buses)),
        f1_new_buses=";".join(str(b) for b in sorted(f1_new_buses_seen)),
        f2_voltage_collapse_buses=";".join(str(b) for b in sorted(f2a_buses_seen)),
        f2_pf_divergence_buses=";".join(str(b) for b in sorted(f2b_buses_seen)),
        f3_deenergized_buses=";".join(str(b) for b in sorted(f3_buses_seen)),
        grid_additional_gen_trips=";".join(str(b) for b in sorted(grid_trip_buses)),
        makeup_before_total_m3h=round(sum(x["makeup_before_m3h"] for x in demand_rows), 3),
        makeup_after_total_m3h=round(sum(x["makeup_after_steady_m3h"] for x in demand_rows), 3),
        makeup_before_survivors_m3h=round(makeup_before_survivors, 3),
        makeup_after_survivors_m3h=round(makeup_after_survivors, 3),
        delta_makeup_survivors_m3h=round(makeup_after_survivors - makeup_before_survivors, 3),
        other_coldend_trips=len(cold_trip_events),
        other_coldend_trip_events=";".join(
            f"{e['unit']}@{e['elapsed_s']:.0f}s" for e in cold_trip_events),
        frequency_model="SFR_governor_plus_ramp_limited_dispatch_event_loop",
        grid_model="post-ramp_quasi_steady_cascade",
    )]
    return summary, demand_rows, cooling_rows, dispatch_rows, assumptions
def write_scenario_outputs(out: Path, summary: list[dict], demand_rows: list[dict],
                           cooling_rows: list[dict], dispatch_rows: list[dict]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "cascade_summary.csv", summary)
    _write_csv(out / "redispatch_cooling_demand.csv", demand_rows)
    _write_csv(out / "cooling_demand_response.csv", cooling_rows)
    _write_csv(out / "dispatch_trajectory.csv", dispatch_rows)
    # 假设参数统一保存在 data/coldend/coupling_reference_assumptions.csv；
    # 结果目录不重复复制同一份参数表，以保持唯一事实来源。


def comparison_row(row: dict, *, default_unit: str = "") -> dict:
    unit_name = row.get("initial_unit") or default_unit
    trip_h = row.get("initial_trip_h") or row.get("g13_trip_h", "")
    trip_pg = row.get("initial_trip_pg_mw") or row.get("g13_trip_pg_mw", "")
    return dict(
        initial_unit=unit_name,
        initial_unit_bus=row.get("initial_unit_bus", 13 if unit_name == "G13" else ""),
        initial_trip_h=trip_h,
        initial_trip_pg_mw=trip_pg,
        ramp_completion_s=row.get("ramp_completion_s", ""),
        pg_settling_s=row.get("pg_settling_s", ""),
        ramp_energy_gap_to_settle_mwh=row.get("dispatch_ramp_energy_gap_to_pg_settle_mwh", ""),
        f_nadir_hz=row.get("f_nadir_hz", ""),
        rocof_hz_s=row.get("rocof_hz_s", ""),
        ufls_shed_mw=row.get("ufls_shed_mw", ""),
        total_shed_mw=row.get("total_shed_mw", ""),
        n_bus_failed=row.get("n_bus_failed", ""),
        bus_failure_definition=row.get(
            "bus_failure_definition",
            "LEGACY_composite_metric:F1_new_or_F2a_or_F2b_or_F3; "
            "includes_voltage-limit_violation; not_primary_hard_failure_endpoint"),
        n_f1_new=row.get("n_f1_new", "0" if unit_name == "G13" else ""),
        n_f2_voltage_collapse=row.get("n_f2_voltage_collapse", "0" if unit_name == "G13" else ""),
        n_f2_pf_divergence=row.get("n_f2_pf_divergence", "0" if unit_name == "G13" else ""),
        n_f3_deenergized=row.get("n_f3_deenergized", "0" if unit_name == "G13" else ""),
        n_bus_dead=row.get("n_bus_dead", "0" if unit_name == "G13" else ""),
        n_bus_hard_failure=row.get("n_bus_hard_failure", "0" if unit_name == "G13" else ""),
        hard_failure_buses=row.get("hard_failure_buses", ""),
        hard_failure_definition=row.get(
            "hard_failure_definition",
            "modelled_hard_service_loss:F3_deenergized_or_F2b_unresolved_AC_collapse; "
            "excludes_F1/F2a_alone; not_physical_damage"),
        n_f1_terminal=row.get("n_f1_terminal", "0" if unit_name == "G13" else ""),
        f1_terminal_buses=row.get("f1_terminal_buses", ""),
        cooling_tracking_elapsed_h=row.get(
            "cooling_tracking_elapsed_h", "24.0" if unit_name == "G13" else ""),
        simulation_stop_reason=row.get(
            "simulation_stop_reason", "legacy_G13_full_24h_track" if unit_name == "G13" else ""),
        impact_class=row.get("impact_class", "N0_no_recorded_violation_or_action"
                             if unit_name == "G13" else ""),
        failed_buses=row.get("failed_buses", ""),
        grid_additional_gen_trips=row.get("grid_additional_gen_trips", ""),
        makeup_before_survivors_m3h=row.get("makeup_before_survivors_m3h", ""),
        makeup_after_survivors_m3h=row.get("makeup_after_survivors_m3h", ""),
        delta_makeup_survivors_m3h=row.get("delta_makeup_survivors_m3h", ""),
        other_coldend_trips=row.get("other_coldend_trips", ""),
        other_coldend_trip_events=row.get("other_coldend_trip_events", ""),
    )


def run_selected_units(unit_names: list[str], output_root: Path) -> list[dict]:
    output_root.mkdir(parents=True, exist_ok=True)
    summaries: list[dict] = []
    for unit_name in unit_names:
        summary, demand_rows, cooling_rows, dispatch_rows, _ = simulate_single_unit_dynamic(unit_name)
        write_scenario_outputs(output_root / "scenarios" / unit_name, summary, demand_rows,
                               cooling_rows, dispatch_rows)
        summaries.extend(summary)
        row = summary[0]
        print(f"{unit_name}: t_trip={row['initial_trip_h']:.4f} h, "
              f"P_trip={row['initial_trip_pg_mw']:.3f} MW, "
              f"f_nadir={row['f_nadir_hz']:.3f} Hz, "
              f"legacy_composite={row['n_bus_failed']}/30 "
              f"(F1 any/terminal={row['n_f1_new']}/{row['n_f1_terminal']}, "
              f"F2a/F2b/F3={row['n_f2_voltage_collapse']}/"
              f"{row['n_f2_pf_divergence']}/{row['n_f3_deenergized']}, "
              f"hard_bus_failure={row['n_bus_hard_failure']}, "
              f"class={row['impact_class']}), "
              f"secondary_cold_trips={row['other_coldend_trips']}")

    _write_csv(output_root / "tables" / "scenario_summary.csv", summaries)
    # 共享假设的唯一来源：data/coldend/coupling_reference_assumptions.csv。

    comparison = []
    existing_g13 = OUT / "cascade_summary.csv"
    if "G13" not in unit_names and existing_g13.exists():
        with existing_g13.open(newline="", encoding="utf-8") as f:
            old_rows = list(csv.DictReader(f))
        if old_rows:
            comparison.append(comparison_row(old_rows[0], default_unit="G13"))
    comparison.extend(comparison_row(row) for row in summaries)
    if comparison:
        _write_csv(output_root / "tables" / "six_unit_comparison.csv", comparison)
    print("结果 →", output_root)
    return summaries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IEEE30 单机补水中断—动态再调度—冷端/母线级联")
    parser.add_argument("--units", default="G13",
                        help="逗号分隔机组名；默认 G13。可用 all 或如 G1,G2,G22,G23,G27")
    parser.add_argument("--output-root", default=None,
                        help="K1 批量情景输出根目录；默认写入 results/K1/")
    args = parser.parse_args(argv)
    fleet_names = sorted(load_fleet())
    if args.units.strip().lower() == "all":
        unit_names = fleet_names
    else:
        unit_names = [x.strip() for x in args.units.split(",") if x.strip()]
    if not unit_names or len(unit_names) != len(set(unit_names)):
        parser.error("--units 不能为空且不能重复")
    unknown = sorted(set(unit_names) - set(fleet_names))
    if unknown:
        parser.error(f"未知机组 {unknown}; available={fleet_names}")

    if unit_names == ["G13"] and args.output_root is None:
        summary, demand_rows, cooling_rows, dispatch_rows, _ = simulate_single_unit_dynamic("G13")
        write_scenario_outputs(OUT, summary, demand_rows, cooling_rows, dispatch_rows)
        r = summary[0]
        print("G13 补水中断 → 再调度爬坡/频率动态 → 冷端需水动态 → 终态母线级联")
        print(f"  IEEE30 基准负荷 {r['total_load_mw']:.3f} MW；G13 @ {r['initial_trip_h']:.4f} h 跳机")
        print(f"  参考爬坡 {r['dispatch_ramp_frac_pmax_per_min']:.1%} Pmax/min，"
              f"命令延时 {r['dispatch_delay_s']:.0f}s；命令爬坡 {r['ramp_completion_s']:.1f}s，"
              f"Pg 收敛(±{r['pg_settling_tolerance_mw']:.2f} MW) {r['pg_settling_s']:.1f}s")
        print(f"  相对终态出力的爬坡缺额面积 {r['dispatch_ramp_energy_gap_to_pg_settle_mwh']:.6f} MWh "
              f"(命令爬坡窗 {r['dispatch_ramp_energy_gap_to_command_end_mwh']:.6f} MWh；非 EENS)")
        print(f"  频率最低 {r['f_nadir_hz']:.3f} Hz；UFLS {r['ufls_shed_mw']:.3f} MW；"
              f"旧复合指标 {r['n_bus_failed']}/30；硬失供 {r['n_bus_hard_failure']}/30")
        print(f"  幸存机组补水需求 {r['makeup_before_survivors_m3h']:.1f}→"
              f"{r['makeup_after_survivors_m3h']:.1f} m³/h "
              f"(Δ{r['delta_makeup_survivors_m3h']:+.1f})；"
              f"24 h 内其他冷端跳机 {r['other_coldend_trips']}")
        print("  注意：参考假设非现场数据；线路/电压级联按爬坡结束后的准稳态求解。")
        print("结果 →", OUT)
    else:
        output_root = Path(args.output_root) if args.output_root else BATCH_OUT
        run_selected_units(unit_names, output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
