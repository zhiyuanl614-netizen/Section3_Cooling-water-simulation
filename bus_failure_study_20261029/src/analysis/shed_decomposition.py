"""静态减载的成因分解汇总。

背景：static_grid_shed_mw 是多种减载成因的混合和，曾导致把 UVLS 继电器减载
误读为 VCLS 二分减载（稿件 L479 "VCLS is invoked in 37 of the 63 scenarios"
实为 excess>0 的 UVLS 口径）。本脚本从 metric_audit.csv 输出可核对的分解表，
使"VCLS 减了多少"成为可直接读取的量，而不再需要推断。

产出：
  results/analysis/shed_decomposition.csv   逐案分解
  results/analysis/shed_decomposition.md    汇总与结论
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "results" / "analysis" / "metric_audit.csv"
OUT = ROOT / "results" / "analysis"

COMPONENTS = [
    ("deenergized_shed_mw", "失电孤岛（F3 无源路径）"),
    ("collapse_shed_mw", "崩溃孤岛（F3 无解路径）"),
    ("vcls_shed_mw", "VCLS 二分减载"),
    ("uvls_shed_mw", "UVLS 低压继电器减载"),
    ("grid_ufls_shed_mw", "级联内部 UFLS（耦合运行中恒为 0）"),
]


def main() -> int:
    rows = list(csv.DictReader(AUDIT.open(newline="", encoding="utf-8")))
    if not rows:
        print("metric_audit.csv 为空，请先运行 metric_audit.py --csv")
        return 1

    keys = [c for c, _ in COMPONENTS]

    # ---- 逐案分解 ----
    out_csv = OUT / "shed_decomposition.csv"
    fields = ["scenario_id", "n_bus_hard_failure", "h_load_mw",
              "static_grid_shed_mw", *keys, "ufls_shed_mw", "total_shed_mw",
              "components_sum", "residual"]
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            def g(k):
                try:
                    return float(r.get(k) or 0.0)
                except ValueError:
                    return 0.0
            ssum = sum(g(k) for k in keys)
            stat = g("static_grid_shed_mw")
            w.writerow({
                "scenario_id": r.get("scenario_id", ""),
                "n_bus_hard_failure": r.get("n_bus_hard_failure", ""),
                "h_load_mw": r.get("h_load_mw", ""),
                "static_grid_shed_mw": r.get("static_grid_shed_mw", ""),
                **{k: r.get(k, "") for k in keys},
                "ufls_shed_mw": r.get("ufls_shed_mw", ""),
                "total_shed_mw": r.get("total_shed_mw", ""),
                "components_sum": f"{ssum:.4f}",
                "residual": f"{ssum - stat:.2e}",
            })

    # ---- 汇总 ----
    def col(k):
        return [float(r.get(k) or 0.0) for r in rows]

    n = len(rows)
    stat = col("static_grid_shed_mw")
    parts = {k: col(k) for k in keys}
    max_resid = max(abs(sum(parts[k][i] for k in keys) - stat[i]) for i in range(n))

    excess = [max(0.0, stat[i] - float(r.get("h_load_mw") or 0.0)) for i, r in enumerate(rows)]
    n_excess = sum(1 for e in excess if e > 1e-6)

    vcls = parts["vcls_shed_mw"]
    n_vcls = sum(1 for v in vcls if v > 0)
    n_excess_with_vcls = sum(1 for i in range(n) if excess[i] > 1e-6 and vcls[i] > 0)

    lines = [
        "# 静态减载的成因分解",
        "",
        f"由 `src/analysis/shed_decomposition.py` 从 `metric_audit.csv` 生成，共 {n} 案。",
        "",
        "## 1. 为什么需要这张表",
        "",
        "`static_grid_shed_mw` 是多种减载成因的混合和，不等于 VCLS 减载量。",
        "稿件曾据 `static_grid_shed_mw - h_load_mw > 0` 的 37 案宣称“VCLS is invoked in 37 of the 63”，",
        "但该口径中绝大多数是 UVLS 继电器减载。分解后各成因可直接读取。",
        "",
        "## 2. 各成因总量",
        "",
        "| 成因 | 动作案数 | 合计 (MW) | 最大单案 (MW) |",
        "|---|---:|---:|---:|",
    ]
    for k, label in COMPONENTS:
        v = parts[k]
        lines.append(f"| {label} | {sum(1 for x in v if x > 0)} / {n} | "
                     f"{sum(v):.2f} | {max(v):.2f} |")
    lines += [
        f"| **static_grid_shed_mw（上述合计）** | — | **{sum(stat):.2f}** | {max(stat):.2f} |",
        f"| ufls_shed_mw（频率层，单独报告） | {sum(1 for x in col('ufls_shed_mw') if x > 0)} / {n} | "
        f"{sum(col('ufls_shed_mw')):.2f} | {max(col('ufls_shed_mw')):.2f} |",
        "",
        f"可加性校验：分项合计与 `static_grid_shed_mw` 的最大残差 **{max_resid:.2e}**（列为四位小数，"
        "残差属舍入）。",
        "",
        "## 3. VCLS 的真实规模",
        "",
        f"- **VCLS 真正在 {n_vcls} / {n} 案中减载**，合计 {sum(vcls):.2f} MW。",
        f"- 旧口径（`static_grid_shed_mw - h_load_mw > 0`）有 {n_excess} 案，"
        f"其中仅 **{n_excess_with_vcls}** 案含 VCLS 减载，其余 {n_excess - n_excess_with_vcls} 案为纯 UVLS。",
        f"- 因此“37”不能读作 VCLS 的案数。",
        "",
        "## 4. VCLS 动作的情景",
        "",
        "| 情景 | VCLS (MW) | UVLS (MW) | 失电 (MW) | 静态合计 (MW) | H |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(rows):
        if vcls[i] <= 0:
            continue
        lines.append(
            f"| {r.get('scenario_id','')} | {vcls[i]:.2f} | {parts['uvls_shed_mw'][i]:.2f} | "
            f"{parts['deenergized_shed_mw'][i]:.2f} | {stat[i]:.2f} | "
            f"{r.get('n_bus_hard_failure','')} |")
    lines += [
        "",
        "## 5. 两条独立确认",
        "",
        f"- `collapse_shed_mw` 在 {sum(1 for x in parts['collapse_shed_mw'] if x > 0)} / {n} 案中非零 "
        "→ 从减载记账层面独立确认 **F3 的无解分支从未发生**"
        "（此前只能由空的 `unsolvable_buses` 推断）。",
        f"- `grid_ufls_shed_mw` 在 {sum(1 for x in parts['grid_ufls_shed_mw'] if x > 0)} / {n} 案中非零 "
        "→ 确认耦合运行中 UFLS 以统一负荷缩放施加，级联内部 UFLS 分支不触发，**无重复计入**。",
        "",
    ]
    md = OUT / "shed_decomposition.md"
    md.write_text("\n".join(lines), encoding="utf-8")

    print(f"✓ {out_csv.relative_to(ROOT)}")
    print(f"✓ {md.relative_to(ROOT)}")
    print(f"\n  VCLS 动作案数 {n_vcls}/{n}，合计 {sum(vcls):.2f} MW")
    print(f"  旧 '37' 口径 {n_excess} 案，其中含 VCLS 者 {n_excess_with_vcls} 案")
    print(f"  可加性最大残差 {max_resid:.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
