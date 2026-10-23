"""
cascade.py — 机组故障 → 级联 → 母线失效 量化引擎（v2）
=========================================================
分层
  L0 再调度     : 在线机组按可用备用比例承担缺失出力（受 reserve_factor 约束）
  L1 稳态潮流   : AC Newton-Raphson，逐孤岛求解
  L2 保护动作   : 线路过载跳闸 / 机端电压越限跳机 / 发电机频保跳机 / 过频切机
  L3 频率动态   : 降阶 SFR（惯性 + 调差 + 阻尼 + 负荷频率特性）→ f_nadir, RoCoF
  L4 安控动作   : UVLS（逐母线限 2 轮）/ UFLS（限 3 轮）
  L5 状态/端点 : F1 越限、F2a 严重低压、F2b 潮流不可解、F3 无源失电；主端点 H=F2b∨F3；切负荷另计

关键工程约束（v1 的两个坑，已修正）
  * 退出运行的母线进入 dead 集，后续不再参与计数（避免重复累计失负荷）
  * UVLS/UFLS 有轮次上限，防止控制动作无限重复触发造成"必然全网崩溃"
"""

from __future__ import annotations

import copy
import numpy as np
from pypower.api import case30, runpf, ppoption
from grid.vcls import vcls

# ============================================================
# 参数（论文中作为灵敏度分析维度）
# ============================================================
CFG = dict(
    f0=60.0,
    v_lo=0.95, v_hi=1.05,          # F1 电压越限
    v_collapse=0.80,               # F2a 严重低压状态（本身不等于硬失供）
    v_uvls1=0.92, v_uvls2=0.88,
    uvls_step1=0.10, uvls_step2=0.25,
    uvls_max_rounds=2,
    v_gen_trip_lo=0.90, v_gen_trip_hi=1.10,
    line_trip=1.25,                # 载流率跳闸阈值
    reserve_factor=0.90,
    reserve_margin=0.15,        # 有效 Pmax = max(Pmax, Pg*(1+margin))
    H_default=5.0, droop=0.05, damping=1.0, Tg=0.30,
    f_uf=[59.30, 58.90, 58.50],
    ufls_frac=[0.07, 0.07, 0.07],
    f_gen_trip=57.5, f_of=60.5,
    max_stages=15,
    shed_on_diverge=0.05,
    max_shed_rounds=15,
)

BUS_I, BUS_TYPE, BUS_PD, BUS_QD, BUS_VM = 0, 1, 2, 3, 7
GEN_BUS, GEN_PG, GEN_QG, GEN_VG, GEN_STATUS, GEN_PMAX = 0, 1, 2, 5, 7, 8
BR_FBUS, BR_TBUS, BR_RATE, BR_STATUS, BR_PF, BR_PT = 0, 1, 5, 10, 13, 15


# ============================================================
# 1. 拓扑与潮流
# ============================================================
def find_islands(case):
    buses = case["bus"][:, BUS_I].astype(int)
    adj = {int(b): set() for b in buses}
    for r in case["branch"]:
        if int(r[BR_STATUS]) <= 0:
            continue
        f, t = int(r[BR_FBUS]), int(r[BR_TBUS])
        if f in adj and t in adj:
            adj[f].add(t)
            adj[t].add(f)
    seen, out = set(), []
    for b in adj:
        if b in seen:
            continue
        stack, comp = [b], []
        seen.add(b)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        out.append(comp)
    return out


def extract_subcase(case, buses):
    buses = sorted(buses)
    idx = {b: i + 1 for i, b in enumerate(buses)}
    bus = np.array([r for r in case["bus"] if int(r[0]) in idx], dtype=float)
    bus[:, BUS_I] = [idx[int(b)] for b in bus[:, BUS_I]]
    br = [r for r in case["branch"] if int(r[0]) in idx and int(r[1]) in idx]
    branch = np.array(br, dtype=float) if br else np.zeros((0, case["branch"].shape[1]))
    if branch.size:
        branch[:, BR_FBUS] = [idx[int(b)] for b in branch[:, BR_FBUS]]
        branch[:, BR_TBUS] = [idx[int(b)] for b in branch[:, BR_TBUS]]
    g = [r for r in case["gen"] if int(r[0]) in idx]
    gen = np.array(g, dtype=float) if g else np.zeros((0, case["gen"].shape[1]))
    if gen.size:
        gen[:, GEN_BUS] = [idx[int(b)] for b in gen[:, GEN_BUS]]
    return {"version": "2", "baseMVA": case["baseMVA"],
            "bus": bus, "branch": branch, "gen": gen}, {v: k for k, v in idx.items()}


