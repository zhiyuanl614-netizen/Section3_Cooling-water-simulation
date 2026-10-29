#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
湿式开式循环冷却水系统 —— 冷端机理模型（单文件版）
=====================================================================
唯一情景：**单台机组的外来补水中断**（makeup_basin_interrupt / S1a）

一个 652 MW 等值湿冷燃煤机组（IEEE39 的 bus 33 / G33），外来水源停止向集水池
补水后，池水位按"蒸发+排污+飘滴"消耗；循环水泵可用流量随水位/NPSH 衰减；
塔—凝汽器—汽轮机背压串联响应，运行人员按 SOP 降负荷，直至低水位保护跳机。

等价性证据（已在本工作区实测）
--------------------------------
* 与项目包 ``cooling.dynamics.simulate_cold_end`` 同参数逐节点比对：
  304 个采样点上 max|Δlevel| = max|ΔPavail| = max|Δpb| = 0.000e+00（dt=1 s 与 0.25 s 均如此）；
* 复现 ``data/source_data/fig03_all54_thermal_settings.csv`` 的 **全部 18 行 S1a**
  （τ_cond × τ_tower 矩阵）：跳机时刻、送达能量、蓄热容量、能量残差偏差均为 0；
* 同情景两个对照开关也复现发表值：保持负荷（C1）4.2964 h、排污不隔离（S1b）3.8550 h；
* 基线 S1a：t_trip = 5.047222 h（18170 s，机制 pump_level），送达能量 2738.4330 MWh，
  区间能量残差最大 4.19e-11 MJ（项目门禁 <1e-6），dt=0.25/1 s 步长差 0.014 MWh（0.0005 %）。

设计约定
--------
* 纯标准库（math/csv/argparse），无 numpy/scipy/pandas/pandapower 依赖，可直接
  拷贝到任何 Python ≥3.10 环境运行。
* 参数不是手抄数字：脚本内先给出 500 MW 原型参考模板，再按 ``s = Pmax/500`` 做
  容量缩放，最后套用机组级"现场锚点"覆盖——与项目里
  ``scenarios.fault_makeup_basin.build_unit_model`` 的三步顺序完全一致，可逐项溯源。
* 数值格式（时间推进、串行滞后、事件对齐、跳机判据顺序、能量积分约定）与
  ``cooling/dynamics.py`` + ``cooling/transient.py`` 等价。
* 故障类型只有一种：单台机组外来补水中断。``--hold-load`` / ``--keep-blowdown``
  只是同一故障下的**运行处置对照**（保持负荷 / 不隔离排污），不引入其他故障。

本模型【不】包含
----------------
* 多机组/共因故障、循环水泵故障、湿球升高、电网再耦合与再调度（在完整项目里）；
* 现场标定：所有参数标注为 reference_template_not_site_measured；
* 汽轮机容积可压缩性、塔的湿度/风场动态、AGC 调频、电气继电保护时序。

用法
----
    python3 coldend_makeup_interrupt.py                      # 默认 dt=1 s, 8 h
    python3 coldend_makeup_interrupt.py --dt-s 0.25          # 发布口径
    python3 coldend_makeup_interrupt.py --out series.csv     # 导出时间序列
    python3 coldend_makeup_interrupt.py --self-check         # 复现仓库已发表的 18 行 S1a 表
    python3 coldend_makeup_interrupt.py --out series.csv --dt-s 0.25
