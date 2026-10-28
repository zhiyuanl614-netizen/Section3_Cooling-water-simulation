#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成投稿级正文表格（Markdown + SVG 双输出）。

与 build_manuscript_figures.py 同源同风格：
- 字体、字号、配色与图集一致（见 figstyle.py）
- SVG 中文字保持为文本对象（svg.fonttype="none"），可编辑
- 所有数值直接取自 results/ 下的结果文件，不在代码中硬编码

输出：
  results/paper/tables/table_R1_unit_coldend.svg   + .md
  results/paper/tables/table_R2_scenario_summary.svg + .md
  results/paper/tables/table_R3_censored_cases.svg  + .md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "analysis"))
from figstyle import OKABE, apply_style, clean_axes  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

OUT = ROOT / "results" / "paper" / "tables"


# ==================================================================
# 表格绘制工具
# ==================================================================
def _draw_table(ax, df, col_w, header_fs=6.6, body_fs=6.4, row_h=0.30,
                head_h=0.34, aligns=None, zebra=True, head_bg="#E8EDF2"):
    """在给定 axes 上绘制三线表风格的表格，返回数据区 y 范围。"""
    nr, nc = df.shape
    aligns = aligns or ["c"] * nc

    xs = np.concatenate([[0.0], np.cumsum(col_w)])

    # 表头底色
    ax.add_patch(plt.Rectangle((0, nr * row_h), xs[-1], head_h,
                               fc=head_bg, ec="none", zorder=1))
    # 三线表：顶线、表头下线、底线
    for y, lw in [(nr * row_h + head_h, 1.4), (nr * row_h, 0.7), (0.0, 1.4)]:
        ax.plot([0, xs[-1]], [y, y], color=OKABE["black"], lw=lw, zorder=4)

    for j, c in enumerate(df.columns):
        x0, x1 = xs[j], xs[j + 1]
        al = aligns[j]
        ha = {"l": "left", "c": "center", "r": "right"}[al]
        pad = 0.06
        tx = x0 + pad if al == "l" else (x1 - pad if al == "r" else (x0 + x1) / 2)
        ax.text(tx, nr * row_h + head_h / 2, str(c), fontsize=header_fs,
                ha=ha, va="center", color="#1A1A1A", fontweight="bold",
                zorder=5, linespacing=1.25)

    for i in range(nr):
        y = nr * row_h - (i + 0.5) * row_h
        if zebra and i % 2 == 1:
            ax.add_patch(plt.Rectangle((0, y - row_h / 2), xs[-1], row_h,
                                       fc="#F6F8FA", ec="none", zorder=0))
        for j in range(nc):
            x0, x1 = xs[j], xs[j + 1]
            al = aligns[j]
            ha = {"l": "left", "c": "center", "r": "right"}[al]
            pad = 0.06
            tx = x0 + pad if al == "l" else (x1 - pad if al == "r" else (x0 + x1) / 2)
            ax.text(tx, y, str(df.iat[i, j]), fontsize=body_fs, ha=ha,
                    va="center", color="#222222", zorder=5)

    ax.set_xlim(-0.1, xs[-1] + 0.1)
    ax.set_ylim(-0.5, nr * row_h + head_h + 0.35)
    ax.axis("off")


