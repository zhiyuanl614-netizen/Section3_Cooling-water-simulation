"""学术论文图生成：冷端机理与电网级联耦合研究。

对应 paper_design_master.md 第七部分图表总清单。

输出目录：results/paper/figures/
每图同时输出 PNG(300dpi) / SVG(字体可编辑) / PDF(矢量印刷)。
"""

import glob
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from analysis.figstyle import (
    K_COLOR, LIGHT_GREY, OKABE, UNIT_COLOR, UNIT_MARKER, UNIT_ORDER,
    apply_style, clean_axes, panel_label, save,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/paper/figures"
APPLY = True  # 由 __main__ 统一 apply_style()


def _load(rel):
    return pd.read_csv(ROOT / rel, encoding="utf-8-sig")


def _anchors():
    return _load("data/coldend/unit_anchors.csv").set_index("unit")


# ==================================================================
# Figure R3 —— 核心图：K2-G1-G2 跨域耦合同步时序
# ==================================================================
def fig_R3_coupled_timeseries():
    """Figure R3. K2-G1-G2 情景下冷端状态与电网响应的同步演化。

    四个面板共用时间轴：(a) 冷端水量库存 (b) 机组出力与补水需求
    (c) 汽轮机热力状态 (d) 系统频率。四条竖虚线标示实际跳闸事件。
    """
    if APPLY:
        apply_style()
    sid = "K2-G1-G2"
    cool = _load(f"results/K2/scenarios/{sid}/cooling_demand_response.csv")
    disp = _load(f"results/K2/scenarios/{sid}/dispatch_trajectory.csv")
    summ = _load("results/K2/tables/pairwise_summary.csv")
    summ = summ[summ.scenario_id == sid].iloc[0]
    anc = _anchors()
    units = ["G1", "G2"]

    # --- 提取跳闸事件（初始终端跳闸用 h，其余冷端跳闸用 s→h）
    trips = []
    for u, t in re.findall(r"([^@;]+)@([0-9.]+)h", str(summ.get("initial_trip_events", ""))):
        trips.append((u.strip(), float(t)))
    for u, t in re.findall(r"([^@;]+)@([0-9.]+)s", str(summ.get("other_coldend_trip_events", ""))):
        trips.append((u.strip(), float(t) / 3600.0))
    trips = sorted(set(trips), key=lambda z: z[1])
    t_end = max(t for _, t in trips) + 0.30

    fig, axs = plt.subplots(
        4, 1, figsize=(7.1, 9.4), sharex=True,
        gridspec_kw={"height_ratios": [0.92, 1.0, 1.0, 1.0], "hspace": 0.16},
    )

    def sub(u):
        return cool[cool.unit == u].sort_values("system_t_h")

    # ---------------- (a) 冷端库存：归一化水位裕度
    ax = axs[0]
    for u in units:
        d = sub(u)
        n, thr = float(anc.loc[u, "level_normal_m"]), float(anc.loc[u, "level_trip_m"])
        y = (d.basin_level_m - thr) / (n - thr)
        ax.plot(d.system_t_h, y, color=UNIT_COLOR[u], lw=1.7, label=u, zorder=3)
        ax.plot(d.system_t_h.iloc[-1], y.iloc[-1], UNIT_MARKER[u],
                color=UNIT_COLOR[u], ms=5, zorder=4)
    ax.axhline(0, color=OKABE["vermillion"], ls=(0, (4, 2)), lw=1.1,
               label="低水位保护阈值", zorder=2)
    ax.set_ylabel("归一化水位裕度\n$(h-h_{trip})/(h_{norm}-h_{trip})$")
    ax.set_ylim(-0.06, 1.10)
    ax.legend(loc="upper right", ncol=3, handlelength=1.8)
    clean_axes(ax)
    panel_label(ax, "(a)")

    # ---------------- (b) 出力与补水需求
    ax = axs[1]
    axr = ax.twinx()
    for u in units:
        d = sub(u)
        ax.plot(d.system_t_h, d.pg_command_mw, color=UNIT_COLOR[u], lw=1.7,
                label=f"$\\it{{P}}_{{\\mathrm{{g}}}}$ {u}", zorder=3)
        axr.plot(d.system_t_h, d.makeup_required_m3h, color=UNIT_COLOR[u], lw=1.2,
                 ls=(0, (3, 1.6)), alpha=0.9,
                 label=f"补水需求 {u}", zorder=2)
    ax.set_ylabel("机组出力 $P_\\mathrm{g}$ (MW)")
    axr.set_ylabel("补水需求 (m$^3$h$^{-1}$)")
    axr.spines["top"].set_visible(False)
    axr.grid(False)
    ax.set_ylim(0, 96)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = axr.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", ncol=2, handlelength=2.0,
              bbox_to_anchor=(0.0, 1.02))
    clean_axes(ax)
    panel_label(ax, "(b)")

    # ---------------- (c) 背压与热力能力
    ax = axs[2]
    axr = ax.twinx()
    for u in units:
        d = sub(u)
        ax.plot(d.system_t_h, d.backpressure_kpa, color=UNIT_COLOR[u], lw=1.7,
                label=f"背压 {u}", zorder=3)
        axr.plot(d.system_t_h, d.thermal_cap_mw, color=UNIT_COLOR[u], lw=1.2,
                 ls=(0, (3, 1.6)), alpha=0.9, label=f"热力能力 {u}", zorder=2)
    ax.set_ylabel("凝汽器背压 (kPa)")
    axr.set_ylabel("热力出力上限 (MW)")
    axr.spines["top"].set_visible(False)
    axr.grid(False)
    ax.set_ylim(3.2, 7.4)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = axr.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower right", ncol=2, handlelength=2.0)
    clean_axes(ax)
    panel_label(ax, "(c)")

    # ---------------- (d) 系统频率
    # 频率瞬变集中在跳闸后数秒内，故对数横轴兼顾全程与瞬态细节。
    ax = axs[3]
    t = disp.system_t_h.to_numpy()
    f = disp.frequency_hz.to_numpy()
    ax.plot(t, f, color="#333333", lw=1.4, zorder=3)
    shed = disp.shed_mw.to_numpy()
    if np.any(shed > 0):
        ax.scatter(t[shed > 0], f[shed > 0], s=18, marker="D",
                   facecolor=OKABE["vermillion"], edgecolor="white", lw=0.4,
                   label="减载动作", zorder=5)
    ax.axhline(59.30, color=OKABE["vermillion"], ls=(0, (4, 2)), lw=1.1,
               label="低频减载第一档 59.30 Hz", zorder=2)
    ax.set_ylabel("系统频率 (Hz)")
    ax.set_xlabel("相对同时断水时刻的时间 (h)")
    ax.set_ylim(59.15, 60.08)
    # 频率瞬变集中在跳闸后数秒内：附加面板 (d2) 放大跳闸前后 ±120 s 的细节。
    axins = ax.inset_axes([0.42, 0.30, 0.55, 0.62])
    m = (t >= trips[0][1] - 0.0334) & (t <= trips[0][1] + 0.0334)
    axins.plot(t[m], f[m], color="#333333", lw=1.3)
    axins.axvline(trips[0][1], color=UNIT_COLOR["G2"], ls=(0, (1, 2)), lw=0.9)
    axins.set_xlim(trips[0][1] - 0.0334, trips[0][1] + 0.0334)
    axins.set_ylim(59.38, 60.05)
    axins.tick_params(labelsize=6.5, length=2)
    axins.set_facecolor("#FAFAFA")
    axins.grid(True, color="#E6E6E6", lw=0.4)
    axins.annotate("G2 跳闸", xy=(trips[0][1], 59.40), xytext=(6, 0),
                   textcoords="offset points", fontsize=6.5,
                   color=UNIT_COLOR["G2"], fontweight="bold")
    ax.legend(loc="lower right", handlelength=2.2, ncol=1)
    clean_axes(ax)
    panel_label(ax, "(d)")

    # ---------------- 跳闸竖线（贯穿全部面板）
    for a in axs:
        for u, tt in trips:
            a.axvline(tt, color=UNIT_COLOR.get(u, GREY_FALLBACK), ls=(0, (1, 2)),
                      lw=1.0, alpha=0.75, zorder=1)
    for u, tt in trips:
        axs[0].annotate(
            f"{u} 跳闸\n{tt:.3f} h",
            xy=(tt, 1.02), xycoords=("data", "axes fraction"),
            ha="center", va="bottom", fontsize=7.6,
            color=UNIT_COLOR.get(u, GREY_FALLBACK), fontweight="bold",
            linespacing=1.35,
        )
    axs[-1].set_xlim(0, t_end)
    for a in axs:
        a.set_xlim(0, t_end)

    save(fig, OUT, "fig_R3_k2_coupled_timeseries")
    plt.close(fig)
    return trips


GREY_FALLBACK = "#444444"


