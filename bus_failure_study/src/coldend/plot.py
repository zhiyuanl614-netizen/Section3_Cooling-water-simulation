"""
plot.py — 冷端故障 → 退出序列的三张图
=====================================
    fig_trip_sequence.png   退出序列甘特图：潜伏期 → 降负荷窗口 → 跳机时刻
    fig_power_trace.png     六台机组功率轨迹 P_i(t)（电网侧看到的慢动态）
    fig_level_trace.png     池位裕度（相对跳机水位）耗尽过程

用法：python3 src/coldend/plot.py
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coldend.fleet import OUT, run_fleet
from coldend.units import load_fleet

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP", "WenQuanYi Zen Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

COLORS = {"G1": "#34495e", "G2": "#c0392b", "G13": "#e67e22",
          "G22": "#8e44ad", "G23": "#16a085", "G27": "#2980b9"}


def fig_gantt(df: pd.DataFrame, path: str, horizon_h: float) -> None:
    d = df.sort_values("t_trip_h", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    for i, r in d.iterrows():
        c = COLORS.get(r.unit, "#555555")
        ax.plot([0, r.t_trip_h], [i, i], color=c, lw=1.25, ls="--", zorder=2)
        ax.scatter([r.t_trip_h], [i], marker="X", s=55, color="#c0392b", zorder=4)
        ax.text(r.t_trip_h + 0.22, i, f"{r.p_before_trip_mw:.0f} MW→0",
                va="center", fontsize=7.5, color="#c0392b")
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([f"{r.unit} (bus{r.bus}, {r.pmax_mw:.0f} MW, 负荷 {r.load_frac*100:.0f}%)"
                        for _, r in d.iterrows()], fontsize=8)
    ax.set_xlim(0, min(horizon_h, d.t_trip_h.max() * 1.18))
    ax.set_xlabel("时间 (h，全部机组 t=0 同时失去外来补水)", fontsize=8)
    ax.set_title("退出序列：保持故障前出力（虚线）→ 低水位保护跳机（×）",
                 fontsize=9.5, loc="left")
    ax.grid(axis="x", ls=":", lw=0.6, alpha=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=190)
    plt.close(fig)


def fig_power(df_prof: pd.DataFrame, df: pd.DataFrame, path: str) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 4.0))
    for _, r in df.iterrows():
        c = COLORS.get(r.unit, "#555555")
        ax.plot(df_prof.t_h, df_prof[r.unit], color=c, lw=1.4,
                label=f"{r.unit} · {r.pg0_mw:.1f} MW · 跳机 {r.t_trip_h:.2f} h")
    ax.set_xlabel("时间 (h)", fontsize=8)
    ax.set_ylabel("机组可用出力 (MW)", fontsize=8)
    ax.set_title("冷端故障下六台机组的功率轨迹（故障前出力保持至低水位保护跳机）",
                 fontsize=9.5, loc="left")
    ax.grid(ls=":", lw=0.6, alpha=0.6)
    ax.legend(fontsize=7, loc="upper right", frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=190)
    plt.close(fig)


def fig_level(runs: dict, path: str) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 3.8))
    for name, r in runs.items():
        c = COLORS.get(name, "#555555")
        m = load_fleet()[name].params
        ex = [l - m.basin_level_trip_m for l in r.level_m]
        t = [x / 3600.0 for x in r.t_s]
        ax.plot(t, ex, color=c, lw=1.3, label=f"{name}（跳机水位 {m.basin_level_trip_m:.2f} m）")
    ax.axhline(0, color="#c0392b", lw=1.0, ls="--")
    ax.text(0.2, 0.06, "跳机水位（余量为 0）", color="#c0392b", fontsize=7.5)
    ax.set_xlabel("时间 (h)", fontsize=8)
    ax.set_ylabel("池位高于跳机水位的余量 (m)", fontsize=8)
    ax.set_title("集水池水位余量耗尽过程：斜率 = 该机组当时的耗水强度（出力越大越陡）",
                 fontsize=9.5, loc="left")
    ax.grid(ls=":", lw=0.6, alpha=0.6)
    ax.legend(fontsize=7, frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=190)
    plt.close(fig)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    df = pd.read_csv(os.path.join(OUT, "trip_sequence.csv"))
    prof = pd.read_csv(os.path.join(OUT, "fleet_power_profile.csv"))
    _, runs = run_fleet(quiet=True)
    fig_gantt(df, os.path.join(OUT, "fig_trip_sequence.png"), 24.0)
    fig_power(prof, df, os.path.join(OUT, "fig_power_trace.png"))
    fig_level(runs, os.path.join(OUT, "fig_level_trace.png"))
    print("图已写出 →", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