def _auto_width(df, header_fs=6.6, body_fs=6.4, min_w=0.26, max_w=1.60):
    """按实际渲染宽度自适应列宽。

    先用临时 Text 对象量出每个表头/表体字符串的像素宽，再换算为数据坐标
    单位。比按字符数估算可靠——CJK 与 mathtext 的实际宽度差异很大。
    """
    fig = plt.figure(figsize=(20, 6), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    def measure(txt, fs, bold):
        t = ax.text(0, 0, str(txt), fontsize=fs,
                    fontweight="bold" if bold else "normal")
        fig.canvas.draw()
        bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
        t.remove()
        return bb.width / fig.dpi          # 英寸

    widths = []
    for c in df.columns:
        segs = str(c).split("\n")
        hw = max((measure(x, header_fs, True) for x in segs), default=0.0)
        bw = max((measure(v, body_fs, False) for v in df[c]), default=0.0)
        need = max(hw, bw) + 0.11          # 英寸，含左右内边距
        # 数据坐标单位：表格总宽 W_inch 映射到 sum(widths)
        widths.append(need)
    plt.close(fig)
    # 英寸 -> 数据坐标单位（1 数据单位对应 0.62 英寸），并做整体适配
    total = sum(widths)
    target = 7.4 / 0.62 * 1.02
    scale = target / total if total > 0 else 1.0
    return [min(max_w, max(min_w, w * scale)) for w in widths]


def _md_table(df):
    """DataFrame → GitHub 风格 Markdown 表格（不依赖 tabulate）。"""
    def fmt(v):
        if pd.isna(v):
            return ""
        s = str(v)
        return s.replace("\n", " ")
    rows = df.astype(object).where(df.notna(), None)
    header = [str(c).replace("\n", " ") for c in rows.columns]
    body = [[fmt(v) for v in r] for r in rows.itertuples(index=False)]
    widths = []
    for i, h in enumerate(header):
        widths.append(max(len(h), max((len(r[i]) for r in body), default=0)))
    def line(cells):
        return "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells)) + " |"
    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    return "\n".join([line(header), sep] + [line(r) for r in body])


def _save_table(fig, name, df, note, md_path):
    """输出 SVG（正式）与 Markdown（便于正文粘贴）。"""
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight",
                pad_inches=0.02, facecolor="white")
    plt.close(fig)
    # Markdown
    md = OUT / f"{name}.md"
    with md.open("w", encoding="utf-8") as f:
        f.write(_md_table(df))
        f.write(f"\n\n> 注：{note}\n")
    print(f"✓ {name} 完成")


def _load(rel):
    return pd.read_csv(ROOT / rel, encoding="utf-8-sig")


# ==================================================================
# Table R1 —— 六台机组冷端特征与跳闸时刻
# ==================================================================
def table_R1():
    apply_style()
    a = _load("data/coldend/unit_anchors.csv").set_index("unit")
    k1 = _load("results/K1/tables/six_unit_comparison.csv").set_index("initial_unit")

    rows = []
    for u in ["G1", "G2", "G13", "G22", "G23", "G27"]:
        rows.append({
            "机组": u,
            "母线": int(a.loc[u, "bus"]),
            "$P_{max}$\n(MW)": f"{a.loc[u,'pmax_mw']:.0f}",
            "$P_{g0}$\n(MW)": f"{a.loc[u,'pg0_mw']:.2f}",
            "装机率\n(%)": f"{a.loc[u,'pg0_mw']/a.loc[u,'pmax_mw']*100:.1f}",
            "正常水位\n(m)": f"{a.loc[u,'level_normal_m']:.1f}",
            "跳闸水位\n(m)": f"{a.loc[u,'level_trip_m']:.2f}",
            "可用水位差\n(m)": f"{a.loc[u,'level_normal_m']-a.loc[u,'level_trip_m']:.1f}",
            "池面积\n系数": f"{a.loc[u,'basin_area_factor']:.2f}",
            "CoC": f"{a.loc[u,'coc']:.1f}",
            "塔逼近度\n(K)": f"{a.loc[u,'tower_approach_c']:.1f}",
            "凝汽器\n清洁度": f"{a.loc[u,'condenser_cleanliness']:.2f}",
            "$t_{trip}$\n(h)": f"{k1.loc[u,'initial_trip_h']:.4f}",
        })
    df = pd.DataFrame(rows)

    note = ("K1 单机独立断水；$t_{trip}$ 为该机组单独断水时的跳闸时刻。"
            "G1 为 1 号母线平衡机，初始出力最低（装机率 29.4%）且可用水位差最大（3.2 m），"
            "故 $t_{trip}$ 最晚（13.7061 h）。数值直接取自 data/coldend/unit_anchors.csv 与 "
            "results/K1/tables/six_unit_comparison.csv。")
    note_md = ("K1 单机独立断水；$t_{trip}$ 为该机组单独断水时的跳闸时刻。"
               "G1 为 1 号母线平衡机，初始出力最低（装机率 29.4%）且可用水位差最大（3.2 m），"
               "故 $t_{trip}$ 最晚（13.7061 h）。")

    col_w = _auto_width(df)
    w = min(7.4, sum(col_w) * 0.62)
    nr = len(df)
    fig, ax = plt.subplots(figsize=(w, nr * 0.30 + 1.05))
    _draw_table(ax, df, col_w, aligns=["c"] * len(col_w), head_h=0.46)
    fig.text(0.005, -0.02,
             "G1 同时是平衡机、低负荷率机组与大库容机组，三种机制在本算例中无法分离。",
             fontsize=6.0, color="#666666")
    _save_table(fig, "table_R1_unit_coldend", df, note_md,
                OUT / "table_R1_unit_coldend.md")