# ==================================================================
# Figure R1 —— 六机冷端状态演化（P5 固定出力参考）
# ==================================================================
def fig_R1_coldend_evolution():
    """Figure R1. P5 参考情景下六台冷端机组的库存耗竭与保护动作。"""
    if APPLY:
        apply_style()
    anc = _anchors()
    series = {u: _load(f"results/reference/coldend_p5/unit_series/{u}.csv")
              for u in UNIT_ORDER}
    cap = {u: float(anc.loc[u, "pmax_mw"]) for u in UNIT_ORDER}

    fig, axs = plt.subplots(1, 3, figsize=(7.1, 3.05),
                            gridspec_kw={"width_ratios": [1.15, 1.0, 1.0],
                                         "wspace": 0.40})

    # (a) 归一化水位裕度
    ax = axs[0]
    for u in UNIT_ORDER:
        d = series[u].sort_values("t_h")
        n, thr = float(anc.loc[u, "level_normal_m"]), float(anc.loc[u, "level_trip_m"])
        y = (d.basin_level_m - thr) / (n - thr)
        ax.plot(d.t_h, y, color=UNIT_COLOR[u], lw=1.5, zorder=3)
        ax.plot(d.t_h.iloc[-1], y.iloc[-1], UNIT_MARKER[u],
                color=UNIT_COLOR[u], ms=4.5, zorder=4)
    ax.axhline(0, color=OKABE["vermillion"], ls=(0, (4, 2)), lw=1.0, zorder=2)
    ax.set_xlabel("断水后时间 (h)")
    ax.set_ylabel("归一化水位裕度")
    ax.set_ylim(-0.08, 1.08)
    clean_axes(ax)
    panel_label(ax, "(a)")

    # (b) 可用出力比例
    ax = axs[1]
    for u in UNIT_ORDER:
        d = series[u].sort_values("t_h")
        ax.plot(d.t_h, d.p_avail_mw / cap[u], color=UNIT_COLOR[u], lw=1.5, zorder=3)
    ax.axhline(1.0, color=LIGHT_GREY, ls=(0, (1, 2)), lw=0.9, zorder=1)
    ax.set_xlabel("断水后时间 (h)")
    ax.set_ylabel("可用出力 / 额定容量")
    ax.set_ylim(-0.05, 1.08)
    ax.set_yticks([0, 0.5, 1.0])
    clean_axes(ax)
    panel_label(ax, "(b)")

    # (c) 背压
    ax = axs[2]
    for u in UNIT_ORDER:
        d = series[u].sort_values("t_h")
        ax.plot(d.t_h, d.backpressure_kpa, color=UNIT_COLOR[u], lw=1.5, zorder=3)
    ax.set_xlabel("断水后时间 (h)")
    ax.set_ylabel("凝汽器背压 (kPa)")
    clean_axes(ax)
    panel_label(ax, "(c)")

    handles = [Line2D([0], [0], color=UNIT_COLOR[u], lw=1.6,
                      marker=UNIT_MARKER[u], ms=4.5, mec=UNIT_COLOR[u],
                      mfc=UNIT_COLOR[u], label=f"{u}  ({cap[u]:.0f} MW)")
               for u in UNIT_ORDER]
    fig.legend(handles=handles, ncol=3, loc="upper center",
               bbox_to_anchor=(0.5, 1.10), handlelength=1.7,
               columnspacing=2.2, handletextpad=0.5)

    save(fig, OUT, "fig_R1_coldend_evolution")
    plt.close(fig)


# ==================================================================
# Figure R2 —— 跳闸时刻的多因素分解
# ==================================================================
def fig_R2_trip_time_decomposition():
    """Figure R2. 六机组跳闸时刻排序及其物理驱动量的关系。

    (a) 跳闸时刻排序；(b) 与初始可用库容的关系；
    (c) 库容—初始出力之比，即单位出力对应的水量裕度。
    """
    if APPLY:
        apply_style()
    T = _load("results/reference/coldend_p5/trip_sequence.csv").sort_values(
        "t_trip_h").reset_index(drop=True)

    fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.72),
                            gridspec_kw={"wspace": 0.40})
    ax = axs[0]
    ypos = np.arange(len(T))[::-1]
    ax.barh(ypos, T.t_trip_h, height=0.62,
            color=[UNIT_COLOR[u] for u in T.unit], zorder=3)
    for y, (_, r) in zip(ypos, T.iterrows()):
        ax.text(r.t_trip_h + 0.30, y, f"{r.t_trip_h:.2f}", va="center",
                fontsize=7.0, color="#333333")
    ax.set_yticks(ypos, T.unit)
    ax.set_xlabel("跳闸时刻 (h)")
    ax.set_xlim(0, T.t_trip_h.max() * 1.24)
    ax.set_ylim(-0.7, len(T) - 0.3)
    clean_axes(ax, grid_axis="x")
    panel_label(ax, "(a)")

    # (b) 跳闸时刻 vs 初始可用库容
    ax = axs[1]
    for _, r in T.iterrows():
        ax.plot(r.basin_usable_m3, r.t_trip_h, UNIT_MARKER[r.unit], ms=7,
                color=UNIT_COLOR[r.unit], mec="white", mew=0.6, zorder=4)
        ax.annotate(r.unit, (r.basin_usable_m3, r.t_trip_h),
                    textcoords="offset points", xytext=(6, 3), fontsize=6.8,
                    color="#333333")
    ax.set_xlabel("初始可用库容 (m$^3$)")
    ax.set_ylabel("跳闸时刻 (h)")
    ax.set_xlim(100, 1120)
    clean_axes(ax)
    panel_label(ax, "(b)")

    # (c) 单位初始出力对应的库容裕度
    ax = axs[2]
    ratio = T.basin_usable_m3 / T.p_before_trip_mw
    for (_, r), q in zip(T.iterrows(), ratio):
        ax.plot(q, r.t_trip_h, UNIT_MARKER[r.unit], ms=7,
                color=UNIT_COLOR[r.unit], mec="white", mew=0.6, zorder=4)
        off = {"G13": (6, -10), "G23": (6, 4)}.get(r.unit, (6, 3))
        ax.annotate(r.unit, (q, r.t_trip_h), textcoords="offset points",
                    xytext=off, fontsize=6.8, color="#333333")
    ax.set_xlabel("库容 / 出力  (m$^3$MW$^{-1}$)")
    ax.set_ylabel("跳闸时刻 (h)")
    ax.set_xlim(0, 48)
    clean_axes(ax)
    panel_label(ax, "(c)")

    save(fig, OUT, "fig_R2_trip_time_decomposition")
    plt.close(fig)


# ==================================================================
# Figure R5 —— 级联后果的整体结构
# ==================================================================
def fig_R5_outcome_drivers():
    """Figure R5. 63 案整体后果结构。

    (a) 全部 63 案按机组数（K1~K6 层）布置的 H 分布，按层着色；
    (b) 台数对触发率的影响；(c) H 取值的频次分布。
    """
    if APPLY:
        apply_style()
    S = _load("results/analysis/scenario_master.csv")
    S = S.assign(
        k=S.units.str.split("+").map(len),
        cen=S.censored_units.notna().to_numpy(),
    )

    fig, axs = plt.subplots(1, 3, figsize=(7.4, 3.10),
                            gridspec_kw={"width_ratios": [1.15, 1.0, 1.0],
                                         "wspace": 0.36})

    # ---- (a) 63 案整体：按机组数布置、按 K 层着色
    ax = axs[0]
    rng = np.random.default_rng(7)
    layer = {1: LIGHT_GREY, 2: OKABE["sky"], 3: OKABE["green"],
             4: OKABE["orange"], 5: OKABE["vermillion"], 6: OKABE["blue"]}
    for _, r in S.sort_values("scenario_id").iterrows():
        xj = r.k + rng.uniform(-0.30, 0.30)
        c = layer[r.k]
        h = r.H_hard_buses
        ax.plot(xj, h, ls="none",
                marker="D" if r.cen else "o",
                ms=4.2 if r.k < 6 else 5.4, mfc=c if h > 0 else "white",
                mec=c, mew=0.9, zorder=3, alpha=0.95)
    for k in sorted(layer):
        d = S[S.k == k]
        nz = int((d.H_hard_buses > 0).sum())
        ax.text(k, -3.4, f"{nz}/{len(d)}", ha="center", va="center",
                fontsize=6.2, color=layer[k], fontweight="bold")
    ax.set_xticks([1, 2, 3, 4, 5, 6], ["K1", "K2", "K3", "K4", "K5", "K6"])
    ax.set_xlabel("同时断水机组数（K 层）")
    ax.set_ylabel("硬失供母线数 $H$")
    ax.set_xlim(0.45, 6.55)
    ax.set_ylim(-8.0, 36.5)
    ax.set_yticks([0, 10, 20, 30])
    ax.axhline(0, color="#8A8A8A", lw=0.7, zorder=2)
    ax.text(0.04, 0.965, "空心点为 $H=0$；横线标注各层 $H>0$ 案数 / 层总数",
            transform=ax.transAxes, fontsize=5.6, color="#666666",
            va="top", ha="left", style="italic")
    ax.text(3.5, -6.6, "触发率随层单调上升：0 / 6.7 / 25 / 60 / 100 / 100%",
            ha="center", va="center", fontsize=6.2, color="#1A1A1A")
    clean_axes(ax)
    panel_label(ax, "(a)")

    # ---- (b) 台数 -> 触发率
    ax = axs[1]
    ucs = sorted(S.unit_count.unique())
    tot = [int((S.unit_count == u).sum()) for u in ucs]
    pos = [int(((S.unit_count == u) & (S.H_hard_buses > 0)).sum()) for u in ucs]
    rate = [p / t * 100 for p, t in zip(pos, tot)]
    x = np.arange(len(ucs))
    ax.bar(x, rate, width=0.66, color=OKABE["green"],
           edgecolor="#00674C", lw=0.5, zorder=3)
    for xi, r, t, pv in zip(x, rate, tot, pos):
        ax.text(xi, r + 2.8, f"{r:.0f}%", ha="center", fontsize=6.6,
                color="#1A1A1A", fontweight="bold")
        ax.text(xi, 3.5, f"{pv}/{t}", ha="center", fontsize=5.8,
                color="white", fontweight="bold")
    ax.set_xticks(x, [str(u) for u in ucs])
    ax.set_xlabel("同时断水机组数")
    ax.set_ylabel("出现硬失供的占比 (%)")
    ax.set_ylim(0, 118)
    ax.set_yticks([0, 50, 100])
    ax.text(0.5, 0.965, "柱内数字为 $H>0$ 案数 / 该层总数", transform=ax.transAxes,
            fontsize=5.8, color="#666666", va="top", ha="center",
            style="italic")
    clean_axes(ax)
    panel_label(ax, "(b)")

    # ---- (c) H 取值频次
    ax = axs[2]
    hp = S[S.H_hard_buses > 0]
    cnt = hp.H_hard_buses.value_counts().sort_index()
    ax.bar(cnt.index.astype(int), cnt.to_numpy(), width=0.70,
           color=OKABE["sky"], edgecolor="#2A6F8E", lw=0.6, zorder=3)
    for xx, yy in zip(cnt.index.astype(int), cnt.to_numpy()):
        ax.text(xx, yy + 0.18, str(yy), ha="center", fontsize=6.4,
                color="#333333")
    ax.set_xlim(0, 31)
    ax.set_ylim(0, cnt.max() + 1.6)
    ax.set_xticks([2, 4, 23, 25, 27, 29])
    ax.set_yticks([0, 2, 4, 6, 8])
    ax.set_xlabel("硬失供母线数 $H$")
    ax.set_ylabel("情景数")
    ax.annotate("两簇分布", xy=(25.5, 6.4), fontsize=6.2, ha="center",
                color="#444444", style="italic")
    clean_axes(ax)
    panel_label(ax, "(c)")

    fig.text(0.012, -0.10,
             "63 案确定性情景；$H=\\sum_i\\mathbb{1}[\\mathrm{F3}_i]$（仅无源失电计入）。"
             "后果集中在 $H=2$–4 与 $H=23$–29 两簇：轻微失供仅出现于 G13–G22–G23 族，"
             "严重失供（$H>2$）均含平衡机 G1——均为枚举属性，非预设假设。",
             fontsize=6.0, color="#666666")

    save(fig, OUT, "fig_R5_outcome_drivers")
    plt.close(fig)


