"""
metrics.py — 母线服务/失效指标口径与汇总
==========================================================
本模块集中定义"母线服务状态 → 严重度 → 后果 → 可信度"四层指标，
供 coupled.py 写入汇总表，并供分析脚本复用。所有口径在此单点定义，
避免同一指标在多处实现产生分歧。

分层
----
L1 服务状态（互斥、可追溯，单条母线最终归属一个状态）
      F3  孤岛无在运电源 —— 唯一硬失供端点
      H = 1[F3]
      （v3 起移除 F1 电压越限 / F2a 严重低压 / F2b 潮流发散的失效语义；
        电压与发散仅作为过程量 / 数值失败端点处理）

L2 严重度（多口径并列，不强行合一）
      H_count  硬失供母线条数
      H_load   负荷加权硬失供比例 ΣP_b(H)/ΣP —— 与 H_count 并列报告
      H_buses  硬失供母线集合

L3 时间
      t_first_H_s  首次出现硬失供的系统时刻（相对 t=0 断水）
      observation_window_h  实际观察时长（显式披露删失）

L4 后果（三个量分列，语义互不替代）
      shed_action_total_mw  各阶段切负荷动作量累计（默认保留的旧口径）
      shed_peak_mw          任一阶段的最大累计切负荷量
      ufls_shed_mw          时域 UFLS 切负荷
      说明：三者均不等于 EENS/MWh；本模型不输出能量型未供电量。

L5 可信度
      solver_converged / n_singular_warnings / n_divergence_warnings
      数值健康度审计：H=F3 为纯拓扑判定不依赖潮流解，但切负荷/频率等
      次级量受求解质量影响，故与结果一并披露。
"""
from __future__ import annotations

import csv
import warnings
from contextlib import contextmanager
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BUS_CSV = ROOT / "data" / "grid" / "IEEE30" / "bus.csv"


# ---------------------------------------------------------------- 负荷权重
def bus_load_mw() -> dict[int, float]:
    """返回 {bus_id: 基准有功负荷 MW}，用于负荷加权严重度。"""
    with BUS_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {int(float(r["BUS_I"])): float(r["PD_MW"]) for r in rows}


LOAD_MW = bus_load_mw()
TOTAL_LOAD_MW = sum(LOAD_MW.values())


def load_weighted_hard_loss(hard_buses) -> tuple[float, float]:
    """返回 (H_load 比例 0..1, 硬失供母线承载负荷 MW)。"""
    lost = sum(LOAD_MW.get(int(b), 0.0) for b in hard_buses)
    return (lost / TOTAL_LOAD_MW if TOTAL_LOAD_MW > 0 else 0.0), lost


# ------------------------------------------------- 收敛性审计（数值可信度）
class ConvergenceAudit:
    """在求解期间统计奇异矩阵/除零告警。

    数值健康度审计：H=F3 由拓扑扫描判定，不依赖潮流求解；但切负荷量、
    频率最低点等次级量受求解器数值质量影响，故把告警计数直接带入结果表，
    与 H 一并披露（未收敛时次级量应视为条件性结果）。
    """

    _BAD = ("MatrixRankWarning", "RuntimeWarning")

    def __init__(self) -> None:
        self.n_singular = 0
        self.n_divergence = 0
        self.categories: dict[str, int] = {}

    @contextmanager
    def track(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            yield
        for w in caught:
            name = type(w.message).__name__
            self.categories[name] = self.categories.get(name, 0) + 1
            if name == "MatrixRankWarning":
                self.n_singular += 1
            elif name == "RuntimeWarning":
                self.n_divergence += 1

    @property
    def clean(self) -> bool:
        return self.n_singular == 0 and self.n_divergence == 0

    def fields(self) -> dict:
        return dict(
            solver_converged=self.clean,
            n_singular_warnings=self.n_singular,
            n_divergence_warnings=self.n_divergence,
            solver_warning_categories=";".join(
                f"{k}={v}" for k, v in sorted(self.categories.items())),
            solver_warning_note=(
                "numerical-health audit of the AC power-flow path that computes "
                "shedding and frequency; False means internal convergence is NOT "
                "proven and derived secondary quantities are conditional on this "
                "limitation (H=F3 itself is a topological determination)"),
        )


# ------------------------------------------------------------ 指标口径常量
METRIC_DEFINITIONS = dict(
    hard_failure_definition=(
        "modelled_hard_service_loss: H = 1[F3_deenergized_only]; "
        "F1/F2a voltage states and F2b unresolved AC collapse do NOT count; "
        "NOT physical equipment damage"),
    h_load_definition=(
        "load-weighted hard-service-loss ratio = sum(PD_MW over H buses) / sum(PD_MW); "
        "reported alongside H_count because buses carry unequal load"),
    bfi_definition=(
        "bfi_hard = n_bus_hard_failure / n_bus_total, i.e. the HARD endpoint H=F3"),
    impact_class_definition=(
        "N3 = F3 only, i.e. aligned 1:1 with H>0; N0 = no hard service loss. "
        "Class is an operational label, not a severity rank, and is not "
        "interchangeable with H"),
    shed_semantics=(
        "shed_action_total_mw = sum of per-stage shed actions (legacy accounting, may "
        "exceed system load and is NOT an unserved-energy figure); "
        "shed_peak_mw = largest per-stage cumulative shed; "
        "neither is EENS/MWh; UFLS MW reported separately"),
    time_definition=(
        "t_first_H_s = elapsed seconds from t=0 makeup interruption to the first "
        "cascade stage that produced any F3 bus; blank if H=0"),
    degeneracy_definition=(
        "scenarios sharing the same (H_count, F3, shed_peak, f_nadir) tuple "
        "are metrically indistinguishable under this model; group_id marks them so "
        "they are not read as independent confirmations"),
)


def degeneracy_key(h_count: int, f3: int,
                   shed_peak: float, f_nadir: float) -> tuple:
    """用于识别指标退化的情景分组键（不含情景标识本身）。"""
    return (int(h_count), int(f3),
            round(float(shed_peak), 3), round(float(f_nadir), 3))


def severity_fields(hard_buses, n_bus_total: int,
                    f3: int, shed_peak: float) -> dict:
    """统一构造 L1/L2 严重度字段，避免各处重复实现。"""
    hard = sorted(int(b) for b in hard_buses)
    h_count = len(hard)
    h_load, h_load_mw = load_weighted_hard_loss(hard)
    return dict(
        n_bus_hard_failure=h_count,
        hard_failure_buses=";".join(str(b) for b in hard),
        h_load_ratio=round(h_load, 6),
        h_load_mw=round(h_load_mw, 4),
        n_f3_deenergized=int(f3),
        bfi_hard=round(h_count / n_bus_total, 6) if n_bus_total else 0.0,
        bfi_load=round(h_load, 6),
        shed_peak_mw=round(float(shed_peak), 4),
    )


def impact_class(h_count: int, f3: int) -> str:
    """N 类判定：N3 与 H 严格对齐（H=F3 唯一端点）。

    v3 简化：移除 F1/F2a 相关类别，N 类仅区分有无硬失供。
    """
    if h_count > 0 or f3:
        return "N3_hard_service_loss"
    return "N0_no_hard_service_loss"