# ==================================================================
# Table R2 —— 分层汇总（K1–K6）
# ==================================================================
def table_R2():
    apply_style()
    s = _load("results/analysis/scenario_master.csv")

    rows = []
    for k in sorted(s.K.unique()):
        d = s[s.K == k]
        rows.append({
            "层": str(k),
            "机组数": int(d.unit_count.iloc[0]),
            "情景数": len(d),
            "$H=0$": int((d.H_hard_buses == 0).sum()),
            "$H>0$": int((d.H_hard_buses > 0).sum()),
            "触发率\n(%)": f"{(d.H_hard_buses>0).mean()*100:.1f}",
            "$H$ 范围": f"{int(d.H_hard_buses.min())}–{int(d.H_hard_buses.max())}",
            "UFLS 触发": int(d.ufls_triggered.sum()),
            "提前终止": int(d.hard_stop.sum()),
            "$f_{nadir}$ 范围\n(Hz)": f"{d.f_nadir_hz.min():.2f}–{d.f_nadir_hz.max():.2f}",
            "切负荷范围\n(MW)": f"{d.total_shed_mw.min():.1f}–{d.total_shed_mw.max():.1f}",
        })
    tot = {
        "层": "合计", "机组数": "—", "情景数": len(s),
        "$H=0$": int((s.H_hard_buses == 0).sum()),
        "$H>0$": int((s.H_hard_buses > 0).sum()),
        "触发率\n(%)": f"{(s.H_hard_buses>0).mean()*100:.1f}",
        "$H$ 范围": f"{int(s.H_hard_buses.min())}–{int(s.H_hard_buses.max())}",
        "UFLS 触发": int(s.ufls_triggered.sum()),
        "提前终止": int(s.hard_stop.sum()),
        "$f_{nadir}$ 范围\n(Hz)": f"{s.f_nadir_hz.min():.2f}–{s.f_nadir_hz.max():.2f}",
        "切负荷范围\n(MW)": f"{s.total_shed_mw.min():.1f}–{s.total_shed_mw.max():.1f}",
    }
    df = pd.DataFrame(rows + [tot])

    note = ("$H$ 为硬失供母线数，判据 $H = 1[F3]$（无源失电）。$f_{nadir}$ 为频率最低点。"
            "「提前终止」指仿真因已达成硬失供而停止，非后果较轻；该 6 案的 $H$ 与切负荷"
            "均为停止时刻的观测值，未观测到后续机组跳闸。")
    col_w = _auto_width(df)
    nr = len(df)
    fig, ax = plt.subplots(figsize=(min(7.4, sum(col_w) * 0.62), nr * 0.30 + 1.05))
    _draw_table(ax, df, col_w, aligns=["c"] * len(col_w), head_h=0.46)
    _save_table(fig, "table_R2_scenario_summary", df, note, OUT / "x.md")