# ==================================================================
# Figure R6 —— 母线失供的空间模式
# ==================================================================
def fig_R6_bus_loss_pattern():
    """Figure R6. 出现硬失供的 22 个情景中，各母线的失供频次与空间分布。

    (a) 按失供频次排序的母线条形图（仅标注频次发生变化的母线）；
    (b) 母线编号沿轴的频次分布，用以显示失供集中于特定编号区段。
    """
    if APPLY:
        apply_style()
    S = _load("results/analysis/scenario_master.csv")

    def parse_buses(v):
        if not isinstance(v, str) or not v.strip():
            return []
        out = []
        for x in v.replace(";", ",").split(","):
            x = x.strip()
            if x and x != "nan":
                try:
                    out.append(int(float(x)))
                except ValueError:
                    pass
        return out

    hp = S[S.H_hard_buses > 0]
    freq = {}
    for _, r in hp.iterrows():
        for b in parse_buses(r.hard_failure_buses):
            freq[b] = freq.get(b, 0) + 1

    buses = np.array(sorted(freq))
    counts = np.array([freq[b] for b in buses])

    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.05),
                            gridspec_kw={"width_ratios": [1.45, 1.0], "wspace": 0.30})

    # ---- (a) 按频次分组的水平条形（组内合并标签，避免 29 行标签互相压盖）
    ax = axs[0]
    uniq = sorted(set(counts.tolist()), reverse=True)
    group_color = [OKABE["vermillion"], OKABE["orange"], OKABE["sky"],
                   OKABE["blue"], OKABE["green"]]
    labels, values, ypos, ylab = [], [], [], []
    y = 0.0
    for gi, cv in enumerate(uniq):
        members = sorted(buses[counts == cv])
        ax.barh(y, len(members), height=0.62, left=0,
                color=group_color[gi % len(group_color)],
                edgecolor="white", lw=0.8, zorder=3)
        labels.append(f"{cv}")
        values.append(len(members))
        ylab.append(f"{len(members)} 条母线")
        ypos.append(y)
        # 组内标注母线编号（横向排布，节省纵向空间）
        txt = " ".join(f"B{b}" for b in members)
        if len(members) <= 6:
            ax.text(len(members) + 0.4, y, txt, va="center", fontsize=6.2,
                    color="#333333")
        else:
            ax.text(len(members) + 0.4, y, txt, va="center", fontsize=5.6,
                    color="#333333", linespacing=1.4,
                    wrap=True)
        y += 1.0
    ax.set_yticks(ypos, [f"{lab}\n({yl})" for lab, yl in zip(labels, ylab)],
                  fontsize=7.0)
    ax.invert_yaxis()
    ax.set_xlabel("母线数")
    ax.set_ylabel("失供频次\n（括号内为母线数）")
    ax.set_xlim(0, 30)
    ax.set_ylim(len(uniq) - 0.4, -0.9)
    clean_axes(ax, grid_axis="x")
    panel_label(ax, "(a)")

    # ---- (b) 按母线编号排列的频次，突出集中区段
    ax = axs[1]
    ax.bar(buses, counts, width=0.78, color=OKABE["blue"],
           edgecolor="#0A4E77", lw=0.4, zorder=3)
    ax.axhline(len(hp), color=OKABE["vermillion"], ls=(0, (4, 2)), lw=1.0, zorder=2)
    ax.annotate(f"全部 {len(hp)} 个 $H>0$ 情景",
                xy=(1, len(hp)), xytext=(0, 3), textcoords="offset points",
                ha="left", fontsize=6.6, color=OKABE["vermillion"])
    top = counts.max()
    for b, c in zip(buses, counts):
        if c == top:
            ax.annotate(f"B{b}", xy=(b, c), xytext=(0, 3),
                        textcoords="offset points", ha="center",
                        fontsize=6.4, color="#333333", fontweight="bold")
    ax.set_xlabel("母线编号")
    ax.set_ylabel("出现硬失供的情景数")
    ax.set_xlim(0, 31)
    ax.set_ylim(0, len(hp) + 3.4)
    ax.set_yticks([0, 10, 20])
    clean_axes(ax)
    panel_label(ax, "(b)")

    save(fig, OUT, "fig_R6_bus_loss_pattern")
    plt.close(fig)


# ==================================================================
# Figure R7 —— 频率响应与低频减载
# ==================================================================
def fig_R7_frequency_ufls():
    """Figure R7. 频率最低点与减载量的关系及低频减载触发情况。"""
    if APPLY:
        apply_style()
    S = _load("results/analysis/scenario_master.csv")

    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9),
                            gridspec_kw={"width_ratios": [1.25, 1.0], "wspace": 0.32})

    # (a) 频率最低点分布，按是否触发减载分组
    ax = axs[0]
    rng = np.random.default_rng(11)
    for flag, color, lbl in [(False, OKABE["sky"], "未触发低频减载"),
                             (True, OKABE["vermillion"], "触发低频减载")]:
        d = S[S.ufls_triggered.astype(bool) == flag]
        x = d.f_nadir_hz.to_numpy()
        jit = rng.uniform(-0.055, 0.055, len(x))
        ax.plot(x, jit + 0.5, ls="none", marker="o", ms=4.4, alpha=0.75,
                mfc=color, mec="white", mew=0.4, label=lbl, zorder=3)
    ax.axvline(59.30, color=OKABE["vermillion"], ls=(0, (4, 2)), lw=1.1, zorder=2)
    ax.annotate("低频减载第一档 59.30 Hz", xy=(59.30, 0.60),
                xytext=(-5, 0), textcoords="offset points",
                ha="right", va="bottom", fontsize=7,
                color=OKABE["vermillion"])
    ax.set_yticks([])
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("频率最低点 (Hz)")
    ax.set_xlim(57.9, 60.1)
    ax.legend(loc="upper left", ncol=1, handletextpad=0.4)
    clean_axes(ax, grid_axis="x")
    panel_label(ax, "(a)")

    # (b) 减载功率按情景层聚合（逐案标签过多，改用分层统计）
    ax = axs[1]
    ks = [f"K{i}" for i in range(1, 7)]
    pos = []
    stat_l, ufls_l = [], []
    for i, k in enumerate(ks):
        d = S[(S.K == k) & (S.total_shed_mw > 0)]
        if not len(d):
            continue
        stat = d.static_grid_shed_mw.fillna(0)
        pos.append(i)
        stat_l.append(stat.mean())
        ufls_l.append((d.total_shed_mw - stat).clip(lower=0).mean())
    ax.bar(pos, stat_l, width=0.64, color=OKABE["green"],
           edgecolor="#00674C", lw=0.5, label="静态失供", zorder=3)
    ax.bar(pos, ufls_l, width=0.64, bottom=stat_l, color=OKABE["orange"],
           edgecolor="#A57400", lw=0.5, label="低频减载", zorder=3)
    for i, sv, uv in zip(pos, stat_l, ufls_l):
        ax.text(i, sv + uv + 5, f"{sv + uv:.0f}", ha="center", fontsize=6.8,
                color="#333333", fontweight="bold")
    ax.set_xticks(range(6), ks)
    ax.set_xlabel("情景层（同时断水机组数）")
    ax.set_ylabel("平均减载功率 (MW)")
    ax.set_ylim(0, (max([s + u for s, u in zip(stat_l, ufls_l)], default=1)) * 1.22)
    ax.legend(loc="upper left", ncol=1, handletextpad=0.4)
    clean_axes(ax)
    panel_label(ax, "(b)")

    save(fig, OUT, "fig_R7_frequency_ufls")
    plt.close(fig)


