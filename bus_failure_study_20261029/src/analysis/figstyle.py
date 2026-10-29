"""学术绘图样式与共用工具。

设计原则（面向期刊/会议双栏排版）：
1. 字体嵌入 SVG，PNG 300 dpi，满足印刷要求；
2. 灰度可辨：线型与标记形状冗余编码，不单靠颜色区分；
3. 色盲友好：采用 Okabe–Ito 配色；
4. 单位进入轴标签而非标题；
5. 图例无边框，网格线弱化，仅保留必要轴脊。
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---------------------------------------------------------------- 字体
# 环境中的 Noto Sans CJK 注册名带 "JP" 后缀，但字形集覆盖简体中文。
_CJK_DIR = Path("/usr/share/fonts/opentype/noto")
_CJK_CANDIDATES = [
    _CJK_DIR / "NotoSansCJK-Regular.ttc",
    _CJK_DIR / "NotoSansCJK-Bold.ttc",
]
for _f in _CJK_CANDIDATES:
    if _f.exists():
        font_manager.fontManager.addfont(str(_f))

_FAMILY = "Noto Sans CJK JP"
if _FAMILY not in {f.name for f in font_manager.fontManager.ttflist}:
    _FAMILY = "DejaVu Sans"

# ---------------------------------------------------------------- 配色
# Okabe–Ito：色盲友好，且在灰度下仍可由线型/形状区分。
OKABE = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "sky": "#56B4E9",
    "yellow": "#F0E442",
    "black": "#000000",
}
GREY = "#4D4D4D"
LIGHT_GREY = "#B3B3B3"

# 六机组配色：按容量降序分配，兼顾灰度与色盲可辨。
UNIT_COLOR = {
    "G1": "#0072B2",   # 80 MW
    "G2": "#E69F00",   # 80 MW
    "G13": "#009E73",  # 40 MW
    "G22": "#D55E00",  # 50 MW
    "G23": "#CC79A7",  # 30 MW
    "G27": "#000000",  # 55 MW
}
# 冗余标记形状：保证灰度打印与色觉障碍下可区分。
UNIT_MARKER = {
    "G1": "o",
    "G2": "s",
    "G13": "^",
    "G22": "D",
    "G23": "v",
    "G27": "P",
}
UNIT_ORDER = ["G1", "G2", "G13", "G22", "G23", "G27"]

K_COLOR = {
    "K1": "#0072B2",
    "K2": "#56B4E9",
    "K3": "#009E73",
    "K4": "#E69F00",
    "K5": "#D55E00",
    "K6": "#CC79A7",
}

RC = {
    "font.family": _FAMILY,
    "font.size": 8.5,
    "axes.titlesize": 9.5,
    "axes.labelsize": 9,
    "axes.titleweight": "bold",
    "axes.labelcolor": "#1A1A1A",
    "axes.edgecolor": "#3F3F3F",
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "axes.axisbelow": True,
    "axes.prop_cycle": mpl.cycler(color=list(OKABE.values())),
    "grid.color": "#D9D9D9",
    "grid.linewidth": 0.5,
    "grid.alpha": 0.75,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.size": 3.0,
    "ytick.major.size": 3.0,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "xtick.color": "#3F3F3F",
    "ytick.color": "#3F3F3F",
    "legend.fontsize": 8,
    "legend.frameon": False,
    "legend.handlelength": 2.2,
    "legend.columnspacing": 1.2,
    "legend.labelspacing": 0.4,
    "lines.linewidth": 1.4,
    "lines.markersize": 4.0,
    "patch.linewidth": 0.7,
    "figure.dpi": 110,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
    "svg.fonttype": "none",   # 字体以文本嵌入，期刊可编辑
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "mathtext.fontset": "dejavusans",
    "axes.unicode_minus": False,
}


def apply_style():
    """应用全局样式。"""
    mpl.rcParams.update(RC)


def clean_axes(ax, grid_axis="y"):
    """弱化视觉噪声：只保留左、下轴脊。"""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid_axis in ("y", "both"):
        ax.grid(True, axis="y")
        ax.grid(False, axis="x")
    elif grid_axis in ("x", "both"):
        ax.grid(True, axis="x")
        ax.grid(False, axis="y")
    elif grid_axis == "none":
        ax.grid(False)


def save(fig, out_dir, name, also_pdf=False, only_svg=False, png=False):
    """保存论文图。

    默认只输出 SVG：矢量、文字以文本嵌入（期刊可编辑）、无损缩放，
    是投稿与排版的优先格式。
    需追加位图时传 png=True（300 dpi），需 PDF 时传 also_pdf=True。
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if only_svg or not (png or also_pdf):
        exts = ("svg",)
    else:
        exts = ["svg"] + (["png"] if png else []) + (["pdf"] if also_pdf else [])
    paths = []
    for ext in exts:
        p = out_dir / f"{name}.{ext}"
        fig.savefig(p)
        paths.append(p)
    return paths


def panel_label(ax, text, dx=-0.02, dy=1.04):
    """左上角面板标记 (a)(b)(c)。"""
    ax.text(
        dx, dy, text, transform=ax.transAxes,
        fontsize=10, fontweight="bold", va="bottom", ha="left",
    )