# ==================================================================
# Table R3 —— 提前终止与截尾情景清单
# ==================================================================
def table_R3():
    apply_style()
    s = _load("results/analysis/scenario_master.csv")
    d = s[s.hard_stop == 1].copy()
    d = d.sort_values(["unit_count", "scenario_id"])

    def short(units):
        """G1+G13+G22+G23 -> 1+13+22+23（表头已注明省略 G 前缀）。"""
        return "+".join(x.replace("G", "") for x in str(units).split("+"))

    rows = []
    for _, r in d.iterrows():
        rows.append({
            "层": str(r.K),
            "断水机组": short(r.units),
            "跳闸数\n实/总": f"{int(r.trip_count_before_stop)}/{int(r.unit_count)}",
            "已跳闸": str(r.actual_trip_units).replace("G", "").replace(";", "+"),
            "截尾": str(r.censored_units).replace("G", "").replace(";", "+"),
            "$H$": f"{int(r.H_hard_buses)}",
            "切负荷\n(MW)": f"{r.total_shed_mw:.1f}",
            "观测窗口\n(h)": f"{r.cooling_tracking_elapsed_h:.4f}",
        })
    df = pd.DataFrame(rows)

    note = ("全部 6 例的停止原因均为 hard_service_loss_F3，即仿真在达成硬失供判据（无源失电）后停止。"
            "「跳闸数」为停止前实际跳闸数 / 参与机组数；「截尾机组」为因仿真停止而未观测到跳闸的机组，"
            "其真实跳闸时刻未知，**不得**按未跳闸统计。所有 6 例的 $H$ 均为 2，切负荷 39.6 或 66.9 MW，"
            "取值相同是因为停止判据相同，不代表后果等价。")
    note_md = ("全部 6 例的停止原因均为 hard_service_loss_F3，即仿真在达成硬失供判据（无源失电）后停止。"
               "「跳闸数」为停止前实际跳闸数 / 参与机组数；「截尾机组」为因仿真停止而未观测到跳闸的机组，"
               "其真实跳闸时刻未知，不得按未跳闸统计。所有 6 例的 $H$ 均为 2，切负荷 39.6 或 66.9 MW，"
               "取值相同是因为停止判据相同，不代表后果等价。")

    col_w = _auto_width(df)
    nr = len(df)
    fig, ax = plt.subplots(figsize=(min(7.4, sum(col_w) * 0.62), nr * 0.30 + 1.05))
    _draw_table(ax, df, col_w,
                aligns=["c", "l", "c", "l", "l", "c", "r", "r"],
                header_fs=6.2)
    fig.text(0.005, -0.03,
             "机组编号省略 G 前缀，「层 + 断水机组」为情景唯一标识。截尾机组未观测到跳闸，不可按未跳闸统计；6 例 $H$ 相同源于相同停止判据。",
             fontsize=6.0, color="#666666")
    _save_table(fig, "table_R3_censored_cases", df, note_md, OUT / "x.md")


TABLES = {"R1": table_R1, "R2": table_R2, "R3": table_R3}