# ==================================================================
# Figure M1 —— 建模框架与三层时间尺度
# ==================================================================
def fig_M1_framework():
    """Figure M1. 冷端—电网耦合建模框架与三个时间尺度。

    上部为 RQ1 的冷端机理链（秒级定步长），中部为接口量
    $P_\\mathrm{available}(t)$ 与跳闸事件，下部为 RQ2 的电网级联链。
    """
    if APPLY:
        apply_style()
    fig, ax = plt.subplots(figsize=(7.1, 3.75))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def box(x, y, w, h, title, sub, fc, ec, fs_t=7.4, fs_s=6.4):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.4",
            fc=fc, ec=ec, lw=0.9, zorder=3))
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
                fontsize=fs_t, fontweight="bold", color="#1A1A1A", zorder=4)
        ax.text(x + w / 2, y + h * 0.26, sub, ha="center", va="center",
                fontsize=fs_s, color="#444444", zorder=4)

    def arrow(x1, y1, x2, y2, color="#3F3F3F", lw=1.0, style="-|>", ms=6):
        ax.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=ms,
            color=color, lw=lw, shrinkA=1.0, shrinkB=1.0, zorder=2))

    # ---------- RQ1 冷端机理链
    ax.text(1.5, 95, "RQ1　冷端运行机理（机组侧）", fontsize=9.0,
            fontweight="bold", color=OKABE["blue"], va="center")
    ax.add_patch(FancyBboxPatch((1.5, 58), 62, 32,
                                boxstyle="round,pad=0.5,rounding_size=1.6",
                                fc="#F2F8FC", ec=OKABE["blue"], lw=1.0,
                                alpha=0.55, zorder=1))
    steps1 = [
        ("补水中断", "$M_\\mathrm{makeup}\\!\\to\\!0$"),
        ("池水库存下降", "$V, h$"),
        ("泵与循环水", "NPSH, $q_\\mathrm{cw}$"),
        ("塔—凝汽器", "$T$, 背压"),
        ("保护动作", "$t_\\mathrm{trip}$"),
    ]
    w1, gap = 10.4, 1.9
    x0 = 4.0
    for i, (t, s) in enumerate(steps1):
        x = x0 + i * (w1 + gap)
        box(x, 70, w1, 12, t, s, "white", OKABE["blue"])
        if i < len(steps1) - 1:
            arrow(x + w1 + 0.2, 76, x + w1 + gap - 0.2, 76)
    ax.text(4.0, 62.5,
            "秒级定步长推进；慢变量为池水库存",
            fontsize=6.6, color="#3F3F3F", va="center")

    # ---------- 接口
    box(28.0, 44.0, 34.0, 9.0,
        "接口量", "可用出力 $P_\\mathrm{avail}(t)$ 与跳闸事件",
        "#FFF6E8", "#B07000", fs_t=7.8, fs_s=6.6)
    arrow(45.0, 58.0, 45.0, 53.2, color="#B07000", lw=1.2, ms=8)

    # ---------- RQ2 电网链
    ax.add_patch(FancyBboxPatch((36.0, 10), 62, 25,
                                boxstyle="round,pad=0.5,rounding_size=1.6",
                                fc="#FDF3F1", ec=OKABE["vermillion"], lw=1.0,
                                alpha=0.55, zorder=1))
    steps2 = [
        ("频率响应", "SFR / UFLS"),
        ("出力再调度", "$P_\\mathrm{g}$ 更新"),
        ("交流潮流级联", "线路 / 孤岛"),
        ("服务损失", "$H$, $f_\\mathrm{min}$, 减载"),
    ]
    ax.text(36.0, 39, "RQ2　冷源中断下的电网级联（网侧）",
            fontsize=9.0, fontweight="bold", color=OKABE["vermillion"],
            va="center")
    w2 = 13.0
    for i, (t, s) in enumerate(steps2):
        x = 38.5 + i * (w2 + 1.6)
        box(x, 19, w2, 10.5, t, s, "white", OKABE["vermillion"],
            fs_t=7.2, fs_s=6.2)
        if i < len(steps2) - 1:
            arrow(x + w2 + 0.15, 24.2, x + w2 + 1.45, 24.2)
    ax.text(70.0, 14.0,
            "级联后果由退出顺序与网侧响应共同决定，\n不由同时断水的机组台数单独决定",
            fontsize=6.6, color="#3F3F3F", va="center", ha="center",
            linespacing=1.5, style="italic")
    arrow(45.0, 44.0, 45.0, 29.7, color="#B07000", lw=1.2, ms=8)

    # ---------- 反馈回路
    ax.add_patch(FancyArrowPatch(
        (78.0, 29.5), (78.0, 62.0),
        arrowstyle="-|>", mutation_scale=8, color=OKABE["orange"], lw=1.3,
        linestyle=(0, (4, 2)), zorder=2,
        connectionstyle="arc3,rad=0.0"))
    ax.text(80.0, 45.0,
            "幸存机组 $P_\\mathrm{g}$ 变化\n反馈至冷端负荷与轨迹",
            fontsize=6.6, color=OKABE["orange"], va="center", ha="left",
            linespacing=1.4)

    # ---------- 时间尺度标注
    for y, lbl, c in [(88, "秒 — 分：冷端水力/热力动态、保护判据", OKABE["blue"]),
                      (6.5, "分 — 时：断面潮流级联、频率与减载", OKABE["vermillion"])]:
        ax.text(1.5, y, lbl, fontsize=6.8, color=c, va="center")

    save(fig, OUT, "fig_M1_framework")
    plt.close(fig)


# ==================================================================
# Figure R8 —— 未级联与提前终止情景
# ==================================================================
def fig_R8_no_cascade():
    """Figure R8. 未引发硬失供与提前终止情景的结构。

    (a) 各层未级联（H=0）案数占比；(b) 6 个提前终止案的已跳闸机组数。
    """
    if APPLY:
        apply_style()
    S = _load("results/analysis/scenario_master.csv")
    ks = [f"K{i}" for i in range(1, 7)]

    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.85),
                            gridspec_kw={"width_ratios": [1.0, 1.15], "wspace": 0.22})

    # (a) H=0 占比
    ax = axs[0]
    tot = [len(S[S.K == k]) for k in ks]
    zer = [int((S[S.K == k].H_hard_buses == 0).sum()) for k in ks]
    x = np.arange(6)
    ax.bar(x, zer, width=0.66, color=OKABE["green"],
           edgecolor="#00674C", lw=0.5, label="未级联 $H=0$", zorder=3)
    ax.bar(x, [t - z for t, z in zip(tot, zer)], width=0.66, bottom=zer,
           color=OKABE["vermillion"], edgecolor="#9C3F00", lw=0.5,
           label="出现硬失供 $H>0$", zorder=3)
    for xi, t, z in zip(x, tot, zer):
        ax.text(xi, z / 2 if z else 0, f"{z}" if z else "", ha="center",
                va="center", fontsize=7.0, color="white", fontweight="bold")
        ax.text(xi, t + 0.5, f"共 {t} 案", ha="center", fontsize=6.4,
                color="#333333")
    ax.set_xticks(x, ks)
    ax.set_xlabel("情景层（同时断水机组数）")
    ax.set_ylabel("情景数")
    ax.set_ylim(0, max(tot) + 6.5)
    ax.legend(loc="upper right", ncol=1, handletextpad=0.4)
    clean_axes(ax)
    panel_label(ax, "(a)")

    # (b) 提前终止（右截尾）案
    ax = axs[1]
    cen = S[S.censored_units.notna()].copy()
    ax.axis("off")
    if len(cen):
        cen = cen.sort_values(["K", "scenario_id"])
        ax.text(0.0, 1.00, f"提前终止情景（共 {len(cen)} 案）",
                fontsize=7.6, fontweight="bold", va="top", ha="left",
                transform=ax.transAxes)
        ax.text(0.0, 0.885,
                "均在首次出现 $H=2$ 后停止，结果为条件性值",
                fontsize=6.4, color="#444444", va="top", ha="left",
                transform=ax.transAxes, style="italic")
        y = 0.72
        for _, r in cen.iterrows():
            ax.add_patch(FancyBboxPatch(
                (0.0, y - 0.045), 0.085, 0.072,
                boxstyle="round,pad=0.004,rounding_size=0.012",
                fc=K_COLOR[r.K], ec="none",
                transform=ax.transAxes, clip_on=False))
            ax.text(0.115, y - 0.009, r.scenario_id.replace("K", ""),
                    fontsize=6.2, va="center", ha="left", transform=ax.transAxes)
            ax.text(0.99, y - 0.009,
                    f"$H$={int(r.H_hard_buses)}　跳闸 {int(r.trip_count_before_stop)} 台",
                    fontsize=6.2, va="center", ha="right", transform=ax.transAxes,
                    color="#333333")
            y -= 0.108
        ax.text(0.0, y - 0.02,
                "颜色表示所属情景层；右截尾意味着实际后果可能不低于此值",
                fontsize=6.2, color="#666666", va="top", ha="left",
                transform=ax.transAxes, style="italic")
    panel_label(ax, "(b)", dx=-0.02, dy=1.06)

    save(fig, OUT, "fig_R8_no_cascade")
    plt.close(fig)


