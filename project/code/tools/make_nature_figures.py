"""
nature-figure optimized manuscript figures (Applied Energy draft v0.4).

Backend: Python / matplotlib (exclusive).
Exports: PDF + SVG + PNG; multi-panel figures run alignment gate before save.

Contracts (working notes):
  Fig.3 — Makeup interruption is progressive & policy-sensitive (inventory hero).
  Fig.4 — Pump-outage trip timing depends on thermal/flow lags (C2).
  Fig.6 — Cascading requires common-mode dual-unit capability loss.
  Fig.7 — K_tower/f_cl ≪ inventory modulators under U1 OAT.
  Fig.8 — Instant-trip outage shapes overstate incremental unserved energy here.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = Path.home() / ".codex" / "skills" / "nature-figure" / "scripts"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(SKILL_SCRIPTS))

from audit_panel_alignment import (  # noqa: E402
    PanelAlignmentError,
    require_matplotlib_panel_alignment,
)
from cooling.prototype_500mw import WetRecircPrototype500  # noqa: E402
from cooling.scale import scale_prototype_to_unit  # noqa: E402
from scenarios.framework_coupling import run_framework_scenario  # noqa: E402

OUT = ROOT / "docs" / "figures" / "nature"
QA = OUT / "qa"

# Restrained family: neutral + signal + accent (print-safe; not rainbow)
PALETTE = {
    "ink": "#272727",
    "mute": "#767676",
    "grid": "#CFCECE",
    "s1a": "#0F4D92",  # hero / isolate+ride
    "s1b": "#42949E",  # maintain
    "c1": "#B64342",  # hold-load
    "dyn": "#0F4D92",
    "qs": "#B64342",
    "ok": "#8BCF8B",
    "bad": "#B64342",
    "fill": "#E8EEF4",
    "fill2": "#DDF3DE",
    "fill3": "#F0E0D0",
}

MM = 1 / 25.4  # inch per mm


def _rc() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.labelsize": 7,
            "axes.titlesize": 7.5,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "legend.fontsize": 6.5,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "axes.edgecolor": PALETTE["ink"],
            "axes.labelcolor": PALETTE["ink"],
            "xtick.color": PALETTE["ink"],
            "ytick.color": PALETTE["ink"],
            # Grid off by default: collision auditor flags legend/label vs grid strokes.
            "axes.grid": False,
            "legend.frameon": False,
            "figure.dpi": 150,
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
        }
    )


def _label(ax, letter: str) -> None:
    ax.text(
        0.0,
        1.02,
        letter,
        transform=ax.transAxes,
        fontsize=8,
        fontweight="bold",
        va="bottom",
        ha="left",
        color=PALETTE["ink"],
        clip_on=False,
    )


def _export(
    fig,
    stem: str,
    *,
    multipanel: bool = False,
    alignment_options: dict | None = None,
) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    base = OUT / stem
    fig.canvas.draw()
    if multipanel:
        opts = dict(alignment_options or {})
        require_matplotlib_panel_alignment(
            fig,
            json_out=QA / f"{stem}.alignment.json",
            overlay_svg=QA / f"{stem}.alignment.svg",
            tolerance_pt=1.5,
            gutter_tolerance_pt=1.5,
            require_panel_labels=False,
            strict=True,
            **opts,
        )
    for ext in ("pdf", "svg", "png"):
        fig.savefig(base.with_suffix(f".{ext}"))
    plt.close(fig)
    return base.with_suffix(".pdf")


def _box(ax, xy, w, h, text, fc, fs=6.5):
    ax.add_patch(
        FancyBboxPatch(
            xy,
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.05",
            facecolor=fc,
            edgecolor=PALETTE["ink"],
            linewidth=0.9,
        )
    )
    ax.text(
        xy[0] + w / 2,
        xy[1] + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        color=PALETTE["ink"],
        linespacing=1.2,
    )


def _arrow(ax, p0, p1, color=None):
    ax.add_patch(
        FancyArrowPatch(
            p0,
            p1,
            arrowstyle="-|>",
            mutation_scale=9,
            lw=0.95,
            color=color or PALETTE["mute"],
            shrinkA=0.5,
            shrinkB=0.5,
        )
    )


def _ts(scenario_id: str):
    return run_framework_scenario(scenario_id).units[0].timeseries


# ---------------------------------------------------------------------------
# Fig. 1 schematic — single panel
# ---------------------------------------------------------------------------
def fig1() -> Path:
    fig, ax = plt.subplots(figsize=(180 * MM, 48 * MM))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 4.8)
    ax.axis("off")
    # Labels sit below nodes so box strokes never clip glyphs (collision audit).
    nodes = [
        (0.3, "Contingency", PALETTE["fill"]),
        (2.85, "Inventory/Qcw", PALETTE["fill"]),
        (5.4, "Tower/cond.", PALETTE["fill"]),
        (7.95, "Backpressure", PALETTE["fill"]),
        (10.5, "Protection", PALETTE["fill2"]),
        (13.05, "Pavail(t)", PALETTE["fill2"]),
        (15.6, "IEEE 39", PALETTE["fill3"]),
    ]
    w, h, y = 1.9, 1.35, 2.35
    for x, t, fc in nodes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.01,rounding_size=0.04",
                facecolor=fc,
                edgecolor=PALETTE["ink"],
                linewidth=0.8,
            )
        )
        ax.text(x + w / 2, y - 0.35, t, ha="center", va="top", fontsize=6.5, color=PALETTE["ink"])
    for i in range(len(nodes) - 1):
        _arrow(
            ax,
            (nodes[i][0] + w, y + h / 2),
            (nodes[i + 1][0], y + h / 2),
            PALETTE["s1a"] if i >= 4 else PALETTE["mute"],
        )
    ax.text(
        9,
        0.35,
        "Policies: ride-down vs hold-load · blowdown isolate vs maintain · C2 dynamic vs quasi-static",
        ha="center",
        fontsize=6.5,
        color=PALETTE["mute"],
    )
    return _export(fig, "fig1_causal_chain")


# ---------------------------------------------------------------------------
# Fig. 2 architecture — single panel
# ---------------------------------------------------------------------------
def fig2() -> Path:
    fig, ax = plt.subplots(figsize=(180 * MM, 55 * MM))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 5.5)
    ax.axis("off")
    layers = [
        (4.15, "Event · IEEE 39 successive overload removal", PALETTE["fill3"], "instant"),
        (3.15, "Fast · Qcw lag (tau_pump=10 s), vacuum delay", "#F6CFCB", "seconds"),
        (2.15, "Intermediate · Tin, Tsat, SOP, delivered P", PALETTE["fill2"], "dt=1 s"),
        (1.15, "Slow · basin inventory; optional wet-bulb (tau_wb=900 s)", PALETTE["fill"], "min–h"),
    ]
    for y, text, fc, tag in layers:
        _box(ax, (0.4, y), 13.2, 0.85, text, fc, fs=7)
        ax.text(14.0, y + 0.42, tag, va="center", fontsize=6.5, color=PALETTE["mute"])
    _box(
        ax,
        (0.4, 0.2),
        17.2,
        0.7,
        "C2 (required): zero thermal & pump time constants → compare S2 vs S2qs",
        "#FFF7ED",
        fs=6.5,
    )
    return _export(fig, "fig2_multitimescale_architecture")


# ---------------------------------------------------------------------------
# Fig. 3 makeup — quantitative grid 2×2
# ---------------------------------------------------------------------------
def fig3() -> Path:
    s1a, s1b, c1 = _ts("S1a"), _ts("S1b"), _ts("C1_hold")
    model = scale_prototype_to_unit(WetRecircPrototype500(), 600.0, gen_id="Bus33")
    series = (
        (s1a, "S1a isolate+ride", PALETTE["s1a"], "-"),
        (s1b, "S1b maintain+ride", PALETTE["s1b"], "--"),
        (c1, "C1 isolate+hold", PALETTE["c1"], ":"),
    )

    fig, axes = plt.subplots(2, 2, figsize=(180 * MM, 125 * MM), sharex=True)
    letters = "abcd"

    ax = axes[0, 0]
    for ts, lab, c, ls in series:
        ax.plot(ts.t_h, ts.level_m, color=c, ls=ls, lw=1.35, label=lab)
    ax.axhline(model.basin_level_trip_m, color=PALETTE["mute"], ls="-.", lw=0.7)
    ax.set_ylabel("Basin level (m)")

    ax = axes[0, 1]
    for ts, lab, c, ls in series:
        ax.plot(ts.t_h, ts.qcw_frac, color=c, ls=ls, lw=1.35)
    ax.set_ylabel("CW flow fraction")
    ax.set_ylim(0.78, 1.02)

    ax = axes[1, 0]
    for ts, lab, c, ls in series:
        ax.plot(ts.t_h, ts.backpressure_kpa, color=c, ls=ls, lw=1.35)
    ax.axhline(model.pb_trip_kpa, color=PALETTE["mute"], ls="-.", lw=0.7)
    ax.set_ylabel("Backpressure (kPa)")

    ax = axes[1, 1]
    for ts, lab, c, ls in series:
        ax.plot(ts.t_h, ts.p_avail_mw, color=c, ls=ls, lw=1.5)
        if ts.t_trip_h is not None:
            ax.axvline(ts.t_trip_h, color=c, ls=":", lw=0.7, alpha=0.85)
    ax.set_ylabel("Delivered power (MW)")
    ax.set_xlim(0, 8)

    for ax, letter in zip(axes.ravel(), letters):
        _label(ax, letter)
        ax.set_xlabel("")

    handles, labels_ = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels_,
        loc="upper center",
        ncol=3,
        bbox_to_anchor=(0.5, 1.02),
        frameon=False,
        fontsize=6.5,
        handlelength=2.4,
    )
    fig.supxlabel("Time after makeup interrupt (h)", fontsize=7, y=0.02)
    fig.tight_layout(pad=0.55, w_pad=0.85, h_pad=0.85, rect=(0, 0.05, 1, 0.94))
    return _export(fig, "fig3_makeup_trajectories", multipanel=True)


# ---------------------------------------------------------------------------
# Fig. 4 pump C2 — 1×2
# ---------------------------------------------------------------------------
def fig4() -> Path:
    s2, s2qs = _ts("S2"), _ts("S2qs")
    model = scale_prototype_to_unit(WetRecircPrototype500(), 600.0, gen_id="Bus33")
    fig, axes = plt.subplots(1, 2, figsize=(180 * MM, 70 * MM))

    ax = axes[0]
    ax.plot([t * 60 for t in s2.t_h], s2.backpressure_kpa, color=PALETTE["dyn"], lw=1.4, label="S2 dynamic")
    ax.plot(
        [t * 60 for t in s2qs.t_h],
        s2qs.backpressure_kpa,
        color=PALETTE["qs"],
        lw=1.3,
        ls="--",
        label="S2qs quasi-static",
    )
    ax.axhline(model.pb_trip_kpa, color=PALETTE["mute"], ls="-.", lw=0.7)
    ax.set_xlabel("Time after full pump outage (min)")
    ax.set_ylabel("Backpressure (kPa)")
    _label(ax, "a")

    ax = axes[1]
    ax.plot([t * 60 for t in s2.t_h], s2.p_avail_mw, color=PALETTE["dyn"], lw=1.4, label="S2")
    ax.plot([t * 60 for t in s2qs.t_h], s2qs.p_avail_mw, color=PALETTE["qs"], lw=1.3, ls="--", label="S2qs")
    ax.set_xlabel("Time after full pump outage (min)")
    ax.set_ylabel("Delivered power (MW)")
    _label(ax, "b")

    handles, labels_ = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels_,
        loc="lower center",
        ncol=2,
        bbox_to_anchor=(0.5, -0.02),
        frameon=False,
        fontsize=6.5,
    )
    fig.text(
        0.5,
        1.01,
        f"Trip times: S2 {s2.t_trip_h*60:.2f} min; S2qs {s2qs.t_trip_h*60:.2f} min",
        ha="center",
        va="bottom",
        fontsize=6.5,
        color=PALETTE["mute"],
    )
    fig.tight_layout(pad=0.55, w_pad=1.0, rect=(0, 0.08, 1, 0.96))
    return _export(fig, "fig4_pump_c2", multipanel=True)


# ---------------------------------------------------------------------------
# Fig. 5 partial / wet-bulb — single
# ---------------------------------------------------------------------------
def fig5() -> Path:
    rows = {
        r["scenario_id"]: r
        for r in csv.DictReader(open(ROOT / "examples" / "framework_cascade_coupling_summary.csv", encoding="utf-8"))
    }
    labels = ["S3b (−30%)", "S3a (−50%)", "S4 (+6 K)", "S0 healthy"]
    keys = ["S3b", "S3a", "S4", "S0"]
    vals = [float(rows[k]["p_final_mw"]) for k in keys]
    colors = [PALETTE["s1b"], PALETTE["s1a"], PALETTE["mute"], PALETTE["grid"]]

    fig, ax = plt.subplots(figsize=(89 * MM, 70 * MM))
    bars = ax.bar(labels, vals, color=colors, edgecolor=PALETTE["ink"], linewidth=0.6, width=0.68)
    ax.axhline(600.0, color=PALETTE["mute"], ls="--", lw=0.8)
    ax.set_ylabel("End-of-horizon power (MW)")
    ax.set_ylim(0, 720)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 18,
            f"{v:.0f}",
            ha="center",
            va="bottom",
            fontsize=6.5,
            color=PALETTE["ink"],
            clip_on=False,
        )
    ax.tick_params(axis="x", labelsize=6)
    return _export(fig, "fig5_partial_wetbulb")


# ---------------------------------------------------------------------------
# Fig. 6 cascade — single hero bars (interpretation stays in caption)
# ---------------------------------------------------------------------------
def fig6() -> Path:
    rows = {
        r["scenario_id"]: r
        for r in csv.DictReader(open(ROOT / "examples" / "framework_cascade_coupling_summary.csv", encoding="utf-8"))
    }
    ids = ["G1", "G2", "G3", "G4"]
    labels = ["G1\nsingle", "G2\ndual pump", "G3\ndual makeup", "G4\nmixed"]
    n_lines = [int(float(rows[i]["n_lines_removed"] or 0)) for i in ids]
    colors = [PALETTE["mute"] if n == 0 else PALETTE["bad"] for n in n_lines]

    fig, ax = plt.subplots(figsize=(120 * MM, 70 * MM))
    bars = ax.bar(labels, n_lines, color=colors, edgecolor=PALETTE["ink"], linewidth=0.6, width=0.65)
    ax.set_ylabel("Overloaded lines removed")
    ax.set_ylim(0, 16.5)
    for b, v in zip(bars, n_lines):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 0.55,
            str(v),
            ha="center",
            va="bottom",
            fontsize=7,
            fontweight="bold",
            color=PALETTE["ink"],
            clip_on=False,
        )
    return _export(fig, "fig6_cascade_outlet")


# ---------------------------------------------------------------------------
# Fig. 7 U1 tornado — single
# ---------------------------------------------------------------------------
def fig7() -> Path:
    rows = list(csv.DictReader(open(ROOT / "examples" / "u1_sensitivity_summary.csv", encoding="utf-8")))
    s1 = [r for r in rows if r["case_id"] == "S1a" and r["level"] in {"low", "high"}]
    params = []
    seen = set()
    for r in s1:
        p = r["param"]
        if p in seen:
            continue
        seen.add(p)
        lo = next(x for x in s1 if x["param"] == p and x["level"] == "low")
        hi = next(x for x in s1 if x["param"] == p and x["level"] == "high")
        dlo = float(lo["delta_t_trip_min"] or 0.0)
        dhi = float(hi["delta_t_trip_min"] or 0.0)
        params.append((p, dlo, dhi, max(abs(dlo), abs(dhi))))
    params.sort(key=lambda t: t[3])

    # Plain labels keep PDF glyph sizes ≥5 pt (mathtext subscripts often fall below).
    name = {
        "tower_characteristic_mult": "K_tower",
        "condenser_cleanliness": "f_cl",
        "evap_heat_fraction": "f_evap",
        "basin_area_m2_scale": "Basin area scale",
        "pb_trip_kpa": "pb_trip",
    }

    fig, ax = plt.subplots(figsize=(120 * MM, 75 * MM))
    for i, (p, dlo, dhi, _) in enumerate(params):
        lo, hi = (dlo, dhi) if dlo <= dhi else (dhi, dlo)
        ax.barh(i, hi - lo, left=lo, height=0.32, color=PALETTE["grid"], alpha=0.55, edgecolor="none", zorder=1)
        ax.plot([dlo, dhi], [i, i], color=PALETTE["ink"], lw=1.0, zorder=2)
        ax.scatter([dlo], [i], color="#E9A6A1", s=28, zorder=3, label="Low" if i == 0 else None)
        ax.scatter([dhi], [i], color=PALETTE["s1a"], s=28, zorder=3, label="High" if i == 0 else None)
    ax.axvline(0, color=PALETTE["ink"], lw=0.8)
    ax.set_yticks(range(len(params)))
    ax.set_yticklabels([name.get(p, p) for p, *_ in params], fontsize=6.5)
    ax.set_xlabel("Delta t_trip vs S1a baseline (min)", fontsize=7)
    handles, labels_ = ax.get_legend_handles_labels()
    fig.legend(handles, labels_, loc="lower center", ncol=2, bbox_to_anchor=(0.55, -0.02), fontsize=6.5)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    return _export(fig, "fig7_u1_tornado")


# ---------------------------------------------------------------------------
# Fig. 8 black-box — single
# ---------------------------------------------------------------------------
def fig8() -> Path:
    rows = [
        r
        for r in csv.DictReader(open(ROOT / "examples" / "model_comparison.csv", encoding="utf-8"))
        if r["scope"] == "IEEE39_G33_grid"
    ]
    order = [
        "instant_trip",
        "fixed_holdup_trip",
        "linear_to_min_then_trip",
        "simplified_level_band",
        "mechanistic_hold_load",
        "mechanistic_ride_down",
    ]
    label_map = {
        "instant_trip": "Instant\ntrip",
        "fixed_holdup_trip": "Fixed\nhold-up",
        "linear_to_min_then_trip": "Linear\nderate",
        "simplified_level_band": "Level\nband",
        "mechanistic_hold_load": "Mechanistic\nhold-load",
        "mechanistic_ride_down": "Mechanistic\nride-down",
    }
    by = {r["benchmark"]: r for r in rows}
    vals = [float(by[k]["incremental_unserved_energy_0_8h_mwh"]) for k in order]
    colors = [
        PALETTE["bad"],
        "#E9A6A1",
        "#E9A6A1",
        PALETTE["mute"],
        PALETTE["s1a"],
        "#3775BA",
    ]

    fig, ax = plt.subplots(figsize=(120 * MM, 75 * MM))
    bars = ax.bar([label_map[k] for k in order], vals, color=colors, edgecolor=PALETTE["ink"], linewidth=0.6)
    ax.set_ylabel("0–8 h incremental unserved energy (MWh)")
    ax.set_ylim(0, max(vals) * 1.18)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + max(vals) * 0.03,
            f"{v:.0f}",
            ha="center",
            va="bottom",
            fontsize=6.5,
            color=PALETTE["ink"],
            clip_on=False,
        )
    ax.tick_params(axis="x", labelsize=6)
    return _export(fig, "fig8_blackbox_unserved")


# ---------------------------------------------------------------------------
# Graphical abstract — schematic + inset bar (asymmetric; exempt width)
# ---------------------------------------------------------------------------
def fig_ga() -> Path:
    fig = plt.figure(figsize=(180 * MM, 55 * MM))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 1.0], wspace=0.35)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])

    ax0.set_xlim(0, 10)
    ax0.set_ylim(0, 4)
    ax0.axis("off")
    items = [
        (0.15, "Contingency"),
        (2.55, "Cold-end\nODE + trip"),
        (4.95, "Pavail(t)"),
        (7.35, "IEEE 39\ncascade?"),
    ]
    for x, t in items:
        _box(ax0, (x, 1.35), 2.0, 1.6, t, PALETTE["fill"] if x < 6 else PALETTE["fill3"], fs=7)
    for i in range(3):
        _arrow(ax0, (items[i][0] + 2.0, 2.15), (items[i + 1][0], 2.15), PALETTE["s1a"])
    ax0.text(
        5,
        0.45,
        "S1a 5.07 h · S2 0.47 min · dual-unit cascade 13 lines · single-unit 0",
        ha="center",
        fontsize=6.5,
        color=PALETTE["mute"],
    )
    _label(ax0, "a")

    rows = {
        r["scenario_id"]: r
        for r in csv.DictReader(open(ROOT / "examples" / "framework_cascade_coupling_summary.csv", encoding="utf-8"))
    }
    ax1.bar(
        ["G1", "G2"],
        [int(float(rows["G1"]["n_lines_removed"] or 0)), int(float(rows["G2"]["n_lines_removed"] or 0))],
        color=[PALETTE["mute"], PALETTE["bad"]],
        edgecolor=PALETTE["ink"],
        width=0.55,
    )
    ax1.set_ylabel("Lines removed")
    ax1.set_ylim(0, 15)
    ax1.set_title("Common-mode", fontsize=7)
    _label(ax1, "b")

    fig.subplots_adjust(left=0.04, right=0.98, bottom=0.12, top=0.88, wspace=0.35)
    return _export(
        fig,
        "graphical_abstract",
        multipanel=True,
        alignment_options={
            "exemptions": [
                {
                    "panels": ["a", "b"],
                    "checks": ["panel-width", "column"],
                    "reason": "intentional schematic+inset unequal width_ratios for graphical abstract",
                }
            ],
        },
    )


def main() -> int:
    _rc()
    writers = [fig_ga, fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8]
    for fn in writers:
        try:
            path = fn()
            print("OK", path)
        except PanelAlignmentError as exc:
            print("ALIGN FAIL", fn.__name__)
            print(exc)
            return 1
    # Sync primary PNG names expected by manuscript into docs/figures/
    pub = ROOT / "docs" / "figures"
    mapping = {
        "graphical_abstract.png": "graphical_abstract.png",
        "fig1_causal_chain.png": "fig1_causal_chain.png",
        "fig2_multitimescale_architecture.png": "fig2_multitimescale_architecture.png",
        "fig3_makeup_trajectories.png": "fig3_makeup_trajectories.png",
        "fig4_pump_c2.png": "fig4_pump_c2.png",
        "fig5_partial_wetbulb.png": "fig5_partial_wetbulb.png",
        "fig6_cascade_outlet.png": "fig6_cascade_g1_g2.png",
        "fig7_u1_tornado.png": "fig7_u1_tornado.png",
        "fig8_blackbox_unserved.png": "fig8_blackbox_unserved.png",
    }
    for src_name, dst_name in mapping.items():
        src = OUT / src_name
        if src.exists():
            dst = pub / dst_name
            dst.write_bytes(src.read_bytes())
            print("sync", dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