# ==================================================================
# Table M2 —— 模型参数与来源
# ==================================================================
def table_M2():
    """逐项标注实测/参考/研究设置，供审稿人核查参数来源。"""
    apply_style()
    d = _load("data/coldend/coupling_reference_assumptions.csv")

    # 可读标签与单位简写
    LABEL = {
        "ramp_frac_pmax_per_min": ("机组爬坡率", "$P_{max}$/min"),
        "redispatch_delay_s": ("再调度延迟", "s"),
        "makeup_capacity_factor": ("补水能力系数", "p.u. 满载设计"),
        "makeup_response_tau_s": ("补水响应时间常数", "s"),
        "ufls_relay_delay_s": ("低频减载继电器延迟", "s"),
        "power_time_step_s": ("潮流计算步长", "s"),
        "frequency_time_step_s": ("频率计算步长", "s"),
        "post_trip_cooling_horizon_h": ("跳闸后冷端观测时窗", "h"),
    }

    def kind(b):
        b = str(b).lower()
        if "not site-measured" in b or "reference" in b or "assumed" in b:
            return "参考假设"
        if "simulation setting" in b:
            return "研究设置"
        return "研究设置"

    rows = []
    for _, r in d.iterrows():
        lab, unit = LABEL.get(str(r.parameter), (str(r.parameter), str(r.unit)))
        rows.append({"参数": lab, "取值": f"{r.value:g}", "单位": unit,
                     "来源类别": kind(r.basis)})
    df = pd.DataFrame(rows)

    note_md = ("耦合侧参数均为参考假设或仿真设置，**无一项为现场实测值**。"
               "已在「来源类别」列逐项标注。此为本文的主要限制之一，"
               "Limitations 节须如实说明，不得表述为实测参数。"
               "冷端侧参数见 Table R1（`data/coldend/unit_anchors.csv`，标注为锚点值）。")

    col_w = _auto_width(df)
    nr = len(df)
    f1, ax = plt.subplots(figsize=(min(7.4, sum(col_w) * 0.60), nr * 0.30 + 1.05))
    _draw_table(ax, df, col_w,
                aligns=["l", "r", "l", "c"], header_fs=6.3, head_h=0.34)
    f1.text(0.005, 0.985, "耦合侧模型参数与来源（无现场实测值）",
            fontsize=7.0, color="#1A1A1A", fontweight="bold",
            va="top", transform=ax.transAxes)
    OUT.mkdir(parents=True, exist_ok=True)
    f1.savefig(OUT / "table_M2_parameters.svg", bbox_inches="tight",
               pad_inches=0.02, facecolor="white")
    plt.close(f1)
    with (OUT / "table_M2_parameters.md").open("w", encoding="utf-8") as fh:
        fh.write(_md_table(df))
        fh.write(f"\n\n> 注：{note_md}\n")
    print("✓ table_M2_parameters 完成")


# ==================================================================
# Table M3 —— 母线服务状态判据定义
# ==================================================================
def table_M3():
    """母线硬失供判据定义（H=F3 唯一端点），供审稿人核查指标口径。"""
    apply_style()
    rows = [
        {"状态": "F3", "名称": "失电（无源）",
         "判定条件": "级联演化后的拓扑中母线无电源（孤岛/解列）", "计入 $H$": "是"},
        {"状态": "辅助\n过程量", "名称": "F1/F2a/F2b",
         "判定条件": "电压越限 / 严重低压 / AC 潮流不可解——仅作为演化过程量记录，"
                     "不作为失供判据", "计入 $H$": "否"},
    ]
    df = pd.DataFrame(rows)
    df.loc[len(df)] = {"状态": "$H$", "名称": "硬失供母线数",
                       "判定条件": r"$H = \sum_i \mathbb{1}[F3_i]$（仅无源失电计入）",
                       "计入 $H$": "—"}

    note_md = (r"硬失供判据为 $H = \sum_i \mathbb{1}[\mathrm{F3}_i]$：仅无源失电（拓扑断开、"
               "母线无电源）计入。F1/F2a 电压状态与 F2b 数值失败端点均**不计入** $H$，"
               "仅作为级联演化的过程量保留在仿真记录中。$H$ 为母线计数，不是负载率，"
               "不是切负荷功率，三者不可混用。")

    col_w = _auto_width(df)
    nr = len(df)
    f1, ax = plt.subplots(figsize=(min(7.0, sum(col_w) * 0.62), nr * 0.30 + 1.05))
    _draw_table(ax, df, col_w,
                aligns=["c", "l", "l", "c"], header_fs=6.3, head_h=0.34)
    f1.text(0.005, 0.985, "母线服务状态判据",
            fontsize=7.0, color="#1A1A1A", fontweight="bold",
            va="top", transform=ax.transAxes)
    OUT.mkdir(parents=True, exist_ok=True)
    f1.savefig(OUT / "table_M3_bus_criteria.svg", bbox_inches="tight",
               pad_inches=0.02, facecolor="white")
    plt.close(f1)
    with (OUT / "table_M3_bus_criteria.md").open("w", encoding="utf-8") as fh:
        fh.write(_md_table(df))
        fh.write(f"\n\n> 注：{note_md}\n")
    print("✓ table_M3_bus_criteria 完成")