# ==================================================================
# Figure M2 —— 冷端系统边界与因果链条
# ==================================================================
def fig_M2_coldend_boundary():
    """Figure M2. 单台机组湿冷冷端系统的物理边界、状态量与保护判据。

    以火用流（exergy-like chain）的因果链表示水量—液压—热力—保护的
    逐级传递，并标出各环节的建模状态与判据阈值。
    """
    if APPLY:
        apply_style()
    anc = _anchors()

    fig, ax = plt.subplots(figsize=(7.1, 2.92))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def node(x, y, w, h, title, sub, fc, ec, tc="#1A1A1A"):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.2",
            fc=fc, ec=ec, lw=1.0, zorder=3))
        ax.text(x + w / 2, y + h * 0.63, title, ha="center", va="center",
                fontsize=7.2, fontweight="bold", color=tc, zorder=4)
        ax.text(x + w / 2, y + h * 0.27, sub, ha="center", va="center",
                fontsize=6.0, color="#3A3A3A", zorder=4, linespacing=1.35)

    def arr(x1, y1, x2, y2, c="#3F3F3F", lw=1.1, ms=7):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                     mutation_scale=ms, color=c, lw=lw,
                                     shrinkA=0.8, shrinkB=0.8, zorder=2))

    # ---------- 上部：因果链
    ax.text(1.0, 97, "冷端因果链条（自左向右逐级传递）",
            fontsize=8.6, fontweight="bold", va="center", color="#1A1A1A")

    chain = [
        ("补水中断", "$M_\\mathrm{mk}\\!\\to\\!0$", "#FDF3F1", OKABE["vermillion"]),
        ("池水库存", "$V(t)$, $h(t)$", "#FFF9E8", "#B07000"),
        ("泵与循环水", "$q_\\mathrm{cw}$, NPSH", "#F2F8FC", OKABE["blue"]),
        ("冷却塔", "$T_\\mathrm{sb}$, $t_\\mathrm{out}$", "#F2F8FC", OKABE["blue"]),
        ("凝汽器", "$T_\\mathrm{sat}$, 背压", "#F2F8FC", OKABE["blue"]),
        ("保护判据", "$t_\\mathrm{trip}$", "#FDF3F1", OKABE["vermillion"]),
    ]
    w, gap = 14.2, 2.2
    x0 = 1.0
    for i, (t, s, fc, ec) in enumerate(chain):
        x = x0 + i * (w + gap)
        node(x, 68, w, 15, t, s, fc, ec)
        if i < len(chain) - 1:
            arr(x + w + 0.25, 75.5, x + w + gap - 0.25, 75.5)
    ax.text(x0, 63.0,
            "断水后库存单调下降 → 泵 NPSH 裕度不足 → 循环水量下降 → "
            "冷却能力恶化 → 背压上升 → 触及判据",
            fontsize=6.4, color="#3A3A3A", va="center")

    # ---------- 中部：状态量与判据
    ax.text(1.0, 54, "建模状态量与判据阈值", fontsize=8.6,
            fontweight="bold", va="center", color="#1A1A1A")

    lv = anc.level_normal_m.to_numpy()
    lt = anc.level_trip_m.to_numpy()
    rows = [
        ("池水位", "$h$ (m)",
         f"正常 {lv.min():.1f}–{lv.max():.1f}；保护 {lt.min():.2f}–{lt.max():.2f}",
         OKABE["orange"]),
        ("凝汽器背压", "$p_\\mathrm{b}$ (kPa)",
         f"保护定值 {anc.pb_trip_kpa.min():.0f}–{anc.pb_trip_kpa.max():.0f}",
         OKABE["blue"]),
        ("泵汽蚀裕度", "NPSH$_\\mathrm{m}$ (m)",
         "由扬程、流量与水池水位耦合求解",
         OKABE["blue"]),
        ("可用出力", "$P_\\mathrm{avail}$ (MW)",
         "受冷端热力上限约束，跳闸时阶跃归零",
         OKABE["vermillion"]),
    ]
    y = 44.0
    for name, sym, val, c in rows:
        ax.add_patch(FancyBboxPatch(
            (1.0, y - 3.4), 9.0, 5.4,
            boxstyle="round,pad=0.3,rounding_size=0.8",
            fc="white", ec=c, lw=0.9, zorder=3))
        ax.text(5.5, y - 0.7, name, ha="center", va="center", fontsize=6.6,
                fontweight="bold", color=c, zorder=4)
        ax.text(11.5, y - 0.7, sym, ha="left", va="center", fontsize=6.4,
                color="#1A1A1A", zorder=4)
        ax.text(28.0, y - 0.7, val, ha="left", va="center", fontsize=6.3,
                color="#3A3A3A", zorder=4)
        y -= 7.2

    # ---------- 右部：模型假设
    ax.text(53.0, 54, "模型假设", fontsize=8.6, fontweight="bold",
            va="center", color="#1A1A1A")
    assumptions = [
        "补水取自区域共用水源，但失效发生在机组侧管线",
        "（$F_\\mathrm{mode}$ = 机组补水管线破裂），非水源站共因断供",
        "断水期间不隔离排污、不执行水位触发的降负荷",
        "机组在保护动作前保持事件前的实际出力",
        "保护动作判据为低水位与背压，参数为参考假设（未实测）",
    ]
    ya = 48.0
    for i, t in enumerate(assumptions):
        ax.text(53.5, ya, "▪", fontsize=5.6, color=OKABE["green"], va="center")
        ax.text(56.0, ya, t, fontsize=6.2, va="center", color="#3A3A3A")
        ya -= 5.2

    save(fig, OUT, "fig_M2_coldend_boundary")
    plt.close(fig)


# ==================================================================
# Figure A1 —— IEEE30 拓扑与机组分布
# ==================================================================
def fig_A1_grid_topology():
    """Figure A1. IEEE30 算例拓扑、六台冷端机组接入位置与负荷分布。

    采用 spring 布局，力导向迭代使支路长度均匀且交叉最小；
    母线圆面积正比于有功负荷，彩色大圆为六台冷端机组。
    """
    if APPLY:
        apply_style()
    import networkx as nx

    bus = pd.read_csv(ROOT / "data/grid/IEEE30/bus.csv")
    br = pd.read_csv(ROOT / "data/grid/IEEE30/branch.csv")
    anc = _anchors()
    units = {int(r["bus"]): str(r.name) for _, r in anc.iterrows()}

    G = nx.Graph()
    for b in bus.itertuples():
        G.add_node(int(b.BUS_I), pd=float(b.PD_MW), bt=int(b.BUS_TYPE))
    for t in br.itertuples():
        G.add_edge(int(t.F_BUS), int(t.T_BUS))

    # spring 布局：k 增大可减少交叉， iterations 足够收敛
    pos = nx.spring_layout(G, k=0.95, iterations=600, seed=11, weight=None)

    fig, ax = plt.subplots(figsize=(7.1, 3.05))

    # 支路
    for u_, v_ in G.edges():
        x1, y1 = pos[u_]
        x2, y2 = pos[v_]
        ax.plot([x1, x2], [y1, y2], color="#C4CAD1", lw=0.6, zorder=1,
                solid_capstyle="round")

    # 负荷母线：面积 ∝ PD
    for n_, dat in G.nodes(data=True):
        x, y = pos[n_]
        pdmw = dat["pd"]
        if pdmw > 0:
            ax.scatter([x], [y], s=16 + 11.0 * np.sqrt(pdmw),
                       facecolor="#DCE9F2", edgecolor=OKABE["blue"],
                       lw=0.7, zorder=3)
            ax.text(x, y, str(n_), ha="center", va="center", fontsize=4.4,
                    color="#12455F", zorder=4)
        else:
            ax.scatter([x], [y], s=13, facecolor="white",
                       edgecolor="#7A8894", lw=0.8, zorder=3)
            ax.text(x, y, str(n_), ha="center", va="center", fontsize=4.4,
                    color="#5A6672", zorder=4)

    # 六台冷端机组：覆盖标记 + 向外标注
    for ub, un in units.items():
        x, y = pos[ub]
        ax.scatter([x], [y], s=165, marker="o",
                   facecolor=UNIT_COLOR[un], edgecolor="white", lw=1.3,
                   zorder=6)
        # 标注沿远离网络中心方向
        cx = np.mean([p[0] for p in pos.values()])
        cy = np.mean([p[1] for p in pos.values()])
        vx, vy = x - cx, y - cy
        nrm = np.hypot(vx, vy) or 1.0
        ax.text(x + vx / nrm * 0.155, y + vy / nrm * 0.155, un,
                ha="center", va="center", fontsize=7.0, fontweight="bold",
                color=UNIT_COLOR[un], zorder=7)

    ax.set_aspect("equal")
    ax.axis("off")
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    ax.set_xlim(min(xs) - 0.30, max(xs) + 0.30)
    ax.set_ylim(min(ys) - 0.26, max(ys) + 0.30)

    handles = [Line2D([0], [0], ls="none", marker="o", ms=7,
                      mfc=UNIT_COLOR[u], mec="white", label=u)
               for u in UNIT_ORDER]
    handles += [
        Line2D([0], [0], ls="none", marker="o", ms=6, mfc="#DCE9F2",
               mec=OKABE["blue"], label="负荷母线（圆面积∝有功负荷）"),
        Line2D([0], [0], color="#C4CAD1", lw=0.9, label="支路"),
    ]
    ax.legend(handles=handles, ncol=4, loc="upper center",
              bbox_to_anchor=(0.5, 0.04), columnspacing=1.5,
              handletextpad=0.4, fontsize=7.0)

    ax.text(0.5, 1.045, "IEEE30 算例：30 母线、41 支路、6 台机组，"
            "基准负荷 189.2 MW",
            transform=ax.transAxes, ha="center", va="bottom",
            fontsize=7.8, fontweight="bold")

    save(fig, OUT, "fig_A1_grid_topology")
    plt.close(fig)


# ==================================================================
# Figure A2 —— 机组冷端特性差异
# ==================================================================
def fig_A2_coldend_heterogeneity():
    """Figure A2. 六台机组冷端特性的异质性来源（多面板小倍数）。"""
    if APPLY:
        apply_style()
    anc = _anchors().reindex(UNIT_ORDER)

    panels = [
        ("pmax_mw", "额定容量 (MW)", 0),
        ("level_normal_m", "正常水位 (m)", 1),
        ("basin_area_factor", "水池面积系数 (–)", 2),
        ("twb_c", "设计湿球温度 (°C)", 3),
        ("tower_approach_c", "冷却塔逼近度 (K)", 4),
        ("coc", "凝汽器污垢系数 (–)", 5),
    ]
    fig, axs = plt.subplots(2, 3, figsize=(7.1, 3.15))
    for (col, xlabel, i) in panels:
        ax = axs.ravel()[i]
        vals = anc[col].to_numpy(dtype=float)
        y = np.arange(len(UNIT_ORDER))[::-1]
        ax.barh(y, vals, height=0.62,
                color=[UNIT_COLOR[u] for u in UNIT_ORDER],
                edgecolor="white", lw=0.5, zorder=3)
        span = max(vals.max() - vals.min(), 1e-9)
        for yy, v in zip(y, vals):
            ax.text(v + span * 0.03, yy, f"{v:g}", va="center", fontsize=6.0,
                    color="#333333")
        ax.set_yticks(y, UNIT_ORDER, fontsize=6.4)
        ax.set_xlim(0, vals.max() * 1.24)
        ax.set_xlabel(xlabel, fontsize=6.6)
        clean_axes(ax, grid_axis="x")
    fig.tight_layout(h_pad=1.5, w_pad=1.4)

    save(fig, OUT, "fig_A2_coldend_heterogeneity")
    plt.close(fig)