def set_slack(sub):
    gen = sub["gen"]
    online = np.where(gen[:, GEN_STATUS] > 0)[0]
    if online.size == 0:
        return False
    k = online[np.argmax(gen[online, GEN_PMAX])]
    slack = int(gen[k, GEN_BUS])
    gb = set(gen[online, GEN_BUS].astype(int))
    for i, r in enumerate(sub["bus"]):
        b = int(r[BUS_I])
        sub["bus"][i, BUS_TYPE] = 3 if b == slack else (2 if b in gb else 1)
    return True


def solve_island(sub, cfg=CFG):
    """
    单孤岛求解。
    返回 (潮流结果, {母线: 减载MW}, 该岛未供负荷 MW, 是否收敛)
    · 直接收敛      → (res, {}, 0, True)
    · 崩溃但减载生存 → (res_λ*, shed_per_bus, shed, True)
    · 真实崩溃      → (None, shed_per_bus, shed, False)
    """
    sub = copy.deepcopy(sub)
    if not set_slack(sub):
        return None, {}, 0.0, False
    r = vcls(sub)
    if r["ok"]:
        return r["res"], {}, 0.0, True
    if r["res"] is None:
        return None, r["shed_per_bus"], r["shed_total"], False
    return r["res"], r["shed_per_bus"], r["shed_total"], True


# ============================================================
# 2. 频率动态
# ============================================================
def sfr_nadir(dp_pu, h_sys, cfg=CFG):
    """dp_pu = 有功缺额（标幺，负值缺额）。返回 (最低频率 Hz, 初始 RoCoF Hz/s)"""
    dt, t_end = 0.01, 30.0
    w = pm = 0.0
    f_min = cfg["f0"]
    rocof = dp_pu * cfg["f0"] / (2 * max(h_sys, 1e-6))
    for _ in range(int(t_end / dt)):
        def d(w_, p_):
            return ((p_ + dp_pu - cfg["damping"] * w_) / (2 * h_sys),
                    (-w_ / cfg["droop"] - p_) / cfg["Tg"])
        k1 = d(w, pm)
        k2 = d(w + .5 * dt * k1[0], pm + .5 * dt * k1[1])
        w += dt * k2[0]
        pm += dt * k2[1]
        f_min = min(f_min, cfg["f0"] * (1 + w))
    return f_min, rocof