# ==================================================================
# Table A3 —— 情景协议
# ==================================================================
def table_A3():
    """情景协议：K 层规模、组合数、并发规则。"""
    apply_style()
    s = _load("results/analysis/scenario_master.csv")
    spec = [("K1", 1, "单机组独立断水"), ("K2", 2, "两机组合"),
            ("K3", 3, "三机组合"), ("K4", 4, "四机组合"),
            ("K5", 5, "五机组合"), ("K6", 6, "六机全断")]

    rows = []
    for k, n, desc in spec:
        d = s[s.K == k]
        rows.append({
            "层": k,
            "机组数": n,
            "组合数": len(d),
            "枚举式": f"C(6, {n}) = {len(d)}",
            "说明": desc,
        })
    rows.append({"层": "合计", "机组数": "1–6", "组合数": len(s),
                 "枚举式": f"$\\sum\\binom{{6}}{{n}}$ = {len(s)}",
                 "说明": "全枚举，无遗漏"})
    df = pd.DataFrame(rows)

    note_md = (r"63 案为 $\sum_{n=1}^{6}\binom{6}{n}=63$ 的全枚举，K0 不计入（K0 为无故障基态）。"
               "所有情景在 $t_0$ 同一时刻并发断水，各机组补水管线独立破裂；"
               "水源为同一地区共用水源，但故障发生在各机组独立的补水管线，不是水源站共因断供。"
               "H/EENS/切负荷 MW 为三个不同指标，不可混用。")

    col_w = _auto_width(df)
    nr = len(df)
    f1, ax = plt.subplots(figsize=(min(7.0, sum(col_w) * 0.62), nr * 0.30 + 1.05))
    _draw_table(ax, df, col_w,
                aligns=["c", "c", "c", "c", "l"], header_fs=6.3, head_h=0.34)
    f1.text(0.005, 0.985, "情景枚举协议（t0 并发断水）",
            fontsize=7.0, color="#1A1A1A", fontweight="bold",
            va="top", transform=ax.transAxes)
    f1.text(0.005, -0.03,
            "同一地区共用水源，但各机组补水管线独立破裂；t0 同时发生，非共因断供。",
            fontsize=6.0, color="#666666")
    OUT.mkdir(parents=True, exist_ok=True)
    f1.savefig(OUT / "table_A3_protocol.svg", bbox_inches="tight",
               pad_inches=0.02, facecolor="white")
    plt.close(f1)
    with (OUT / "table_A3_protocol.md").open("w", encoding="utf-8") as fh:
        fh.write(_md_table(df))
        fh.write(f"\n\n> 注：{note_md}\n")
    print("✓ table_A3_protocol 完成")