# ==================================================================
# Figure A3 —— 情景矩阵结构
# ==================================================================
def fig_A3_scenario_matrix():
    """Figure A3. K1–K6 情景集的组合结构、规模与硬失供结果。

    (a) 情景矩阵热图：63 个情景沿 x 轴展开，按 K1→K6 自上而下分层；
        单元颜色为硬失供母线数 H；(b) 各层规模与 H>0 案数。
    """
    if APPLY:
        apply_style()
    S = _load("results/analysis/scenario_master.csv")
    ks = [f"K{i}" for i in range(1, 7)]

    # H -> 颜色（0 近白，30 最深红）
    cmap = {0: "#F2F7F4", 2: "#FDEDE4", 4: "#FBD5C2", 23: "#F7A98C",
            25: "#F2805C", 27: "#E85A32", 29: "#C6361A", 30: "#9E2410"}

    fig = plt.figure(figsize=(7.2, 3.30))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.52, 1.0], wspace=0.28)

    # ---- (a) 情景矩阵热图
    ax = fig.add_subplot(gs[0, 0])
    CELL_W = 1.0
    BAND_GAP = 0.42
    NS = 63
    y = 0.0
    for k in reversed(ks):
        d = S[S.K == k].copy()
        d["has_g1"] = d.units.apply(lambda s: "G1" in [x for x in str(s).split("+")])
        d = d.sort_values(["has_g1", "H_hard_buses", "scenario_id"],
                          ascending=[False, False, True]).reset_index(drop=True)
        n = len(d)
        ax.add_patch(plt.Rectangle(
            (0.5, y), NS * CELL_W, 1.0, fc="#FAFBFC",
            ec="#DDE2E7", lw=0.5, zorder=1))
        for i, row in d.iterrows():
            h = int(row.H_hard_buses)
            x0 = i * CELL_W + 0.58
            yy = y + 0.28
            ax.add_patch(plt.Rectangle(
                (x0, yy), CELL_W * 0.80, 0.44,
                fc=cmap.get(h, "#FBD5C2"), ec="white", lw=0.35, zorder=3))
            if h >= 23:
                ax.text(x0 + CELL_W * 0.40, yy + 0.22, str(h), ha="center",
                        va="center", fontsize=4.0, color="white", zorder=5)
            if row.ufls_triggered:
                ax.plot([x0 + 0.10], [yy + 0.38], marker="v", ms=2.0,
                        color="#1A1A1A", zorder=5)
            if pd.notna(row.censored_units):
                ax.plot([x0 + 0.68], [yy + 0.38], marker="D", ms=1.8,
                        color="#1A1A1A", zorder=5)
        ax.text(NS * CELL_W + 0.9, y + 0.5, f"{k}   ($n$={n})",
                ha="left", va="center", fontsize=7.0,
                fontweight="bold", color=K_COLOR[k])
        y += 1.0 + BAND_GAP
    total_h = y - BAND_GAP

    ax.set_xlim(0, NS * CELL_W + 6.2)
    ax.set_ylim(total_h + 0.24, -0.55)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.text(0.5, -0.38, "63 个情景，层内按含 G1 与 $H$ 降序排列",
            fontsize=6.3, va="center", ha="left", color="#333333")
    panel_label(ax, "(a)", dx=0.0, dy=1.0)

    # 色标
    cax = ax.inset_axes([0.09, -0.125, 0.36, 0.026])
    from matplotlib.colors import BoundaryNorm, ListedColormap
    levels = [0, 4, 23, 25, 27, 29, 30]
    cols = [cmap[v] if v in cmap else cmap[29] for v in levels[:-1]]
    norm = BoundaryNorm(levels, len(cols))
    grad = np.linspace(levels[0], levels[-1], 256).reshape(1, -1)
    cax.imshow(grad, aspect="auto", cmap=ListedColormap(cols), norm=norm,
               extent=[levels[0], levels[-1], 0, 1])
    cax.set_yticks([])
    cax.set_xticks(levels, [str(v) for v in levels], fontsize=6.0)
    cax.set_xlabel("硬失供母线数 $H$", fontsize=6.6, labelpad=2)
    for sp in cax.spines.values():
        sp.set_edgecolor("#999999")
        sp.set_linewidth(0.5)

    # ---- (b) 各层规模与 H>0 案数
    ax2 = fig.add_subplot(gs[0, 1])
    tot = [len(S[S.K == k]) for k in ks]
    posn = [int((S[S.K == k].H_hard_buses > 0).sum()) for k in ks]
    x = np.arange(6)
    ax2.bar(x, tot, width=0.64, color="#E4E9EE", edgecolor="#9AA5B1", lw=0.6,
            label="情景总数", zorder=3)
    ax2.bar(x, posn, width=0.64, color=OKABE["vermillion"],
            edgecolor="#9C3F00", lw=0.6, label="出现硬失供", zorder=4)
    for xi, t, pv in zip(x, tot, posn):
        ax2.text(xi, t + 0.6, f"{t}", ha="center", fontsize=6.6,
                 color="#333333", fontweight="bold")
        if pv:
            ax2.text(xi, pv / 2, f"{pv}", ha="center", va="center",
                     fontsize=6.6, color="white", fontweight="bold")
    ax2.set_xticks(x, ks)
    ax2.set_xlabel("情景层（同时断水机组数 1–6）", fontsize=7.0)
    ax2.set_ylabel("情景数", fontsize=7.0)
    ax2.set_ylim(0, max(tot) + 3.6)
    ax2.legend(loc="upper left", fontsize=6.6, handletextpad=0.4)
    clean_axes(ax2)
    panel_label(ax2, "(b)")

    fig.text(0.012, 0.055, "▲ 触发低频减载    ◆ 提前终止（右截尾）",
             fontsize=6.2, color="#333333")

    save(fig, OUT, "fig_A3_scenario_matrix")
    plt.close(fig)


# ==================================================================
# Figure M5 —— 级联事件流程与母线状态判别准则
# ==================================================================
def fig_M5_cascade_judgement():
    """Figure M5. 逐事件断面求解流程与母线状态判别准则 H 的构成。"""
    if APPLY:
        apply_style()
    S = _load("results/analysis/scenario_master.csv")

    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.2),
                            gridspec_kw={"width_ratios": [1.0, 1.05], "wspace": 0.34})

    # ---- (a) 事件处理流程
    ax = axs[0]
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    steps = [
        ("切除已跳闸设备", "更新在线支路，拆分电气孤岛"),
        ("孤岛电源判别", "无在运电源 → F3，去电并移除"),
        ("交流潮流求解", "求解并记录数值健康度（失败不判 H）"),
        ("母线状态记录", "F3 判 H；F1/F2a/F2b 仅过程量"),
        ("低频减载检查", "频率低于第一档时减载"),
        ("累计服务损失", "$H$、减载功率、频率最低点"),
    ]
    y = 92.0
    for i, (t, s) in enumerate(steps):
        ax.add_patch(FancyBboxPatch(
            (4.0, y - 7.4), 66.0, 9.2,
            boxstyle="round,pad=0.4,rounding_size=1.0",
            fc="white", ec=OKABE["blue"] if i < 4 else OKABE["orange"],
            lw=0.9, zorder=3))
        ax.text(7.0, y - 1.7, f"{i + 1}. {t}", fontsize=7.0,
                fontweight="bold", va="center", color="#1A1A1A", zorder=4)
        ax.text(7.0, y - 5.4, s, fontsize=6.0, va="center", color="#4A4A4A",
                zorder=4)
        if i < len(steps) - 1:
            ax.add_patch(FancyArrowPatch((37.0, y - 8.0), (37.0, y - 11.6),
                                         arrowstyle="-|>", mutation_scale=7,
                                         color="#5A5A5A", lw=0.9, zorder=2))
        y -= 13.4
    ax.add_patch(FancyArrowPatch((72.0, 12.0), (72.0, 92.0),
                                 arrowstyle="-|>", mutation_scale=7,
                                 color=LIGHT_GREY, lw=1.0,
                                 linestyle=(0, (3, 2)), zorder=2))
    ax.text(74.0, 52.0, "下一事件\n断面", fontsize=6.2, color="#7A7A7A",
            va="center", linespacing=1.4)
    panel_label(ax, "(a)", dx=-0.02, dy=1.0)

    # ---- (b) H 判据构成
    ax = axs[1]
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch(
        (19.0, 78.0), 40.0, 13.0,
        boxstyle="round,pad=0.5,rounding_size=1.2",
        fc="#F2F8FC", ec=OKABE["blue"], lw=1.2, zorder=4))
    ax.text(39.0, 86.5, "$H=\\sum_i\\mathbb{1}[\\mathrm{F3}_i]$",
            ha="center", va="center", fontsize=9.0, fontweight="bold",
            color="#1A1A1A", zorder=5)

    crits = [
        ("F3", "无源失电（拓扑判据）", True, OKABE["vermillion"]),
        ("F2b", "数值失败端点", False, "#9AA5B1"),
        ("F2a", "严重低压", False, "#9AA5B1"),
        ("F1", "电压越限", False, "#9AA5B1"),
    ]
    y = 64.0
    for code, desc, counted, c in crits:
        ax.add_patch(FancyBboxPatch(
            (2.0, y - 5.0), 33.0, 9.0,
            boxstyle="round,pad=0.4,rounding_size=1.0",
            fc="white", ec=c, lw=1.0, zorder=3))
        ax.text(4.5, y + 0.9, code, ha="left", va="center", fontsize=7.6,
                fontweight="bold", color=c, zorder=4)
        ax.text(12.0, y + 0.9, desc, ha="left", va="center", fontsize=6.2,
                color="#3A3A3A", zorder=4)
        if counted:
            # 从框右侧引出，向上汇入 H
            ax.add_patch(FancyArrowPatch(
                (35.0, y + 1.5), (42.0, y + 1.5),
                arrowstyle="-", color=c, lw=1.0, zorder=3))
            ax.plot([42.0, 42.0], [y + 1.5, 84.5], color=c, lw=1.0, zorder=3)
        else:
            ax.text(36.8, y + 1.5, "不计入 $H$", fontsize=6.0, va="center",
                    ha="left", color=c, style="italic")
        y -= 12.5
    ax.add_patch(FancyArrowPatch((42.0, 84.5), (42.0, 78.6),
                                 arrowstyle="-|>", mutation_scale=8,
                                 color=OKABE["vermillion"], lw=1.2, zorder=3))

    # 数据核对：63 案的实际计数
    n_f3 = int((S.F3_buses_seen.fillna(0) > 0).sum())
    n_h = int((S.H_hard_buses > 0).sum())
    ax.text(6.0, 12.0,
            f"63 案核对：F3 出现 {n_f3} 案，$H>0$ 共 {n_h} 案\n"
            f"—— 两列严格一致（$H=\\sum\\mathbb{{1}}[F3]$）",
            fontsize=6.3, va="center", color="#3A3A3A", linespacing=1.5)
    ax.text(6.0, 3.5,
            "注：$H$ 为母线计数，不等于期望缺供电量",
            fontsize=6.0, va="center", color="#7A4A00", style="italic")
    panel_label(ax, "(b)", dx=-0.02, dy=1.0)

    fig.subplots_adjust(wspace=0.30)
    save(fig, OUT, "fig_M5_cascade_judgement")
    plt.close(fig)