# ============================================================
# 3. 级联仿真器
# ============================================================
class CascadeSim:
    def __init__(self, case=None, cfg=CFG, load_scale=1.0, *, sync_dispatch=False):
        self.cfg = cfg
        self.sync_dispatch = bool(sync_dispatch)
        self.base = copy.deepcopy(case) if case is not None else case30()
        # ---- 逐母线电压限值（优先用例数据 VMIN/VMAX，回退到 cfg）----
        vmax_case = self.base["bus"][:, 11].copy()
        vmin_case = self.base["bus"][:, 12].copy()
        self.v_hi_bus = np.where((vmax_case > 0) & (vmax_case <= 1.5),
                                 vmax_case, cfg["v_hi"])
        self.v_lo_bus = np.where((vmin_case > 0.5) & (vmin_case < 1.0),
                                 vmin_case, cfg["v_lo"])
        # 机端电压设定值夹到算例限值内，保证 N-0 安全
        self.base["gen"][:, GEN_VG] = np.clip(
            self.base["gen"][:, GEN_VG],
            self.v_lo_bus.max() + 0.005, self.v_hi_bus.min() - 0.005)
        self.base["bus"][:, BUS_PD] *= load_scale
        self.base["bus"][:, BUS_QD] *= load_scale
        self.base["gen"][:, GEN_PMAX] = np.maximum(
            self.base["gen"][:, GEN_PMAX],
            self.base["gen"][:, GEN_PG] * (1 + cfg["reserve_margin"]))
        self.load_scale = load_scale
        self.gen_bus = {int(g[GEN_BUS]): i for i, g in enumerate(self.base["gen"])}
        self.bus_ids = self.base["bus"][:, BUS_I].astype(int)
        self.load0 = dict(zip(self.bus_ids, self.base["bus"][:, BUS_PD]))
        self.total_load0 = float(self.base["bus"][:, BUS_PD].sum())
        online0 = self.base["gen"][:, GEN_STATUS] > 0
        self.total_gen0_mw = float(self.base["gen"][online0, GEN_PG].sum())
        self.vlim = {int(b): (float(lo), float(hi)) for b, lo, hi
                     in zip(self.bus_ids, self.v_lo_bus, self.v_hi_bus)}
        # ---- 基线（N-0）合格性：用于区分"新增失效"与"基线已越限" ----
        self.base_v = self._baseline_voltage()

    def _baseline_voltage(self):
        """求解 N-0 基线，返回 {母线: V}。"""
        r = solve_island(copy.deepcopy(self.base), self.cfg)
        res = r[0]
        if res is None:
            return {}
        return {int(row[BUS_I]): float(row[BUS_VM]) for row in res["bus"]}

    # ---------- 再调度 ----------
    def _redispatch(self, case, lost_mw):
        gen = case["gen"]
        online = gen[:, GEN_STATUS] > 0
        head = np.where(online, np.maximum(gen[:, GEN_PMAX] - gen[:, GEN_PG], 0), 0)
        avail = head * self.cfg["reserve_factor"]
        tot = avail.sum()
        if tot <= 1e-9:
            return 0.0
        pick = min(lost_mw, tot)
        gen[online, GEN_PG] += avail[online] / tot * pick
        return pick

    # ---------- 单场景 ----------
    def run_scenario(self, gen_trip=(), line_trip=(), *, dispatch_override=None):
        cfg = self.cfg
        case = copy.deepcopy(self.base)
        log = []
        fail = {int(b): {"F1": False, "F1_new": False,
                         "F2": False, "F2a": False, "F2b": False, "F2c": False,
                         "F3": False,
                         "v_sev": 0.0, "vmin": 1.0, "vmax": 1.0,
                         "shed": 0.0, "stage_failed": None, "causes": set()}
                for b in self.bus_ids}
        trace = []            # 结构化传播记录（供因果链分析）
        dead = set()          # 已退出的母线（不再参与任何计数）
        uvls_round = {b: 0 for b in self.bus_ids}
        ufls_round = 0
        total_shed = 0.0

        def mark(b, kind, cause, stage):
            b = int(b)
            if b in dead:
                return
            d = fail[b]
            d[kind] = True
            d["causes"].add(cause)
            if d["stage_failed"] is None:
                d["stage_failed"] = stage

        def shed_at(b, mw, cause, stage, kind=None):
            nonlocal total_shed
            b = int(b)
            if b in dead or mw <= 1e-9:
                return
            fail[b]["shed"] += mw
            total_shed += mw
            if kind:
                mark(b, kind, cause, stage)

        # ---- 阶段 0：初始故障 ----
        lost = 0.0
        for gb in gen_trip:
            i = self.gen_bus[int(gb)]
            if case["gen"][i, GEN_STATUS] > 0:
                lost += case["gen"][i, GEN_PG]
                case["gen"][i, GEN_STATUS] = 0
                case["gen"][i, GEN_PG] = case["gen"][i, GEN_QG] = 0.0
                log.append((0, "gen_trip", f"bus {int(gb)} "
                            f"({case['gen'][i, GEN_PMAX]:.0f}MW)"))
        for ln in line_trip:
            if case["branch"][ln, BR_STATUS] > 0:
                case["branch"][ln, BR_STATUS] = 0
                log.append((0, "line_trip", f"branch#{ln}"))
        if dispatch_override is None:
            picked = self._redispatch(case, lost)
        else:
            # 外部动态耦合器已按时间推进到当前 Pg；将该终态写入潮流初值，避免重复理想再调度。
            for gb, pg in dispatch_override.items():
                i = self.gen_bus.get(int(gb))
                if i is None or case["gen"][i, GEN_STATUS] <= 0:
                    continue
                pmax = float(case["gen"][i, GEN_PMAX])
                case["gen"][i, GEN_PG] = min(max(float(pg), 0.0), pmax)
            increase = sum(max(0.0, float(case["gen"][i, GEN_PG] - self.base["gen"][i, GEN_PG]))
                           for i in range(len(case["gen"]))
                           if case["gen"][i, GEN_STATUS] > 0)
            picked = min(lost, increase)
        shortfall = max(lost - picked, 0.0)

        stage, f_nad, rocof = 0, cfg["f0"], 0.0
        active = True
        while active and stage < cfg["max_stages"]:
            stage += 1
            active = False

            # ===== L1 潮流 + L4 拓扑 =====
            vm, loading = {}, {}
            for isl in find_islands(case):
                live = [b for b in isl if b not in dead]
                if not live:
                    continue
                has_gen = any(int(g[GEN_BUS]) in live and g[GEN_STATUS] > 0
                              for g in case["gen"])
                if not has_gen:
                    for b in live:
                        mark(b, "F3", "island_without_source", stage)
                        shed_at(b, self._current_load(case, b), "deenergized", stage)
                        dead.add(b)
                    self._remove(case, live)
                    log.append((stage, "island_deenergized", f"{len(live)} buses"))
                    active = True
                    continue

                sub, back = extract_subcase(case, live)
                res, shed_bus, shed, ok = solve_island(sub, cfg)
                if not ok:
                    for b in live:
                        mark(b, "F2b", "divergence", stage)
                        mark(b, "F2", "divergence", stage)
                        shed_at(b, self._current_load(case, b), "collapse", stage)
                        dead.add(b)
                    self._remove(case, live)
                    log.append((stage, "island_collapse", f"{len(live)} buses"))
                    active = True
                    continue
                if shed > 1e-6:
                    for b_sub, mw in shed_bus.items():
                        b = back.get(int(b_sub), int(b_sub))
                        cur = self._current_load(case, b)
                        keep = max(0.0, 1.0 - mw / max(cur, 1e-9))
                        m = case["bus"][:, BUS_I].astype(int) == b
                        case["bus"][m, BUS_PD] *= keep
                        case["bus"][m, BUS_QD] *= keep
                        shed_at(b, min(mw, cur), "vcls", stage)
                    log.append((stage, "load_shed_vcls", f"{shed:.0f} MW "
                                f"lambda={1-shed/max(sum(shed_bus.values())+0,1e-9):.2f}"))

                if self.sync_dispatch:
                    # Coupled dynamic runs carry solved Pg/Qg into the next cascade stage.
                    for gpf in res["gen"]:
                        original_bus = back[int(gpf[GEN_BUS])]
                        gi = self.gen_bus.get(int(original_bus))
                        if gi is not None and case["gen"][gi, GEN_STATUS] > 0:
                            case["gen"][gi, GEN_PG] = float(gpf[GEN_PG])
                            case["gen"][gi, GEN_QG] = float(gpf[GEN_QG])

                for row in res["bus"]:
                    vm[back[int(row[BUS_I])]] = row[BUS_VM]
                for row in res["branch"]:
                    if row[BR_STATUS] <= 0:
                        continue
                    rate = row[BR_RATE] if row[BR_RATE] > 0 else 1e9
                    ld = max(abs(row[BR_PF]), abs(row[BR_PT])) / rate
                    # 键必须排序：否则 fbus>tbus 的支路（case30 存在）查不到
                    key = tuple(sorted((back[int(row[BR_FBUS])], back[int(row[BR_TBUS])])))
                    loading[key] = max(ld, loading.get(key, 0.0))

            if not vm:
                break

            # ===== L5 电压判定 =====
            for b, v in vm.items():
                if b in dead:
                    continue
                fail[b]["vmin"] = min(fail[b]["vmin"], float(v))
                fail[b]["vmax"] = max(fail[b]["vmax"], float(v))
                lo, hi = self.vlim.get(b, (cfg["v_lo"], cfg["v_hi"]))
                v0 = self.base_v.get(b, None)
                base_bad = (v0 is not None and (v0 < lo or v0 > hi))
                if v < lo or v > hi:
                    mark(b, "F1", "voltage_limit", stage)
                    if not base_bad:
                        mark(b, "F1_new", "new_voltage_violation", stage)
                    sev = (lo - v) / lo if v < lo else (v - hi) / hi
                    fail[b]["v_sev"] = max(fail[b]["v_sev"], float(sev))
                if v < cfg["v_collapse"]:
                    mark(b, "F2a", "voltage_collapse", stage)
                    mark(b, "F2", "voltage_collapse", stage)

            # ===== L2-1 线路过载跳闸 =====
            trip = set()
            for (f, t), ld in loading.items():
                if ld >= cfg["line_trip"]:
                    for i, r in enumerate(case["branch"]):
                        if (r[BR_STATUS] > 0 and
                                {int(r[BR_FBUS]), int(r[BR_TBUS])} == {f, t}):
                            trip.add(i)
            for i in sorted(trip):
                case["branch"][i, BR_STATUS] = 0
                log.append((stage, "line_overload_trip",
                            f"branch#{i} L={loading[tuple(sorted((int(case['branch'][i,BR_FBUS]), int(case['branch'][i,BR_TBUS]))))]:.2f}"))
                active = True

            # ===== L2-2 机端电压跳机 =====
            for i, g in enumerate(case["gen"]):
                if g[GEN_STATUS] <= 0:
                    continue
                v = vm.get(int(g[GEN_BUS]), np.nan)
                if np.isnan(v):
                    continue
                if v < cfg["v_gen_trip_lo"] or v > cfg["v_gen_trip_hi"]:
                    mark(int(g[GEN_BUS]), "F2c", "generator_uv_trip", stage)
                    case["gen"][i, GEN_STATUS] = 0
                    case["gen"][i, GEN_PG] = case["gen"][i, GEN_QG] = 0.0
                    log.append((stage, "gen_trip_voltage",
                                f"bus {int(g[GEN_BUS])} V={v:.3f}"))
                    active = True

            # ===== L4-1 UVLS（逐母线限轮次）=====
            for b, v in vm.items():
                if b in dead or uvls_round[b] >= cfg["uvls_max_rounds"]:
                    continue
                frac = cfg["uvls_step2"] if v < cfg["v_uvls2"] else \
                    (cfg["uvls_step1"] if v < cfg["v_uvls1"] else 0.0)
                if frac <= 0:
                    continue
                m = case["bus"][:, BUS_I].astype(int) == b
                cut = float(case["bus"][m, BUS_PD].sum()) * frac
                if cut <= 1e-6:
                    continue
                case["bus"][m, BUS_PD] *= (1 - frac)
                case["bus"][m, BUS_QD] *= (1 - frac)
                uvls_round[b] += 1
                shed_at(b, cut, f"uvls_r{uvls_round[b]}", stage)
                log.append((stage, "uvls", f"bus {b} V={v:.3f} -{cut:.0f}MW"))
                active = True

            # ===== L3 频率 → 切机 / UFLS =====
            online = case["gen"][:, GEN_STATUS] > 0
            # 同步出力的动态耦合运行，以事故前系统总出力为频率基准；
            # 旧版静态调用默认沿用原有口径，避免改变既有算例结果。
            base_mw = max(float(self.total_gen0_mw if self.sync_dispatch else
                                case["gen"][online, GEN_PG].sum()), 1.0)
            # 频率最低点在 AGC 之前的一次调频窗口内决定：
            # 只有发电机组的调差响应，不含二次调度（再调度）恢复量
            net = max(lost - total_shed, 0.0)
            f_nad, rocof = sfr_nadir(-net / base_mw, cfg["H_default"], cfg)

            if f_nad < cfg["f_gen_trip"]:
                idx = np.where(online)[0]
                if idx.size:
                    k = idx[np.argmin(case["gen"][idx, GEN_PMAX])]
                    case["gen"][k, GEN_STATUS] = 0
                    lost += case["gen"][k, GEN_PG]
                    case["gen"][k, GEN_PG] = case["gen"][k, GEN_QG] = 0.0
                    shortfall = max(lost - picked - total_shed, 0.0)
                    log.append((stage, "gen_trip_underfreq",
                                f"bus {int(case['gen'][k, GEN_BUS])} f={f_nad:.2f}"))
                    active = True
            elif f_nad > cfg["f_of"]:
                idx = np.where(online)[0]
                if idx.size > 1:
                    k = idx[np.argmin(case["gen"][idx, GEN_PMAX])]
                    case["gen"][k, GEN_STATUS] = 0
                    case["gen"][k, GEN_PG] = case["gen"][k, GEN_QG] = 0.0
                    log.append((stage, "gen_trip_overfreq",
                                f"bus {int(case['gen'][k, GEN_BUS])}"))
                    active = True
            elif (ufls_round < len(cfg["f_uf"]) and
                  f_nad < cfg["f_uf"][ufls_round]):
                frac = cfg["ufls_frac"][ufls_round]
                for b in self.bus_ids:
                    if b in dead:
                        continue
                    m = case["bus"][:, BUS_I].astype(int) == b
                    cut = float(case["bus"][m, BUS_PD].sum()) * frac
                    if cut > 1e-6:
                        case["bus"][m, BUS_PD] *= (1 - frac)
                        case["bus"][m, BUS_QD] *= (1 - frac)
                        shed_at(b, cut, f"ufls_r{ufls_round+1}", stage)
                ufls_round += 1
                log.append((stage, "ufls",
                            f"round{ufls_round} f_nad={f_nad:.2f}Hz"))
                active = True

            # ---- 结构化快照（本阶段结束时的状态）----
            trace.append(dict(
                stage=stage,
                actions=[dict(kind=a, detail=d) for st, a, d in log if st == stage],
                gen_online=sorted(int(g[GEN_BUS]) for g in case["gen"]
                                  if g[GEN_STATUS] > 0),
                volt={int(b): float(v) for b, v in vm.items() if b not in dead},
                loading={f"{f}-{t}": round(float(ld), 3)
                         for (f, t), ld in loading.items() if ld >= 1.0},
                dead=sorted(int(b) for b in dead),
                shed={int(b): float(d["shed"]) for b, d in fail.items()
                      if d["shed"] > 1e-6},
            ))

        for b, d in fail.items():
            if d["F2a"] or d["F2b"]:
                d["F2"] = True
            # Legacy composite indicator (includes ordinary F1); do not treat as the
            # study's primary hard-service-loss endpoint H=F2b or F3.
            d["I"] = bool(d["F1_new"] or d["F2a"] or d["F2b"] or d["F3"])
            d["causes"] = sorted(d["causes"])
        for b, d in fail.items():
            d["load0"] = self.load0[b]
            d["shed_frac"] = d["shed"] / max(self.load0[b], 1e-9)
        n_fail = sum(1 for b, d in fail.items() if d["I"])
        gen_final = [dict(bus=int(g[GEN_BUS]), online=bool(g[GEN_STATUS] > 0),
                          pg_mw=float(g[GEN_PG]), qg_mvar=float(g[GEN_QG]))
                     for g in case["gen"]]
        result = {"log": log, "trace": trace, "bus": fail, "stage_total": stage,
                  "n_bus_failed": n_fail, "n_bus_dead": len(dead),
                  "total_shed": total_shed, "shortfall": shortfall,
                  "f_nadir": f_nad, "rocof": rocof,
                  "shed_frac": total_shed / max(self.total_load0, 1e-9),
                  "gen_final": gen_final}
        if self.sync_dispatch:
            result["case_final"] = copy.deepcopy(case)
        return result

    # ---------- 内部工具 ----------
    @staticmethod
    def _current_load(case, b):
        m = case["bus"][:, BUS_I].astype(int) == b
        return float(case["bus"][m, BUS_PD].sum())

    @staticmethod
    def _remove(case, buses):
        for b in buses:
            m = case["bus"][:, BUS_I].astype(int) == b
            case["bus"][m, BUS_TYPE] = 4
            case["bus"][m, BUS_PD] = case["bus"][m, BUS_QD] = 0.0
            mask = ((case["branch"][:, BR_FBUS].astype(int) == b) |
                    (case["branch"][:, BR_TBUS].astype(int) == b))
            case["branch"][mask, BR_STATUS] = 0
            gmask = case["gen"][:, GEN_BUS].astype(int) == b
            case["gen"][gmask, GEN_STATUS] = 0
            case["gen"][gmask, GEN_PG] = case["gen"][gmask, GEN_QG] = 0.0


if __name__ == "__main__":
    sim = CascadeSim()
    for ev in [dict(gen_trip=[30]), dict(gen_trip=[39]), dict(gen_trip=[30, 39])]:
        r = sim.run_scenario(**ev)
        print(f"{ev}: stages={r['stage_total']} failed={r['n_bus_failed']} "
              f"dead={r['n_bus_dead']} shed={r['total_shed']:.0f}MW "
              f"({r['shed_frac']*100:.1f}%) f={r['f_nadir']:.2f}")