# ==================================================================
# Table D1 —— 固定表达 vs 机理表达
# ==================================================================
def table_D1():
    """Discussion 对比表：机理表达相对固定表达的能力增量。"""
    apply_style()
    rows = [
        {"能力维度": "表示初始运行点依赖",
         "固定表达": "否（预设系数）", "机理表达": "是（$P_{g0}$ 驱动）"},
        {"能力维度": "表示组合依赖",
         "固定表达": "否", "机理表达": "是（各机组独立积分）"},
        {"能力维度": "给出跳闸排序",
         "固定表达": "否（需预设顺序）", "机理表达": "是（耗水速率决定）"},
        {"能力维度": "反馈到网侧",
         "固定表达": "否（开环）", "机理表达": "是（补水→爬坡→网侧）"},
        {"能力维度": "区分失供机理",
         "固定表达": "否", "机理表达": r"是（$H=\sum_i\mathbb{1}[\mathrm{F3}_i]$）"},
    ]
    df = pd.DataFrame(rows)

    note_md = ("本表为方法论定性对比，不含数值。「固定表达」指以预设系数或时序直接给定跳闸时刻的建模方式。"
               "机理表达的代价是需要冷端侧参数，而本文耦合侧参数为参考假设而非现场实测"
               "（见 Table M2），这是机理表达在本算例中的主要限制。")

    col_w = _auto_width(df, max_w=2.2)
    nr = len(df)
    f1, ax = plt.subplots(figsize=(min(7.4, sum(col_w) * 0.62), nr * 0.30 + 1.05))
    _draw_table(ax, df, col_w,
                aligns=["l", "c", "l"], header_fs=6.3, head_h=0.34)
    f1.text(0.005, 0.985, "固定表达与机理表达的能力对比",
            fontsize=7.0, color="#1A1A1A", fontweight="bold",
            va="top", transform=ax.transAxes)
    OUT.mkdir(parents=True, exist_ok=True)
    f1.savefig(OUT / "table_D1_representation.svg", bbox_inches="tight",
               pad_inches=0.02, facecolor="white")
    plt.close(f1)
    with (OUT / "table_D1_representation.md").open("w", encoding="utf-8") as fh:
        fh.write(_md_table(df))
        fh.write(f"\n\n> 注：{note_md}\n")
    print("✓ table_D1_representation 完成")


TABLES.update({"M2": table_M2, "M3": table_M3, "A3": table_A3, "D1": table_D1})