# ==================================================================
# Figure D1 —— G1 跳闸时刻随组合的演化（R4 与 D1 合并，决策点 #9）
# ==================================================================
def _load_trip_events():
    """从各层汇总表抽取全部冷端跳闸事件。

    事件串格式为 ``G1@35058s``（秒）或 ``G1@13.7061h``（小时），两种单位均需处理。
    """
    rows = []
    for f in sorted(glob.glob(str(ROOT / "results/K*/tables/*.csv"))):
        d = pd.read_csv(f, encoding="utf-8-sig")
        if "scenario_id" not in d.columns or "other_coldend_trip_events" not in d.columns:
            continue
        for _, r in d.iterrows():
            ev = str(r.get("other_coldend_trip_events", ""))
            if ev == "nan" or not ev.strip():
                continue
            for u, t in re.findall(r"([^@;]+)@([0-9.]+)s", ev):
                rows.append({"sid": r.scenario_id, "unit": u.strip(),
                             "t_h": float(t) / 3600.0})
            for u, t in re.findall(r"([^@;]+)@([0-9.]+)h", ev):
                rows.append({"sid": r.scenario_id, "unit": u.strip(),
                             "t_h": float(t)})
    if not rows:
        return pd.DataFrame(columns=["sid", "unit", "t_h"])
    return (pd.DataFrame(rows).drop_duplicates(subset=["sid", "unit"])
            .reset_index(drop=True))