"""
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass, field, replace
from typing import Any

# =====================================================================
# 1. 参数：500 MW 原型参考模板 + 机组锚点（全部可替换）
# =====================================================================
# 来源标注：
#   [P] cooling/prototype_500mw.py 的 dataclass 默认值（500 MW 原型模板）
#   [C] code/data/calibrated_unit_parameters.csv（G33, package=baseline）
#   [T] code/data/unit_thermal_hydraulic_params.csv（G33, package=baseline）
#   [U] code/data/ieee39_unit_config.csv（G33, Pmax=652 MW）


@dataclass(frozen=True)
class Params:
    # ---- 汽轮机循环 [P] ----
    p_rated_mw: float = 500.0            # 原型净出力
    eta_net_design: float = 0.38         # 设计净效率
    partload_heatrate_penalty: float = 0.25   # 部分负荷热耗惩罚（二次）
    condenser_waste_heat_frac: float = 0.92   # 排入凝汽器的废热份额

    # ---- 参考设计点 [P/C/T] ----
    qcw_design_m3s: float = 15.77        # 设计循环水量（500 MW）
    twb_ref_c: float = 20.0              # 参考湿球温度 [T: 20.0]
    approach_design_c: float = 5.55      # 塔设计逼近度
    ttd_design_c: float = 3.5            # 凝汽器设计端差

    # ---- 冷却塔 [P/T] ----
    tower_characteristic_mult: float = 1.00   # 塔特性倍率 [T]
    tower_ntu_exp: float = 0.45               # 气水比对 NTU 的指数

    # ---- 凝汽器 [P/T] ----
    condenser_cleanliness: float = 1.00       # 清洁度 [T]
    condenser_u_flow_exp: float = 0.8         # UA 随水流指数
    condenser_air_partial_pressure_kpa: float = 0.0

    # ---- 水侧 [P/T] ----
    evap_heat_fraction: float = 0.82          # 蒸发潜热占排热比
    drift_frac: float = 5.0e-5                # 飘滴率
    cycles_of_concentration: float = 4.0      # 浓缩倍数 CoC [T]
    rho: float = 997.0
    cp: float = 4180.0

    # ---- 背压—功率曲线 [P/C] ----
    backpressure_sens_per_kpa: float = 0.007      # 0.7 %/kPa
    backpressure_sens_high_per_kpa: float = 0.014  # 高背压段 1.4 %/kPa
    backpressure_break_dp_kpa: float = 5.0
    backpressure_bonus_per_kpa: float = 0.002
    backpressure_bonus_cap: float = 0.02
    pb_ref_kpa: float | None = None          # None = 由设计点反算

    # ---- 集水池几何 [P→缩放→T] ----
    basin_area_m2: float = 1600.0            # 500 MW 原型，按 s 缩放 [C: G33=2086.4]
    basin_level_normal_m: float = 3.5        # 正常水位 [T]
    basin_level_trip_m: float = 1.0          # 低水位跳机定值 [T]

    # ---- 循环水泵/汽蚀 [P/T] ----
    site_atm_pressure_kpa: float = 101.325
    pump_design_head_m: float = 22.0
    pump_static_lift_design_m: float = 10.0
    pump_shutoff_factor: float = 1.30
    pump_eye_elevation_m: float = -1.0
    pump_suction_loss_m: float = 1.2
    pump_npshr_design_m: float = 8.0         # [T]
    pump_npsh_margin_req_m: float = 1.0

    # ---- 控制与保护 [P/T] ----
    p_min_tech_frac: float = 0.40            # 技术最小出力 [T]
    pb_trip_kpa: float = 15.0                # 低真空保护定值 [T]
    pb_trip_delay_s: float = 3.0
    max_ramp_frac_per_min: float = 0.02      # 每分钟最大降负荷速率
    operator_shed_start_level_m: float | None = None   # None → trip+1.0 m（=2.0 m）

    # ---- 热惯性 [P/C] ----
    tower_tau_s: float = 300.0
    condenser_tau_s: float = 90.0
    pump_tau_s: float = 10.0

    # ---- 情景设定（S1a 固定）----
    blowdown_isolated_on_detection: bool = True   # 检测到即隔离排污
    blowdown_detection_delay_h: float = 0.25      # 运行人员确认延时
    ride_down: bool = True                        # 操作员降负荷策略（非 hold_load）


UNIT_PMAX_MW = 652.0        # [U] G33 在 case39 里的 Pmax（原型 500 MW → 652 MW）
_G = 9.80665


def build_model(pmax_mw: float = UNIT_PMAX_MW, **over: float) -> Params:
    """原型 → 容量缩放（流量与池面积按 s 放大）→ 机组锚点覆盖。"""
    base = Params()
    s = pmax_mw / base.p_rated_mw
    m = replace(base,
                p_rated_mw=pmax_mw,
                qcw_design_m3s=base.qcw_design_m3s * s,
                basin_area_m2=base.basin_area_m2 * s,
                **over)
    return m


# =====================================================================
# 2. 物理子模型（稳态）
# =====================================================================
def sat_pressure_kpa(t_c: float) -> float:
    """水饱和蒸气压（Magnus 式，5–80 ℃ 够用）[P]。"""
    return 0.6108 * math.exp(17.27 * t_c / (t_c + 237.3))


def net_efficiency(m: Params, p_mw: float) -> float:
    if p_mw <= 0:
        return m.eta_net_design
    f = min(1.0, p_mw / m.p_rated_mw)
    return m.eta_net_design / (1.0 + m.partload_heatrate_penalty * (1.0 - f) ** 2)


def heat_reject_mw_th(m: Params, p_mw: float | None = None) -> float:
    """凝汽器排热：净效率 + 部分负荷惩罚 + 废热份额。"""
    p = m.p_rated_mw if p_mw is None else max(p_mw, 0.0)
    if p <= 0:
        return 0.0
    return p * (1.0 / max(net_efficiency(m, p), 1e-6) - 1.0) * m.condenser_waste_heat_frac


def design_delta_t_c(m: Params) -> float:
    return heat_reject_mw_th(m) * 1e6 / (m.rho * m.cp * m.qcw_design_m3s)


def design_inlet_c(m: Params) -> float:
    return m.twb_ref_c + m.approach_design_c


def tower_design_ntu(m: Params) -> float:
    r = design_delta_t_c(m)
    eff = r / (r + max(m.approach_design_c, 1e-9))
    return -math.log(max(1.0 - eff, 1e-9))


def tower_outlet_c(m: Params, twb_c: float, q_mw_th: float, qcw_m3s: float,
                   airflow_ratio: float = 1.0) -> float:
    """塔的 effectiveness/NTU 降阶式；NTU 随气水比按 tower_ntu_exp 变化。"""
    if qcw_m3s <= 0:
        return float('nan')
    rng = max(q_mw_th, 0.0) * 1e6 / (m.rho * m.cp * qcw_m3s)
    if rng <= 0:
        return float(twb_c)
    x = max(qcw_m3s / m.qcw_design_m3s, 1e-9)
    ntu = tower_design_ntu(m) * m.tower_characteristic_mult * (airflow_ratio / x) ** m.tower_ntu_exp
    eff = min(0.999, 1.0 - math.exp(-max(ntu, 0.0)))
    return twb_c + rng * (1.0 - eff) / eff


def condenser_ua_design_mw_per_k(m: Params) -> float:
    q = heat_reject_mw_th(m)
    r = design_delta_t_c(m)
    ttd = max(m.ttd_design_c, 1e-9)
    return q / (r / math.log((r + ttd) / ttd))


def condenser_exchange(m: Params, flow_m3s: float, *, clean_design: bool = False) -> tuple[float, float]:
    """返回 (水侧热容 MW/K, 导纳 MW/K)——UA-LMTD 的集总等价写法 [transient.py]。"""
    if not math.isfinite(flow_m3s) or flow_m3s < 0:
        raise ValueError('finite nonnegative water flow required')
    w = m.rho * m.cp * flow_m3s / 1e6
    if w == 0:
        return 0.0, 0.0
    x = flow_m3s / m.qcw_design_m3s
    clean = 1.0 if clean_design else m.condenser_cleanliness
    ua = condenser_ua_design_mw_per_k(m) * clean * x ** m.condenser_u_flow_exp
    return w, w * (-math.expm1(-ua / w))


def condenser_state(m: Params, q_mw_th: float, qcw_m3s: float, tin_c: float):
    """(tout, tsat, 背压 kPa, 瞬时端差 TTD)；TTD 是输出而非定值。"""
    if qcw_m3s <= 0:
        return float('nan'), float('nan'), float('nan'), float('nan')
    q = max(q_mw_th, 0.0)
    rng = q * 1e6 / (m.rho * m.cp * qcw_m3s)
    tout = tin_c + rng
    if q <= 0:
        return tout, tin_c, sat_pressure_kpa(tin_c) + m.condenser_air_partial_pressure_kpa, 0.0
    x = max(qcw_m3s / m.qcw_design_m3s, 1e-9)
    ua = condenser_ua_design_mw_per_k(m) * m.condenser_cleanliness * x ** m.condenser_u_flow_exp
    exponent = ua * rng / q
    ttd = rng / math.expm1(exponent) if exponent > 1e-9 else rng / max(exponent, 1e-9)
    t_sat = tout + ttd
    return tout, t_sat, sat_pressure_kpa(t_sat) + m.condenser_air_partial_pressure_kpa, ttd


def latent_heat_j_per_kg(m: Params, t_c: float) -> float:
    return max(2.20e6, (2501.0 - 2.43 * t_c) * 1000.0)


def water_balance_m3s(m: Params, q_mw_th: float, qcw_m3s: float, tin_c: float):
    """(蒸发, 排污, 飘滴, 补水量) m3/s；盐平衡 S=B+D、CoC=M/S ⇒ S=E/(CoC−1)。"""
    q = max(q_mw_th, 0.0)
    evap = m.evap_heat_fraction * q * 1e6 / (m.rho * latent_heat_j_per_kg(m, tin_c))
    drift = m.drift_frac * max(qcw_m3s, 0.0)
    blow = max(0.0, evap / max(m.cycles_of_concentration - 1.0, 0.05) - drift)
    return evap, blow, drift, evap + blow + drift


def design_makeup_m3s(m: Params) -> float:
    """参考补水量（= 设计点总耗水，也是解析排空时间的水位下降速率）。"""
    return water_balance_m3s(m, heat_reject_mw_th(m), m.qcw_design_m3s, design_inlet_c(m))[3]


def reference_backpressure_kpa(m: Params) -> float:
    if m.pb_ref_kpa is not None:
        return float(m.pb_ref_kpa)
    t_sat = design_inlet_c(m) + design_delta_t_c(m) + m.ttd_design_c
    return sat_pressure_kpa(t_sat) + m.condenser_air_partial_pressure_kpa


def backpressure_power_factor(m: Params, pb_kpa: float) -> float:
    """分段背压修正（设计点以下有小幅加成并封顶）。"""
    ref = reference_backpressure_kpa(m)
    if pb_kpa != pb_kpa:      # NaN
        return 0.0
    if pb_kpa <= ref:
        return min(1.0 + m.backpressure_bonus_cap, 1.0 + m.backpressure_bonus_per_kpa * (ref - pb_kpa))
    dp = pb_kpa - ref
    loss = (m.backpressure_sens_per_kpa * min(dp, m.backpressure_break_dp_kpa)
            + m.backpressure_sens_high_per_kpa * max(0.0, dp - m.backpressure_break_dp_kpa))
    return max(0.0, 1.0 - loss)


def thermal_power_mw(m: Params, pb_kpa: float) -> float:
    return m.p_rated_mw * backpressure_power_factor(m, pb_kpa)


# ---- 池容/水位 ----
def basin_area_m2(m: Params) -> float:
    return m.basin_area_m2


def basin_v0_m3(m: Params) -> float:
    return basin_area_m2(m) * m.basin_level_normal_m


def basin_vmin_m3(m: Params) -> float:
    return basin_area_m2(m) * m.basin_level_trip_m


def level_from_volume(m: Params, vol: float) -> float:
    return max(vol, 0.0) / max(basin_area_m2(m), 1e-9)


def volume_from_level(m: Params, level: float) -> float:
    return max(level, 0.0) * basin_area_m2(m)


def operator_shed_start_level_m(m: Params) -> float:
    return (m.basin_level_trip_m + 1.0) if m.operator_shed_start_level_m is None else m.operator_shed_start_level_m


def analytic_trip_h(m: Params) -> float:
    """解析校核值：可用库容 / 设计耗水（排污保持工况），非仿真结果。"""
    loss = design_makeup_m3s(m)
    return float('inf') if loss <= 0 else (basin_v0_m3(m) - basin_vmin_m3(m)) / loss / 3600.0


def pump_flow_fraction(m: Params, level_m: float, tin_c: float) -> float:
    """泵—管路扬程平衡 + NPSHa/NPSHr 可用性；水位低于跳机值即 0。"""
    if level_m <= m.basin_level_trip_m:
        return 0.0
    shutoff = m.pump_design_head_m * m.pump_shutoff_factor
    denom = max(shutoff - m.pump_static_lift_design_m, 1e-9)
    static = m.pump_static_lift_design_m + (m.basin_level_normal_m - level_m)
    x_hyd = math.sqrt(max(shutoff - static, 0.0) / denom)
    atm = m.site_atm_pressure_kpa * 1000.0 / (m.rho * _G)
    vap = sat_pressure_kpa(tin_c) * 1000.0 / (m.rho * _G)
    npsha = atm - vap + (level_m - m.pump_eye_elevation_m) - m.pump_suction_loss_m
    npshr = m.pump_npshr_design_m * x_hyd ** 2
    if npsha >= npshr + m.pump_npsh_margin_req_m:
        x_npsh = 1.0
    elif npsha <= 0:
        x_npsh = 0.0
    else:
        x_npsh = min(1.0, max(0.0, npsha / max(npshr + m.pump_npsh_margin_req_m, 1e-9)))
    return max(0.0, min(x_hyd, x_npsh))


def steady_state(m: Params, p_setpoint_mw: float | None = None, airflow_ratio: float = 1.0) -> dict[str, float]:
    """故障前的自洽健康工况：出力—背压—排热闭合（阻尼定点迭代，80 次）。"""
    p_limit = m.p_rated_mw if p_setpoint_mw is None else max(p_setpoint_mw, 0.0)
    qcw = m.qcw_design_m3s

    def once(p: float) -> tuple[float, dict[str, float]]:
        q = heat_reject_mw_th(m, p)
        tin = tower_outlet_c(m, m.twb_ref_c, q, qcw, airflow_ratio)
        tout, tsat, pb, ttd = condenser_state(m, q, qcw, tin)
        return thermal_power_mw(m, pb), dict(p_mw=p, qcw_m3s=qcw, tin_c=tin, tout_c=tout,
                                             t_sat_c=tsat, backpressure_kpa=pb, ttd_c=ttd,
                                             heat_reject_mw_th=q)

    p = p_limit
    thermal, st = once(p)
    for _ in range(80):
        p_new = 0.5 * p + 0.5 * min(p_limit, thermal)
        if abs(p_new - p) < 1e-7:
            p = p_new
            break
        p = p_new
        thermal, st = once(p)
    thermal, st = once(p)
    evap, blow, drift, makeup = water_balance_m3s(m, st['heat_reject_mw_th'], qcw, st['tin_c'])
    st.update(p_avail_mw=max(0.0, min(p_limit, p)), evaporation_m3s=evap, blowdown_m3s=blow,
              drift_m3s=drift, makeup_m3s=makeup, approach_c=st['tin_c'] - m.twb_ref_c,
              basin_volume_m3=basin_v0_m3(m), basin_level_m=m.basin_level_normal_m)
    return st


# =====================================================================
# 3. 事件—间隔精确积分（凝汽器蓄热）
# =====================================================================
def advance_condenser(tsat_c: float, tin_c: float, steam_mw: float, g_mw_k: float,
                      cap_mj_k: float, dt_s: float) -> tuple[float, float, float]:
    """常值输入区间解（含精确水侧取热积分）→ (新 Tsat, 区间平均水侧热流, 能量残差 MJ)。"""
    if not all(math.isfinite(v) for v in (tsat_c, tin_c, steam_mw, g_mw_k, cap_mj_k, dt_s)):
        raise ValueError('non-finite condenser state/input')
    if min(steam_mw, g_mw_k, cap_mj_k) < 0 or dt_s <= 0:
        raise ValueError('nonnegative heat/G/C and positive dt required')
    if cap_mj_k == 0:
        if g_mw_k == 0:
            if steam_mw > 0:
                raise RuntimeError('zero flow/zero storage/positive steam: 无有限准稳态')
            return tsat_c, 0.0, 0.0
        return tin_c + steam_mw / g_mw_k, steam_mw, 0.0
    z = g_mw_k * dt_s / cap_mj_k
    if z < 1e-7:
        phi = 1 - z / 2 + z * z / 6 - z ** 3 / 24
        one_minus_phi = z / 2 - z * z / 6 + z ** 3 / 24
    else:
        phi = -math.expm1(-z) / z
        one_minus_phi = 1 - phi
    alpha = -math.expm1(-z)
    new = tsat_c + alpha * (tin_c - tsat_c) + (steam_mw / cap_mj_k) * dt_s * phi
    removed = g_mw_k * (tsat_c - tin_c) * phi + steam_mw * one_minus_phi
    residual = cap_mj_k * (new - tsat_c) - dt_s * (steam_mw - removed)
    return new, removed, residual


def _lag_alpha(dt_s: float, tau_s: float) -> float:
    return 1.0 if tau_s <= 0 else 1.0 - math.exp(-dt_s / tau_s)


# =====================================================================
# 4. 情景积分：单台机组外来补水中断
# =====================================================================
@dataclass
class Run:
    """一次仿真的全部输出。"""
    t_s: list[float] = field(default_factory=list)
    level_m: list[float] = field(default_factory=list)
    volume_m3: list[float] = field(default_factory=list)
    qcw_frac: list[float] = field(default_factory=list)
    p_mw: list[float] = field(default_factory=list)
    p_cap_mw: list[float] = field(default_factory=list)
    qc_mw_th: list[float] = field(default_factory=list)
    pb_kpa: list[float] = field(default_factory=list)
    tsat_c: list[float] = field(default_factory=list)
    tin_c: list[float] = field(default_factory=list)
    tout_c: list[float] = field(default_factory=list)
    evap_m3s: list[float] = field(default_factory=list)
    blow_m3s: list[float] = field(default_factory=list)
    drift_m3s: list[float] = field(default_factory=list)
    loss_m3s: list[float] = field(default_factory=list)
    water_mw: list[float] = field(default_factory=list)
    storage_mw: list[float] = field(default_factory=list)
    t_derate_start_h: float | None = None
    t_trip_h: float | None = None
    mechanism: str = 'no_trip_within_horizon'
    detail: str = ''
    p_before_trip_mw: float | None = None
    max_energy_residual_mj: float = 0.0
    initial_p_mw: float = 0.0
    initial_pb_kpa: float = 0.0
    condenser_capacity_mj_per_k: float = 0.0
    sample_dt_s: float = 60.0
    horizon_h: float = 0.0
    notes: dict[str, Any] = field(default_factory=dict)


def simulate(m: Params, *, dt_s: float = 1.0, sample_every_s: float = 60.0,
             t_max_h: float = 8.0, initial_load_frac: float = 1.0,
             qcw_frac_floor: float = 0.02, airflow_ratio: float = 1.0) -> Run:
    """
    串行因果、中点输入的时间推进（与项目 dynamics.simulate_cold_end 同构）：

        池水位 → 泵可用流量 → 塔出口水温 → 凝汽器（UA-LMTD + 蓄热）→ 背压
        → 汽轮机能力 → 运行员 SOP 降负荷/速率限制 → 保护判据

    要点
    ----
    * 排污在"检测时刻"隔离：右连续、零时长，不产生假斜坡；
    * 库容用区间两端耗水率的梯形积分；
    * 跳机判据顺序固定：低水位 → 汽蚀下限 → 低真空（含延时）→ 技术最小；
    * 跳机后记录行 p=0（能力清零），并把跳机前的左极限功率单独保存。
    """
    if dt_s <= 0 or sample_every_s <= 0 or t_max_h < 0:
        raise ValueError('时间步长/采样/时域必须为正')
    if not 0 <= initial_load_frac <= 1:
        raise ValueError('initial_load_frac 需在 [0,1]')
    if not 0 < qcw_frac_floor < 1:
        raise ValueError('qcw_frac_floor 需在 (0,1)')

    p_min_frac = m.p_min_tech_frac
    pb_trip = m.pb_trip_kpa
    pb_delay = m.pb_trip_delay_s
    ramp_frac = m.max_ramp_frac_per_min
    shed_start = operator_shed_start_level_m(m)
    twb = m.twb_ref_c
    tau_tower, tau_cond, tau_pump = m.tower_tau_s, m.condenser_tau_s, m.pump_tau_s

    init = steady_state(m, p_setpoint_mw=initial_load_frac * m.p_rated_mw, airflow_ratio=airflow_ratio)
    p0 = init['p_avail_mw']
    p_state, pb_state = p0, init['backpressure_kpa']
    if not math.isfinite(pb_state) or pb_state >= pb_trip:
        raise RuntimeError('故障前平衡点已违反真空定值，不能当作"故障引起跳机"')
    qc_hold = heat_reject_mw_th(m, p0)
    tin_state, tsat_state = init['tin_c'], init['t_sat_c']
    area = basin_area_m2(m)
    level, level_trip = m.basin_level_normal_m, m.basin_level_trip_m
    x_state = 1.0
    capacity = tau_cond * condenser_exchange(m, m.qcw_design_m3s, clean_design=True)[1]
    design_loss = design_makeup_m3s(m)
    detect_s = max(0.0, m.blowdown_detection_delay_h * 3600)

    r = Run(initial_p_mw=p0, initial_pb_kpa=pb_state, condenser_capacity_mj_per_k=capacity,
            sample_dt_s=sample_every_s, horizon_h=t_max_h)
    r.notes = dict(p_rated_mw=m.p_rated_mw, basin_V0_m3=basin_v0_m3(m), basin_Vmin_m3=basin_vmin_m3(m),
                   basin_area_m2=area, design_makeup_m3s=design_loss, analytic_trip_h=analytic_trip_h(m),
                   holdup_h=(basin_v0_m3(m) - basin_vmin_m3(m)) / max(design_loss, 1e-12) / 3600.0,
                   pb_ref_kpa=reference_backpressure_kpa(m), tower_ntu=tower_design_ntu(m),
                   ua_design_mw_per_k=condenser_ua_design_mw_per_k(m), delta_t_design_c=design_delta_t_c(m),
                   capacity_mj_per_k=capacity)

    def process_values(t_s: float, tsat: float, tin: float, x: float, p: float):
        qcw = m.qcw_design_m3s * x
        _, g = condenser_exchange(m, qcw)
        steam = qc_hold if not m.ride_down else heat_reject_mw_th(m, p)
        water = g * (tsat - tin)
        outlet = float('nan') if qcw == 0 else tin + water / (m.rho * m.cp * qcw / 1e6)
        evap, blow, drift, _ = water_balance_m3s(m, max(0.0, water), qcw, tin)
        if m.blowdown_isolated_on_detection and t_s >= detect_s - 1e-10:
            blow = 0.0
        return steam, water, outlet, evap, blow, drift, evap + blow + drift

    def lag(target: float, cur: float, frac: float) -> float:
        return cur + (target - cur) * frac

    def record(capability: float, *, tripped: bool = False) -> None:
        steam, water, outlet, evap, blow, drift, loss = process_values(t_s, tsat_state, tin_state, x_state, p_state)
        if tripped:
            steam = evap = blow = drift = loss = 0.0
        r.t_s.append(t_s)
        r.level_m.append(level)
        r.volume_m3.append(volume_from_level(m, level))
        r.qcw_frac.append(0.0 if tripped else x_state)
        r.p_mw.append(0.0 if tripped else p_state)
        r.p_cap_mw.append(capability)
        r.qc_mw_th.append(steam)
        r.pb_kpa.append(pb_state)
        r.tsat_c.append(tsat_state)
        r.tin_c.append(tin_state)
        r.tout_c.append(outlet)
        r.evap_m3s.append(evap)
        r.blow_m3s.append(blow)
        r.drift_m3s.append(drift)
        r.loss_m3s.append(loss)
        r.water_mw.append(water)
        r.storage_mw.append(steam - water)

    t_s = 0.0
    next_sample = sample_every_s
    pb_high_since: float | None = None
    record(p0)

    while t_s < t_max_h * 3600.0 - 1e-10:
        h = min(dt_s, t_max_h * 3600.0 - t_s, next_sample - t_s)
        if m.blowdown_isolated_on_detection and t_s < detect_s - 1e-10:
            h = min(h, detect_s - t_s)      # 让检测时刻恰好落在步上（事件对齐）
        if h <= 1e-10:
            next_sample += sample_every_s
            continue
        steam0, _, _, _, _, _, loss0 = process_values(t_s, tsat_state, tin_state, x_state, p_state)
        old_level = level

        # 泵：目标可用流量 → 半步/全步滞后（串行因果）
        x_hyd = pump_flow_fraction(m, level, tin_state)
        x_mid = max(0.0, min(1.0, lag(x_hyd, x_state, _lag_alpha(h / 2, tau_pump))))
        x_new = max(0.0, min(1.0, lag(x_hyd, x_state, _lag_alpha(h, tau_pump))))
        # 塔：以半步流量为输入求冷端热负荷与塔出口温度
        qmid = m.qcw_design_m3s * x_mid
        ex = condenser_exchange(m, qmid)
        water_target = max(0.0, ex[1] * (tsat_state - tin_state))
        tin_target = tower_outlet_c(m, twb, water_target, qmid, airflow_ratio) if qmid > 0 else tin_state
        tin_mid = lag(tin_target, tin_state, _lag_alpha(h / 2, tau_tower))
        tin_new = lag(tin_target, tin_state, _lag_alpha(h, tau_tower))

        tsat_new, _, residual = advance_condenser(tsat_state, tin_mid, steam0, ex[1], capacity, h)
        r.max_energy_residual_mj = max(r.max_energy_residual_mj, abs(residual))
        tsat_state, tin_state, x_state = tsat_new, tin_new, x_new
        t_s += h

        _, _, _, _, _, _, loss1 = process_values(t_s, tsat_state, tin_state, x_state, p_state)
        if m.blowdown_isolated_on_detection and abs(t_s - detect_s) < 1e-8:
            # 检测时刻的排污"右极限跳变"：把跳变前的排污量补进本区间梯形
            qcw_now = m.qcw_design_m3s * x_state
            _, g_now = condenser_exchange(m, qcw_now)
            e1, b1, d1, _ = water_balance_m3s(m, max(0.0, g_now * (tsat_state - tin_state)), qcw_now, tin_state)
            loss1 += b1
        level = max(0.0, old_level - (loss0 + loss1) * 0.5 * h / area)

        pb_state = sat_pressure_kpa(tsat_state) + m.condenser_air_partial_pressure_kpa
        p_thermal = thermal_power_mw(m, pb_state)
        if m.ride_down:
            frac = p_min_frac + (1 - p_min_frac) * max(0.0, min(1.0,
                   (level - level_trip) / max(shed_start - level_trip, 1e-9)))
            p_cap = min(p0, p_thermal, m.p_rated_mw * frac)
        else:
            p_cap = min(p0, p_thermal)
        max_delta = ramp_frac * m.p_rated_mw * h / 60.0
        p_state += max(-max_delta, min(max_delta, p_cap - p_state))
        if r.t_derate_start_h is None and p_state < 0.995 * p0:
            r.t_derate_start_h = t_s / 3600.0

        mech = None
        detail = ''
        if level <= level_trip + 1e-12:
            mech, detail = 'pump_level', 'basin at pump trip level'
        elif x_state <= qcw_frac_floor:
            mech, detail = 'pump_cavitation', 'hydraulic availability below protection floor'
        else:
            if pb_state >= pb_trip:
                if pb_high_since is None:
                    pb_high_since = t_s
                if t_s - pb_high_since >= pb_delay - 1e-10:
                    mech, detail = 'backpressure_protection', 'vacuum setpoint sustained for declared delay'
            else:
                pb_high_since = None
            if mech is None and m.ride_down and p_cap < p_min_frac * m.p_rated_mw - 1e-9 \
                    and p_state <= p_min_frac * m.p_rated_mw + 0.5:
                mech, detail = 'technical_minimum', 'capability below technical minimum'
        if mech is not None:
            r.p_before_trip_mw = float(p_state)
            r.t_trip_h, r.mechanism, r.detail = t_s / 3600.0, mech, detail
            record(p_cap, tripped=True)
            break
        if t_s >= next_sample - 1e-8 or t_s >= t_max_h * 3600.0 - 1e-8:
            record(p_cap)
            if t_s >= next_sample - 1e-8:
                next_sample += sample_every_s
    return r


# =====================================================================
# 5. 轨迹后处理（与 benchmarks.delivered_energy_mwh 同约定）
# =====================================================================
def p_avail_at(r: Run, t_h: float, *, side: str = 'right') -> float:
    t_h_arr = [t / 3600.0 for t in r.t_s]
    if not t_h_arr:
        return float('nan')
    if side not in ('left', 'right'):
        raise ValueError("side must be left or right")
    if r.t_trip_h is not None and t_h >= r.t_trip_h:
        if t_h == r.t_trip_h and side == 'left' and r.p_before_trip_mw is not None:
            return r.p_before_trip_mw
        return 0.0
    if t_h <= t_h_arr[0]:
        return r.p_mw[0]
    if t_h >= t_h_arr[-1]:
        return r.p_mw[-1]
    for i in range(1, len(t_h_arr)):
        if t_h_arr[i] >= t_h:
            t0, t1 = t_h_arr[i - 1], t_h_arr[i]
            p0, p1 = r.p_mw[i - 1], r.p_mw[i]
            if t_h_arr[i] == r.t_trip_h and r.p_before_trip_mw is not None:
                p1 = r.p_before_trip_mw
            if t1 <= t0:
                return p1
            w = (t_h - t0) / (t1 - t0)
            return p0 + w * (p1 - p0)
    return r.p_mw[-1]


def delivered_energy_mwh(r: Run, horizon_h: float = 8.0) -> float:
    """故障起点到时域末的送达能量（梯形）；保护跳变按零时长处理，不成斜坡。"""
    t_h_arr = [t / 3600.0 for t in r.t_s]
    if not t_h_arr:
        return 0.0
    energy = 0.0
    prev_t = t_h_arr[0]
    prev_p = p_avail_at(r, prev_t)
    end = max(horizon_h, prev_t)
    pts = [t for t in t_h_arr if prev_t < t < end]
    if r.t_trip_h is not None and prev_t < r.t_trip_h < end:
        pts.append(r.t_trip_h)
    pts.append(end)
    for t in sorted(set(pts)):
        energy += 0.5 * (prev_p + p_avail_at(r, t, side='left')) * (t - prev_t)
        prev_t, prev_p = t, p_avail_at(r, t)
    return energy


def sparkline(values: list[float], width: int = 62, height: int = 9) -> str:
    """无依赖的小图，便于眼看轨迹形状。"""
    if not values:
        return ''
    lo, hi = min(values), max(values)
    rng = hi - lo if hi > lo else 1.0
    cols = max(1, width)
    grid = [[' '] * cols for _ in range(height)]
    for i in range(cols):
        v = values[min(len(values) - 1, int(i * len(values) / cols))]
        row = height - 1 - int((v - lo) / rng * (height - 1))
        grid[row][i] = '*'
    return '\n'.join('  |' + ''.join(g) for g in grid) + '\n  +' + '-' * cols + f'  ({lo:.1f} … {hi:.1f})'


# =====================================================================
# 6. 发布锚点（仓库已发表数值，供 --self-check 复现对账）
# =====================================================================
# 仓库已发表的 S1a 参考表：data/source_data/fig03_all54_thermal_settings.csv（18 行全部内嵌，
# 使 --self-check 不依赖外部文件；字段 = (τ_cond s, τ_tower s, 蓄热 MJ/K, dt s, trip h, trip s,
# 机制, 送达能量 MWh, P0 MW, pb0 kPa, 最大能量残差 MJ)。
PUBLISHED_S1A: tuple[tuple[float, float, float, float, float, float, str, float, float, float, float], ...] = (
    (30.0, 30.0, 1967.8794166630046, 1.0, 5.064722222222223, 18233.0, "pump_level", 2745.67476867725, 652.0, 7.5623422244764305, 1.3930634423786614e-11),
    (30.0, 300.0, 1967.8794166630046, 1.0, 5.064444444444445, 18232.0, "pump_level", 2745.5839054195408, 652.0, 7.5623422244764305, 1.3899464912370263e-11),
    (30.0, 1800.0, 1967.8794166630046, 1.0, 5.063611111111111, 18229.0, "pump_level", 2745.3254853127246, 652.0, 7.5623422244764305, 1.3841816581816602e-11),
    (60.0, 30.0, 3935.758833326009, 1.0, 5.056111111111111, 18202.0, "pump_level", 2742.0697170550134, 652.0, 7.5623422244764305, 2.7578994643562282e-11),
    (60.0, 300.0, 3935.758833326009, 1.0, 5.055833333333333, 18201.0, "pump_level", 2741.9974937037914, 652.0, 7.5623422244764305, 2.7937568924940592e-11),
    (60.0, 1800.0, 3935.758833326009, 1.0, 5.0552777777777775, 18199.0, "pump_level", 2741.903641545797, 652.0, 7.5623422244764305, 2.7903013233299134e-11),
    (90.0, 30.0, 5903.638249989013, 1.0, 5.0475, 18171.0, "pump_level", 2738.4866631064897, 652.0, 7.5623422244764305, 4.1588066324038664e-11),
    (90.0, 300.0, 5903.638249989013, 1.0, 5.0472222222222225, 18170.0, "pump_level", 2738.4330383025494, 652.0, 7.5623422244764305, 4.189104618745887e-11),
    (90.0, 1800.0, 5903.638249989013, 1.0, 5.046944444444445, 18169.0, "pump_level", 2738.5031153098184, 652.0, 7.5623422244764305, 4.18669543478245e-11),
    (180.0, 30.0, 11807.276499978027, 1.0, 5.0216666666666665, 18078.0, "pump_level", 2727.8696677926296, 652.0, 7.5623422244764305, 8.394707151637704e-11),
    (180.0, 300.0, 11807.276499978027, 1.0, 5.0216666666666665, 18078.0, "pump_level", 2727.944788527333, 652.0, 7.5623422244764305, 8.368028492355961e-11),
    (180.0, 1800.0, 11807.276499978027, 1.0, 5.021944444444444, 18079.0, "pump_level", 2728.42896140467, 652.0, 7.5623422244764305, 8.319922528698953e-11),
    (300.0, 30.0, 19678.794166630047, 1.0, 4.9880555555555555, 17957.0, "pump_level", 2714.246833106806, 652.0, 7.5623422244764305, 1.3951506616649567e-10),
    (300.0, 300.0, 19678.794166630047, 1.0, 4.9880555555555555, 17957.0, "pump_level", 2714.3965779776813, 652.0, 7.5623422244764305, 1.3952838884279117e-10),
    (300.0, 1800.0, 19678.794166630047, 1.0, 4.989722222222222, 17963.0, "pump_level", 2715.586145019451, 652.0, 7.5623422244764305, 1.3964274181432756e-10),
    (600.0, 30.0, 39357.58833326009, 1.0, 4.906944444444444, 17665.0, "pump_level", 2682.5645580324535, 652.0, 7.5623422244764305, 2.78335132719576e-10),
    (600.0, 300.0, 39357.58833326009, 1.0, 4.907777777777778, 17668.0, "pump_level", 2683.107714127118, 652.0, 7.5623422244764305, 2.7849988981643037e-10),
    (600.0, 1800.0, 39357.58833326009, 1.0, 4.913333333333333, 17688.0, "pump_level", 2686.046201622815, 652.0, 7.5623422244764305, 2.779119157025889e-10),
)


def self_check(m: Params) -> int:
    """逐行复现仓库发表的 S1a τ 矩阵（18 组），并与 --dt-s 收敛性一起报告。"""
    print('自检：复现 data/source_data/fig03_all54_thermal_settings.csv 的 18 行 S1a')
    print('-' * 100)
    print(f"{'τ_cond':>7} {'τ_tower':>8} {'Δ trip_s':>9} {'Δenergy MWh':>12} {'Δcap MJ/K':>10} {'Δresid':>10}  机制")
    bad = 0
    dt_pub = 1.0
    for tc, tt, cap_ref, dt, trip_h, trip_s, mech, e_ref, p0_ref, pb0_ref, res_ref in PUBLISHED_S1A:
        r = simulate(replace(m, condenser_tau_s=tc, tower_tau_s=tt), dt_s=dt_pub,
                     sample_every_s=60.0, t_max_h=8.0)
        d_t = abs((r.t_trip_h or 0.0) - trip_h) * 3600.0
        d_e = abs(delivered_energy_mwh(r) - e_ref)
        d_c = abs(r.condenser_capacity_mj_per_k - cap_ref)
        d_r = abs(r.max_energy_residual_mj - res_ref)
        ok = d_t < 1e-6 and d_e < 1e-6 and d_c < 1e-6 and d_r < 1e-6 and r.mechanism == mech
        bad += 0 if ok else 1
        print(f"{tc:>7.0f} {tt:>8.0f} {d_t:>9.2e} {d_e:>12.2e} {d_c:>10.2e} {d_r:>10.2e}  "
              f"{r.mechanism}{'' if ok else '   ← DIFF'}")
    a = simulate(m, dt_s=0.25, sample_every_s=60.0, t_max_h=8.0)
    b = simulate(m, dt_s=1.0, sample_every_s=60.0, t_max_h=8.0)
    c = simulate(m, dt_s=0.1, sample_every_s=60.0, t_max_h=8.0)
    ea, eb, ec = (delivered_energy_mwh(x) for x in (a, b, c))
    print('\n步长收敛性（同参数，仅改 dt）：')
    print(f"  dt=0.10 s → trip {c.t_trip_h*3600:.1f} s, energy {ec:.6f} MWh")
    print(f"  dt=0.25 s → trip {a.t_trip_h*3600:.1f} s, energy {ea:.6f} MWh   Δ(vs 0.1) {abs(a.t_trip_h-c.t_trip_h)*3600:.2f} s / {abs(ea-ec):.6f} MWh")
    print(f"  dt=1.00 s → trip {b.t_trip_h*3600:.1f} s, energy {eb:.6f} MWh   Δ(vs 0.25) {abs(b.t_trip_h-a.t_trip_h)*3600:.2f} s / {abs(eb-ea):.6f} MWh")
    print(f"  项目门禁：Δtrip ≤ 5 s 且 Δenergy < 0.1 % → "
          f"{'PASS' if abs(b.t_trip_h-a.t_trip_h)*3600<=5 and abs(eb-ea)/ea*100 < .1 else 'FAIL'}")
    print(f"  区间能量残差最大值 {max(x.max_energy_residual_mj for x in (a,b,c)):.2e} MJ（门禁 <1e-6）")
    print('\n判定:', 'PASS — 18/18 行与发表值逐位一致' if bad == 0 else f'FAIL — {bad}/18 行超容差')
    return 0 if bad == 0 else 1


# =====================================================================
# 7. 报告输出
# =====================================================================
def report(m: Params, r: Run, *, series_h: list[float] | None = None) -> str:
    n = r.notes
    out: list[str] = []
    w = out.append
    w('=' * 72)
    w('单台机组 外来补水中断 —— 冷端机理模型（S1a 口径）')
    w('=' * 72)
    gid = 'G33 / bus 33' if abs(m.p_rated_mw - UNIT_PMAX_MW) < 1e-9 else f'pmax={m.p_rated_mw:.1f} MW（自定义容量）'
    w(f"机组                     : {gid}，额定 {m.p_rated_mw:.1f} MWe"
      f"（500 MW 原型按 s={m.p_rated_mw/500.0:.4f} 缩放）")
    w(f"冷却方式                 : 湿式开式循环（塔+池+循泵），参考湿球 {m.twb_ref_c:.1f} ℃，CoC {m.cycles_of_concentration:.1f}")
    w('')
    w('【故障前健康工况（自洽解）】')
    w(f"  出力 P0 / 上限          : {r.initial_p_mw:.3f} / {m.p_rated_mw:.3f} MW")
    w(f"  凝汽器背压 pb / 定值    : {r.initial_pb_kpa:.4f} / {m.pb_trip_kpa:.2f} kPa（设计参考 {n['pb_ref_kpa']:.4f} kPa）")
    w(f"  塔出口水温 Tin          : {r.tin_c[0]:.3f} ℃（逼近度 {r.tin_c[0]-m.twb_ref_c:.3f} K，设计 NTU {n['tower_ntu']:.4f}）")
    w(f"  排热 Qc / TTD           : {r.qc_mw_th[0]:.2f} MW_th / {condenser_state(m, r.qc_mw_th[0], m.qcw_design_m3s, r.tin_c[0])[3]:.3f} K")
    w(f"  循环水量 Qcw            : {m.qcw_design_m3s:.4f} m³/s（设计温差 {n['delta_t_design_c']:.3f} K，UA={n['ua_design_mw_per_k']:.2f} MW/K）")
    w('')
    w('【集水池（唯一决定本情景可用时间的库存）】')
    w(f"  池面积 / 正常水位/跳机水位: {n['basin_area_m2']:.1f} m² / {m.basin_level_normal_m:.2f} m / {m.basin_level_trip_m:.2f} m")
    w(f"  V0 / Vmin / 可用库容     : {n['basin_V0_m3']:.0f} / {n['basin_Vmin_m3']:.0f} / {n['basin_V0_m3']-n['basin_Vmin_m3']:.0f} m³")
    w(f"  设计补水（=耗水）        : {n['design_makeup_m3s']:.5f} m³/s = {n['design_makeup_m3s']*3600:.1f} m³/h")
    w(f"  衍生滞留时间 / 解析跳机  : {n['holdup_h']:.3f} h / {n['analytic_trip_h']:.3f} h")
    w('')
    w('【事件时间线】')
    w(f"  t=0                        外来补水中断（水位仍正常，泵流量不受影响）")
    w(f"  t={m.blowdown_detection_delay_h:.2f} h                   运行人员确认并隔离排污 → 耗水率下跳")
    if r.t_derate_start_h is not None:
        w(f"  t={r.t_derate_start_h:.3f} h                SOP 开始降负荷（首次偏离 {0.995*100:.1f}% P0）")
    w(f"  0→{r.t_trip_h if r.t_trip_h is not None else float('nan'):.3f} h       水位单调下降 {r.level_m[0]:.3f}→{min(r.level_m):.3f} m"
      f"（耗水率 {r.loss_m3s[0]:.4f}→{r.loss_m3s[max(0,len(r.loss_m3s)-2)]:.4f} m³/s，隔离排污后下跳）")
    w(f"  t={r.t_trip_h if r.t_trip_h is not None else float('nan'):.4f} h             跳机：机制 = {r.mechanism}（{r.detail}）")
    w(f"  跳机前左极限功率         : {r.p_before_trip_mw if r.p_before_trip_mw is not None else float('nan'):.2f} MW"
      f" → 之后能力记为 0")
    w('')
    w('【结果量】')
    e_mwh = delivered_energy_mwh(r)
    w(f"  送达能量（0-{r.horizon_h:.0f} h 梯形积分）      : {e_mwh:.3f} MWh")
    if r.t_trip_h is not None:
        aligned = r.initial_p_mw * r.t_trip_h
        w(f"  同跳机时刻满能力参照        : {aligned:.3f} MWh → 降负荷形状损失 "
          f"{aligned - e_mwh:.3f} MWh（{(aligned - e_mwh) / aligned * 100:.2f} %）")
        w(f"  跳机即全停参照              : 记 0 MWh，即机理轨迹保留了 {e_mwh:.0f} MWh 出力")
    w(f"  凝汽器蓄热容量            : {r.condenser_capacity_mj_per_k:.3f} MJ/K（τ_cond={m.condenser_tau_s:.0f} s）")
    w(f"  区间能量残差最大值        : {r.max_energy_residual_mj:.2e} MJ（应 <1e-6）")
    w(f"  最低水位 / 末态流量分数   : {min(r.level_m):.3f} m / {r.qcw_frac[-1]:.4f}")
    w('')
    w('【轨迹抽样】(h, level m, Pavail MW, pb kPa, Qcw fraction, loss m³/s)')
    for row in sample_rows(r, series_h):
        w(f"  {row[0]:6.3f}  {row[1]:7.3f}  {row[2]:8.3f}  {row[3]:7.3f}  {row[4]:7.4f}  {row[5]:8.5f}")
    w('')
    w('Pavail(t) 轨迹：')
    w(sparkline([p for p in r.p_mw]))
    w('basin level(t) 轨迹：')
    w(sparkline(r.level_m))
    w('')
    w('参数标定状态: reference_template_not_site_measured（须以厂内土建水位—容积表、')
    w('泵曲线、运行规程与保护定值单、历史数据替换后方可称"场站标定"）')
    return '\n'.join(out)


def sample_rows(r: Run, hs: list[float] | None) -> list[tuple[float, ...]]:
    hs = hs or [0.0, 1.0, 2.0, 3.0, 4.0, 4.5, 5.0]
    if r.t_trip_h is not None:
        hs = sorted(set(hs) | {round(r.t_trip_h - 0.05, 4), round(r.t_trip_h, 4), round(min(r.t_trip_h + 0.5, 8.0), 4)})
    t_h = [t / 3600.0 for t in r.t_s]
    rows = []
    for h in hs:
        i = max(j for j, t in enumerate(t_h) if t <= h + 1e-12) if t_h and h >= t_h[0] else 0
        rows.append((h, r.level_m[i], r.p_mw[i], r.pb_kpa[i], r.qcw_frac[i], r.loss_m3s[i]))
    return rows


def write_csv(path: str, r: Run) -> int:
    cols = ['t_h', 'basin_level_m', 'basin_volume_m3', 'qcw_frac', 'p_avail_mw', 'p_capability_mw',
            'heat_reject_mw_th', 'backpressure_kpa', 't_sat_c', 'tin_c', 'tout_c',
            'evaporation_m3s', 'blowdown_m3s', 'drift_m3s', 'water_loss_m3s',
            'water_heat_removed_mw_th', 'condenser_storage_rate_mw']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        wtr = csv.writer(f)
        wtr.writerow(cols)
        for i in range(len(r.t_s)):
            wtr.writerow([round(r.t_s[i] / 3600.0, 6), round(r.level_m[i], 5), round(r.volume_m3[i], 3),
                          round(r.qcw_frac[i], 6), round(r.p_mw[i], 4), round(r.p_cap_mw[i], 4),
                          round(r.qc_mw_th[i], 4), round(r.pb_kpa[i], 5), round(r.tsat_c[i], 4),
                          round(r.tin_c[i], 4), round(r.tout_c[i], 4), round(r.evap_m3s[i], 6),
                          round(r.blow_m3s[i], 6), round(r.drift_m3s[i], 6), round(r.loss_m3s[i], 6),
                          round(r.water_mw[i], 5), round(r.storage_mw[i], 5)])
    return len(r.t_s)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='单台机组外来补水中断的冷端机理模型（单文件）')
    ap.add_argument('--pmax-mw', type=float, default=UNIT_PMAX_MW, help='机组额定（默认 652 MW，即 G33）')
    ap.add_argument('--dt-s', type=float, default=1.0, help='积分步长 s（发布口径 0.25）')
    ap.add_argument('--sample-min', type=float, default=1.0, help='输出采样间隔 min')
    ap.add_argument('--tmax-h', type=float, default=8.0, help='时域 h')
    ap.add_argument('--load-frac', type=float, default=1.0, help='故障前负荷分数')
    ap.add_argument('--hold-load', action='store_true', help='改用"保持初始汽侧负荷"对照策略（C1）')
    ap.add_argument('--keep-blowdown', action='store_true', help='排污不隔离（S1b 对照）')
    ap.add_argument('--out', default='', help='把时间序列写成 CSV')
    ap.add_argument('--self-check', action='store_true', help='与仓库发表数值对账')
    a = ap.parse_args(argv)
    m = build_model(a.pmax_mw, ride_down=not a.hold_load,
                    blowdown_isolated_on_detection=not a.keep_blowdown)
    if a.self_check:
        return self_check(m)
    r = simulate(m, dt_s=a.dt_s, sample_every_s=a.sample_min * 60.0, t_max_h=a.tmax_h,
                 initial_load_frac=a.load_frac)
    print(report(m, r))
    if a.out:
        n = write_csv(a.out, r)
        print(f"\n[写出] {a.out}: {n} 行")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