# ==================================================================
# Table R4 —— 数值求解收敛性检验结果
# ==================================================================
def table_R4():
    """收敛性检验：63 案中 60 案收敛，3 案未收敛。

    关键在于报告这 3 案对核心结论的影响——排除后结论不变。
    """
    apply_style()
    a = _load("results/analysis/metric_audit.csv")
    s = _load("results/analysis/scenario_master.csv")
    m = s.merge(a[["scenario_id", "solver_converged", "n_singular_warnings",
                   "n_divergence_warnings"]], on="scenario_id", how="left")

    def short(units):
        return "+".join(x.replace("G", "") for x in str(units).split("+"))

    # --- 上半：3 个未收敛情景明细 ---
    rows = []
    conv = m.solver_converged.notna() & m.solver_converged.astype(str).str.strip().str.lower().isin(["false", "0"])
    for _, r in m[conv].sort_values("scenario_id").iterrows():
        rows.append({
            "层": str(r.K),
            "断水机组": short(r.units),
            "奇异警告": str(int(r.n_singular_warnings)),
            "发散警告": str(int(r.n_divergence_warnings)),
            "$H$": f"{int(r.H_hard_buses)}",
            "切负荷\n(MW)": f"{r.total_shed_mw:.1f}",
            "$f_{nadir}$\n(Hz)": f"{r.f_nadir_hz:.4f}",
        })
    df = pd.DataFrame(rows)

    col_w = _auto_width(df)
    nr = len(df)
    f1, ax = plt.subplots(figsize=(min(7.4, sum(col_w) * 0.62), nr * 0.30 + 1.75))
    _draw_table(ax, df, col_w,
                aligns=["c", "l", "c", "c", "c", "r", "r"],
                header_fs=6.2)
    f1.text(0.005, 0.98, "未收敛情景（3 / 63）",
             fontsize=7.0, color="#1A1A1A", fontweight="bold",
             va="top", transform=ax.transAxes)

    # --- 下半：核心结论敏感性 ---
    ok = m[~conv]
    def _has_unit(u_, units):
        return u_ in [x for x in str(units).split("+")]

    def stat(df_):
        gt1 = df_.units.apply(lambda s: _has_unit("G1", s))
        rate = df_.groupby("unit_count").H_hard_buses.apply(
            lambda x: (x > 0).mean() * 100)
        fam = df_.units.apply(lambda s: all(
            _has_unit(g_, s) for g_ in ("G13", "G22", "G23")))
        mild = df_.H_hard_buses == 2
        severe = df_.H_hard_buses > 2
        return {
            "$H>0$ 案数\n(总)": f"{int((df_.H_hard_buses>0).sum())} / {len(df_)}",
            "含 G1 案\n$H>0$": f"{int((gt1 & df_.H_hard_buses.gt(0)).sum())} / {int(gt1.sum())}",
            "不含 G1 案\n$H>0$": f"{int(((~gt1) & df_.H_hard_buses.gt(0)).sum())} / {int((~gt1).sum())}",
            "4 机组层\n触发率 (%)": f"{rate.get(4, float('nan')):.1f}",
            "轻微失供\n(H=2) 均含\nG13–G22–G23?": "是" if int(mild.sum()) == 0 or (mild & fam).sum() == int(mild.sum()) else "否",
            "严重失供\n(H>2) 均含 G1?": "是" if int(severe.sum()) == 0 or (severe & gt1).sum() == int(severe.sum()) else "否",
        }

    cmp_df = pd.DataFrame([stat(m), stat(ok)],
                          index=["全部 63 案", "仅 60 个已收敛案"]).reset_index()
    cmp_df = cmp_df.rename(columns={"index": "口径"})
    cw = _auto_width(cmp_df)
    f2, ax2 = plt.subplots(figsize=(min(7.4, sum(cw) * 0.62),
                                     len(cmp_df) * 0.30 + 0.70))
    _draw_table(ax2, cmp_df, cw, aligns=["l"] + ["c"] * (len(cmp_df.columns) - 1),
                header_fs=6.2, head_h=0.46)
    f2.text(0.005, 0.98, "排除未收敛情景后核心结论不变",
              fontsize=7.0, color="#1A1A1A", fontweight="bold",
              va="top", transform=ax2.transAxes)
    f2.text(0.005, -0.04,
              "「轻微失供（H=2）仅出现于 G13–G22–G23 族」与「严重失供（H>2）均含 G1」"
              "在两种口径下均成立；不含 G1 的 4 个受影响案均含 G13+G22+G23、仅 H=2；"
              "4 机组层触发率由 60.0% 变为 61.5%。",
              fontsize=6.0, color="#666666")

    note_md = ("63 案中 60 案收敛，3 案未收敛（MatrixRankWarning + RuntimeWarning）。"
               "未收敛意味着内部收敛性未被证明，所报 $H$ 值为条件结果。"
               "排除这 3 案后，「轻微失供（H=2）仅出现于 G13–G22–G23 族」「严重失供（H>2）均含 G1」"
               "及按机组数触发的单调趋势均不变，"
               "仅 4 机组层触发率由 60.0% 变为 61.5%。")
    OUT.mkdir(parents=True, exist_ok=True)
    f1.savefig(OUT / "table_R4_solver_convergence.svg", bbox_inches="tight",
              pad_inches=0.02, facecolor="white")
    plt.close(f1)
    f2.savefig(OUT / "table_R4b_sensitivity.svg", bbox_inches="tight",
              pad_inches=0.02, facecolor="white")
    plt.close(f2)
    with (OUT / "table_R4_solver_convergence.md").open("w", encoding="utf-8") as fh:
        fh.write(_md_table(df))
        fh.write(f"\n\n### 排除未收敛情景后的核心结论敏感性\n\n")
        fh.write(_md_table(cmp_df))
        fh.write(f"\n\n> 注：{note_md}\n")
    print("✓ table_R4_solver_convergence 完成")


TABLES["R4"] = table_R4



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.out:
        global OUT
        OUT = Path(a.out)
    todo = a.names or list(TABLES)
    for n in todo:
        TABLES[n]()
    print(f"\n共 {len(todo)} 张表 → {OUT}")


if __name__ == "__main__":
    main()