def fig_D1_trip_time_evolution():
    """Figure D1. 同一台机组 G1 的跳闸时刻如何随并网组合变化。

    (a) 28 个记录到 G1 跳闸时刻的组合中 G1 的跳闸时刻，按是否引发硬失供着色；
    (b) 跳闸提前量相对于 K1 独立断水基准的分布；
    (c) 提前量按组合规模（机组数）分组，显示规模与构成的共同作用。
    """
    if APPLY:
        apply_style()
    S = _load("results/analysis/scenario_master.csv")
    # K1 独立断水基准
    K1 = _load("results/K1/tables/scenario_summary.csv")
    k1 = K1[K1.initial_unit.astype(str).str.strip().eq("G1")]
    t_base = float(k1.initial_trip_h.iloc[0]) if len(k1) else 13.7061

    # G1 跳闸时刻权威源：scenario_master.trip_order（"G1@<h>" 片段，含 K1-G1）
    g1rows = []
    for _, r in S.iterrows():
        if pd.isna(r["trip_order"]):
            continue
        hit = re.search(r"G1@([\d.]+)h", str(r["trip_order"]))
        if hit:
            g1rows.append({"sid": r["scenario_id"], "t_h": float(hit.group(1))})
    g1 = (pd.DataFrame(g1rows).merge(
        S[["scenario_id", "units", "H_hard_buses", "ufls_triggered"]],
        left_on="sid", right_on="scenario_id", how="left")
        .dropna(subset=["units"]).copy())
    g1["n_units"] = g1.units.astype(str).str.split("+").map(len)
    g1["early"] = (1 - g1.t_h / t_base) * 100
    g1 = g1.sort_values("t_h").reset_index(drop=True)

    fig, axs = plt.subplots(1, 3, figsize=(7.4, 3.05),
                            gridspec_kw={"width_ratios": [1.35, 1.0, 1.0],
                                         "wspace": 0.34})

    # ---- (a) 28 案跳闸时刻（按 H 分色）
    ax = axs[0]
    x = np.arange(len(g1))
    h = g1.H_hard_buses.to_numpy()
    ax.vlines(x, t_base, g1.t_h.to_numpy(), color="#C8CDD2", lw=0.6, zorder=1)
    for xi, ti, hi in zip(x, g1.t_h.to_numpy(), h):
        c = OKABE["vermillion"] if hi > 0 else OKABE["blue"]
        ax.plot(xi, ti, ls="none", marker="o", ms=4.2, mfc=c, mec="white",
                mew=0.5, zorder=3)
    ax.axhline(t_base, color=OKABE["black"], ls=(0, (4, 2)), lw=1.1, zorder=2)
    ax.text(-0.6, t_base + 0.16, f"K1 独立断水基准 {t_base:.2f} h",
            ha="left", va="bottom", fontsize=6.4, color=OKABE["black"])
    ax.set_xlabel(f"G1 记录到跳闸的组合（{len(g1)} 案，按跳闸时刻排序）")
    ax.set_ylabel("G1 跳闸时刻 (h)")
    ax.set_xlim(-0.8, len(g1) - 0.2)
    ax.set_ylim(7.0, 14.4)
    n_tick = max(3, len(g1) // 4)
    ticks = list(range(0, len(g1), n_tick))
    if ticks[-1] != len(g1) - 1:
        ticks.append(len(g1) - 1)
    ax.set_xticks(ticks, [str(i + 1) for i in ticks])
    clean_axes(ax)
    panel_label(ax, "(a)")

    # ---- (b) 跳闸提前量分布
    ax = axs[1]
    nz = g1[g1.H_hard_buses == 0]
    yz = g1[g1.H_hard_buses > 0]
    bins = np.linspace(0, 50, 11)
    ax.hist([nz.early, yz.early], bins=bins, density=False,
            color=[OKABE["blue"], OKABE["vermillion"]],
            edgecolor="white", lw=0.6,
            label=[f"$H=0$（{len(nz)} 案）", f"$H>0$（{len(yz)} 案）"], zorder=3)
    ax.set_xlabel("相对 K1 基准的跳闸提前量 (%)")
    ax.set_ylabel("情景数")
    ax.set_xlim(0, 52)
    ax.set_xticks([0, 10, 20, 30, 40, 50])
    ax.set_yticks([0, 2, 4, 6])
    ax.legend(loc="upper left", fontsize=6.2, handletextpad=0.4)
    clean_axes(ax)
    panel_label(ax, "(b)")

    # ---- (c) 提前量按组合规模分组（排除 K1 单机基准）
    ax = axs[2]
    rng = np.random.default_rng(3)
    g1m = g1[g1.n_units >= 2]
    order = sorted(g1m.n_units.unique(), reverse=True)  # 5,4,3,2
    col = {2: OKABE["sky"], 3: OKABE["green"], 4: OKABE["orange"],
           5: OKABE["vermillion"]}
    for yi, k in enumerate(order):
        d = g1m[g1m.n_units == k]
        jit = rng.uniform(-1.4, 1.4, len(d))
        ax.plot(d.early.to_numpy() + jit, np.full(len(d), yi),
                ls="none", marker="o", ms=4.4, mfc=col[k], mec="white",
                mew=0.5, zorder=3, alpha=0.92)
        ax.text(d.early.max() + 3.2, yi, f"{len(d)} 案", va="center",
                fontsize=6.0, color="#444444")
    ax.set_yticks(range(len(order)), [f"{k} 机组" for k in order])
    ax.set_xlabel("相对 K1 基准的跳闸提前量 (%)")
    ax.set_xlim(0, 56)
    ax.set_xticks([0, 10, 20, 30, 40, 50])
    means = [np.round(d.early.mean(), 1) for k in order
             for d in [g1m[g1m.n_units == k]]]
    ax.annotate("层均值：" + " / ".join(f"{k}机 {m:.1f}%" for k, m in zip(order, means)),
                xy=(0.04, 0.96), xycoords="axes fraction", ha="left",
                va="top", fontsize=6.0, color="#444444", linespacing=1.4,
                style="italic")
    clean_axes(ax, grid_axis="x")
    panel_label(ax, "(c)")

    fig.text(0.012, -0.085,
             "同一台 G1，因并网组合不同，跳闸时刻提前 9.9%–45.4%；"
             "提前量随组合规模增大而增大，层内离散度由组合构成引起。"
             "G1 为平衡机（1 号母线），三种机制无法分离。",
             fontsize=6.0, color="#666666")

    save(fig, OUT, "fig_D1_trip_time_evolution")
    plt.close(fig)


# ==================================================================
# Figure D2 —— K2-G1-G2 事件链因果图（Discussion 机制图）
# ==================================================================
def fig_D2_event_chain():
    """Figure D2. K2-G1-G2 情景的事件链：冷端断水 → 相继跳机 → 静态级联失供。

    (a) 双泳道因果时序图：冷端域（补水中断、水位降至阈值）与电网域
        （机组跳闸、母线失供、频率）沿同一时间轴对齐；
    (b) 失供母线数的时间演化，说明 23 母线失供为一次性静态级联而非频率事件。
    """
    if APPLY:
        apply_style()
    S = _load("results/analysis/scenario_master.csv")
    r = S[S.scenario_id.astype(str).str.strip() == "K2-G1-G2"].iloc[0]
    d = pd.read_csv(ROOT / "results/K2/scenarios/K2-G1-G2/dispatch_trajectory.csv",
                    encoding="utf-8-sig")
    c = pd.read_csv(ROOT / "results/K2/scenarios/K2-G1-G2/cooling_demand_response.csv",
                    encoding="utf-8-sig")
    g1 = c[c.unit.astype(str).str.strip() == "G1"].sort_values("elapsed_min")
    g2 = c[c.unit.astype(str).str.strip() == "G2"].sort_values("elapsed_min")

    t_g2 = float(r.initial_trip_h)
    t_g1 = 9.7383
    t_end = float(d.system_t_h.max())
    buses = [b for b in str(r.hard_failure_buses).split(";") if b]

    fig = plt.figure(figsize=(7.4, 3.6))
    gs = fig.add_gridspec(2, 1, height_ratios=[2.45, 1.0], hspace=0.30,
                          left=0.085, right=0.985, top=0.90, bottom=0.17)

    # ================= (a) 双泳道因果链 =================
    ax = fig.add_subplot(gs[0])
    ax.set_xlim(-1.35, t_end + 0.55)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # 泳道底色
    for y0, y1, fc, ec, lab in [(6.55, 9.55, "#F2F6FA", "#C9D6E2", "冷端域"),
                                (2.35, 5.35, "#FAF4EE", "#E4D3BF", "电网域")]:
        ax.add_patch(FancyBboxPatch((-1.25, y0), t_end + 1.7, y1 - y0,
                                    boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc=fc, ec=ec, lw=0.7, zorder=0))
        ax.text(-1.18, y1 - 0.16, lab, fontsize=6.6, color="#55606B",
                va="top", ha="left", style="italic")

    # 时间轴
    ax.plot([-1.1, t_end + 0.35], [6.05, 6.05], color="#9AA4AE", lw=0.8, zorder=1)
    for tt in [0, 4, 8, 12]:
        if tt <= t_end:
            ax.plot([tt, tt], [5.95, 6.15], color="#9AA4AE", lw=0.8, zorder=1)
            ax.text(tt, 5.72, f"{tt} h", fontsize=6.0, color="#55606B",
                    ha="center", va="top")

    def box(x, y, w, h, txt, fc, ec, fs=6.0, tc="#1A1A1A"):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0.02,rounding_size=0.06",
                                    fc=fc, ec=ec, lw=0.8, zorder=3))
        ax.text(x + w / 2, y + h / 2, txt, fontsize=fs, color=tc,
                ha="center", va="center", zorder=4, linespacing=1.35)

    def arrow(x0, y0, x1, y1, c="#6B7480"):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=0.9,
                                    shrinkA=1.5, shrinkB=1.5), zorder=2)

    # --- 冷端域事件 ---
    box(-0.95, 7.95, 1.85, 1.0, "t=0 并发\nG1+G2 补水中断",
        "#FFFFFF", OKABE["black"], fs=5.9)
    box(2.55, 8.55, 2.05, 0.85, "G2 水位降至 1.10 m\n触及跳闸阈值",
        "#FDEBD8", OKABE["orange"], fs=5.9)
    box(2.55, 7.35, 2.05, 0.85, "G1 承担 25.97→52.64 MW\n需水 71.7→128.8 m³/h",
        "#FDEBD8", OKABE["orange"], fs=5.6)
    arrow(-0.05, 8.45, 2.50, 8.95)
    arrow(-0.05, 8.30, 2.50, 7.80)

    box(9.05, 7.95, 2.15, 1.0, "G1 水位降至 1.00 m\n触及跳闸阈值",
        "#FADBD8", OKABE["vermillion"], fs=5.9)

    # --- 电网域事件 ---
    box(2.55, 3.75, 2.05, 0.95, f"t={t_g2:.4g} h\nG2 跳闸（{t_g2:.2f} MW）",
        "#FDEBD8", OKABE["orange"], fs=5.9)
    box(5.55, 3.75, 2.05, 0.95, "调频/AGC 补偿\nG1 爬坡至 52.64 MW",
        "#E4EEF7", OKABE["blue"], fs=5.9)
    box(8.20, 3.75, 2.15, 0.95, f"t={t_g1:.4f} h\nG1 跳闸（52.64 MW）",
        "#FADBD8", OKABE["vermillion"], fs=5.9)
    box(11.05, 3.75, 2.30, 0.95, "1 号与 2 号母线失电\n→ 23 母线级联失供",
        "#FADBD8", OKABE["vermillion"], fs=5.9)

    arrow(4.62, 4.22, 5.50, 4.22)
    arrow(7.62, 4.22, 8.15, 4.22)
    arrow(10.37, 4.22, 11.00, 4.22)

    # 跨域因果箭头
    arrow(3.57, 7.32, 3.57, 4.74, c=OKABE["orange"])
    arrow(10.13, 7.92, 9.30, 4.74, c=OKABE["vermillion"])

    # 后果标签
    ax.text(11.05, 3.35, f"$H$={int(r.H_hard_buses)}   切负荷 {r.total_shed_mw:.1f} MW"
            f"   $f_{{nadir}}$={r.f_nadir_hz:.2f} Hz   UFLS 未动作",
            fontsize=5.9, color=OKABE["vermillion"], ha="center", va="top",
            style="italic")
    panel_label(ax, "(a)", dx=-0.135, dy=0.055)

    # ================= (b) 补水平衡：真实驱动量 =================
    ax2 = fig.add_subplot(gs[1])
    for u, col, lab in [("G1", OKABE["vermillion"], "G1（1 号母线，平衡机）"),
                        ("G2", OKABE["orange"], "G2（2 号母线）")]:
        du = c[c.unit.astype(str).str.strip() == u].sort_values("elapsed_min")
        ax2.plot(du.system_t_h, du.makeup_required_m3h, color=col, lw=1.35,
                 zorder=3, label=lab)
        tt = du[du.status != "online"]
        if len(tt):
            tm = float(tt.system_t_h.iloc[0])
            ax2.plot([tm], [float(tt.makeup_required_m3h.iloc[0])], ls="none",
                     marker="v", ms=6.0, mfc=col, mec="white", mew=0.7, zorder=5)

    ax2.axhline(0, color=OKABE["black"], lw=0.9, zorder=2)
    ax2.fill_between([0, t_end], -1, 0, color=OKABE["black"], alpha=0.07,
                     zorder=1)
    ax2.text(t_end * 0.015, -13.0, "补水量供给 = 0（t=0 起）", fontsize=5.9,
             color="#444444", ha="left", va="center", style="italic")
    for col, tx, ha in [(OKABE["orange"], t_g2, "right"),
                        (OKABE["vermillion"], t_g1, "left")]:
        ax2.plot([tx, tx], [0, 158], color=col, ls=(0, (3, 2)), lw=0.8, zorder=2)
    ax2.text(t_g2 - 0.22, 160, f"G2 跳闸 {t_g2:.2f} h", fontsize=5.8,
             color=OKABE["orange"], ha=ha, va="bottom")
    ax2.text(t_g1 + 0.22, 160, f"G1 跳闸 {t_g1:.2f} h", fontsize=5.8,
             color=OKABE["vermillion"], ha=ha, va="bottom")
    ax2.set_xlim(0, t_end)
    ax2.set_ylim(-22, 178)
    ax2.set_xlabel("系统时间 (h)")
    ax2.set_ylabel("冷端补水量需求 (m³/h)")
    ax2.set_yticks([0, 60, 120])
    ax2.legend(loc="lower right", fontsize=5.9, handletextpad=0.4, ncol=1,
               frameon=True, framealpha=0.92, edgecolor="#DDDDDD")
    clean_axes(ax2)
    panel_label(ax2, "(b)", dx=-0.105, dy=1.10)

    save(fig, OUT, "fig_D2_event_chain")
    plt.close(fig)


if __name__ == "__main__":
    apply_style()
    APPLY = False
    raw = sys.argv[1:]

    # --out DIR：改写输出目录（默认 results/paper/figures）
    _out_override = None
    if "--out" in raw:
        _out_override = Path(raw[raw.index("--out") + 1])

    flags = {a for a in raw if a.startswith("--") and a != "--out"}
    argv = [a for a in raw if not a.startswith("--")]
    # 摘掉 "--out" 及其取值，避免被当作图编号
    if "--out" in raw:
        argv = [a for a in argv if a != str(_out_override)]

    # --png : 额外输出 PNG(300 dpi)，供预览或投稿系统要求位图时使用
    # --pdf : 额外输出 PDF 矢量
    _orig_save = save
    _want_extra = ("--png" in flags) or ("--pdf" in flags)

    def _save(fig, out_dir, name, **_kw):
        # 只在显式请求时追加位图/PDF，默认仍只输出 SVG
        return _orig_save(fig, out_dir, name,
                          png=("--png" in flags),
                          also_pdf=("--pdf" in flags))

    which = argv[0] if argv else "all"
    fns = {
        "R1": fig_R1_coldend_evolution,
        "R2": fig_R2_trip_time_decomposition,
        "R3": fig_R3_coupled_timeseries,
        "R5": fig_R5_outcome_drivers,
        "R6": fig_R6_bus_loss_pattern,
        "R7": fig_R7_frequency_ufls,
        "M1": fig_M1_framework,
        "M2": fig_M2_coldend_boundary,
        "M5": fig_M5_cascade_judgement,
        "A1": fig_A1_grid_topology,
        "A2": fig_A2_coldend_heterogeneity,
        "A3": fig_A3_scenario_matrix,
        "R8": fig_R8_no_cascade,
        "D1": fig_D1_trip_time_evolution,
        "D2": fig_D2_event_chain,
    }
    for k, fn in fns.items():
        if which in ("all", k):
            # 各函数在定义时已绑定 save/OUT，需逐个改写其所在命名空间
            if _want_extra:
                fn.__globals__["save"] = _save
            if _out_override is not None:
                fn.__globals__["OUT"] = _out_override
            fn()
            print(f"✓ {k} 完成")
